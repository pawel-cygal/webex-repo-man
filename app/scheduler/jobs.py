# app/scheduler/jobs.py
import time
import schedule
from functools import partial
from webexteamssdk import WebexTeamsAPI
from .. import db
from ..models import ScheduledJob
from datetime import datetime
import pytz

def send_scheduled_message(app, job_id):
    """
    Fetches a job by its ID and sends the message to Webex.
    This function runs within the Flask application context.
    """
    with app.app_context():
        app.logger.info(f"Running job ID: {job_id}")
        job = ScheduledJob.query.get(job_id)
        if not job or not job.is_active:
            app.logger.warning(f"Job {job_id} not found or is inactive. Skipping.")
            return

        try:
            # Initialize API with the token from config
            api = WebexTeamsAPI(access_token=app.config['WEBEX_BOT_TOKEN'])
            
            message_to_send = job.message
            if job.mentions:
                tokens = [t.strip() for t in job.mentions.split(',') if t.strip()]
                for token in tokens:
                    if token.lower() == 'all':
                        message_to_send += " <@all>"
                    else:
                        message_to_send += f" <@personEmail:{token}|>"

            api.messages.create(roomId=job.channel.room_id, markdown=message_to_send)
            
            # Update last_run timestamp
            job.last_run = datetime.utcnow()
            db.session.commit()
            
            app.logger.info(f"Successfully sent message for job: {job.name}")
            
        except Exception as e:
            app.logger.error(f"Error sending message for job {job.id}: {e}")


def run_scheduler(app):
    """
    The main scheduler loop that runs in a background thread.
    """
    app.logger.info("Scheduler thread started.")
    
    # This loop will periodically re-read the jobs from the database
    # and update the schedule. This allows for dynamic updates without restarting the app.
    while True:
        with app.app_context():
            try:
                # Clear previous schedule
                schedule.clear()

                # Get all active jobs from the database
                jobs = ScheduledJob.query.filter_by(is_active=True).all()
                
                local_tz = datetime.now().astimezone().tzinfo

                for job in jobs:
                    # Create a timezone-aware datetime object for the job's scheduled time
                    user_tz = pytz.timezone(job.timezone)
                    hour, minute = map(int, job.schedule_time.split(':'))
                    
                    # Create a naive datetime, then localize it
                    now_in_user_tz = datetime.now(user_tz)
                    target_time_user_tz = now_in_user_tz.replace(hour=hour, minute=minute, second=0, microsecond=0)

                    # Convert to server's local time
                    target_time_local = target_time_user_tz.astimezone(local_tz)
                    schedule_time_str = target_time_local.strftime('%H:%M')

                    # Use partial to pass arguments to the job function
                    job_func = partial(send_scheduled_message, app=app, job_id=job.id)
                    
                    # Schedule the job based on its frequency
                    if job.frequency == 'daily':
                        schedule.every().day.at(schedule_time_str).do(job_func)
                    else:
                        # For 'monday', 'tuesday', etc.
                        getattr(schedule.every(), job.frequency).at(schedule_time_str).do(job_func)
                
                app.logger.info(f"Scheduler updated. {len(jobs)} jobs loaded.")

            except Exception as e:
                app.logger.error(f"Error loading jobs into scheduler: {e}")

        # Run any pending jobs
        schedule.run_pending()
        
        # Wait for a while before re-loading the schedule.
        # This determines how often the app checks for new/updated jobs.
        time.sleep(60)

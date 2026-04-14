# app/scheduler/jobs.py
import time
import schedule
from functools import partial
from webexteamssdk import WebexTeamsAPI
from .. import db
from ..models import ScheduledJob

def send_scheduled_message(app, job_id):
    """
    Fetches a job by its ID and sends the message to Webex.
    This function runs within the Flask application context.
    """
    with app.app_context():
        print(f"Running job ID: {job_id}")
        job = ScheduledJob.query.get(job_id)
        if not job or not job.is_active:
            print(f"Job {job_id} not found or is inactive. Skipping.")
            return

        try:
            # Initialize API with the token from config
            api = WebexTeamsAPI(access_token=app.config['WEBEX_BOT_TOKEN'])
            
            message_to_send = job.message
            if job.mentions:
                # Simple mention implementation, may need to be more robust
                mentioned_emails = [email.strip() for email in job.mentions.split(',')]
                for email in mentioned_emails:
                    message_to_send += f" <@personEmail:{email}|>"

            api.messages.create(roomId=job.channel.room_id, markdown=message_to_send)
            print(f"Successfully sent message for job: {job.name}")
            
            # TODO: Update last_run timestamp for the job
            
        except Exception as e:
            print(f"Error sending message for job {job.id}: {e}")


def run_scheduler(app):
    """
    The main scheduler loop that runs in a background thread.
    """
    print("Scheduler thread started.")
    
    # This loop will periodically re-read the jobs from the database
    # and update the schedule. This allows for dynamic updates without restarting the app.
    while True:
        with app.app_context():
            try:
                # Clear previous schedule
                schedule.clear()

                # Get all active jobs from the database
                jobs = ScheduledJob.query.filter_by(is_active=True).all()
                
                for job in jobs:
                    # Use partial to pass arguments to the job function
                    job_func = partial(send_scheduled_message, app=app, job_id=job.id)
                    
                    # Schedule the job based on its frequency
                    if job.frequency == 'daily':
                        schedule.every().day.at(job.schedule_time).do(job_func)
                    else:
                        # For 'monday', 'tuesday', etc.
                        getattr(schedule.every(), job.frequency).at(job.schedule_time).do(job_func)
                
                print(f"Scheduler updated. {len(jobs)} jobs loaded.")

            except Exception as e:
                print(f"Error loading jobs into scheduler: {e}")

        # Run any pending jobs
        schedule.run_pending()
        
        # Wait for a while before re-loading the schedule.
        # This determines how often the app checks for new/updated jobs.
        time.sleep(60)
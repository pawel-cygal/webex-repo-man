# app/scheduler/jobs.py
import time
import schedule
from webexteamssdk import WebexTeamsAPI
from app import db
from app.models import ScheduledJob

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
            
            # TODO: Add logic for mentions
            message_to_send = job.message

            api.messages.create(roomId=job.room_id, markdown=message_to_send)
            print(f"Successfully sent message for job: {job.name}")
            
            # TODO: Update last_run timestamp for the job
            
        except Exception as e:
            print(f"Error sending message for job {job.id}: {e}")


def run_scheduler(app):
    """
    The main scheduler loop that runs in a background thread.
    """
    print("Scheduler thread started.")
    
    # For now, we just add a dummy job to test.
    # In the final version, this will dynamically schedule jobs from the database.
    schedule.every(10).seconds.do(lambda: print("Scheduler is running..."))

    while True:
        with app.app_context():
            # TODO: Add logic to query the DB and schedule jobs dynamically
            # For example:
            # jobs = ScheduledJob.query.filter_by(is_active=True).all()
            # for job in jobs:
            #     ... schedule.every(job.frequency).at(job.schedule_time).do(send_scheduled_message, app, job.id) ...
            pass

        schedule.run_pending()
        time.sleep(1)

# app/scheduler/jobs.py
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from webexteamssdk import WebexTeamsAPI
from .. import db
from ..models import ScheduledJob

_scheduler = None
RECONCILE_JOB_ID = '_reconcile'


def send_scheduled_message(app, job_id):
    """
    Fetches a job by its ID and sends the message to Webex.
    Runs inside the Flask application context.
    """
    with app.app_context():
        app.logger.info(f"Running job ID: {job_id}")
        job = ScheduledJob.query.get(job_id)
        if not job or not job.is_active:
            app.logger.warning(f"Job {job_id} not found or is inactive. Skipping.")
            return

        try:
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

            job.last_run = datetime.utcnow()
            db.session.commit()

            app.logger.info(f"Successfully sent message for job: {job.name}")

        except Exception as e:
            app.logger.error(f"Error sending message for job {job.id}: {e}")


def _build_trigger(job):
    hour, minute = map(int, job.schedule_time.split(':'))
    day_of_week = '*' if job.frequency == 'daily' else job.frequency[:3]
    return CronTrigger(
        day_of_week=day_of_week,
        hour=hour,
        minute=minute,
        timezone=pytz.timezone(job.timezone),
    )


def _reconcile(app):
    """Sync APScheduler state to match active jobs in the database."""
    with app.app_context():
        try:
            jobs = ScheduledJob.query.filter_by(is_active=True).all()
            desired_ids = set()

            for job in jobs:
                sched_id = f"job_{job.id}"
                desired_ids.add(sched_id)
                _scheduler.add_job(
                    send_scheduled_message,
                    trigger=_build_trigger(job),
                    args=[app, job.id],
                    id=sched_id,
                    name=job.name,
                    replace_existing=True,
                    misfire_grace_time=3600,
                )

            for sched_job in _scheduler.get_jobs():
                if sched_job.id == RECONCILE_JOB_ID:
                    continue
                if sched_job.id not in desired_ids:
                    _scheduler.remove_job(sched_job.id)

            app.logger.info(f"Scheduler reconciled. {len(jobs)} active job(s) loaded.")

        except Exception as e:
            app.logger.error(f"Error reconciling scheduler: {e}")


def start_scheduler(app):
    """Initialize APScheduler and start the reconciliation loop."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=pytz.UTC)
    _scheduler.start()

    _scheduler.add_job(
        _reconcile,
        trigger='interval',
        seconds=60,
        args=[app],
        id=RECONCILE_JOB_ID,
        replace_existing=True,
    )

    _reconcile(app)

    app.logger.info("APScheduler started.")
    return _scheduler

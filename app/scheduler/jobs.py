# app/scheduler/jobs.py
import hashlib
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from webexteamssdk import WebexTeamsAPI
from .. import db
from ..models import ScheduledJob, JobLog

_scheduler = None
_job_hashes = {}
RECONCILE_JOB_ID = '_reconcile'


def send_scheduled_message(app, job_id, trigger_type='scheduled'):
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
            db.session.add(JobLog(job_id=job.id, success=True, trigger_type=trigger_type))
            db.session.commit()

            app.logger.info(f"Successfully sent message for job: {job.name}")

        except Exception as e:
            app.logger.error(f"Error sending message for job {job.id}: {e}")
            db.session.add(JobLog(job_id=job.id, success=False, error_message=str(e), trigger_type=trigger_type))
            db.session.commit()


def _job_config_hash(job):
    key = f"{job.id}|{job.schedule_time}|{job.frequency}|{job.timezone}|{job.is_active}"
    return hashlib.md5(key.encode()).hexdigest()


_LEGACY_TZ_MAP = {
    'US/Eastern': 'America/New_York',
    'US/Central': 'America/Chicago',
    'US/Mountain': 'America/Denver',
    'US/Pacific': 'America/Los_Angeles',
    'US/Alaska': 'America/Anchorage',
    'US/Hawaii': 'Pacific/Honolulu',
    'US/Arizona': 'America/Phoenix',
    'Canada/Eastern': 'America/Toronto',
    'Canada/Central': 'America/Winnipeg',
    'Canada/Pacific': 'America/Vancouver',
}


def _normalize_tz(tz_name):
    return _LEGACY_TZ_MAP.get(tz_name, tz_name)


def _build_trigger(job):
    hour, minute = map(int, job.schedule_time.split(':'))
    if job.frequency == 'daily':
        day_of_week = '*'
    else:
        days = [d.strip()[:3] for d in job.frequency.split(',') if d.strip()]
        day_of_week = ','.join(days)
    tz_name = _normalize_tz(job.timezone)
    return CronTrigger(
        day_of_week=day_of_week,
        hour=hour,
        minute=minute,
        timezone=pytz.timezone(tz_name),
    )


def _preflight_check(app, job):
    """
    Validate everything needed to deliver a job's message.
    Returns (ok: bool, issues: list[str]).
    """
    issues = []

    # 1. Timezone
    tz_name = _normalize_tz(job.timezone)
    try:
        pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        issues.append(f"unknown timezone '{job.timezone}' (normalized: '{tz_name}')")

    # 2. Channel
    if not job.channel:
        issues.append("no channel linked")
    elif not job.channel.room_id:
        issues.append(f"channel '{job.channel.name}' has no room_id")

    # 3. Bot token
    if not app.config.get('WEBEX_BOT_TOKEN'):
        issues.append("WEBEX_BOT_TOKEN is not configured")

    # 4. Schedule time format
    try:
        h, m = map(int, job.schedule_time.split(':'))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except (ValueError, AttributeError):
        issues.append(f"invalid schedule_time '{job.schedule_time}'")

    return len(issues) == 0, issues


def _reconcile(app):
    """
    Sync APScheduler state to match active jobs in the database.
    Only adds/replaces a job when its schedule config has changed since
    the last reconcile, preserving next_run for unchanged jobs.
    """
    global _job_hashes
    with app.app_context():
        try:
            jobs = ScheduledJob.query.filter_by(is_active=True).all()

            desired_ids = set()
            new_hashes = {}
            changes = 0
            failed_ids = set()

            for job in jobs:
                ok, issues = _preflight_check(app, job)
                if not ok:
                    for issue in issues:
                        app.logger.error(
                            f"Preflight FAIL job '{job.name}' (id={job.id}): {issue}"
                        )
                    failed_ids.add(job.id)

            for job in jobs:
                sched_id = f"job_{job.id}"
                desired_ids.add(sched_id)

                if job.id in failed_ids:
                    continue

                h = _job_config_hash(job)
                new_hashes[sched_id] = h

                if _job_hashes.get(sched_id) == h:
                    continue

                trigger = _build_trigger(job)
                _scheduler.add_job(
                    send_scheduled_message,
                    trigger=trigger,
                    args=[app, job.id],
                    id=sched_id,
                    name=job.name,
                    replace_existing=True,
                    misfire_grace_time=3600,
                )
                tz_name = _normalize_tz(job.timezone)
                next_fire = trigger.get_next_fire_time(None, datetime.now(pytz.UTC))
                app.logger.info(
                    f"Scheduled job '{job.name}' (id={job.id}): "
                    f"{job.frequency} at {job.schedule_time} {job.timezone}"
                    f"{' -> ' + tz_name if tz_name != job.timezone else ''}"
                    f", next fire: {next_fire}"
                )
                changes += 1

            removed = 0
            for sched_job in _scheduler.get_jobs():
                if sched_job.id == RECONCILE_JOB_ID:
                    continue
                if sched_job.id not in desired_ids:
                    _scheduler.remove_job(sched_job.id)
                    removed += 1

            _job_hashes = new_hashes

            queued = len([j for j in _scheduler.get_jobs() if j.id != RECONCILE_JOB_ID])
            passed = len(jobs) - len(failed_ids)
            if failed_ids:
                app.logger.warning(
                    f"Preflight: {passed}/{len(jobs)} jobs OK, "
                    f"{len(failed_ids)} FAILED validation."
                )
            else:
                app.logger.info(
                    f"Preflight: all {len(jobs)} job(s) passed validation."
                )

            if changes or removed:
                app.logger.info(
                    f"Scheduler reconciled: {changes} added/updated, "
                    f"{removed} removed, {queued} in queue."
                )
            else:
                app.logger.info(f"Scheduler: no changes, {queued} job(s) in queue.")

        except Exception as e:
            app.logger.error(f"Error reconciling scheduler: {e}")


def start_scheduler(app):
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

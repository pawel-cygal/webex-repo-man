# app/main/routes.py
import pytz
from . import main
from flask import render_template, request, redirect, url_for, flash, current_app
from .. import db
from ..models import ScheduledJob, WebexChannel
from ..scheduler.jobs import send_scheduled_message

@main.route('/')
def index():
    """
    Main page of the web panel. Displays channels and scheduled jobs.
    """
    jobs = ScheduledJob.query.order_by(ScheduledJob.created_at.desc()).all()
    channels = WebexChannel.query.order_by(WebexChannel.name).all()
    timezones = pytz.common_timezones
    return render_template('index.html', jobs=jobs, channels=channels, timezones=timezones)

@main.route('/add_channel', methods=['POST'])
def add_channel():
    """
    Handles the creation of a new Webex channel.
    """
    try:
        name = request.form.get('name')
        room_id = request.form.get('room_id')
        
        if not name or not room_id:
            flash('Channel Name and Room ID are required.', 'warning')
            return redirect(url_for('main.index'))

        new_channel = WebexChannel(name=name, room_id=room_id)
        db.session.add(new_channel)
        db.session.commit()
        flash(f"Channel '{name}' added successfully!", 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding channel: {e}")
        flash('Error adding channel. Check logs for details.', 'danger')
        
    return redirect(url_for('main.index'))

@main.route('/delete_channel/<int:channel_id>', methods=['POST'])
def delete_channel(channel_id):
    """
    Handles the deletion of a Webex channel and its associated jobs.
    """
    try:
        channel = WebexChannel.query.get_or_404(channel_id)
        db.session.delete(channel)
        db.session.commit()
        flash(f"Channel '{channel.name}' and all its jobs have been deleted.", 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting channel: {e}")
        flash('Error deleting channel. Check logs for details.', 'danger')

    return redirect(url_for('main.index'))

@main.route('/add_job', methods=['POST'])
def add_job():
    """
    Handles the creation of a new scheduled job.
    """
    try:
        name = request.form.get('name')
        channel_id = request.form.get('channel_id')
        message = request.form.get('message')
        frequency = request.form.get('frequency')
        schedule_time = request.form.get('schedule_time')
        timezone = request.form.get('timezone')
        mentions = request.form.get('mentions')

        new_job = ScheduledJob(
            name=name,
            channel_id=channel_id,
            message=message,
            frequency=frequency,
            schedule_time=schedule_time,
            timezone=timezone,
            mentions=mentions,
            is_active=True
        )
        db.session.add(new_job)
        db.session.commit()
        flash('Job added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding job: {e}")
        flash('Error adding job. Check logs for details.', 'danger')
        
    return redirect(url_for('main.index'))

@main.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
def edit_job(job_id):
    """
    Handles editing of an existing job.
    """
    job = ScheduledJob.query.get_or_404(job_id)
    channels = WebexChannel.query.order_by(WebexChannel.name).all()
    timezones = pytz.common_timezones

    if request.method == 'POST':
        try:
            job.name = request.form.get('name')
            job.channel_id = request.form.get('channel_id')
            job.message = request.form.get('message')
            job.frequency = request.form.get('frequency')
            job.schedule_time = request.form.get('schedule_time')
            job.timezone = request.form.get('timezone')
            job.mentions = request.form.get('mentions')
            job.is_active = 'is_active' in request.form

            db.session.commit()
            flash('Job updated successfully!', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error editing job: {e}")
            flash('Error editing job. Check logs for details.', 'danger')

    return render_template('edit_job.html', job=job, channels=channels, timezones=timezones)

@main.route('/delete_job/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    """
    Handles the deletion of a scheduled job.
    """
    try:
        job = ScheduledJob.query.get_or_404(job_id)
        db.session.delete(job)
        db.session.commit()
        flash('Job deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting job: {e}")
        flash('Error deleting job. Check logs for details.', 'danger')

    return redirect(url_for('main.index'))

@main.route('/run_now/<int:job_id>', methods=['POST'])
def run_now(job_id):
    """
    Manually triggers a job to run immediately.
    """
    job = ScheduledJob.query.get_or_404(job_id)
    try:
        # We need the app object to pass to the function
        app = current_app._get_current_object()
        send_scheduled_message(app, job.id)
        flash(f"Job '{job.name}' was triggered successfully!", 'success')
    except Exception as e:
        current_app.logger.error(f"Error running job '{job.name}' manually: {e}")
        flash(f"Error running job '{job.name}'. Check logs for details.", 'danger')
    
    return redirect(url_for('main.index'))
# app/main/routes.py
from . import main
from flask import render_template, request, redirect, url_for, flash
from .. import db
from ..models import ScheduledJob, WebexChannel

@main.route('/')
def index():
    """
    Main page of the web panel. Displays channels and scheduled jobs.
    """
    jobs = ScheduledJob.query.order_by(ScheduledJob.created_at.desc()).all()
    channels = WebexChannel.query.order_by(WebexChannel.name).all()
    return render_template('index.html', jobs=jobs, channels=channels)

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
        flash(f'Error adding channel: {e}', 'danger')
        
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
        flash(f'Error deleting channel: {e}', 'danger')

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
        mentions = request.form.get('mentions')

        new_job = ScheduledJob(
            name=name,
            channel_id=channel_id,
            message=message,
            frequency=frequency,
            schedule_time=schedule_time,
            mentions=mentions,
            is_active=True
        )
        db.session.add(new_job)
        db.session.commit()
        flash('Job added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding job: {e}', 'danger')
        
    return redirect(url_for('main.index'))

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
        flash(f'Error deleting job: {e}', 'danger')

    return redirect(url_for('main.index'))

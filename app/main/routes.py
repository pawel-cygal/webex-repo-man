# app/main/routes.py
from . import main
from flask import render_template, request, redirect, url_for, flash
from .. import db
from ..models import ScheduledJob

@main.route('/')
def index():
    """
    Main page of the web panel. Displays the list of scheduled jobs.
    """
    jobs = ScheduledJob.query.order_by(ScheduledJob.created_at.desc()).all()
    return render_template('index.html', jobs=jobs)

@main.route('/add_job', methods=['POST'])
def add_job():
    """
    Handles the creation of a new scheduled job.
    """
    try:
        name = request.form.get('name')
        room_id = request.form.get('room_id')
        message = request.form.get('message')
        frequency = request.form.get('frequency')
        schedule_time = request.form.get('schedule_time')
        mentions = request.form.get('mentions')

        new_job = ScheduledJob(
            name=name,
            room_id=room_id,
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
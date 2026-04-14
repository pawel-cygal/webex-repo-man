# app/main/routes.py
from . import main
from flask import render_template
from ..models import ScheduledJob

@main.route('/')
def index():
    """
    Main page of the web panel. Displays the list of scheduled jobs.
    """
    jobs = ScheduledJob.query.order_by(ScheduledJob.created_at.desc()).all()
    return render_template('index.html', jobs=jobs)

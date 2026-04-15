# app/models.py
from . import db
from datetime import datetime
from flask import url_for

class WebexChannel(db.Model):
    """
    Represents a Webex room/channel saved by the user.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    room_id = db.Column(db.String(256), unique=True, nullable=False)
    jobs = db.relationship('ScheduledJob', backref='channel', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<WebexChannel {self.name}>'

class ScheduledJob(db.Model):
    """
    Represents a scheduled message job defined by the user.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Foreign Key to WebexChannel
    channel_id = db.Column(db.Integer, db.ForeignKey('webex_channel.id'), nullable=False)
    
    # Schedule properties
    schedule_time = db.Column(db.String(5), nullable=False) # e.g., "09:00"
    timezone = db.Column(db.String(64), nullable=False, default='UTC')
    frequency = db.Column(db.String(20), nullable=False, default='daily') # e.g., 'daily', 'monday', 'saturday'
    
    # Mentions - stored as a simple comma-separated string of emails
    mentions = db.Column(db.String(1024), nullable=True)
    
    # State tracking
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_run = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ScheduledJob {self.name}>'

    def to_dict(self):
        """
        Serializes the object to a dictionary.
        """
        return {
            'id': self.id,
            'name': self.name,
            'message': self.message,
            'channel': {
                'id': self.channel.id,
                'name': self.channel.name,
                'room_id': self.channel.room_id
            },
            'schedule_time': self.schedule_time,
            'timezone': self.timezone,
            'frequency': self.frequency,
            'frequency_display': self.frequency.capitalize(),
            'mentions': self.mentions,
            'is_active': self.is_active,
            'last_run': self.last_run.strftime('%Y-%m-%d %H:%M') if self.last_run else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'urls': {
                'run_now': url_for('main.run_now', job_id=self.id),
                'edit': url_for('main.edit_job', job_id=self.id),
                'delete': url_for('main.delete_job', job_id=self.id)
            }
        }
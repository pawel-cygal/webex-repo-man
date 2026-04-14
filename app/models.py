# app/models.py
from . import db
from datetime import datetime

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
    frequency = db.Column(db.String(20), nullable=False, default='daily') # e.g., 'daily', 'monday', 'saturday'
    
    # Mentions - stored as a simple comma-separated string of emails
    mentions = db.Column(db.String(1024), nullable=True)
    
    # State tracking
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_run = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ScheduledJob {self.name}>'
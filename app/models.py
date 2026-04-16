# app/models.py
from . import db
from datetime import datetime
from flask import url_for
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(255), nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    webex_id = db.Column(db.String(255), unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_super_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active_flag = db.Column('is_active', db.Boolean, default=True, nullable=False)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    channels = db.relationship('WebexChannel', backref='owner', lazy=True)
    jobs = db.relationship('ScheduledJob', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.is_active_flag

    def display(self):
        return self.display_name or self.email

    def __repr__(self):
        return f'<User {self.email}>'


class AppSetting(db.Model):
    """
    Simple key/value store for application-wide configuration
    (auth mode, Webex OAuth credentials, etc.). Edited by super admin.
    """
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JobLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('scheduled_job.id'), nullable=False)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    success = db.Column(db.Boolean, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    trigger_type = db.Column(db.String(20), default='scheduled')

    def to_dict(self):
        return {
            'id': self.id,
            'executed_at': self.executed_at.strftime('%Y-%m-%d %H:%M:%S') if self.executed_at else None,
            'success': self.success,
            'error_message': self.error_message,
            'trigger_type': self.trigger_type,
        }


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    members = db.relationship('TeamMember', backref='team', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Team {self.name}>'


class TeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(255), nullable=True)

    def display(self):
        return self.display_name or self.email

    def __repr__(self):
        return f'<TeamMember {self.email}>'


class WebexChannel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    room_id = db.Column(db.String(256), unique=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    jobs = db.relationship('ScheduledJob', backref='channel', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<WebexChannel {self.name}>'


class ScheduledJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)

    channel_id = db.Column(db.Integer, db.ForeignKey('webex_channel.id'), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    delivery_mode = db.Column(db.String(20), nullable=False, default='channel')
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    selected_members = db.Column(db.Text, nullable=True)

    team = db.relationship('Team', backref='jobs')

    schedule_time = db.Column(db.String(5), nullable=False)
    timezone = db.Column(db.String(64), nullable=False, default='UTC')
    frequency = db.Column(db.String(128), nullable=False, default='daily')

    mentions = db.Column(db.String(1024), nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_run = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    logs = db.relationship('JobLog', backref='job', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ScheduledJob {self.name}>'

    _DAY_SHORT = {
        'monday': 'Mon', 'tuesday': 'Tue', 'wednesday': 'Wed',
        'thursday': 'Thu', 'friday': 'Fri', 'saturday': 'Sat', 'sunday': 'Sun',
    }

    def _frequency_display(self):
        if self.frequency == 'daily':
            return 'Daily'
        parts = [d.strip() for d in self.frequency.split(',') if d.strip()]
        return ', '.join(self._DAY_SHORT.get(d, d.capitalize()) for d in parts)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'message': self.message,
            'delivery_mode': self.delivery_mode,
            'channel': {
                'id': self.channel.id,
                'name': self.channel.name,
                'room_id': self.channel.room_id
            } if self.channel else None,
            'team': {
                'id': self.team.id,
                'name': self.team.name,
            } if self.team else None,
            'owner': self.owner.display() if self.owner else None,
            'schedule_time': self.schedule_time,
            'timezone': self.timezone,
            'frequency': self.frequency,
            'frequency_display': self._frequency_display(),
            'mentions': self.mentions,
            'is_active': self.is_active,
            'last_run': self.last_run.strftime('%Y-%m-%d %H:%M') if self.last_run else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'urls': {
                'run_now': url_for('main.run_now', job_id=self.id),
                'edit': url_for('main.edit_job', job_id=self.id),
                'delete': url_for('main.delete_job', job_id=self.id),
                'clone': url_for('main.clone_job', job_id=self.id),
                'history': url_for('main.job_history', job_id=self.id)
            }
        }

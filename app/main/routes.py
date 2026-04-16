# app/main/routes.py
import pytz
from . import main
from flask import render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from .. import db
from ..models import ScheduledJob, WebexChannel, JobLog, Team, TeamMember
from ..scheduler.jobs import send_scheduled_message


@main.before_request
@login_required
def require_login():
    """Every route in this blueprint requires authentication."""
    pass


@main.route('/')
def index():
    """
    Main page of the web panel. Displays channels and scheduled jobs.
    `?scope=my` restricts the lists to items owned by the current user.
    """
    scope = 'my' if request.args.get('scope') == 'my' else 'all'

    jobs_q = ScheduledJob.query
    channels_q = WebexChannel.query
    if scope == 'my':
        jobs_q = jobs_q.filter_by(owner_id=current_user.id)
        channels_q = channels_q.filter_by(owner_id=current_user.id)

    jobs = jobs_q.order_by(ScheduledJob.created_at.desc()).all()
    channels = channels_q.order_by(WebexChannel.name).all()
    timezones = pytz.common_timezones
    return render_template(
        'index.html',
        jobs=jobs,
        channels=channels,
        timezones=timezones,
        scope=scope,
    )

@main.route('/add_channel', methods=['POST'])
def add_channel():
    """
    Handles the creation of a new Webex channel.
    """
    try:
        name = request.form.get('name')
        room_id = request.form.get('room_id')
        
        if not name or not room_id:
            return jsonify({'success': False, 'message': 'Channel Name and Room ID are required.'}), 400

        if WebexChannel.query.filter_by(name=name).first() or WebexChannel.query.filter_by(room_id=room_id).first():
            return jsonify({'success': False, 'message': 'A channel with this name or Room ID already exists.'}), 400

        new_channel = WebexChannel(name=name, room_id=room_id, owner_id=current_user.id)
        db.session.add(new_channel)
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f"Channel '{name}' added successfully! Page will reload.",
            'reload': True
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding channel: {e}")
        return jsonify({'success': False, 'message': 'Error adding channel. Check logs for details.'}), 500

@main.route('/delete_channel/<int:channel_id>', methods=['POST'])
def delete_channel(channel_id):
    """
    Handles the deletion of a Webex channel and its associated jobs.
    """
    channel = WebexChannel.query.get_or_404(channel_id)
    try:
        db.session.delete(channel)
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f"Channel '{channel.name}' and all its jobs have been deleted.",
            'reload': True
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting channel: {e}")
        return jsonify({'success': False, 'message': 'Error deleting channel. Check logs for details.'}), 500

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

        if not all([name, channel_id, message, frequency, schedule_time, timezone]):
            return jsonify({'success': False, 'message': 'All fields are required.'}), 400

        new_job = ScheduledJob(
            name=name,
            channel_id=channel_id,
            message=message,
            frequency=frequency,
            schedule_time=schedule_time,
            timezone=timezone,
            mentions=mentions,
            is_active=True,
            owner_id=current_user.id,
        )
        db.session.add(new_job)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Job added successfully!', 
            'job': new_job.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding job: {e}")
        return jsonify({'success': False, 'message': 'Error adding job. Check logs for details.'}), 500

@main.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
def edit_job(job_id):
    """
    Handles editing of an existing job.
    """
    job = ScheduledJob.query.get_or_404(job_id)
    
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
            return jsonify({
                'success': True,
                'message': 'Job updated successfully!',
                'redirect_url': url_for('main.index')
            })
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error editing job: {e}")
            return jsonify({'success': False, 'message': 'Error editing job. Check logs for details.'}), 500

    channels = WebexChannel.query.order_by(WebexChannel.name).all()
    timezones = pytz.common_timezones
    return render_template('edit_job.html', job=job, channels=channels, timezones=timezones)

@main.route('/delete_job/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    """
    Handles the deletion of a scheduled job.
    """
    job = ScheduledJob.query.get_or_404(job_id)
    try:
        db.session.delete(job)
        db.session.commit()
        return jsonify({'success': True, 'message': f"Job '{job.name}' deleted successfully!"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting job: {e}")
        return jsonify({'success': False, 'message': 'Error deleting job. Check logs for details.'}), 500

@main.route('/clone_job/<int:job_id>', methods=['POST'])
def clone_job(job_id):
    """
    Creates a copy of an existing job (inactive by default).
    """
    source = ScheduledJob.query.get_or_404(job_id)
    try:
        copy = ScheduledJob(
            name=f"{source.name} (copy)",
            channel_id=source.channel_id,
            message=source.message,
            frequency=source.frequency,
            schedule_time=source.schedule_time,
            timezone=source.timezone,
            mentions=source.mentions,
            is_active=False,
            owner_id=current_user.id,
        )
        db.session.add(copy)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f"Job '{source.name}' cloned. Review and activate the copy.",
            'job': copy.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cloning job '{source.name}': {e}")
        return jsonify({'success': False, 'message': 'Error cloning job. Check logs for details.'}), 500


@main.route('/run_now/<int:job_id>', methods=['POST'])
def run_now(job_id):
    """
    Manually triggers a job to run immediately.
    """
    job = ScheduledJob.query.get_or_404(job_id)
    try:
        # We need the app object to pass to the function
        app = current_app._get_current_object()
        send_scheduled_message(app, job.id, trigger_type='manual')
        # The job object is updated in send_scheduled_message, so we can serialize it
        return jsonify({
            'success': True, 
            'message': f"Job '{job.name}' was triggered successfully!",
            'job': job.to_dict()
        })
    except Exception as e:
        current_app.logger.error(f"Error running job '{job.name}' manually: {e}")
        return jsonify({'success': False, 'message': f"Error running job '{job.name}'. Check logs for details."}), 500


@main.route('/job/<int:job_id>/history')
def job_history(job_id):
    job = ScheduledJob.query.get_or_404(job_id)
    page = request.args.get('page', 1, type=int)
    logs = JobLog.query.filter_by(job_id=job.id)\
        .order_by(JobLog.executed_at.desc())\
        .paginate(page=page, per_page=50, error_out=False)
    return render_template('job_history.html', job=job, logs=logs)


# --- Team Management ---

@main.route('/teams')
def teams():
    all_teams = Team.query.order_by(Team.name).all()
    return render_template('teams.html', teams=all_teams)


@main.route('/teams/add', methods=['POST'])
def add_team():
    try:
        name = (request.form.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'message': 'Team name is required.'}), 400
        if Team.query.filter_by(name=name).first():
            return jsonify({'success': False, 'message': 'A team with this name already exists.'}), 400

        team = Team(name=name, owner_id=current_user.id)
        db.session.add(team)
        db.session.commit()
        return jsonify({'success': True, 'message': f"Team '{name}' created.", 'reload': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding team: {e}")
        return jsonify({'success': False, 'message': 'Error adding team.'}), 500


@main.route('/teams/<int:team_id>/delete', methods=['POST'])
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    try:
        name = team.name
        db.session.delete(team)
        db.session.commit()
        return jsonify({'success': True, 'message': f"Team '{name}' deleted.", 'reload': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting team: {e}")
        return jsonify({'success': False, 'message': 'Error deleting team.'}), 500


@main.route('/teams/<int:team_id>/members')
def team_members(team_id):
    team = Team.query.get_or_404(team_id)
    return render_template('team_members.html', team=team)


@main.route('/teams/<int:team_id>/members/add', methods=['POST'])
def add_member(team_id):
    team = Team.query.get_or_404(team_id)
    try:
        email = (request.form.get('email') or '').strip().lower()
        display_name = (request.form.get('display_name') or '').strip() or None
        if not email:
            return jsonify({'success': False, 'message': 'Email is required.'}), 400

        existing = TeamMember.query.filter_by(team_id=team.id, email=email).first()
        if existing:
            return jsonify({'success': False, 'message': f'{email} is already in this team.'}), 400

        member = TeamMember(team_id=team.id, email=email, display_name=display_name)
        db.session.add(member)
        db.session.commit()
        return jsonify({'success': True, 'message': f'{email} added to {team.name}.', 'reload': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding member: {e}")
        return jsonify({'success': False, 'message': 'Error adding member.'}), 500


@main.route('/teams/<int:team_id>/members/<int:member_id>/delete', methods=['POST'])
def delete_member(team_id, member_id):
    member = TeamMember.query.get_or_404(member_id)
    if member.team_id != team_id:
        return jsonify({'success': False, 'message': 'Member does not belong to this team.'}), 400
    try:
        email = member.email
        db.session.delete(member)
        db.session.commit()
        return jsonify({'success': True, 'message': f'{email} removed.', 'reload': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing member: {e}")
        return jsonify({'success': False, 'message': 'Error removing member.'}), 500
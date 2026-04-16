# app/auth/routes.py
from flask import render_template, request, redirect, url_for, flash, current_app, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from . import webex_oauth
from .. import db, settings
from ..models import User


def _login_context():
    mode = settings.get_auth_mode()
    return {
        'auth_mode': mode,
        'local_enabled': mode in (settings.AUTH_MODE_LOCAL, settings.AUTH_MODE_BOTH),
        'webex_enabled': mode in (settings.AUTH_MODE_WEBEX, settings.AUTH_MODE_BOTH)
                         and settings.webex_oauth_configured(),
    }


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    ctx = _login_context()

    if request.method == 'POST':
        if not ctx['local_enabled']:
            abort(403)

        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        user = User.query.filter_by(email=email).first()
        if not user or not user.is_active or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html', email=email, **ctx), 401

        login_user(user, remember=bool(request.form.get('remember')))
        current_app.logger.info(f"User {user.email} logged in (local).")

        if user.must_change_password:
            return redirect(url_for('auth.change_password'))

        next_url = request.args.get('next') or url_for('main.index')
        return redirect(next_url)

    return render_template('auth/login.html', **ctx)


@auth.route('/webex')
def webex_start():
    """Kick off the Webex OAuth 2.0 authorization code flow."""
    if not settings.webex_oauth_configured():
        flash("Webex SSO is not configured yet.", 'danger')
        return redirect(url_for('auth.login'))
    if settings.get_auth_mode() == settings.AUTH_MODE_LOCAL:
        abort(403)

    state = webex_oauth.new_state()
    session['webex_oauth_state'] = state
    session['webex_oauth_next'] = request.args.get('next') or url_for('main.index')

    url = webex_oauth.authorize_url(
        client_id=settings.get('webex_client_id'),
        redirect_uri=settings.get('webex_redirect_uri'),
        state=state,
    )
    return redirect(url)


@auth.route('/webex/callback')
def webex_callback():
    if not settings.webex_oauth_configured():
        flash("Webex SSO is not configured.", 'danger')
        return redirect(url_for('auth.login'))

    expected_state = session.pop('webex_oauth_state', None)
    next_url = session.pop('webex_oauth_next', url_for('main.index'))

    if request.args.get('error'):
        flash(f"Webex sign-in cancelled: {request.args.get('error_description') or request.args['error']}", 'warning')
        return redirect(url_for('auth.login'))

    received_state = request.args.get('state')
    code = request.args.get('code')
    if not code or not expected_state or received_state != expected_state:
        current_app.logger.warning("Invalid OAuth state on Webex callback.")
        flash("OAuth state check failed. Please try again.", 'danger')
        return redirect(url_for('auth.login'))

    try:
        token_resp = webex_oauth.exchange_code(
            client_id=settings.get('webex_client_id'),
            client_secret=settings.get_secret('webex_client_secret'),
            redirect_uri=settings.get('webex_redirect_uri'),
            code=code,
        )
        profile = webex_oauth.fetch_profile(token_resp['access_token'])
    except Exception as e:
        current_app.logger.error(f"Webex OAuth exchange failed: {e}")
        flash("Webex sign-in failed. Check settings or try again.", 'danger')
        return redirect(url_for('auth.login'))

    webex_id = profile.get('id')
    emails = profile.get('emails') or []
    email = (emails[0] if emails else '').strip().lower()
    display_name = profile.get('displayName') or None

    if not email or not webex_id:
        flash("Webex profile did not include an email.", 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(webex_id=webex_id).first() \
        or User.query.filter_by(email=email).first()

    if user is None:
        user = User(
            email=email,
            display_name=display_name,
            webex_id=webex_id,
            is_active_flag=True,
            is_admin=False,
            is_super_admin=False,
            must_change_password=False,
        )
        db.session.add(user)
        current_app.logger.info(f"Provisioned new user via Webex SSO: {email}")
    else:
        user.webex_id = webex_id
        if display_name and not user.display_name:
            user.display_name = display_name

    if not user.is_active:
        flash("This account has been deactivated.", 'danger')
        return redirect(url_for('auth.login'))

    db.session.commit()
    login_user(user)
    current_app.logger.info(f"User {user.email} logged in (Webex SSO).")
    return redirect(next_url)


@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    current_app.logger.info(f"User {current_user.email} logged out.")
    logout_user()
    return redirect(url_for('auth.login'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_pw = request.form.get('current_password') or ''
        new_pw = request.form.get('new_password') or ''
        confirm_pw = request.form.get('confirm_password') or ''

        if not current_user.check_password(current_pw):
            flash('Current password is incorrect.', 'danger')
            return render_template('auth/change_password.html'), 400

        if len(new_pw) < 8:
            flash('New password must be at least 8 characters.', 'danger')
            return render_template('auth/change_password.html'), 400

        if new_pw != confirm_pw:
            flash('New password and confirmation do not match.', 'danger')
            return render_template('auth/change_password.html'), 400

        current_user.set_password(new_pw)
        current_user.must_change_password = False
        db.session.commit()
        flash('Password updated.', 'success')
        return redirect(url_for('main.index'))

    return render_template('auth/change_password.html')

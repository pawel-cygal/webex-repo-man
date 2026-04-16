# app/admin/routes.py
from flask import render_template, request, redirect, url_for, flash, current_app, abort
from flask_login import current_user
from . import admin, admin_required, super_admin_required
from .. import db, settings
from ..models import User


@admin.route('/users')
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@admin.route('/users/new', methods=['GET', 'POST'])
@admin_required
def new_user():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        display_name = (request.form.get('display_name') or '').strip() or None
        password = request.form.get('password') or ''
        make_admin = bool(request.form.get('is_admin'))

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('admin/new_user.html', email=email, display_name=display_name, make_admin=make_admin), 400

        if User.query.filter_by(email=email).first():
            flash('A user with this email already exists.', 'danger')
            return render_template('admin/new_user.html', email=email, display_name=display_name, make_admin=make_admin), 400

        # Only a super admin can create another admin.
        if make_admin and not current_user.is_super_admin:
            abort(403)

        user = User(
            email=email,
            display_name=display_name,
            is_admin=make_admin,
            is_active_flag=True,
            must_change_password=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash(f"User {email} created. They must change their password on first login.", 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/new_user.html')


@admin.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@super_admin_required
def toggle_admin(user_id):
    target = User.query.get_or_404(user_id)
    if target.is_super_admin:
        flash("Cannot change admin flag on a super admin.", 'warning')
        return redirect(url_for('admin.users'))

    target.is_admin = not target.is_admin
    db.session.commit()
    flash(f"{target.email}: admin = {target.is_admin}.", 'success')
    return redirect(url_for('admin.users'))


@admin.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_active(user_id):
    target = User.query.get_or_404(user_id)
    if target.is_super_admin:
        flash("Cannot deactivate a super admin.", 'warning')
        return redirect(url_for('admin.users'))
    if target.id == current_user.id:
        flash("You cannot deactivate your own account.", 'warning')
        return redirect(url_for('admin.users'))

    target.is_active_flag = not target.is_active_flag
    db.session.commit()
    flash(f"{target.email}: active = {target.is_active_flag}.", 'success')
    return redirect(url_for('admin.users'))


@admin.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_password(user_id):
    target = User.query.get_or_404(user_id)
    # An admin may not reset a super admin's password.
    if target.is_super_admin and not current_user.is_super_admin:
        abort(403)

    new_pw = settings.random_password()
    target.set_password(new_pw)
    target.must_change_password = True
    db.session.commit()

    flash(
        f"Temporary password for {target.email}: {new_pw} — share securely. "
        "The user will be required to change it on next login.",
        'warning',
    )
    return redirect(url_for('admin.users'))


@admin.route('/users/<int:user_id>/delete', methods=['POST'])
@super_admin_required
def delete_user(user_id):
    target = User.query.get_or_404(user_id)
    if target.is_super_admin:
        flash("A super admin cannot be deleted through the UI.", 'warning')
        return redirect(url_for('admin.users'))
    if target.id == current_user.id:
        flash("You cannot delete your own account.", 'warning')
        return redirect(url_for('admin.users'))

    email = target.email
    db.session.delete(target)
    db.session.commit()
    flash(f"User {email} deleted.", 'success')
    return redirect(url_for('admin.users'))


@admin.route('/settings', methods=['GET', 'POST'])
@super_admin_required
def app_settings():
    if request.method == 'POST':
        mode = (request.form.get('auth_mode') or settings.AUTH_MODE_LOCAL).strip()
        if mode not in settings.VALID_AUTH_MODES:
            flash("Invalid auth mode.", 'danger')
            return redirect(url_for('admin.app_settings'))

        settings.set('auth_mode', mode)
        settings.set('webex_client_id', (request.form.get('webex_client_id') or '').strip() or None)
        settings.set('webex_redirect_uri', (request.form.get('webex_redirect_uri') or '').strip() or None)

        new_secret = request.form.get('webex_client_secret') or ''
        if new_secret.strip():
            settings.set_secret('webex_client_secret', new_secret.strip())

        flash("Settings updated.", 'success')
        current_app.logger.info(f"Auth settings changed by {current_user.email}.")
        return redirect(url_for('admin.app_settings'))

    return render_template(
        'admin/settings.html',
        auth_mode=settings.get_auth_mode(),
        webex_client_id=settings.get('webex_client_id', ''),
        webex_redirect_uri=settings.get('webex_redirect_uri', ''),
        webex_secret_set=bool(settings.get('webex_client_secret')),
    )

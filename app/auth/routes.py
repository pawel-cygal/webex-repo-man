# app/auth/routes.py
from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from .. import db
from ..models import User


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        user = User.query.filter_by(email=email).first()
        if not user or not user.is_active or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html', email=email), 401

        login_user(user, remember=bool(request.form.get('remember')))
        current_app.logger.info(f"User {user.email} logged in.")

        if user.must_change_password:
            return redirect(url_for('auth.change_password'))

        next_url = request.args.get('next') or url_for('main.index')
        return redirect(next_url)

    return render_template('auth/login.html')


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

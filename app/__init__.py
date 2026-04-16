# app/__init__.py
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from .config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .main.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    _bootstrap_super_admin(app)

    from .scheduler.jobs import start_scheduler
    start_scheduler(app)

    return app


def _bootstrap_super_admin(app):
    """
    If no users exist, create the super admin from config. Logs the initial
    password once so the operator can see it on first container start.
    """
    from sqlalchemy.exc import OperationalError
    from .models import User

    with app.app_context():
        try:
            if User.query.count() > 0:
                return
        except OperationalError:
            # Tables not yet migrated (first-ever boot before `flask db upgrade`).
            app.logger.warning("User table missing — run database migrations, then restart.")
            return

        email = (
            app.config.get('SUPER_ADMIN_EMAIL')
            or app.config.get('ADMIN_EMAIL')
            or ''
        ).strip().lower()
        if not email:
            app.logger.warning("SUPER_ADMIN_EMAIL / ADMIN_EMAIL not configured — skipping bootstrap.")
            return

        initial_password = (
            app.config.get('SUPER_ADMIN_INITIAL_PASSWORD')
            or 'changeme'
        )
        user = User(
            email=email,
            display_name='Super Admin',
            is_admin=True,
            is_super_admin=True,
            is_active_flag=True,
            must_change_password=True,
        )
        user.set_password(initial_password)
        db.session.add(user)
        db.session.commit()

        app.logger.warning("=" * 70)
        app.logger.warning(f"Super admin bootstrapped: {email}")
        app.logger.warning(f"Initial password: {initial_password}")
        app.logger.warning("You will be forced to change it on first login.")
        app.logger.warning("=" * 70)

# app/__init__.py
import os
import threading
import time

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import schedule
from .config import Config

# Initialize extensions
db = SQLAlchemy()

def create_app(config_class=Config):
    """
    Application factory function to create and configure the Flask app.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions
    db.init_app(app)

    # Register blueprints
    from .main.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # In the future, to enable webhooks, we would uncomment the following:
    # from app.webhook.routes import webhook as webhook_blueprint
    # app.register_blueprint(webhook_blueprint)

    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()

    # Start the background scheduler
    from .scheduler.jobs import run_scheduler
    scheduler_thread = threading.Thread(target=run_scheduler, args=(app,))
    scheduler_thread.daemon = True
    scheduler_thread.start()

    return app

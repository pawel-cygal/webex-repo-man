# app/__init__.py
import os
import threading
import time
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import schedule
from .config import Config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    """
    Application factory function to create and configure the Flask app.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from .main.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # In the future, to enable webhooks, we would uncomment the following:
    # from app.webhook.routes import webhook as webhook_blueprint
    # app.register_blueprint(webhook_blueprint)

    # Start the background scheduler
    from .scheduler.jobs import run_scheduler
    scheduler_thread = threading.Thread(target=run_scheduler, args=(app,))
    scheduler_thread.daemon = True
    scheduler_thread.start()

    return app

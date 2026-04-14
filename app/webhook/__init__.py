# app/webhook/__init__.py
from flask import Blueprint

webhook = Blueprint('webhook', __name__)

from . import routes

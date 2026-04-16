# app/auth/__init__.py
from flask import Blueprint

auth = Blueprint('auth', __name__, url_prefix='/auth')

from . import routes  # noqa: E402,F401

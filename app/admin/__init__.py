# app/admin/__init__.py
from functools import wraps
from flask import Blueprint, abort
from flask_login import current_user, login_required

admin = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def super_admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_super_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


from . import routes  # noqa: E402,F401

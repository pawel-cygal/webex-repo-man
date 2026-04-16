# app/settings.py
"""
Typed accessors for the AppSetting key/value table, with symmetric
encryption for secrets (Webex OAuth client_secret) using Fernet + a key
derived from SECRET_KEY.
"""
import base64
import hashlib
import secrets as pysecrets
from flask import current_app
from cryptography.fernet import Fernet, InvalidToken
from . import db
from .models import AppSetting


AUTH_MODE_LOCAL = 'local'
AUTH_MODE_WEBEX = 'webex'
AUTH_MODE_BOTH = 'both'
VALID_AUTH_MODES = {AUTH_MODE_LOCAL, AUTH_MODE_WEBEX, AUTH_MODE_BOTH}


def _fernet():
    key_material = (current_app.config.get('SECRET_KEY') or 'a-hard-to-guess-string').encode()
    derived = base64.urlsafe_b64encode(hashlib.sha256(key_material).digest())
    return Fernet(derived)


def get(key, default=None):
    row = AppSetting.query.get(key)
    return row.value if row and row.value is not None else default


def set(key, value):
    row = AppSetting.query.get(key)
    if row is None:
        row = AppSetting(key=key, value=value)
        db.session.add(row)
    else:
        row.value = value
    db.session.commit()


def get_secret(key, default=None):
    raw = get(key)
    if not raw:
        return default
    try:
        return _fernet().decrypt(raw.encode()).decode()
    except InvalidToken:
        return default


def set_secret(key, value):
    if value is None or value == '':
        set(key, None)
        return
    token = _fernet().encrypt(value.encode()).decode()
    set(key, token)


def get_auth_mode():
    mode = get('auth_mode', AUTH_MODE_LOCAL)
    return mode if mode in VALID_AUTH_MODES else AUTH_MODE_LOCAL


def webex_oauth_configured():
    return bool(get('webex_client_id') and get_secret('webex_client_secret'))


def random_password(n=12):
    return pysecrets.token_urlsafe(n)

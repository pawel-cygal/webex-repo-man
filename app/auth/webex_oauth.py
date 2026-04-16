# app/auth/webex_oauth.py
"""Webex OAuth 2.0 helpers (authorize URL + token exchange + profile fetch)."""
import secrets
from urllib.parse import urlencode
import requests

AUTHORIZE_URL = 'https://webexapis.com/v1/authorize'
TOKEN_URL = 'https://webexapis.com/v1/access_token'
PROFILE_URL = 'https://webexapis.com/v1/people/me'
SCOPE = 'spark:people_read'


def new_state():
    return secrets.token_urlsafe(24)


def authorize_url(client_id, redirect_uri, state):
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': SCOPE,
        'state': state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code(client_id, client_secret, redirect_uri, code):
    data = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'redirect_uri': redirect_uri,
    }
    r = requests.post(TOKEN_URL, data=data, timeout=10)
    r.raise_for_status()
    return r.json()  # contains access_token, refresh_token, etc.


def fetch_profile(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    r = requests.get(PROFILE_URL, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()

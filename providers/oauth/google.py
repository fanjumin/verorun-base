#!/usr/bin/env python3
"""Google OAuth Provider — OpenID Connect (OAuth 2.0).

Environment variables:
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET

Scopes: openid email profile
"""
import os, urllib.parse, urllib.request, json

from .base import BaseOAuthProvider


class GoogleOAuthProvider(BaseOAuthProvider):
    """Google OAuth 2.0 + OpenID Connect."""

    PROVIDER = 'google'

    AUTHORIZE_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URL = 'https://oauth2.googleapis.com/token'
    USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'

    def get_client_id(self) -> str:
        return os.environ.get('GOOGLE_CLIENT_ID', '')

    def get_client_secret(self) -> str:
        return os.environ.get('GOOGLE_CLIENT_SECRET', '')

    def get_authorize_url(self, redirect_uri: str, state: str = 'login') -> str:
        params = urllib.parse.urlencode({
            'client_id': self.get_client_id(),
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': state or 'login',
        })
        return f'{self.AUTHORIZE_URL}?{params}'

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        data = {
            'code': code,
            'client_id': self.get_client_id(),
            'client_secret': self.get_client_secret(),
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }
        req = urllib.request.Request(
            self.TOKEN_URL,
            data=urllib.parse.urlencode(data).encode(),
            headers={'Accept': 'application/json'},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            result = json.loads(resp.read().decode())
            if 'access_token' in result:
                return result
            return {'error': result.get('error_description', result.get('error', 'unknown'))}
        except Exception as e:
            return {'error': str(e)}

    def get_userinfo(self, access_token: str) -> dict:
        req = urllib.request.Request(
            self.USERINFO_URL,
            headers={'Authorization': f'Bearer {access_token}'},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            info = json.loads(resp.read().decode())
            return {
                'open_id': info.get('sub', ''),
                'nickname': info.get('name', ''),
                'avatar': info.get('picture', ''),
                'email': info.get('email', ''),
            }
        except Exception as e:
            return {'error': str(e)}

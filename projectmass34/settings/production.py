from .base import *
import dj_database_url
import os
from pathlib import Path


DOTENV_PATH = BASE_DIR.parent / ".env"

if DOTENV_PATH.exists():
    env.read_env(str(DOTENV_PATH))

DEBUG = False
SECRET_KEY = env('DJANGO_SECRET_KEY')

ALLOWED_HOSTS = [
    'reclutamiento.mass34.com',
    '3.146.169.121',
    'localhost',
    '127.0.0.1'
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CSRF_TRUSTED_ORIGINS = [
    'https://reclutamiento.mass34.com',
]

DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL'),
        conn_max_age=600
    )
}
# projectmass34/settings/development.py

from .base import *
import os

# Carga variables del .env en el entorno de desarrollo
environ.Env.read_env(os.path.join(BASE_DIR.parent.parent, '.env'))

DEBUG = True

SECRET_KEY = env('DJANGO_SECRET_KEY', default='django-insecure-7-1$s+e3uy7r(y-^&l6n(6d_35wt2g)0p!eh9#86wj9rbm1*%^')

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '192.168.10.131','mavis-aphorismic-unexcessively.ngrok-free.dev'] 



# Database (SQLite para desarrollo)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

NGROK_DOMAIN = 'mavis-aphorismic-unexcessively.ngrok-free.dev'
NGROK_URL = f'https://{NGROK_DOMAIN}'


CSRF_TRUSTED_ORIGINS = [
    'http://localhost',
    'http://127.0.0.1',
    'http://192.168.10.131', 
    NGROK_URL,
]
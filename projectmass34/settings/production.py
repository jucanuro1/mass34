# projectmass34/settings/production.py

from .base import *
import dj_database_url
import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False # Siempre False en producción

# La clave secreta debe venir exclusivamente del entorno de AWS
SECRET_KEY = env('DJANGO_SECRET_KEY')

# Los hosts permitidos vendrán de la variable de entorno DJANGO_ALLOWED_HOSTS
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['.elasticbeanstalk.com'])

# Database (MySQL para producción)
# dj_database_url leerá la variable DATABASE_URL inyectada por AWS
DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL'),
        conn_max_age=600 # Opcional: mantiene la conexión abierta por más tiempo
    )
}

# --- CONFIGURACIÓN DE SEGURIDAD PARA PRODUCCIÓN ---
# Es vital para entornos reales. Asume que usas SSL/HTTPS.
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True) # Redireccionar a HTTPS
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=True)
SECURE_HSTS_SECONDS = 31536000 # Habilitar HSTS por 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Opcional: Añade WhiteNoise para servir estáticos si no usas S3
# INSTALLED_APPS.append('whitenoise.runserver_nostatic')
# MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# projectmass34/settings/base.py

from pathlib import Path
import os
import environ # Importamos para usar env.list y env()

# Configuración del manejo de entorno. La carga del .env se hace en development.py o production.py
env = environ.Env()

# BASE_DIR: Para llegar a projectmass34/ (donde está manage.py) desde settings/base.py
# (settings/base.py -> settings/ -> projectmass34/ -> projectmass34/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    #apps
    'candidatos',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'projectmass34.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], # Directorio de templates global (si existe)
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'projectmass34.wsgi.application'

# Password validation... (Lo mismo que tenías)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Lima' # Usa tu zona horaria
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
# Directorio donde Django recolectará los estáticos en producción (EB/collectstatic)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 
# Directorios de estáticos globales para DESARROLLO (el warning viene de aquí)
STATICFILES_DIRS = [ 
    os.path.join(BASE_DIR, 'static'), 
]

# Media files (archivos subidos por usuarios)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'kanban/'
LOGIN_URL = '/login/'

# Las siguientes 3 variables serán definidas/sobrescritas en development/production
SECRET_KEY = '' 
DEBUG = False
ALLOWED_HOSTS = []
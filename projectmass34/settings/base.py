# projectmass34/settings/base.py

from pathlib import Path
import os
import environ

# =========================
# PATHS Y VARIABLES DE ENTORNO
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()

# Cargar .env si existe
env_path = BASE_DIR / ".env"
if env_path.exists():
    environ.Env.read_env(env_path)

# =========================
# CONFIGURACIONES PRINCIPALES
# =========================
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-secret")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# =========================
# APPS INSTALADAS
# =========================
INSTALLED_APPS = [
    # Jazzmin (siempre activado porque lo usas)
    "jazzmin",

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_extensions',

    # Tus apps
    'candidatos',
    'coaching_agenda',
]

# =========================
# MIDDLEWARE
# =========================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# =========================
# URLS & TEMPLATES
# =========================
ROOT_URLCONF = 'projectmass34.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

# =========================
# CONTRASEÑAS Y VALIDACIÓN
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# =========================
# CONFIGURACIÓN JAZZMIN
# =========================
JAZZMIN_SETTINGS = {
    "site_title": "+34",
    "site_header": "Administración MASS",
    "site_brand": "Administración +34",
    "theme": "default",
    "custom_css": "/css/custom_jazzmin.css",
}

# =========================
# INTERNACIONALIZACIÓN
# =========================
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True

HORA_LIMITE_ASISTENCIA = "7:00"

# =========================
# ARCHIVOS ESTÁTICOS / MEDIA
# =========================
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles')

# =========================
# LOGIN
# =========================
LOGIN_REDIRECT_URL = '/kanban/'
LOGIN_URL = '/login/'

# =========================
# WHATSAPP API
# =========================
WHATSAPP_API_VERSION = 'v19.0'
WHATSAPP_API_URL = f'https://graph.facebook.com/{WHATSAPP_API_VERSION}/'
WHATSAPP_PHONE_ID = '96582358756'
WHATSAPP_ACCESS_TOKEN = 'TU_TOKEN_TEMPORAL_DE_24_HORAS'

# =========================
# LOGGING (FIJO, SIN ERRORES)
# =========================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'errors.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

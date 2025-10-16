# projectmass34/settings/__init__.py

import os

# Determina qué configuración cargar
# Lee la variable de entorno DJANGO_ENV. Por defecto, usa 'development'.
if os.environ.get('DJANGO_ENV', 'development') == 'production':
    from .production import *
else:
    from .development import *
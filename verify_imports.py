import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projectmass34.settings')
django.setup()

try:
    print("Attempting to import candidatos.views...")
    from candidatos import views
    print("Successfully imported candidatos.views")
    
    # Check for a few key symbols to ensure star import worked
    print(f"Checking for Candidato model: {views.Candidato}")
    print(f"Checking for render function: {views.render}")
    print(f"Checking for messages module: {views.messages}")
    
except Exception as e:
    print(f"FAILED to import candidatos.views: {e}")
    sys.exit(1)

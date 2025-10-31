# coaching_agenda/urls.py

from django.urls import path
from .views import AgendaDemoView

urlpatterns = [
    path('agenda/', AgendaDemoView.as_view(), name='coaching_agenda_demo'),
]
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/candidatos/login/'), name='logout'),
    
    path('kanban/', views.KanbanDashboardView.as_view(), name='kanban_dashboard'),
    
    path('registro/', views.RegistroCandidatoView.as_view(), name='registro_candidato'),
    
    path('iniciar-proceso/<str:dni>/', views.IniciarProcesoView.as_view(), name='iniciar_proceso'),
    
    path('proceso/actualizar/<int:proceso_id>/', views.ActualizarProcesoView.as_view(), name='actualizar_proceso'),
    path('proceso/asignar_supervisor/<int:proceso_id>/', views.AsignarSupervisorIndividualView.as_view(), name='asignar_supervisor_individual'), 

    path('candidato/update-status/', views.UpdateStatusView.as_view(), name='update_candidato_status'),

    path('exportar/candidatos/<str:estado>/', views.ExportarCandidatosExcelView.as_view(), name='exportar_candidatos_excel'),

    path('api/search-candidato/', views.CandidatoSearchView.as_view(), name='candidato_search_api'),
]
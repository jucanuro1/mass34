from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.urls import reverse_lazy

urlpatterns = [
    path('', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page=reverse_lazy('login')), name='logout'),    
    # Dashboard Principal
    path('kanban/', views.KanbanDashboardView.as_view(), name='kanban_dashboard'),
    
    # Vistas de Candidato y Proceso
        path('registro/', views.RegistroCandidatoView.as_view(), name='registro_candidato'),
    path('detalle/<str:dni>/', views.CandidatoDetailView.as_view(), name='detalle_candidato'),
    path('registro/candidato-completo/', views.RegistroPublicoCompletoView.as_view(), name='registro_publico_completo'),
    
    # Vistas de Proceso 
    path('iniciar-proceso/<str:dni>/', views.IniciarProcesoView.as_view(), name='iniciar_proceso'),
    path('proceso/actualizar/<int:proceso_id>/', views.ActualizarProcesoView.as_view(), name='actualizar_proceso'),
    path('proceso/asignar_supervisor/<int:proceso_id>/', views.AsignarSupervisorIndividualView.as_view(), name='asignar_supervisor_individual'), 

    # APIs para Drag & Drop y Acciones Rápidas
    path('candidato/update-status/', views.UpdateStatusView.as_view(), name='update_candidato_status'),
    path('candidato/update-status-multiple/', views.UpdateStatusMultipleView.as_view(), name='update_candidato_status_multiple'), 
    
    # Exportación
    path('exportar/candidatos/<str:estado>/', views.ExportarCandidatosExcelView.as_view(), name='exportar_candidatos_excel'),

    path('proceso/registrar-observacion/', views.registrar_observacion, name='registrar_observacion'),
    path('proceso/registrar-test-archivo/', views.registrar_test_archivo, name='registrar_test_archivo'),

    path('convocatoria/desactivar/', views.DesactivarConvocatoriaView.as_view(), name='desactivar_convocatoria'),

    # APIs para Búsqueda y Asistencia
    path('asistencia/', views.asistencia_dashboard, name='asistencia_dashboard'),
    path('asistencia/registrar/', views.registrar_asistencia_rapida, name='registrar_asistencia_rapida'),
    path('api/search-candidato/', views.CandidatoSearchView.as_view(), name='candidato_search_api'),
    path('api/asistencia-check/', views.AsistenciaDiariaCheckView.as_view(), name='api_asistencia_check'),

    path('candidatos/', views.CandidatoListView.as_view(), name='candidatos_list'),
    path('candidatos/exportar/', views.CandidatoExportView.as_view(), name='candidatos_export'),

    path('candidatos/asistencia/', views.CandidatoAsistenciaListView.as_view(), name='candidatos_asistencia_list'),
    path('candidatos/asistencia/<int:pk>/detalle/', views.RegistroAsistenciaDetailView.as_view(), name='registro_asistencia_detalle'),

    path('documentos/registrar/', views.RegistrarDocumentoView.as_view(), name='registrar_documento_laboral'),

    path('api/proceso/<int:proceso_id>/actualizar_fecha/', views.actualizar_fecha_proceso, name='actualizar_fecha_proceso_api'),
    
]
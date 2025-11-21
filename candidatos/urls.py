from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.urls import reverse_lazy

urlpatterns = [
    # --- Autenticación ---
    path('', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page=reverse_lazy('login')), name='logout'),
    
    # --- Tableros ---
    path('kanban/', views.KanbanDashboardView.as_view(), name='kanban_dashboard'),
    path('asistencia/', views.asistencia_dashboard, name='asistencia_dashboard'),
    
    # --- Gestión de Candidatos ---
    path('registro/', views.RegistroCandidatoView.as_view(), name='registro_candidato'),
    path('detalle/<str:dni>/', views.CandidatoDetailView.as_view(), name='detalle_candidato'),
    path('registro/candidato-completo/', views.RegistroPublicoCompletoView.as_view(), name='registro_publico_completo'),
    path('candidato/update-status/', views.UpdateStatusView.as_view(), name='update_candidato_status'),
    path('candidato/update-status-multiple/', views.UpdateStatusMultipleView.as_view(), name='update_candidato_status_multiple'),
    path('candidatos/', views.CandidatoListView.as_view(), name='candidatos_list'),
    path('candidatos/exportar/', views.CandidatoExportView.as_view(), name='candidatos_export'),
    path('candidatos/ocultar/', views.OcultarCandidatosView.as_view(), name='ocultar_candidatos'),
    path('candidatos/mostrar/', views.MostrarCandidatosView.as_view(), name='mostrar_candidatos'),
    path('candidatos/gestion/lista/', views.ListaCandidatosPorFechaView.as_view(), name='lista_candidatos_por_fecha'),
    
    # --- Procesos ---
    path('iniciar-proceso/<str:dni>/', views.IniciarProcesoView.as_view(), name='iniciar_proceso'),
    path('proceso/actualizar/<int:proceso_id>/', views.ActualizarProcesoView.as_view(), name='actualizar_proceso'),
    path('proceso/asignar_supervisor/<int:proceso_id>/', views.AsignarSupervisorIndividualView.as_view(), name='asignar_supervisor_individual'),
    path('proceso/registrar-observacion/', views.registrar_observacion, name='registrar_observacion'),
    path('proceso/registrar-test-archivo/', views.registrar_test_archivo, name='registrar_test_archivo'),
    path('api/proceso/<int:proceso_id>/actualizar_fecha/', views.actualizar_fecha_proceso, name='actualizar_fecha_proceso_api'),

    # --- Convocatorias ---
    path('convocatoria/desactivar/', views.DesactivarConvocatoriaView.as_view(), name='desactivar_convocatoria'),
    path('convocatorias/activar/', views.ActivarConvocatoriaView.as_view(), name='activar_convocatoria'),
    path('gestion/convocatorias/', views.ListaConvocatoriasView.as_view(), name='gestion_convocatorias'),

    # --- Documentos y Exportación ---
    path('documentos/registrar/', views.RegistrarDocumentoView.as_view(), name='registrar_documento_laboral'),
    path('exportar/candidatos/<str:estado>/', views.ExportarCandidatosExcelView.as_view(), name='exportar_candidatos_excel'),

    # --- Asistencia ---
    path('asistencia/registrar/', views.registrar_asistencia_rapida, name='registrar_asistencia_rapida'),
    path('api/asistencia-check/', views.AsistenciaDiariaCheckView.as_view(), name='api_asistencia_check'),
    path('candidatos/asistencia/', views.CandidatoAsistenciaListView.as_view(), name='candidatos_asistencia_list'),
    path('candidatos/asistencia/<int:pk>/detalle/', views.RegistroAsistenciaDetailView.as_view(), name='registro_asistencia_detalle'),
    path('candidatos/asistencia/registrar/<int:candidato_pk>/', views.registrar_asistencia_htmx, name='registrar_asistencia_htmx'),

    # --- APIs Generales ---
    path('api/search-candidato/', views.CandidatoSearchView.as_view(), name='candidato_search_api'),
    path('api/candidato/<str:dni>/historial/', views.HistoryDetailView.as_view(), name='api_candidato_historial'),

    # --- Módulo de Mensajería Masiva ---
    path('mensajeria/', views.MensajeriaDashboardView.as_view(), name='mensajeria_dashboard'),
    path('api/mensajeria/', views.MensajeriaAPIView.as_view(), name='mensajeria_api'),
    path('api/mensajeria/iniciar/', views.IniciarEnvioMasivoView.as_view(), name='iniciar_envio_masivo'),
    
    # Esta es la URL que llama el JS del modal. Ahora ya no choca con nada.
    path('api/mensajeria/historial-data/', views.HistorialEnviosJsonView.as_view(), name='api_historial_envios'),
    path('api/historial/detalle/<int:tarea_id>/', views.DetalleTareaJsonView.as_view(), name='api_detalle_tarea'),

    # Es la url para manejar los estados post envío
    path('api/whatsapp/webhook/', views.WhatsappWebhookView.as_view(), name='whatsapp_webhook'),
]
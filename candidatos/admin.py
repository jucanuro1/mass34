from django.contrib import admin
from .models import (
    Empresa, Sede, Supervisor, Candidato, Proceso, RegistroAsistencia, 
    DatosCualificacion, ComentarioProceso, RegistroTest, DocumentoCandidato,
    TipoDocumento, MensajePlantilla, TareaEnvioMasivo, DetalleEnvio
)
from django.utils.html import format_html

admin.site.register(Empresa)
admin.site.register(Sede)
admin.site.register(Supervisor)


class ProcesoInline(admin.TabularInline):
    model = Proceso
    extra = 0
    fields = [
        'fecha_inicio', 'empresa_proceso', 'sede_proceso', 'estado', 
        'objetivo_ventas_alcanzado', 'faptor_aptitud_aplica', 
        'supervisor', 'fecha_teorico', 'fecha_practico', 'fecha_contratacion','kanban_activo'
    ]
    readonly_fields = [
        'objetivo_ventas_alcanzado', 'factor_aptitud_aplica', 
        'fecha_teorico', 'fecha_practico', 'fecha_contratacion'
    ]

class RegistroAsistenciaInline(admin.TabularInline):
    model = RegistroAsistencia
    extra = 0
    fields = ('momento_registro', 'fase_actual', 'movimiento', 'estado')
    readonly_fields = ('momento_registro',)

@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ('tipo_documento','DNI', 'nombres_completos','edad', 'estado_actual', 'telefono_whatsapp','email','fecha_registro','usuario_ultima_modificacion')
    list_filter = ('estado_actual',) 
    search_fields = ('DNI', 'nombres_completos','telefono_whatsapp') 
    inlines = [ProcesoInline] 


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_pais', 'longitud_requerida', 'solo_numeros')
    search_fields = ('nombre', 'codigo_pais')
    list_filter = ('solo_numeros', 'longitud_requerida')
    
@admin.register(Proceso)
class ProcesoAdmin(admin.ModelAdmin):
    list_display = (
        'candidato', 'empresa_proceso', 'sede_proceso', 'fecha_inicio', 'estado', 
        'objetivo_ventas_alcanzado', 'factor_aptitud_aplica','kanban_activo'
    )
    list_filter = ('empresa_proceso', 'sede_proceso', 'estado', 'objetivo_ventas_alcanzado', 'factor_aptitud_aplica')
    date_hierarchy = 'fecha_inicio' 
    search_fields = ('candidato__DNI', 'candidato__nombres_completos')
    
    fieldsets = (
        ('Información General del Candidato/Proceso', {
            'fields': ('candidato', 'empresa_proceso', 'sede_proceso', 'supervisor', 'fecha_inicio', 'estado')
        }),
        ('Trazabilidad de Fechas', {
            'fields': ('fecha_teorico', 'fecha_practico', 'fecha_contratacion',),
            'classes': ('collapse',), 
        }),
        ('Resultados de las Pruebas y Contratación', {
            'fields': (
                'objetivo_ventas_alcanzado', 
                'factor_aptitud_aplica', 
            ),
            'classes': ('wide', 'extrapretty'),
        }),
    )
    
    inlines = [RegistroAsistenciaInline] 

@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = (
        'proceso_candidato', 
        'momento_registro', 
        'fase_actual', 
        'movimiento', 
        'estado'
    )
    list_filter = (
        'proceso__empresa_proceso', 
        'fase_actual', 
        'movimiento', 
        'estado', 
        'momento_registro'
    )
    search_fields = ('proceso__candidato__DNI', 'proceso__candidato__nombres_completos')
    date_hierarchy = 'momento_registro'
    
    def proceso_candidato(self, obj):
        ident = obj.proceso.candidato.DNI
        return format_html(f"{obj.proceso.candidato.nombres_completos} (<span style='font-weight: bold;'>{ident}</span>)")
    proceso_candidato.short_description = 'Candidato (Identificación)'
    proceso_candidato.admin_order_field = 'proceso__candidato__nombres_completos'

@admin.register(DatosCualificacion)
class DatosCualificacionAdmin(admin.ModelAdmin):
    list_display = (
        'candidato_nombre', 
        'secundaria_completa', 
        'experiencia_campanas_espanolas', 
        'experiencia_ventas_tipo', 
        'disponibilidad_horario'
    )
    
    list_filter = (
        'secundaria_completa', 
        'experiencia_campanas_espanolas', 
        'experiencia_ventas_tipo', 
        'disponibilidad_horario'
    )
    
    search_fields = (
        'candidato__nombres_completos', 
        'candidato__DNI',
        'empresa_vendedor'
    )
    
    ordering = ('candidato__nombres_completos',)
    
    def candidato_nombre(self, obj):
        return obj.candidato.nombres_completos
    candidato_nombre.short_description = 'Candidato'
    
    fieldsets = (
        ('Información del Candidato', {
            'fields': ('candidato',),
        }),
        ('Educación y Experiencia de Venta', {
            'fields': ('secundaria_completa', 'experiencia_campanas_espanolas', 'experiencia_ventas_tipo', 'empresa_vendedor', 'tiempo_experiencia_vendedor'),
        }),
        ('Condiciones y Disponibilidad', {
            'fields': ('conforme_beneficios', 'detalle_beneficios_otro', 'disponibilidad_horario', 'discapacidad_enfermedad_cronica', 'dificultad_habla'),
        }),
    )

@admin.register(ComentarioProceso)
class ComentarioProcesoAdmin(admin.ModelAdmin):
    list_display = (
        'candidato_nombre', 
        'proceso_id', 
        'fase_proceso', 
        'registrado_por', 
        'fecha_registro_format'
    )
    
    list_filter = (
        'fase_proceso', 
        'registrado_por', 
        'proceso__empresa_proceso', 
        'fecha_registro'
    )
    
    search_fields = (
        'proceso__candidato__nombres_completos', 
        'proceso__candidato__DNI',
        'texto'
    )
    
    readonly_fields = ('fecha_registro', 'fase_proceso')

    fieldsets = (
        (None, {
            'fields': ('proceso', 'texto', 'registrado_por')
        }),
        ('Trazabilidad', {
            'fields': ('fase_proceso', 'fecha_registro'),
            'classes': ('collapse',), 
        }),
    )

    def candidato_nombre(self, obj):
        return obj.proceso.candidato.nombres_completos
    candidato_nombre.short_description = 'Candidato'
    
    def proceso_id(self, obj):
        return obj.proceso.pk
    proceso_id.short_description = 'ID Proceso'

    def fecha_registro_format(self, obj):
        return obj.fecha_registro.strftime("%d/%m/%Y %H:%M")
    fecha_registro_format.short_description = 'Fecha/Hora'

@admin.register(RegistroTest)
class RegistroTestAdmin(admin.ModelAdmin):
    list_display = (
        'candidato_nombre', 
        'proceso_id', 
        'tipo_test', 
        'fase_proceso', 
        'resultado_obtenido', 
        'descargar_archivo'
    )
    
    list_filter = (
        'tipo_test', 
        'fase_proceso', 
        'registrado_por', 
        'proceso__empresa_proceso'
    )
    
    search_fields = (
        'proceso__candidato__nombres_completos', 
        'proceso__candidato__DNI',
        'resultado_obtenido'
    )
    
    readonly_fields = ('fecha_registro', 'fase_proceso')

    fieldsets = (
        (None, {
            'fields': ('proceso', 'tipo_test', 'archivo_url', 'resultado_obtenido')
        }),
        ('Información de Registro', {
            'fields': ('registrado_por', 'fase_proceso', 'fecha_registro'),
        }),
    )
    
    def candidato_nombre(self, obj):
        return obj.proceso.candidato.nombres_completos
    candidato_nombre.short_description = 'Candidato'

    def proceso_id(self, obj):
        return obj.proceso.pk
    proceso_id.short_description = 'ID Proceso'

    def descargar_archivo(self, obj):
        if obj.archivo_url:
            from django.utils.html import format_html
            return format_html('<a href="{}" target="_blank">Descargar</a>', obj.archivo_url.url)
        return "No hay archivo"
    descargar_archivo.short_description = 'Archivo'

@admin.register(DocumentoCandidato)
class DocumentoCandidatoAdmin(admin.ModelAdmin):
    list_display = (
        'candidato_link', 
        'tipo_documento', 
        'proceso', 
        'fecha_subida', 
        'subido_por', 
        'archivo_link'
    )
    
    list_filter = (
        'tipo_documento', 
        'proceso', 
        'fecha_subida'
    )
    
    search_fields = (
        'candidato__nombres_completos', 
        'candidato__DNI',
        'observaciones'
    )
    
    fieldsets = (
        (None, {
            'fields': ('candidato', 'proceso', 'tipo_documento', 'archivo', 'observaciones'),
        }),
        ('Metadatos', {
            'fields': ('fecha_subida', 'subido_por'),
            'classes': ('collapse',), 
        }),
    )
    
    readonly_fields = ('fecha_subida', 'subido_por')
    
    @admin.display(description='Candidato')
    def candidato_link(self, obj):
        return format_html('<a href="{}">{}</a>',
                           f'/admin/candidatos/candidato/{obj.candidato.pk}/change/', 
                           obj.candidato.nombres_completos)
    
    @admin.display(description='Descargar Archivo')
    def archivo_link(self, obj):
        if obj.archivo:
            return format_html('<a href="{}">Descargar</a>', obj.archivo.url)
        return "N/A"
    
class DetalleEnvioInline(admin.TabularInline):
    """Muestra los mensajes individuales dentro de la Tarea."""
    model = DetalleEnvio
    extra = 0 # No agregar formularios vacíos por defecto
    fields = ('contacto', 'telefono', 'estado_meta', 'fecha_envio', 'id_mensaje_meta')
    readonly_fields = ('contacto', 'telefono', 'estado_meta', 'fecha_envio', 'id_mensaje_meta')
    can_delete = False
    show_change_link = True # Permite navegar al detalle

    def has_add_permission(self, request, obj=None):
        return False # Los detalles se crean automáticamente por el sistema

# --- MODEL ADMINS ---

@admin.register(MensajePlantilla)
class MensajePlantillaAdmin(admin.ModelAdmin):
    """Administración de las plantillas de mensajes reusables."""
    list_display = ('titulo', 'variables_usadas', 'fecha_creacion', 'creado_por')
    list_filter = ('fecha_creacion', 'creado_por')
    search_fields = ('titulo', 'contenido_texto')
    ordering = ('titulo',)
    
    fieldsets = (
        (None, {
            'fields': ('titulo', 'contenido_texto'),
            'description': 'Información principal y contenido del mensaje.'
        }),
        ('Variables y Auditoría', {
            'fields': ('variables_usadas', 'creado_por'),
            'classes': ('collapse',), 
            'description': 'Define las variables usadas para la personalización (ej: {DNI}, {nombres_completos}).'
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        fields = ['fecha_creacion']
        if obj:
            fields.append('creado_por')
        return fields


@admin.register(TareaEnvioMasivo)
class TareaEnvioMasivoAdmin(admin.ModelAdmin):
    """Administración de las tareas de envío (Historial de Campañas)."""
    list_display = (
        '__str__', 'fecha_inicio', 'proceso_tipo', 'fecha_origen', 
        'total_contactos', 'total_entregados', 'estado', 'mostrar_tasa_exito'
    )
    list_filter = ('estado', 'proceso_tipo', 'fecha_origen', 'fecha_inicio', 'usuario_que_envia')
    search_fields = ('mensaje_plantilla__titulo', 'usuario_que_envia__username', 'task_id')
    date_hierarchy = 'fecha_inicio' 
    
    inlines = [DetalleEnvioInline]
    
    readonly_fields = (
        'fecha_inicio', 'usuario_que_envia', 'total_contactos', 
        'total_entregados', 'total_fallidos', 'task_id', 'mostrar_tasa_exito'
    )

    def mostrar_tasa_exito(self, obj):
        """Calcula y muestra la tasa de éxito con formato."""
        if obj.total_contactos > 0:
            tasa = (obj.total_entregados / obj.total_contactos) * 100
            color = 'green' if tasa > 90 else 'orange' if tasa > 50 else 'red'
            return format_html(f'<strong style="color: {color};">{tasa:.1f}%</strong>')
        return '0%'
    mostrar_tasa_exito.short_description = 'Tasa de Éxito'


@admin.register(DetalleEnvio)
class DetalleEnvioAdmin(admin.ModelAdmin):
    """Administración de los detalles individuales de cada mensaje."""
    list_display = ('tarea_envio', 'contacto', 'telefono', 'estado_meta', 'fecha_envio', 'id_mensaje_meta')
    list_filter = ('estado_meta', 'fecha_envio', 'tarea_envio__proceso_tipo')
    search_fields = ('contacto__DNI', 'telefono', 'id_mensaje_meta', 'contenido_final')
    date_hierarchy = 'fecha_envio'
    
    fieldsets = (
        (None, {
            'fields': ('tarea_envio', 'contacto', 'telefono'),
        }),
        ('Contenido y Estado', {
            'fields': ('contenido_final', 'estado_meta', 'id_mensaje_meta', 'fecha_envio'),
        }),
    )
    
    readonly_fields = (
        'tarea_envio', 'contacto', 'telefono', 'contenido_final', 
        'estado_meta', 'id_mensaje_meta', 'fecha_envio'
    )

    def has_add_permission(self, request):
        return False 
    
    def has_delete_permission(self, request, obj=None):
        return False 
    

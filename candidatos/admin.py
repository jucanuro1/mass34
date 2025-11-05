from django.contrib import admin
from .models import Empresa, Sede, Supervisor, Candidato, Proceso, RegistroAsistencia, DatosCualificacion, ComentarioProceso, RegistroTest, DocumentoCandidato
from django.utils.html import format_html

admin.site.register(Empresa)
admin.site.register(Sede)
admin.site.register(Supervisor)

class ProcesoInline(admin.TabularInline):
    model = Proceso
    extra = 0
    fields = [
        'fecha_inicio', 'empresa_proceso', 'sede_proceso', 'estado', 
        'objetivo_ventas_alcanzado', 'factor_actitud_aplica', 
        'supervisor', 'fecha_teorico', 'fecha_practico', 'fecha_contratacion','kanban_activo'
    ]
    readonly_fields = [
        'objetivo_ventas_alcanzado', 'factor_actitud_aplica', 
        'fecha_teorico', 'fecha_practico', 'fecha_contratacion'
    ]

@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ('DNI', 'nombres_completos','edad', 'estado_actual', 'telefono_whatsapp','email','fecha_registro','usuario_ultima_modificacion')
    list_filter = ('estado_actual',) 
    search_fields = ('DNI', 'nombres_completos')
    inlines = [ProcesoInline] 

class RegistroAsistenciaInline(admin.TabularInline):
    model = RegistroAsistencia
    extra = 0
    # Campos actualizados para reflejar el nuevo modelo (momento, fase, movimiento)
    fields = ('momento_registro', 'fase_actual', 'movimiento', 'estado')
    readonly_fields = ('momento_registro',)


@admin.register(Proceso)
class ProcesoAdmin(admin.ModelAdmin):
    list_display = (
        'candidato', 'empresa_proceso', 'sede_proceso', 'fecha_inicio', 'estado', 
        'objetivo_ventas_alcanzado', 'factor_actitud_aplica','kanban_activo'
    )
    list_filter = ('empresa_proceso', 'sede_proceso', 'estado', 'objetivo_ventas_alcanzado', 'factor_actitud_aplica')
    date_hierarchy = 'fecha_inicio' 
    search_fields = ('candidato__DNI', 'candidato__nombres_completos')
    
    fieldsets = (
        ('Información General del Candidato/Proceso', {
            'fields': ('candidato', 'empresa_proceso', 'sede_proceso', 'supervisor', 'fecha_inicio', 'estado')
        }),
        ('Trazabilidad de Fechas', {
            # Se añaden las fechas de trazabilidad como solo lectura
            'fields': ('fecha_teorico', 'fecha_practico', 'fecha_contratacion',),
            'classes': ('collapse',), # Opcional: Colapsar sección de fechas
        }),
        ('Resultados de las Pruebas y Contratación', {
            'fields': (
                'objetivo_ventas_alcanzado', 
                'factor_actitud_aplica', 
            ),
            'classes': ('wide', 'extrapretty'),
        }),
    )
    
    inlines = [RegistroAsistenciaInline] 

@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    # list_display actualizado para usar los nuevos campos de asistencia
    list_display = (
        'proceso_candidato', 
        'momento_registro', 
        'fase_actual', 
        'movimiento', 
        'estado'
    )
    # list_filter actualizado para usar los nuevos campos del modelo
    list_filter = (
        'proceso__empresa_proceso', 
        'fase_actual', 
        'movimiento', 
        'estado', 
        'momento_registro'
    )
    search_fields = ('proceso__candidato__DNI', 'proceso__candidato__nombres_completos')
    date_hierarchy = 'momento_registro'
    
    # Nuevo método para mostrar el DNI y nombre del candidato
    def proceso_candidato(self, obj):
        return format_html(f"{obj.proceso.candidato.nombres_completos} (<span style='font-weight: bold;'>{obj.proceso.candidato.DNI}</span>)")
    proceso_candidato.short_description = 'Candidato (DNI)'
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
    # Campos a mostrar en la lista principal
    list_display = (
        'candidato_nombre', 
        'proceso_id', 
        'fase_proceso', 
        'registrado_por', 
        'fecha_registro_format'
    )
    
    # Campos por los que se puede filtrar
    list_filter = (
        'fase_proceso', 
        'registrado_por', 
        'proceso__empresa_proceso', 
        'fecha_registro'
    )
    
    # Campos que permiten la búsqueda
    search_fields = (
        'proceso__candidato__nombres_completos', 
        'proceso__candidato__DNI', 
        'texto'
    )
    
    # Solo lectura
    readonly_fields = ('fecha_registro', 'fase_proceso')

    # Agrupación de campos en la vista de detalle
    fieldsets = (
        (None, {
            'fields': ('proceso', 'texto', 'registrado_por')
        }),
        ('Trazabilidad', {
            'fields': ('fase_proceso', 'fecha_registro'),
            'classes': ('collapse',), # Ocultar por defecto
        }),
    )

    # Funciones personalizadas para obtener datos de modelos relacionados
    def candidato_nombre(self, obj):
        return obj.proceso.candidato.nombres_completos
    candidato_nombre.short_description = 'Candidato'
    
    def proceso_id(self, obj):
        return obj.proceso.pk
    proceso_id.short_description = 'ID Proceso'

    def fecha_registro_format(self, obj):
        # Muestra fecha y hora legible
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

    # Función para crear un enlace de descarga en la lista (mejor UX que solo el path)
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
    
    # Campos por los que se puede buscar
    search_fields = (
        'candidato__nombres_completos', 
        'candidato__DNI', 
        'observaciones'
    )
    
    # Campos que se muestran en el formulario de detalle/edición
    fieldsets = (
        (None, {
            'fields': ('candidato', 'proceso', 'tipo_documento', 'archivo', 'observaciones'),
        }),
        ('Metadatos', {
            'fields': ('fecha_subida', 'subido_por'),
            'classes': ('collapse',), # Opcional: Oculta por defecto
        }),
    )
    
    # Hacer que algunos campos se muestren pero no sean editables
    readonly_fields = ('fecha_subida', 'subido_por')
    
    @admin.display(description='Candidato')
    def candidato_link(self, obj):
        from django.utils.html import format_html
        return format_html('<a href="{}">{}</a>',
                           f'/admin/candidatos/candidato/{obj.candidato.pk}/change/', # Ajusta 'tu_app_name'
                           obj.candidato.nombres_completos)
    
    # Muestra el enlace para descargar el archivo
    @admin.display(description='Descargar Archivo')
    def archivo_link(self, obj):
        from django.utils.html import format_html
        if obj.archivo:
            return format_html('<a href="{}">Ver/Descargar</a>', obj.archivo.url)
        return "N/A"


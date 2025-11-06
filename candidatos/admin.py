from django.contrib import admin
from .models import (
    Empresa, Sede, Supervisor, Candidato, Proceso, RegistroAsistencia, 
    DatosCualificacion, ComentarioProceso, RegistroTest, DocumentoCandidato,
    TipoDocumento
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
        'objetivo_ventas_alcanzado', 'factor_actitud_aplica', 
        'supervisor', 'fecha_teorico', 'fecha_practico', 'fecha_contratacion','kanban_activo'
    ]
    readonly_fields = [
        'objetivo_ventas_alcanzado', 'factor_actitud_aplica', 
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
            'fields': ('fecha_teorico', 'fecha_practico', 'fecha_contratacion',),
            'classes': ('collapse',), 
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
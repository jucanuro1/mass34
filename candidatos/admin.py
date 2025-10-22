from django.contrib import admin
from .models import Empresa, Sede, Supervisor, Candidato, Proceso, RegistroAsistencia, DatosCualificacion
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
        'supervisor', 'fecha_teorico', 'fecha_practico', 'fecha_contratacion'
    ]
    readonly_fields = [
        'objetivo_ventas_alcanzado', 'factor_actitud_aplica', 
        'fecha_teorico', 'fecha_practico', 'fecha_contratacion'
    ]

@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ('DNI', 'nombres_completos', 'estado_actual', 'telefono_whatsapp','email','fecha_registro')
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
        'objetivo_ventas_alcanzado', 'factor_actitud_aplica'
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
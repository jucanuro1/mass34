from django.contrib import admin
from .models import Empresa, Sede, Supervisor, Candidato, Proceso, RegistroAsistencia,DatosCualificacion

# 1. Registro de Entidades Estáticas
admin.site.register(Empresa)
admin.site.register(Sede)
admin.site.register(Supervisor)

# 2. Configuración de la Vista de Candidato (Maestro)
class ProcesoInline(admin.TabularInline):
    """Muestra el historial de procesos de un candidato directamente en su ficha."""
    model = Proceso
    extra = 0
    # Se añaden los nuevos campos de performance a la vista rápida
    fields = [
        'fecha_inicio', 'empresa_proceso', 'sede_proceso', 'estado', 
        'objetivo_ventas_alcanzado', 'factor_actitud_aplica', 
        'supervisor', 'fecha_contratacion'
    ]
    # Hacemos los campos de performance y contratación de solo lectura en el inline
    # para que solo se editen desde la vista principal de Proceso.
    readonly_fields = ['objetivo_ventas_alcanzado', 'factor_actitud_aplica', 'fecha_contratacion']

@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    # La lista de display permanece igual
    list_display = ('DNI', 'nombres_completos', 'estado_actual', 'telefono_whatsapp','email','fecha_registro')
    # Los filtros ahora reflejan los nuevos estados de capacitación
    list_filter = ('estado_actual',) 
    search_fields = ('DNI', 'nombres_completos')
    inlines = [ProcesoInline] 

# 3. Configuración de las Vistas de Flujo y Data
class RegistroAsistenciaInline(admin.TabularInline):
    """Permite ver y gestionar la asistencia diaria de un proceso."""
    model = RegistroAsistencia
    extra = 1 # Muestra un formulario vacío para añadir rápidamente

@admin.register(Proceso)
class ProcesoAdmin(admin.ModelAdmin):
    # Se añade la fecha de inicio del proceso y el factor de actitud a la lista
    list_display = (
        'candidato', 'empresa_proceso', 'sede_proceso', 'fecha_inicio', 'estado', 
        'objetivo_ventas_alcanzado', 'factor_actitud_aplica'
    )
    list_filter = ('empresa_proceso', 'sede_proceso', 'estado', 'objetivo_ventas_alcanzado', 'factor_actitud_aplica')
    date_hierarchy = 'fecha_inicio' 
    search_fields = ('candidato__DNI', 'candidato__nombres_completos')
    
    # Define la estructura de la ficha de edición del Proceso
    fieldsets = (
        ('Información General del Candidato/Proceso', {
            'fields': ('candidato', 'empresa_proceso', 'sede_proceso', 'supervisor', 'fecha_inicio', 'estado')
        }),
        ('Resultados de las Pruebas y Contratación', {
            # Los campos de performance y contratación son cruciales para el resultado final
            'fields': (
                'objetivo_ventas_alcanzado', 
                'factor_actitud_aplica', 
                'fecha_contratacion'
            ),
            'classes': ('wide', 'extrapretty'), # Clases opcionales para mejor presentación
        }),
    )
    
    inlines = [RegistroAsistenciaInline] # Se añade para gestionar asistencia desde el Proceso

@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = ('proceso_candidato_dni', 'proceso_fecha_inicio', 'fecha', 'tipo', 'estado')
    list_filter = ('proceso__empresa_proceso', 'proceso__sede_proceso', 'estado', 'tipo', 'fecha')
    search_fields = ('proceso__candidato__DNI', 'proceso__candidato__nombres_completos')
    date_hierarchy = 'fecha'
    
    # Permite mostrar el DNI y fecha de inicio del Proceso en la lista de asistencia
    def proceso_candidato_dni(self, obj):
        return obj.proceso.candidato.DNI
    proceso_candidato_dni.short_description = 'DNI Candidato'

    def proceso_fecha_inicio(self, obj):
        return obj.proceso.fecha_inicio
    proceso_fecha_inicio.short_description = 'Inicio Proceso'


@admin.register(DatosCualificacion)
class DatosCualificacionAdmin(admin.ModelAdmin):
    # Campos a mostrar en la lista del admin
    list_display = (
        'candidato_nombre', 
        'secundaria_completa', 
        'experiencia_campanas_espanolas', 
        'experiencia_ventas_tipo', 
        'disponibilidad_horario'
    )
    
    # Filtros laterales
    list_filter = (
        'secundaria_completa', 
        'experiencia_campanas_espanolas', 
        'experiencia_ventas_tipo', 
        'disponibilidad_horario'
    )
    
    # Campos de búsqueda
    search_fields = (
        'candidato__nombres_completos', 
        'candidato__DNI', 
        'empresa_vendedor'
    )
    
    # Campo para ordenar por defecto
    ordering = ('candidato__nombres_completos',)
    
    # Campo calculado para mostrar el nombre del candidato en la lista
    def candidato_nombre(self, obj):
        return obj.candidato.nombres_completos
    candidato_nombre.short_description = 'Candidato'
    
    # Campos que se muestran en el detalle del registro (agrupados por Fieldsets)
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
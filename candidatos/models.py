from django.db import models
from datetime import date
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User

class Empresa(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "Empresas"

class Sede(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, help_text="Empresa a la que pertenece esta sede.")

    nombre = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"

    class Meta:
        unique_together = ('empresa', 'nombre')

class Supervisor(models.Model):
    nombre = models.CharField(max_length=150)

    def __str__(self):
        return self.nombre

class TipoDocumento(models.Model):
    nombre = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Nombre del Documento (Ej: DNI, Cédula)"
    )
    codigo_pais = models.CharField(
        max_length=5, 
        unique=True, 
        verbose_name="Código de País (Ej: PER, COL)"
    )
    longitud_requerida = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name="Longitud Fija (Ej: 8 para DNI)"
    )
    solo_numeros = models.BooleanField(
        default=True, 
        verbose_name="Requiere solo caracteres numéricos"
    )
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo_pais})"

    class Meta:
        verbose_name = "Tipo de Documento de Identidad"
        verbose_name_plural = "Tipos de Documento de Identidad"

MOTIVOS_DESCARTE = [
    ('NO_CONFIRMA', 'No Confirma Asistencia'),
    ('NO_SE_PRESENTE', 'No Se Presentó'),
    ('SALARIO_NO_CONVENIENTE', 'Salario No Conveniente'),
    ('PROBLEMAS_PERSONALES', 'Problemas Personales'),
    ('OTRO', 'Otro Motivo'),
]

class Candidato(models.Model):
    DNI = models.CharField(max_length=30, primary_key=True, unique=True, verbose_name="Número de Documento")
    tipo_documento = models.ForeignKey(
        'TipoDocumento', 
        on_delete=models.PROTECT, 
        verbose_name='Tipo de Identificación', 
        default=1 
    )
    nombres_completos = models.CharField(max_length=255)
    edad = models.IntegerField(blank=True, null=True, help_text="Edad del candidato.")
    telefono_whatsapp = models.CharField(max_length=9)
    email = models.EmailField(max_length=255,blank=True,null=True)
    distrito = models.CharField(max_length=200)
    sede_registro = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        help_text="Sede donde se registró o fue contactado inicialmente el candidato."
    )

    fecha_registro = models.DateField(
        auto_now_add=True,
        help_text="Fecha de creación del registro del candidato."
    )

    ESTADOS = [
        ('REGISTRADO', 'Registrado (Primer Contacto)'),
        ('CONVOCADO', 'Convocado (Segundo Contacto)'),
        ('CAPACITACION_TEORICA', 'En Capacitación Teórica'),
        ('CAPACITACION_PRACTICA', 'En Capacitación Práctica'),
        ('NO_APTO', 'No Apto (Descarte por rendimiento)'),
        ('DESISTE', 'Desiste / No Confirmó / Abandona'),
        ('CONTRATADO', 'Contratado'),
    ]
    estado_actual = models.CharField(max_length=250, choices=ESTADOS, default='REGISTRADO')
    usuario_ultima_modificacion = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='candidatos_modificados',
    )
    motivo_descarte = models.CharField(
        max_length=255, 
        choices=MOTIVOS_DESCARTE, 
        blank=True, 
        null=True, 
        help_text="Motivo por el cual el candidato desistió o fue descartado."
    )

    def clean(self):
        if self.DNI and not self.DNI.isdigit():
            raise ValidationError({'DNI': 'El DNI solo debe contener dígitos (0-9).'})
        super().clean()

    def __str__(self):
        return f"{self.nombres_completos} ({self.DNI})"
    
    def get_ultimo_movimiento_display(self):
        MOVIMIENTO_MAP = dict(RegistroAsistencia.TIPO_MOVIMIENTO)
        return MOVIMIENTO_MAP.get(self.ultimo_movimiento, 'Desconocido')
    
    def get_ultimo_movimiento_color_class(self):
        movimiento = getattr(self, 'ultimo_movimiento', None)
        
        if not movimiento:
            return 'text-gray-500'    
        if movimiento == 'ENTRADA':
            return 'text-green-600 bg-green-100 rounded-full px-2' 
        elif movimiento == 'SALIDA':
            return 'text-red-600 bg-red-100 rounded-full px-2'   
        elif movimiento == 'REGISTRO':
            return 'text-yellow-700 bg-yellow-100 rounded-full px-2' 
        
        return 'text-gray-500'



class DatosCualificacion(models.Model):
    candidato = models.OneToOneField(
        Candidato, 
        on_delete=models.CASCADE, 
        primary_key=True
    )
    
    distrito = models.CharField(max_length=100, help_text="Distrito de residencia.")
    secundaria_completa = models.BooleanField(
        help_text="¿Tienes secundaria completa?"
    )
    
    # (image_dfc79a.png)
    experiencia_campanas_espanolas = models.BooleanField(
        help_text="¿Has tenido experiencia con campañas españolas como vendedor?"
    )
    
    TIPO_VENTA_CHOICES = [
        ('CALLCENTER', 'Sí, ventas por teléfono (CALLCENTER)'),
        ('ESCRITOS', 'Sí, ventas por medios escritos'),
        ('PRESENCIALES', 'Sí, ventas presenciales'),
        ('NO', 'No'),
    ]
    experiencia_ventas_tipo = models.CharField(
        max_length=20,
        choices=TIPO_VENTA_CHOICES,
        default='NO',
        help_text="Tipo de experiencia en ventas."
    )
    
    empresa_vendedor = models.CharField(
        max_length=150, 
        blank=True, 
        null=True, 
        help_text="¿En qué empresa has trabajado como vendedor?"
    )
    
    TIEMPO_EXP_CHOICES = [
        ('MENOS_3', 'Menos de 3 meses'),
        ('MENOS_6', 'Menos de 6 meses'),
        ('MENOS_1_ANIO', 'Menos de 1 año'),
        ('MAS_1_ANIO', 'De 1 año a más'),
    ]
    tiempo_experiencia_vendedor = models.CharField(
        max_length=20,
        choices=TIEMPO_EXP_CHOICES,
        blank=True, 
        null=True,
        help_text="¿Cuánto tiempo de experiencia has tenido como vendedor?"
    )
    
    conforme_beneficios = models.CharField(
        max_length=10, 
        choices=[('SI', 'Sí'), ('NO', 'No'), ('OTRO', 'Otro')],
        help_text="¿Estás conforme con los beneficios que te damos?"
    )
    detalle_beneficios_otro = models.TextField(
        blank=True, 
        null=True, 
        help_text="Detalle si la respuesta a beneficios fue 'Otro'."
    )
    
    disponibilidad_horario = models.BooleanField(
        help_text="¿Tienes disponibilidad para trabajar en el horario de 06:15am a 03:00pm?"
    )

    discapacidad_enfermedad_cronica = models.TextField(
        blank=True, 
        null=True,
        help_text="¿Tienes alguna discapacidad o enfermedad crónica?"
    )
    
    dificultad_habla = models.BooleanField(
        help_text="¿Tienes alguna dificultad en el habla?"
    )

    # El campo del teléfono está en Candidato, no lo repetimos.

    def __str__(self):
        return f"Cualificación de {self.candidato.nombres_completos}"
    

class Proceso(models.Model):
    candidato = models.ForeignKey(
        'Candidato', 
        on_delete=models.CASCADE, 
        related_name='procesos' 
    )
    fecha_inicio = models.DateField(help_text="Fecha de inicio de esta convocatoria/proceso.")

    supervisor = models.ForeignKey('Supervisor', on_delete=models.SET_NULL, null=True, blank=True)

    empresa_proceso = models.ForeignKey('Empresa', on_delete=models.CASCADE, help_text="Cliente para este ciclo de prueba.")
    sede_proceso = models.ForeignKey('Sede', on_delete=models.CASCADE, help_text="Sede donde tomó la prueba.")
    kanban_activo = models.BooleanField(default=True)

    ESTADOS_PROCESO = [
        ('INICIADO', 'Iniciado/Confirmado'),
        ('TEORIA', 'Capacitación Teórica'),
        ('PRACTICA', 'Capacitación Práctica'),
        ('CONTRATADO', 'Contratado'),
        ('NO_APTO', 'No Apto (No cumple pruebas/objetivos)'),
        ('ABANDONO', 'Abandono/Deserción')
    ]
    estado = models.CharField(max_length=15, choices=ESTADOS_PROCESO, default='INICIADO')

    # Campos para guardar la fecha de llegada a cada etapa (Mantener null=True, blank=True)
    fecha_teorico = models.DateField(
        null=True, blank=True,
        help_text="Fecha en que el candidato ingresó a Capacitación Teórica."
    )
    fecha_practico = models.DateField(
        null=True, blank=True,
        help_text="Fecha en que el candidato ingresó a Capacitación Práctica (OJT)."
    )
    fecha_contratacion = models.DateField(
        null=True, blank=True, 
        help_text="Fecha de firma del contrato (si aplica)."
    )
    
    objetivo_ventas_alcanzado = models.BooleanField(
        default=False,
        help_text="Resultado de la prueba de objetivo de ventas/KPI en práctica."
    )
    factor_actitud_aplica = models.BooleanField(
        default=False,
        help_text="Indica si se queda por 'Actitud' a pesar de fallar otras pruebas (Opción escasa)."
    )

    # Lógica de guardado automático de fechas (Sobrescribe el método save)
    def save(self, *args, **kwargs):
        
        old_estado = None
        if self.pk:
            try:
                # Recuperar el estado actual del objeto ANTES de que se apliquen los cambios
                old_proceso = Proceso.objects.get(pk=self.pk)
                old_estado = old_proceso.estado
            except Proceso.DoesNotExist:
                pass # Nuevo objeto

        current_date = date.today() 
        
        # Transición a TEORIA: solo si el estado cambia A 'TEORIA' y el campo está vacío
        if self.estado == 'TEORIA' and old_estado != 'TEORIA' and not self.fecha_teorico:
            self.fecha_teorico = current_date
            
        # Transición a PRACTICA: solo si el estado cambia A 'PRACTICA' y el campo está vacío
        elif self.estado == 'PRACTICA' and old_estado != 'PRACTICA' and not self.fecha_practico:
            self.fecha_practico = current_date
            
        # Transición a CONTRATADO: solo si el estado cambia A 'CONTRATADO' y el campo está vacío
        elif self.estado == 'CONTRATADO' and old_estado != 'CONTRATADO' and not self.fecha_contratacion:
            self.fecha_contratacion = current_date
        
        # Llama al método save original para guardar el objeto y las fechas
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Proceso {self.pk}: {self.candidato.DNI} - {self.fecha_inicio.strftime('%Y-%m-%d')} ({self.get_estado_display()})"

    class Meta:
        unique_together = ('candidato', 'fecha_inicio', 'empresa_proceso')


class RegistroAsistencia(models.Model):
    # Relación Principal: La asistencia siempre pertenece a un proceso.
    proceso = models.ForeignKey('Proceso', on_delete=models.CASCADE)
    
    # 🆕 Campo Adicional SOLICITADO (opcional para mantener la normalización)
    # Lo vinculamos directamente al candidato para consultas rápidas, si se desea.
    candidato = models.ForeignKey(
        'Candidato', 
        on_delete=models.CASCADE, 
        null=True, blank=True, # Lo dejamos opcional para manejar migraciones
        help_text="Candidato asociado (duplicado para optimización de consultas)."
    )
    
    # 🆕 CAMBIO CLAVE: Usamos DateTimeField para hora exacta de registro
    momento_registro = models.DateTimeField(default=timezone.now)
    
    # Nuevo: Para diferenciar entre la hora de entrada y la hora de salida
    TIPO_MOVIMIENTO = [
        ('ENTRADA', 'Entrada'),
        ('SALIDA', 'Salida'),
        ('REGISTRO', 'Registro Único') # Para Convocado/Teoría si no requieren hora de salida
    ]

    estado_asistencia = models.CharField(
            max_length=1, 
            default='A', # Por defecto 'A' (Asistió)
            choices=[('A', 'Asistió'), ('F', 'Faltó'), ('T', 'Tardanza')]
        )
    registrado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='registros_creados'
    )

    movimiento = models.CharField(max_length=8, choices=TIPO_MOVIMIENTO, default='REGISTRO')

    FASE_ASISTENCIA = [
        ('CONVOCADO', 'Convocado'),
        ('TEORIA', 'Capacitación Teórica'),
        ('PRACTICA', 'Capacitación Práctica (OJT)'),
    ]
    fase_actual = models.CharField(max_length=15, choices=FASE_ASISTENCIA)

    ASISTENCIA_ESTADO = [
        ('A', 'Asistió (Puntual)'),
        ('T', 'Tardanza'),
        ('F', 'Faltó'),
        ('J', 'Justificado') 
    ]
    estado = models.CharField(max_length=1, choices=ASISTENCIA_ESTADO, default='A')

    class Meta:
        verbose_name_plural = "Registros de Asistencia"
        ordering = ['-momento_registro']

    def __str__(self):
        dni = self.candidato.DNI if self.candidato else self.proceso.candidato.DNI
        return f"{dni} - {self.fase_actual} ({self.get_movimiento_display()}) el {self.momento_registro.strftime('%d/%m/%Y %H:%M')}"

    def save(self, *args, **kwargs):
        if not self.candidato and self.proceso_id:
            self.candidato = self.proceso.candidato
        super().save(*args, **kwargs)

    def get_movimiento_color_class(self):
        """ Devuelve la clase CSS de color basada en el tipo de movimiento. """
        
        if self.movimiento == 'ENTRADA':
            return 'text-green-600 bg-green-100' 
        elif self.movimiento == 'SALIDA':
            return 'text-red-600 bg-red-100'   
        elif self.movimiento == 'REGISTRO':
            return 'text-yellow-700 bg-yellow-100' 
        
        return 'text-gray-500 bg-gray-100'


class ComentarioProceso(models.Model):
    """
    Registra observaciones o comentarios sobre un candidato durante una fase de su proceso.
    """
    
    proceso = models.ForeignKey(
        'Proceso', 
        on_delete=models.CASCADE, 
        related_name='comentarios',
        help_text="Proceso de convocatoria al que se le añade el comentario."
    )
    

    fase_proceso = models.CharField(
        max_length=150, 
        choices=Proceso.ESTADOS_PROCESO, # Reutiliza los choices del modelo Proceso
        default='INICIADO',
        help_text="Fase del proceso en el momento del registro del comentario."
    )
    
    texto = models.TextField(help_text="Contenido de la observación o comentario.")
    
    # Trazabilidad
    registrado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Usuario del sistema que realizó la observación."
    )
    
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora exactas del registro."
    )
    
    def __str__(self):
        return f"Comentario en {self.proceso.candidato.DNI} ({self.get_fase_proceso_display()})"
    
    class Meta:
        verbose_name = "Comentario de Proceso"
        verbose_name_plural = "Comentarios de Procesos"
        ordering = ['-fecha_registro'] 


class RegistroTest(models.Model):
    """
    Registra la subida o realización de un test/archivo de un candidato durante una fase de su proceso.
    Permite registrar múltiples tests/archivos por proceso.
    """
    proceso = models.ForeignKey(
        'Proceso', 
        on_delete=models.CASCADE, 
        related_name='tests_registrados',
        help_text="Proceso de convocatoria al que pertenece el registro del test."
    )

    fase_proceso = models.CharField(
        max_length=150, 
        choices=Proceso.ESTADOS_PROCESO, 
        default='TEORIA', 
        help_text="Fase del proceso en el momento del registro del test."
    )
    
    TIPO_TEST_CHOICES = [
        ('PSICOLOGICO', 'Test Psicológico'),
        ('CONOCIMIENTO', 'Test de Conocimiento'),
        ('VENTAS_PRACTICA', 'Simulación/Prueba de Ventas'),
        ('DOCUMENTO', 'Documento/Archivo Adicional'),
        ('OTRO', 'Otro')
    ]
    tipo_test = models.CharField(
        max_length=50, 
        choices=TIPO_TEST_CHOICES,
        help_text="Tipo de test o archivo subido."
    )
    
    archivo_url = models.FileField(
        upload_to='proceso_tests/%Y/%m/', 
        blank=True, 
        null=True,
        help_text="Archivo subido (PDF, imagen, etc.)."
    )
    
    resultado_obtenido = models.CharField(
        max_length=50,
        blank=True, 
        null=True,
        help_text="Resultado o calificación obtenida (ej. 'Apto', '9/10', 'No Apto')."
    )
    
    registrado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Usuario del sistema que registró el test/archivo."
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora exactas del registro."
    )
    
    def clean(self):
        """Asegura que al menos se suba un archivo."""
        if not self.archivo_url:
             raise ValidationError({
                'archivo_url': 'Debe subir un archivo para registrar el test/documento.'
             })


    def __str__(self):
        return f"{self.get_tipo_test_display()} de {self.proceso.candidato.DNI} en {self.get_fase_proceso_display()}"
        
    class Meta:
        verbose_name = "Registro de Test/Archivo"
        verbose_name_plural = "Registros de Tests/Archivos"
        ordering = ['-fecha_registro']

class DocumentoCandidato(models.Model):
    TIPO_DOCUMENTO_OPCIONES = [
        ('CERTIFICADO_LABORAL', 'Certificado de Experiencia Laboral'),
        ('CUL', 'Certificado Único Laboral (CUL)'),
        ('ANTECEDENTES', 'Certificado de Antecedentes'),
        ('CURRICULUM', 'Curriculum Vitae (CV)'),
        ('OTRO', 'Otro Documento'),
    ]
    
    candidato = models.ForeignKey(
        'Candidato', 
        on_delete=models.CASCADE,
        related_name='documentos_laborales',
        verbose_name="Candidato Asociado"
    )
    proceso = models.ForeignKey(
        'Proceso', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        verbose_name="Proceso Relacionado"
    )
    
    tipo_documento = models.CharField(
        max_length=50,
        choices=TIPO_DOCUMENTO_OPCIONES,
        verbose_name="Tipo de Documento"
    )
    
    archivo = models.FileField(
        upload_to='candidatos/documentos/',
        verbose_name="Archivo Adjunto"
    )
    
    observaciones = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Observaciones"
    )
    
    fecha_subida = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Subida"
    )
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Usuario que Subió"
    )
    
    class Meta:
        verbose_name = "Documento del Candidato"
        verbose_name_plural = "Documentos del Candidato"
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"{self.candidato.nombres_completos} - {self.get_tipo_documento_display()}"
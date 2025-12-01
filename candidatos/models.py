from django.db import models
from datetime import date
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

class Empresa(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(
        upload_to='logos_empresa/', 
        null=True, 
        blank=True, 
        help_text="Logo principal de la empresa."
    )

    color_primario = models.CharField(
        max_length=20, 
        default='blue-600', 
        help_text="Color Tailwind CSS principal (ej: red-600, blue-900)."
    )

    color_secundario = models.CharField(
        max_length=20, 
        default='gray-100', 
        help_text="Color Tailwind CSS secundario (ej: gray-100, yellow-300)."
    )

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
    kanban_activo = models.BooleanField(
        default=True,
        help_text="Controla si el candidato es visible en el tablero Kanban/Dashboard."
    )

    ESTADOS = [
        ('REGISTRADO', 'Registrado'),
        ('CONVOCADO', 'Convocado'),
        ('CONFIRMADO', 'Confirmado'),
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
        ('CONVOCADO', 'Convocado'),
        ('CONFIRMADO', 'Confirmado'),
        ('TEORIA', 'Capacitación Teórica'),
        ('PRACTICA', 'Capacitación Práctica'),
        ('CONTRATADO', 'Contratado'),
        ('NO_APTO', 'No Apto (No cumple pruebas/objetivos)'),
        ('ABANDONO', 'Abandono/Deserción')
    ]
    estado = models.CharField(max_length=15, choices=ESTADOS_PROCESO, default='CONVOCADO')

    fecha_confirmado = models.DateField(null=True, blank=True, help_text="Fecha en el que el cadidato pasó a Confirmado")

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
    factor_aptitud_aplica = models.BooleanField(
        default=False,
        help_text="Indica si se queda por 'Aptitud' a pesar de fallar otras pruebas (Opción escasa)."
    )

    def save(self, *args, **kwargs):
        
        old_estado = None
        if self.pk:
            try:
                old_proceso = Proceso.objects.get(pk=self.pk)
                old_estado = old_proceso.estado
            except Proceso.DoesNotExist:
                pass 

        current_date = date.today() 

        if self.estado == 'CONFIRMADO' and old_estado != 'CONFIRMADO' and not self.fecha_confirmado:
            self.fecha_confirmado = current_date 

        if self.estado == 'CONFIRMADO' and old_estado != 'CONFIRMADO' and not self.fecha_confirmado:
            self.fecha_confirmado = current_date
        
        if self.estado == 'TEORIA' and old_estado != 'TEORIA' and not self.fecha_teorico:
            self.fecha_teorico = current_date
            
        elif self.estado == 'PRACTICA' and old_estado != 'PRACTICA' and not self.fecha_practico:
            self.fecha_practico = current_date
            
        elif self.estado == 'CONTRATADO' and old_estado != 'CONTRATADO' and not self.fecha_contratacion:
            self.fecha_contratacion = current_date
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Proceso {self.pk}: {self.candidato.DNI} - {self.fecha_inicio.strftime('%Y-%m-%d')} ({self.get_estado_display()})"

    class Meta:
        unique_together = ('candidato', 'fecha_inicio', 'empresa_proceso')

class RegistroAsistencia(models.Model):
    proceso = models.ForeignKey('Proceso', on_delete=models.CASCADE)
    
    candidato = models.ForeignKey(
        'Candidato', 
        on_delete=models.CASCADE, 
        null=True, blank=True, 
        help_text="Candidato asociado (duplicado para optimización de consultas)."
    )
    momento_registro = models.DateTimeField(default=timezone.now)
    
    TIPO_MOVIMIENTO = [
        ('ENTRADA', 'Entrada'),
        ('SALIDA', 'Salida')
    ]

    estado_asistencia = models.CharField(
            max_length=1, 
            default='A', 
            choices=[('A', 'Asistió'), ('F', 'Faltó'), ('T', 'Tardanza')]
        )
    registrado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='registros_creados'
    )

    movimiento = models.CharField(max_length=8, choices=TIPO_MOVIMIENTO, default='ENTRADA')

    FASE_ASISTENCIA = [
        ('CONVOCADO', 'Convocado'),
        ('CONFIRMADO', 'Confirmado'),
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
        choices=Proceso.ESTADOS_PROCESO, 
        default='CONVOCADO',
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
    
class MensajePlantilla(models.Model):
    """
    1. Almacena el texto base de los mensajes que se pueden reutilizar en las campañas.
    """
    titulo = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name="Título Único de la Plantilla",
        help_text="Nombre que identifica la plantilla, ej: 'CONVOCATORIA_LUNES_9AM'"
    )
    contenido_texto = models.TextField(
        verbose_name="Contenido del Mensaje",
        help_text="Texto con las variables de personalización (ej: {nombres_completos})."
    )
    variables_usadas = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Variables de Candidato usadas en el texto (separadas por coma), ej: DNI, telefono_whatsapp, sede_registro."
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='plantillas_creadas'
    )

    def __str__(self):
        return self.titulo
    
    class Meta:
        verbose_name = "Plantilla de Mensaje"
        verbose_name_plural = "Plantillas de Mensajes"
        ordering = ['titulo']

class TareaEnvioMasivo(models.Model):
    """
    2. Registro central de una campaña de envío masivo (el Historial que se muestra en el modal).
    """
    
    PROCESO_CHOICES = [
        ('GLOBAL', 'Envío Global/Múltiples Estados'),
        ('REGISTRADO', 'Registrado (Primer Contacto)'), 
        ('CONVOCADO', 'Convocado (Segundo Contacto)'),
        ('CONFIRMADO', 'Confirmado'),
        ('CAPACITACION_TEORICA', 'En Capacitación Teórica'),
        ('CONTRATADO','Contratado')
    ]
    proceso_tipo = models.CharField(
        max_length=50, 
        choices=PROCESO_CHOICES, 
        default='GLOBAL',
        verbose_name="Filtro de Proceso Usado",
        help_text="Estado/Filtro usado para seleccionar a los candidatos (Corresponde a tu campo 'Proceso' en el modal)."
    )
    
    fecha_origen = models.DateField(
        verbose_name="Fecha de Origen de los Datos",
        help_text="Fecha de registro o modificación que se usó como filtro (Corresponde a tu campo 'Fecha Origen' en el modal)."
    )
    
    fecha_inicio = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Inicio del Envío"
    )
    usuario_que_envia = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Usuario del Sistema"
    )

    mensaje_plantilla = models.ForeignKey(
        MensajePlantilla,
        on_delete=models.PROTECT,
        verbose_name="Plantilla Enviada"
    )

    total_contactos = models.PositiveIntegerField(default=0, help_text="Número total de contactos que deberían recibir el mensaje.")
    
    ESTADOS_TAREA = [
        ('PENDIENTE', 'Pendiente (En cola de Celery)'),
        ('EN_PROCESO', 'En Proceso'),
        ('COMPLETADO', 'Completado'),
        ('FALLIDO', 'Fallido (Error en el worker)')
    ]
    estado = models.CharField(max_length=15, choices=ESTADOS_TAREA, default='PENDIENTE')
    
    task_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        unique=True,
        help_text="ID de la tarea en Celery para seguimiento asíncrono."
    )
    
    total_entregados = models.PositiveIntegerField(default=0)
    total_fallidos = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Tarea #{self.pk} - {self.get_proceso_tipo_display()} ({self.get_estado_display()})"
    
    class Meta:
        verbose_name = "Tarea de Envío Masivo"
        verbose_name_plural = "Tareas de Envío Masivo"
        ordering = ['-fecha_inicio']

class DetalleEnvio(models.Model):
    """
    3. El registro individual de cada mensaje enviado. Es la auditoría fina.
    """
    tarea_envio = models.ForeignKey(
        TareaEnvioMasivo,
        on_delete=models.CASCADE,
        related_name='detalles_envio',
        verbose_name="Campaña/Tarea Asociada"
    )
    
    contacto = models.ForeignKey(
        'Candidato', 
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Candidato/Contacto"
    )
    
    telefono = models.CharField(max_length=20, help_text="Teléfono final usado (campo telefono_whatsapp del Candidato).")
    
    contenido_final = models.TextField(
        help_text="Contenido del mensaje después de la personalización de variables."
    )
    
    ESTADOS_META = [
        ('ENVIADO', 'Enviado'),
        ('ENTREGADO', 'Entregado'),
        ('LEIDO', 'Leído'),
        ('FALLIDO', 'Fallido')
    ]
    estado_meta = models.CharField(
        max_length=15,
        choices=ESTADOS_META,
        default='ENVIADO',
        verbose_name="Estado de WhatsApp"
    )
    
    id_mensaje_meta = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        unique=True,
        help_text="ID único devuelto por la API de Meta/WhatsApp (Webhook ID)."
    )
    
    fecha_envio = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        try:
            dni_display = self.contacto.DNI
        except ObjectDoesNotExist:
            dni_guardado = getattr(self, 'contacto_id', '???') 
            dni_display = f'DNI Eliminado ({dni_guardado})'
        
        return f"Detalle {self.pk}: {dni_display} - {self.get_estado_meta_display()}"
        
    
    class Meta:
        verbose_name = "Detalle de Envío Individual"
        verbose_name_plural = "Detalles de Envíos Individuales"
        unique_together = ('tarea_envio', 'contacto')
        ordering = ['-fecha_envio']
from django.db import models
from datetime import date
from django.core.exceptions import ValidationError

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

class Candidato(models.Model):
    DNI = models.CharField(max_length=8, unique=True, primary_key=True)
    nombres_completos = models.CharField(max_length=255)
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
        ('CONTRATADO', 'Contratado'),
    ]
    estado_actual = models.CharField(max_length=250, choices=ESTADOS, default='REGISTRADO')

    def clean(self):
        if self.DNI and not self.DNI.isdigit():
            raise ValidationError({'DNI': 'El DNI solo debe contener dígitos (0-9).'})
        super().clean()

    def __str__(self):
        return f"{self.nombres_completos} ({self.DNI})"

class DatosCualificacion(models.Model):
    # Relación 1:1 con Candidato. Esto asegura que cada candidato solo tenga un set de respuestas.
    # Usamos on_delete=models.CASCADE: si el candidato es eliminado, también se eliminan sus respuestas.
    candidato = models.OneToOneField(
        Candidato, 
        on_delete=models.CASCADE, 
        primary_key=True
    )
    
    # --- CAMPOS DEL FORMULARIO REAL (Basado en las imágenes) ---
    
    # (image_dfc7de.png)
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
    
    # (image_dfc727.png)
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
    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE)
    fecha = models.DateField()

    TIPO_ASISTENCIA = [
        ('TEORIA', 'Teoría'),
        ('PRACTICA', 'Práctica/Llamada')
    ]
    tipo = models.CharField(max_length=8, choices=TIPO_ASISTENCIA)

    ASISTENCIA_ESTADO = [
        ('A', 'Asistió'),
        ('F', 'Faltó'),
        ('T', 'Tardanza'),
        ('B', 'Baja/Desistió')
    ]
    estado = models.CharField(max_length=1, choices=ASISTENCIA_ESTADO, default='F')

    class Meta:
        unique_together = ('proceso', 'fecha', 'tipo')
        verbose_name_plural = "Registros de Asistencia"

    def __str__(self):
        return f"{self.proceso.candidato.DNI} - {self.fecha} - {self.get_estado_display()}"
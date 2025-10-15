from django.db import models
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

class Proceso(models.Model):
    candidato = models.ForeignKey(
        Candidato, 
        on_delete=models.CASCADE, 
        related_name='procesos' 
    )
    fecha_inicio = models.DateField(help_text="Fecha de inicio de esta convocatoria/proceso.")

    supervisor = models.ForeignKey(Supervisor, on_delete=models.SET_NULL, null=True, blank=True)

    empresa_proceso = models.ForeignKey(Empresa, on_delete=models.CASCADE, help_text="Cliente para este ciclo de prueba.")
    sede_proceso = models.ForeignKey(Sede, on_delete=models.CASCADE, help_text="Sede donde tomó la prueba.")

    ESTADOS_PROCESO = [
        ('INICIADO', 'Iniciado/Confirmado'),
        ('TEORIA', 'Capacitación Teórica'),
        ('PRACTICA', 'Capacitación Práctica'),
        ('CONTRATADO', 'Contratado'),
        ('NO_APTO', 'No Apto (No cumple pruebas/objetivos)'),
        ('ABANDONO', 'Abandono/Deserción')
    ]
    estado = models.CharField(max_length=15, choices=ESTADOS_PROCESO, default='INICIADO')

    objetivo_ventas_alcanzado = models.BooleanField(
        default=False,
        help_text="Resultado de la prueba de objetivo de ventas/KPI en práctica."
    )
    factor_actitud_aplica = models.BooleanField(
        default=False,
        help_text="Indica si se queda por 'Actitud' a pesar de fallar otras pruebas (Opción escasa)."
    )

    fecha_contratacion = models.DateField(null=True, blank=True, help_text="Fecha de firma del contrato (si aplica).")

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
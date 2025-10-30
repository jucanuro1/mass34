from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, DetailView 
from django.db import IntegrityError
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction, DatabaseError, OperationalError, IntegrityError
from django.http import JsonResponse, HttpResponse,HttpResponseForbidden
from django.db.models import Q, Count, Prefetch
from .models import Candidato, Proceso, Empresa, Sede, Supervisor, RegistroAsistencia,DatosCualificacion, ComentarioProceso, RegistroTest, MOTIVOS_DESCARTE
from datetime import date, datetime
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
import pandas as pd
import io
import json
from datetime import date
from django.db import models
import time


class RegistroCandidatoView(LoginRequiredMixin, View):
    def get(self, request):
        context = {
            'title': 'Registro Rápido de Candidato',
            'sedes': Sede.objects.all()
        }
        return render(request, 'registro_candidato.html', context)

    def post(self, request):
        dni = request.POST.get('DNI', '').strip()
        nombres_completos = request.POST.get('nombres_completos', '').strip()
        telefono_whatsapp = request.POST.get('telefono_whatsapp', '').strip()
        correo_electronico = request.POST.get('correo_electronico', '').strip()
        sede_id = request.POST.get('sede_id', '').strip()

        context = {
            'title': 'Registro Rápido de Candidato',
            'DNI': dni,
            'nombres_completos': nombres_completos,
            'telefono_whatsapp': telefono_whatsapp,
            'correo_electronico': correo_electronico,
            'sede_id': sede_id,
            'sedes': Sede.objects.all()
        }

        if not all([dni, nombres_completos, telefono_whatsapp, sede_id]):
            messages.error(request, 'Los campos DNI, Nombres, Teléfono y **Sede** son obligatorios.')
            return render(request, 'registro_candidato.html', context)

        if not dni.isdigit():
            messages.error(request, 'El DNI debe contener solo números.')
            return render(request, 'registro_candidato.html', context)

        try:
            sede = get_object_or_404(Sede, pk=sede_id)

            candidato, created = Candidato.objects.get_or_create(
                DNI=dni,
                defaults={
                    'nombres_completos': nombres_completos,
                    'telefono_whatsapp': telefono_whatsapp,
                    'email': correo_electronico if correo_electronico else None,
                    'sede_registro': sede,
                    'estado_actual': 'REGISTRADO'
                }
            )

            if created:
                messages.success(request, f'Candidato {candidato.nombres_completos} registrado con éxito en la sede **{sede.nombre}**.')
            else:
                Candidato.objects.filter(DNI=dni).update(
                    nombres_completos=nombres_completos,
                    telefono_whatsapp=telefono_whatsapp,
                    email=correo_electronico if correo_electronico else None,
                    sede_registro=sede,
                )
                messages.warning(request, f'Candidato {candidato.nombres_completos} ya existía. Datos actualizados.')

            return redirect('kanban_dashboard')

        except Sede.DoesNotExist:
            messages.error(request, "La Sede de registro seleccionada no es válida.")
            return render(request, 'registro_candidato.html', context)
        except IntegrityError:
            messages.error(request, f'Error de base de datos: El DNI {dni} ya está registrado.')
            return render(request, 'registro_candidato.html', context)
        except Exception as e:
            messages.error(request, f'Error inesperado al guardar: {e}')
            return render(request, 'registro_candidato.html', context)

class IniciarProcesoView(LoginRequiredMixin, View):
    def post(self, request, dni):
        candidato = get_object_or_404(Candidato, DNI=dni)

        # Verificamos si ya existe un proceso activo que no esté en estado final
        proceso_activo_no_finalizado = Proceso.objects.filter(
            candidato=candidato
        ).exclude(estado__in=['CONTRATADO', 'NO_APTO']).exists()

        if proceso_activo_no_finalizado:
            messages.error(request, f"El candidato {candidato.nombres_completos} (DNI: {dni}) ya tiene un proceso activo. Finalícelo primero.")
            return redirect('kanban_dashboard')


        fecha_inicio_str = request.POST.get('fecha_inicio')

        if not fecha_inicio_str:
            messages.error(request, "La fecha de inicio (convocatoria) es obligatoria.")
            return redirect('kanban_dashboard')

        sede_registro = candidato.sede_registro

        if not sede_registro:
            messages.error(request, f"El candidato {dni} no tiene una sede de registro asignada. No se puede convocar.")
            return redirect('kanban_dashboard')

        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()

            empresa_proceso = sede_registro.empresa

            proceso = Proceso.objects.create(
                candidato=candidato,
                fecha_inicio=fecha_inicio,
                empresa_proceso=empresa_proceso,
                sede_proceso=sede_registro,
                estado='CONVOCADO'
            )

            candidato.estado_actual = 'CONVOCADO'
            candidato.save()

            messages.success(request, f'Candidato {candidato.nombres_completos} convocado con éxito el {fecha_inicio_str} en {empresa_proceso.nombre} ({sede_registro.nombre}).')

        except ValueError:
            messages.error(request, "Formato de fecha de inicio inválido. Use AAAA-MM-DD.")
        except IntegrityError:
            messages.error(request, f"Ya existe un proceso para {candidato.DNI} en la fecha {fecha_inicio_str} para esta empresa.")
        except Exception as e:
            messages.error(request, f'Error al crear el Proceso: {e}')

        return redirect('kanban_dashboard')

class ActualizarProcesoView(LoginRequiredMixin, View):
    def post(self, request, proceso_id):
        proceso = get_object_or_404(Proceso, pk=proceso_id)
        candidato = proceso.candidato

        estado_anterior = proceso.estado # Capturar el estado antes de la actualización

        nuevo_estado_proceso = request.POST.get('estado_proceso')

        objetivo_ventas = request.POST.get('objetivo_ventas_alcanzado') == 'on'
        factor_actitud = request.POST.get('factor_actitud_aplica') == 'on'

        # Mapeo de estados de Proceso (Proceso.estado) a estados de Candidato (Candidato.estado_actual)
        estado_candidato_map = {
            'INICIADO': 'CONVOCADO', 
            'TEORIA': 'CAPACITACION_TEORICA',
            'PRACTICA': 'CAPACITACION_PRACTICA',
            'CONTRATADO': 'CONTRATADO',
            'NO_APTO': 'NO_APTO', 
            'ABANDONO': 'ABANDONO'
        }

        if not nuevo_estado_proceso:
            messages.error(request, "Debe seleccionar un nuevo estado para el proceso.")
            return redirect('kanban_dashboard')

        try:
            with transaction.atomic():
                
                proceso.estado = nuevo_estado_proceso

                if nuevo_estado_proceso in ['CONTRATADO', 'NO_APTO']:
                    proceso.objetivo_ventas_alcanzado = objetivo_ventas
                    proceso.factor_actitud_aplica = factor_actitud

                # ❌ ELIMINADA: La asignación de fecha manual (proceso.fecha_contratacion = date.today())
                # La lógica se encuentra ahora en el método Proceso.save()

                # 1. GUARDAR PROCESO: Esto activa la lógica de auto-fechado en el modelo.
                proceso.save()

                # 2. ACTUALIZAR ESTADO MAESTRO DEL CANDIDATO
                nuevo_estado_maestro = estado_candidato_map.get(nuevo_estado_proceso)

                if nuevo_estado_maestro:
                    # *Asume que Candidato.ESTADOS está definido y ordenado*
                    estado_orden = {state[0]: i for i, state in enumerate(Candidato.ESTADOS)}
                    current_order = estado_orden.get(candidato.estado_actual, -1)
                    new_order = estado_orden.get(nuevo_estado_maestro, -1)
                    
                    # Criterio de avance: solo actualizar si el nuevo estado es superior al actual o si es un estado final.
                    if new_order > current_order or nuevo_estado_proceso in ['CONTRATADO', 'NO_APTO', 'ABANDONO']:
                        candidato.estado_actual = nuevo_estado_maestro
                        candidato.save()
                        messages.success(request, f'Candidato {candidato.nombres_completos} actualizado a: **{candidato.get_estado_actual_display()}**.')
                    else:
                        messages.success(request, f'Proceso de {candidato.nombres_completos} actualizado de {estado_anterior} a: {proceso.get_estado_display()}.')
                
                else:
                    messages.success(request, f'Proceso de {candidato.nombres_completos} actualizado a: {proceso.get_estado_display()}.')


        except Exception as e:
            messages.error(request, f'Error al actualizar el Proceso: {e}')

        return redirect('kanban_dashboard')
    

ESTADOS_FINALES_OCULTOS = ['NO_APTO', 'DESISTE']
class KanbanDashboardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):

        search_query = request.GET.get('search')
        fecha_inicio_filter = request.GET.get('fecha_inicio')
        
        latest_proceso_prefetch = Prefetch(
            'procesos', 
            queryset=Proceso.objects.order_by('-pk').select_related('empresa_proceso', 'supervisor'),
            to_attr='latest_proceso'
        )

        candidatos = Candidato.objects.prefetch_related(latest_proceso_prefetch).all()
        
        candidatos = candidatos.exclude(estado_actual__in=ESTADOS_FINALES_OCULTOS)
        
        if fecha_inicio_filter:
            try:
                datetime.strptime(fecha_inicio_filter, '%Y-%m-%d').date() 

                candidatos = candidatos.filter(
                    procesos__fecha_inicio=fecha_inicio_filter
                ).distinct()

            except ValueError:
                messages.error(request, "Formato de fecha de filtro inválido. Use AAAA-MM-DD.")
                fecha_inicio_filter = None
        
        if search_query:
            candidatos = candidatos.filter(
                Q(DNI__icontains=search_query) | 
                Q(nombres_completos__icontains=search_query)
            )

        convocatoria_dates = Proceso.objects.values('fecha_inicio') \
            .annotate(count=Count('candidato', distinct=True)) \
            .order_by('-fecha_inicio') \
            .filter(fecha_inicio__isnull=False)

        total_candidatos = candidatos.count()

        ESTADOS_KANBAN_ACTIVOS = [
            estado[0] for estado in Candidato.ESTADOS 
            if estado[0] not in ESTADOS_FINALES_OCULTOS
        ]
        
        kanban_data = {estado: [] for estado in ESTADOS_KANBAN_ACTIVOS}

        PROCESO_ESTADOS = getattr(Proceso, 'ESTADOS_PROCESO', None)

        for candidato in candidatos:
            estado = candidato.estado_actual

            if estado in kanban_data: 
                proceso_actual = candidato.latest_proceso[0] if candidato.latest_proceso else None
                
                proceso_status_display = 'N/A'
                proceso_id = None
                empresa_nombre = 'N/A'
                supervisor_nombre = 'N/A'
                objetivo_alcanzado = 'false'
                factor_actitud = 'false'
                fecha_inicio = None

                if proceso_actual:
                    proceso_status_display = proceso_actual.get_estado_display()
                    proceso_id = proceso_actual.pk
                    empresa_nombre = proceso_actual.empresa_proceso.nombre if proceso_actual.empresa_proceso else 'N/A'
                    supervisor_nombre = proceso_actual.supervisor.nombre if proceso_actual.supervisor else 'N/A'
                    objetivo_alcanzado = 'true' if proceso_actual.objetivo_ventas_alcanzado else 'false'
                    factor_actitud = 'true' if proceso_actual.factor_actitud_aplica else 'false'
                    fecha_inicio = proceso_actual.fecha_inicio
                
                kanban_data[estado].append({
                    'candidato': candidato,
                    'proceso': proceso_actual,
                    'proceso_status': proceso_status_display,
                    'proceso_id': proceso_id,
                    'empresa_nombre': empresa_nombre,
                    'supervisor_nombre': supervisor_nombre,
                    'objetivo_alcanzado': objetivo_alcanzado,
                    'factor_actitud': factor_actitud,
                    'fecha_inicio': fecha_inicio,
                })

        context = {
            'kanban_data': kanban_data,
            'empresas': Empresa.objects.all(),
            'sedes': Sede.objects.all(),
            'supervisores': Supervisor.objects.all(),

            'PROCESO_ESTADOS': PROCESO_ESTADOS,
            'title': 'Dashboard Kanban de Candidatos',

            'convocatoria_dates': convocatoria_dates,
            'active_date': fecha_inicio_filter,
            'total_candidatos': total_candidatos,
            
            'motivos_descarte': MOTIVOS_DESCARTE,
        }
        
        return render(request, 'dashboard.html', context)
    

@method_decorator(csrf_exempt, name='dispatch')
class UpdateStatusMultipleView(LoginRequiredMixin, View):
    """
    Recibe una lista de DNI's y un nuevo estado para actualizar múltiples candidatos
    y sus procesos activos en una sola transacción.
    """
    def post(self, request):
        try:
            # 1. Validación de Request
            if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Invalid request: Must be an AJAX POST.'}, status=400)
            
            # Obtener datos: la lista de DNI's, el nuevo estado y la fecha de inicio (si aplica)
            dni_list = request.POST.getlist('dnis[]')
            new_status_key = request.POST.get('new_status')
            fecha_inicio_nueva = request.POST.get('fecha_inicio') # Nuevo dato para el flujo REGISTRADO->CONVOCADO

            if not dni_list or not new_status_key:
                # Este error es el 'DNI list and new status are required.'
                # Se mantiene, la solución está en el FRONTEND (Función confirmMassUpdate).
                return JsonResponse({'status': 'error', 'message': 'DNI list and new status are required.'}, status=400)

            # 2. Mapeo de Estados
            # Usaremos 'INICIADO' para CONVOCADO, que es el estado inicial del Proceso.
            proceso_estado_map = {
                'CONVOCADO': 'INICIADO', 
                'CAPACITACION_TEORICA': 'TEORIA',
                'CAPACITACION_PRACTICA': 'PRACTICA',
                'CONTRATADO': 'CONTRATADO',
                'NO_APTO': 'NO_APTO', 
                # 'REGISTRADO' no requiere actualización de Proceso
            }

            proceso_status_to_update = proceso_estado_map.get(new_status_key)
            estado_orden = {state[0]: i for i, state in enumerate(Candidato.ESTADOS)}
            
            candidatos_actualizados = 0

            with transaction.atomic():
                
                # 3. Obtener Candidatos con la CORRECCIÓN del related_name
                candidatos = Candidato.objects.filter(DNI__in=dni_list).prefetch_related(
                    Prefetch(
                        'procesos', # <-- CORRECCIÓN CLAVE: Usar 'procesos'
                        queryset=Proceso.objects.order_by('-fecha_inicio'), 
                        to_attr='latest_proceso'
                    )
                )
                
                # Si la transición es a CONVOCADO, necesitamos la fecha
                is_to_convocado = new_status_key == 'CONVOCADO'
                if is_to_convocado and not fecha_inicio_nueva:
                     return JsonResponse({'status': 'error', 'message': 'La fecha de inicio es requerida para iniciar el proceso de convocatoria masiva.'}, status=400)

                # Definir IDs por defecto para la creación de Proceso (AJUSTAR SEGÚN NECESIDAD)
                # *Necesitas obtener estos valores del frontend o usar valores por defecto/primeros*
                # Ejemplo de valores por defecto (asegúrate de que existan)
                default_supervisor_id = 1 
                default_empresa_id = 1
                
                for candidato in candidatos:
                    
                    current_order = estado_orden.get(candidato.estado_actual, -1)
                    new_order = estado_orden.get(new_status_key, -1)

                    # Solo actualizar si es un avance o un estado final
                    if new_order > current_order or new_status_key in ['CONTRATADO', 'NO_APTO']:
                        
                        proceso_activo = candidato.latest_proceso[0] if candidato.latest_proceso else None
                        
                        # A. Lógica de REGISTRADO a CONVOCADO (Creación de Proceso)
                        if candidato.estado_actual == 'REGISTRADO' and is_to_convocado:
                            
                            Proceso.objects.create(
                                candidato=candidato,
                                fecha_inicio=fecha_inicio_nueva,
                                # Usamos la sede del candidato, y valores por defecto para los demás
                                supervisor_id=default_supervisor_id, 
                                empresa_proceso_id=default_empresa_id, 
                                sede_proceso_id=candidato.sede_registro_id, 
                                estado='INICIADO'
                            )
                            # El nuevo proceso se crea, no es necesario reasignar proceso_activo aquí
                            
                        # B. Actualización de Proceso Existente
                        elif proceso_status_to_update and proceso_activo:
                            
                            if proceso_status_to_update == 'CONTRATADO':
                                proceso_activo.fecha_contratacion = date.today()
                            
                            proceso_activo.estado = proceso_status_to_update
                            proceso_activo.save()
                        
                        # Actualizar estado maestro del Candidato
                        candidato.estado_actual = new_status_key
                        candidato.save()
                        
                        candidatos_actualizados += 1
                        
                # 6. Respuesta JSON
                # Usamos el método de instancia get_FOO_display() de Django.
                if candidatos:
                    # Usamos el display name del nuevo estado (no de un candidato específico)
                    display_status = dict(Candidato.ESTADOS).get(new_status_key, new_status_key)
                else:
                    display_status = new_status_key 
                
                return JsonResponse({
                    'status': 'success', 
                    'message': f'{candidatos_actualizados} candidatos movidos a **{display_status}** con éxito.',
                    'count': candidatos_actualizados,
                    'new_status_key': new_status_key 
                })

        except Exception as e:
            print(f"Error en UpdateStatusMultipleView: {e}")
            return JsonResponse({'status': 'error', 'message': f'Error al actualizar estados masivamente: {str(e)}'}, status=500)

class CandidatoDetailView(LoginRequiredMixin, DetailView):
    """
    Muestra la vista de detalle de un candidato. 
    Usa el DNI como campo para la búsqueda (slug_field).
    """
    model = Candidato
    template_name = 'detalle_candidato.html' 
    slug_field = 'DNI'
    slug_url_kwarg = 'dni'
    context_object_name = 'candidato'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        candidato = self.object
        
        # Obtener todos los procesos del candidato ordenados por fecha de inicio descendente
        context['procesos'] = Proceso.objects.filter(candidato=candidato).order_by('-fecha_inicio').select_related('empresa_proceso', 'supervisor')
        context['title'] = f'Detalle: {candidato.nombres_completos}'
        
        # Opcional: Obtener el último proceso y la asistencia si es necesario
        context['ultimo_proceso'] = context['procesos'].first()
        
        if context['ultimo_proceso']:
            context['asistencias'] = RegistroAsistencia.objects.filter(proceso=context['ultimo_proceso']).order_by('-fecha')

        return context

class CandidatoSearchView(View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '')
        results = []

        if query:
            candidatos = Candidato.objects.filter(
                Q(DNI__startswith=query) | Q(nombres_completos__icontains=query)
            ).values('DNI', 'nombres_completos')[:10]

            for c in candidatos:
                results.append({
                    'DNI': c['DNI'],
                    'nombres_completos': c['nombres_completos'],
                })

        return JsonResponse(results, safe=False)

class AsistenciaDiariaCheckView(View):
    """
    Verifica si un candidato específico tiene un registro de asistencia para el día de hoy.
    """
    def get(self, request, *args, **kwargs):
        dni = request.GET.get('dni')
        hoy = date.today()
        
        if not dni:
            return JsonResponse({'asistencia_registrada': False, 'candidato_encontrado': False}, status=400)

        try:
            candidato = Candidato.objects.get(DNI=dni)
            
            # Buscamos el proceso activo (el último)
            proceso_activo = Proceso.objects.filter(candidato=candidato).order_by('-pk').first()

            if proceso_activo:
                asistencia_existe = RegistroAsistencia.objects.filter(
                    proceso=proceso_activo,
                    fecha=hoy
                ).exists()

                return JsonResponse({
                    'asistencia_registrada': asistencia_existe,
                    'candidato_encontrado': True,
                    'dni': dni,
                    'proceso_id': proceso_activo.pk 
                })
            else:
                # Si el candidato existe pero no tiene proceso (ej: estado REGISTRADO)
                return JsonResponse({'asistencia_registrada': False, 'candidato_encontrado': True, 'dni': dni, 'proceso_id': None})

        except Candidato.DoesNotExist:
            return JsonResponse({'asistencia_registrada': False, 'candidato_encontrado': False}, status=200)

@csrf_exempt 
@require_http_methods(["POST"])
@transaction.atomic
def registrar_asistencia_rapida(request):
    """
    Recibe los datos POST del modal (AJAX) para registrar la asistencia y devuelve JSON.
    """
    # 1. VERIFICACIÓN DE AUTENTICACIÓN (Devuelve JSON 403)
    if not request.user.is_authenticated:
        return JsonResponse(
            {'success': False, 'message': 'Fallo de autenticación. Sesión expirada. Recargue la página.'}, 
            status=403
        )

    try:
        proceso_id = request.POST.get('proceso_id')
        fase_actual_key = request.POST.get('fase_actual') 
        movimiento = request.POST.get('movimiento')      
        estado_asistencia = request.POST.get('estado_asistencia', 'A') 
        
        if not all([proceso_id, fase_actual_key, movimiento]):
            return JsonResponse(
                {'success': False, 'message': "Error de datos: Faltan campos obligatorios para el registro."}, 
                status=400
            )

        # 3. Obtener el proceso
        proceso = Proceso.objects.get(pk=proceso_id)
        candidato_nombre = proceso.candidato.nombres_completos
        hoy = timezone.localdate()
        mensaje_exito = "" 
        
        
        if movimiento == 'REGISTRO':
            registro_existente_hoy = RegistroAsistencia.objects.filter(
                proceso=proceso,
                fase_actual=fase_actual_key,
                momento_registro__date=hoy
            ).exclude(movimiento__in=['ENTRADA', 'SALIDA']).exists()

            if registro_existente_hoy:
                return JsonResponse(
                    {'success': False, 'message': f"⚠️ El candidato ya tiene registrada la asistencia ÚNICA para hoy en la fase {fase_actual_key}."}, 
                    status=409
                )
        
        elif movimiento in ['ENTRADA', 'SALIDA'] and fase_actual_key == 'PRACTICA':
            ultimo_registro_hoy = RegistroAsistencia.objects.filter(
                proceso=proceso, 
                fase_actual='PRACTICA', 
                momento_registro__date=hoy
            ).order_by('-momento_registro').first()
            
            if movimiento == 'ENTRADA' and ultimo_registro_hoy and ultimo_registro_hoy.movimiento == 'ENTRADA':
                hora_registro = timezone.localtime(ultimo_registro_hoy.momento_registro).strftime('%H:%M')
                return JsonResponse(
                    {'success': False, 'message': f"❌ Error: Ya marcó ENTRADA hoy a las {hora_registro}."}, 
                    status=409
                )

            if movimiento == 'SALIDA' and (not ultimo_registro_hoy or ultimo_registro_hoy.movimiento == 'SALIDA'):
                return JsonResponse(
                    {'success': False, 'message': "❌ Error: Debe marcar ENTRADA antes de marcar SALIDA."}, 
                    status=409
                )

        # --- 5. Crear el nuevo registro de asistencia ---
        RegistroAsistencia.objects.create(
            proceso=proceso,
            fase_actual=fase_actual_key,
            movimiento=movimiento,
            estado_asistencia=estado_asistencia,
            registrado_por=request.user,
            momento_registro=timezone.now()
        )
        
        # --- 6. Lógica de Transición de Estado y Mensajes de Éxito ---
        
        # Si el candidato asiste a la convocatoria, avanza a Teoria
        if proceso.estado == 'INICIADO' and fase_actual_key == 'CONVOCADO':
            proceso.estado = 'TEORIA' 
            proceso.save()
            mensaje_exito = f"🎉 ¡Asistencia Registrada y Avance! {candidato_nombre} ha avanzado a la fase de TEORÍA."
            
        elif movimiento == 'REGISTRO':
            mensaje_exito = f"✅ Asistencia Única para {candidato_nombre} en fase {fase_actual_key} registrada."
        elif movimiento == 'ENTRADA':
            mensaje_exito = f"🟢 ENTRADA registrada para {candidato_nombre}."
        elif movimiento == 'SALIDA':
            mensaje_exito = f"🔴 SALIDA registrada para {candidato_nombre}. ¡Fin de Jornada!"

        # 7. RETORNO FINAL DE ÉXITO (JSON 200)
        return JsonResponse({'success': True, 'message': mensaje_exito})

    except Proceso.DoesNotExist:
        return JsonResponse({'success': False, 'message': "Error: El proceso referenciado no existe o no es válido."}, status=404)

    except Exception as e:
        # Esto captura cualquier error de Python (500) y lo devuelve como JSON
        return JsonResponse(
            {'success': False, 'message': f"Error interno crítico en el servidor: {str(e)}"}, 
            status=500
        )


@login_required
@require_http_methods(["GET", "POST"])
def asistencia_dashboard(request):
    """
    Muestra la interfaz para escanear/digitar DNI (GET) y maneja la búsqueda AJAX (POST).
    """
    
    if request.method == 'POST':
        # Esta función solo acepta peticiones AJAX (para mayor seguridad)
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
            
        dni = request.POST.get('dni', '').strip()
        
        if not dni:
            return JsonResponse({'success': False, 'message': 'DNI no puede estar vacío.'})

        try:
            # 1. Buscar el candidato por DNI
            candidato = Candidato.objects.get(DNI=dni)
            
            # 2. Encontrar el proceso activo más reciente
            ultimo_proceso = Proceso.objects.filter(
                candidato=candidato
            ).exclude(
                estado__in=['CONTRATADO', 'NO_APTO', 'ABANDONO']
            ).order_by('-fecha_inicio').first()
            
            if not ultimo_proceso:
                return JsonResponse({
                    'success': False, 
                    'message': f'Candidato "{candidato.nombres_completos}" no tiene un proceso activo para registrar asistencia.'
                })

            # 3. Determinar el TIPO DE MOVIMIENTO y FASE
            fase_proceso = ultimo_proceso.estado # Ejemplo: 'PRACTICA', 'INDUCCION', etc.
            
            # Solo la fase 'PRACTICA' o similar requiere control de Entrada/Salida
            requiere_entrada_salida = (fase_proceso == 'PRACTICA')
            
            movimiento_requerido = 'REGISTRO' # Valor por defecto para fases que solo requieren un check-in
            ultimo_registro_hoy = None 
            
            # Lógica específica para Entrada/Salida
            if requiere_entrada_salida:
                hoy = timezone.localdate()
                
                # Buscar el último movimiento de asistencia para hoy, en esta fase.
                ultimo_registro_hoy = RegistroAsistencia.objects.filter(
                    proceso=ultimo_proceso, 
                    fase_actual=fase_proceso,
                    momento_registro__date=hoy 
                ).order_by('-momento_registro').first()

                if ultimo_registro_hoy and ultimo_registro_hoy.movimiento == 'ENTRADA':
                    movimiento_requerido = 'SALIDA'
                elif ultimo_registro_hoy and ultimo_registro_hoy.movimiento == 'SALIDA':
                    # Si ya marcó salida HOY, el próximo movimiento debe ser ENTRADA (mañana o si vuelve a entrar)
                    # Se mantiene como 'ENTRADA' para un eventual nuevo turno o día.
                    movimiento_requerido = 'ENTRADA'
                else:
                    # Si no hay registros o el último fue un registro único, asumimos ENTRADA.
                    movimiento_requerido = 'ENTRADA'

            if ultimo_registro_hoy:
                hora_local = timezone.localtime(ultimo_registro_hoy.momento_registro)
                ultimo_registro_str = f"{ultimo_registro_hoy.get_movimiento_display()} a las {hora_local.strftime('%H:%M:%S')}"
            else:
                ultimo_registro_str = '' # Enviamos string vacío si es None

            # 5. Devolver los datos para mostrar el modal de registro
            return JsonResponse({
                'success': True,
                'proceso_id': ultimo_proceso.pk,
                'candidato_nombre': candidato.nombres_completos,
                'candidato_dni': candidato.DNI,
                'fase_proceso': ultimo_proceso.get_estado_display(),
                'fase_proceso_key': fase_proceso,
                'movimiento_requerido': movimiento_requerido,
                'requiere_entrada_salida': requiere_entrada_salida,
                'ultimo_registro': ultimo_registro_str, # Se envía el string formateado
            })

        except Candidato.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'DNI "{dni}" no encontrado en la base de datos.'}, status=404)
        
        except Exception as e:
            # Captura cualquier otro error de la base de datos o lógica
            print(f"Error en asistencia_dashboard: {e}")
            return JsonResponse({'success': False, 'message': f'Error interno en el servidor: {e}'}, status=500)

    # Si es GET, renderiza la plantilla principal
    return render(request, 'asistencia_dashboard.html', {'today': date.today()})

@method_decorator(csrf_exempt, name='dispatch')
class UpdateStatusView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
                # Si no es AJAX, podrías devolver un mensaje de error o redirigir
                return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

            dni = request.POST.get('dni')
            new_status_key = request.POST.get('new_status')

            if not dni or not new_status_key:
                return JsonResponse({'status': 'error', 'message': 'DNI and new status are required.'}, status=400)

            candidato = Candidato.objects.get(DNI=dni)

            proceso_activo = candidato.procesos.order_by('-fecha_inicio').first() 

            proceso_estado_map = {
                'CONVOCADO': 'INICIADO',
                'CAPACITACION_TEORICA': 'TEORIA',
                'CAPACITACION_PRACTICA': 'PRACTICA',
                'CONTRATADO': 'CONTRATADO',
                'NO_APTO': 'NO_APTO', 
            }

            proceso_status_to_update = proceso_estado_map.get(new_status_key)
            
            current_candidato_estado = candidato.estado_actual

            with transaction.atomic():
                
                # --- MANEJO ESPECIAL PARA REGISTRADO a CONVOCADO (Creación de Proceso) ---
                if current_candidato_estado == 'REGISTRADO' and new_status_key == 'CONVOCADO':
                    fecha_inicio = request.POST.get('fecha_inicio') 

                    if not fecha_inicio:
                        return JsonResponse({'status': 'error', 'message': 'La fecha de inicio es requerida para iniciar el proceso.'}, status=400)

                    proceso_nuevo = Proceso.objects.create(
                        candidato=candidato,
                        fecha_inicio=fecha_inicio,
                        supervisor_id=1,
                        empresa_proceso_id=1,
                        sede_proceso_id=candidato.sede_registro_id,
                        estado='INICIADO'
                    )
                    proceso_activo = proceso_nuevo
                
                # --- ACTUALIZACIÓN DE PROCESO EXISTENTE ---
                elif proceso_status_to_update and proceso_activo:
                    proceso_activo.estado = proceso_status_to_update
                    proceso_activo.save()

                # --- Lógica de Avance de Estado Maestro ---
                estado_orden = {state[0]: i for i, state in enumerate(Candidato.ESTADOS)}
                current_order = estado_orden.get(current_candidato_estado, -1)
                new_order = estado_orden.get(new_status_key, -1)
                
                candidato_avanzado = False # Bandera para controlar si hubo avance de estado maestro
                
                if new_order > current_order or new_status_key in ['CONTRATADO', 'NO_APTO']:
                    candidato.estado_actual = new_status_key
                    candidato.save()
                    candidato_avanzado = True
                    
                    proceso_id_respuesta = proceso_activo.pk if proceso_activo else None
                    
                    # -----------------------------------------------------
                    # AJUSTE PARA UNIFORMIZAR EL MENSAJE DE CONVOCADO 🎯
                    # -----------------------------------------------------
                    if new_status_key == 'CONVOCADO' and proceso_activo:
                        # Si es CONVOCADO, usamos el display del Proceso ('INICIADO/CONFIRMADO')
                        display_status_message = proceso_activo.get_estado_display()
                    else:
                        # Para el resto de movimientos, usamos el display del Candidato
                        display_status_message = candidato.get_estado_actual_display()

                    return JsonResponse({
                        'status': 'success', 
                        'message': f'Candidato {dni} movido a **{display_status_message}** con éxito.', # USA EL TEXTO CORREGIDO
                        'proceso_id': proceso_id_respuesta,
                        'new_status': new_status_key,
                        'new_proceso_status': proceso_activo.get_estado_display() if proceso_activo else 'N/A'
                    })
                
                # Mensaje si no hubo avance de estado maestro (ej: mover CONVOCADO a TEORICA sin avanzar)
                if not candidato_avanzado:
                    # Usamos el estado actual del candidato después de que el proceso se actualizó (si aplica)
                    display_status_message = candidato.get_estado_actual_display()
                    if new_status_key == 'CAPACITACION_TEORICA' and proceso_activo:
                         display_status_message = proceso_activo.get_estado_display()
                         
                    return JsonResponse({'status': 'success', 'message': f'Candidato {dni} movido a {display_status_message} (No se avanzó de estado maestro).'})

        except Candidato.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': f'Candidato con DNI {dni} no encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error al actualizar estado: {str(e)}'}, status=500)

class AsignarSupervisorIndividualView(LoginRequiredMixin, View):
    def post(self, request, proceso_id):
        supervisor_id_str = request.POST.get('supervisor_id')

        if not supervisor_id_str:
            messages.error(request, "Error: Debe seleccionar un supervisor para asignar.")
            return redirect('kanban_dashboard')

        try:
            proceso = get_object_or_404(Proceso, pk=proceso_id)
            supervisor = Supervisor.objects.get(pk=supervisor_id_str)
            candidato = proceso.candidato

            with transaction.atomic():
                proceso.supervisor = supervisor
                proceso.estado = 'PRACTICA'
                proceso.save()

                candidato.estado_actual = 'CAPACITACION_PRACTICA'
                candidato.save()
                messages.success(request, f"✅ Candidato {candidato.nombres_completos} movido a Práctica y Supervisor **{supervisor.nombre}** asignado con éxito.")

        except Supervisor.DoesNotExist:
            messages.error(request, "Error: El supervisor seleccionado no existe.")
        except Exception as e:
            messages.error(request, f"Ocurrió un error al asignar el supervisor: {e}")

        return redirect('kanban_dashboard')

class ExportarCandidatosExcelView(LoginRequiredMixin, View):
    def get(self, request, estado, *args, **kwargs):
        
        fecha_filtro_str = request.GET.get('fecha_filtro')
        
        proceso_queryset = Proceso.objects.order_by('-fecha_inicio').select_related('supervisor', 'empresa_proceso')
        
        if fecha_filtro_str:
            proceso_queryset = proceso_queryset.filter(fecha_inicio=fecha_filtro_str)
        
        candidatos_qs = Candidato.objects.filter(estado_actual=estado)
        
        # FILTRO CLAVE: Asegura que el Candidato tiene un Proceso con la fecha seleccionada
        if fecha_filtro_str:
            candidatos_qs = candidatos_qs.filter(procesos__fecha_inicio=fecha_filtro_str).distinct()

        candidatos_qs = candidatos_qs.order_by('fecha_registro').select_related(
            'sede_registro',
            'datoscualificacion' 
        )

        candidatos = candidatos_qs.prefetch_related(
            models.Prefetch('procesos', queryset=proceso_queryset)
        )
        
        candidatos_a_exportar = list(candidatos)
        
        if not candidatos_a_exportar:
            messages.info(request, f"No se encontraron candidatos en el estado: {estado} para la fecha: {fecha_filtro_str if fecha_filtro_str else 'Todas'}")
            return redirect('kanban_dashboard')

        data = []
        
        def format_date(date_field):
            return date_field.strftime('%d/%m/%Y') if date_field else ''
        
        def format_bool(bool_field):
            if bool_field is True: return 'SÍ'
            if bool_field is False: return 'NO'
            return 'N/A' 
        
        for c in candidatos_a_exportar:
            
            # El queryset c.procesos.all() ya está filtrado por la fecha si se usó el filtro
            ultimo_proceso = next(iter(c.procesos.all()), None)
            cualificacion = getattr(c, 'datoscualificacion', None) 

            row = {
                'DNI': c.DNI,
                'Nombres_Completos': c.nombres_completos,
                'Telefono_Whatsapp': c.telefono_whatsapp,
                'Email': c.email if c.email else '',
                'Edad': c.edad,
                'Distrito_Candidato': c.distrito, 
                'Estado_Actual_Candidato': c.get_estado_actual_display(), 
                'Fecha_Registro': format_date(c.fecha_registro),
                'Sede_Registro': c.sede_registro.nombre if c.sede_registro else 'N/A',

                'Secundaria_Completa': format_bool(cualificacion.secundaria_completa) if cualificacion else '',
                'Exp_Campanas_Espanolas': format_bool(cualificacion.experiencia_campanas_espanolas) if cualificacion else '', 
                'Tipo_Exp_Ventas': cualificacion.get_experiencia_ventas_tipo_display() if cualificacion else '', 
                'Empresa_Exp_Ventas': cualificacion.empresa_vendedor if cualificacion else '',
                'Tiempo_Experiencia_Vendedor': cualificacion.get_tiempo_experiencia_vendedor_display() if cualificacion else '', 
                'Conforme_Beneficios': cualificacion.get_conforme_beneficios_display() if cualificacion else '',
                'Detalle_Beneficios_Otro': cualificacion.detalle_beneficios_otro if cualificacion else '', 
                'Disponibilidad_Horario': format_bool(cualificacion.disponibilidad_horario) if cualificacion else '',
                'Discapacidad_Enfermedad_Cronica': cualificacion.discapacidad_enfermedad_cronica if cualificacion else '',
                'Dificultad_Habla': format_bool(cualificacion.dificultad_habla) if cualificacion else '',

                'Empresa_Cliente': ultimo_proceso.empresa_proceso.nombre if ultimo_proceso and ultimo_proceso.empresa_proceso else '',
                'Fecha_Convocatoria': format_date(ultimo_proceso.fecha_inicio) if ultimo_proceso else '',
                'Fecha_Teorico': format_date(ultimo_proceso.fecha_teorico) if ultimo_proceso else '',
                'Fecha_Practico': format_date(ultimo_proceso.fecha_practico) if ultimo_proceso else '',
                'Fecha_Contratacion': format_date(ultimo_proceso.fecha_contratacion) if ultimo_proceso else '',
                'Supervisor_Asignado': ultimo_proceso.supervisor.nombre if ultimo_proceso and ultimo_proceso.supervisor else '',
                'Estado_Proceso': ultimo_proceso.get_estado_display() if ultimo_proceso else 'N/A', 
            }
            
            data.append(row)

        df = pd.DataFrame(data)

        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl') 
            
        nombre_hoja = f"Candidatos_{estado}"[:31]
        df.to_excel(writer, sheet_name=nombre_hoja, index=False)

        worksheet = writer.sheets[nombre_hoja]
        for col_idx, column in enumerate(df.columns):
            max_len = max(df[column].astype(str).map(len).max(), len(column)) + 2 
            worksheet.column_dimensions[chr(65 + col_idx)].width = max_len

        writer.close() 

        output.seek(0)

        filename = f"candidatos_{estado.lower()}_{date.today().strftime('%Y%m%d')}.xlsx"

        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    

class RegistroPublicoCompletoView(View):
    def get(self, request):
        sedes_disponibles = Sede.objects.all().order_by('nombre') 

        context = {
            'title': 'Registro y Cualificación de Candidato',
            'is_public': True,
            'sedes': sedes_disponibles,
            'TIPO_VENTA_CHOICES': DatosCualificacion.TIPO_VENTA_CHOICES,
            'TIEMPO_EXP_CHOICES': DatosCualificacion.TIEMPO_EXP_CHOICES,
        }
        return render(request, 'registro_publico_completo.html', context)

    @transaction.atomic
    def post(self, request):
        dni = request.POST.get('DNI', '').strip()
        nombres_completos = request.POST.get('nombres_completos', '').strip()
        edad = request.POST.get('edad','').strip()
        telefono_whatsapp = request.POST.get('telefono_whatsapp', '').strip()
        email = request.POST.get('email', '').strip()
        distrito = request.POST.get('distrito', '').strip() 
        sede_id_seleccionada = request.POST.get('sede_registro')
        
        secundaria_completa_post = request.POST.get('secundaria_completa') 
        
        experiencia_campanas_espanolas = request.POST.get('experiencia_campanas_espanolas') == 'Si'
        experiencia_ventas_tipo = request.POST.get('experiencia_ventas_tipo')
        empresa_vendedor = request.POST.get('empresa_vendedor', '').strip()
        tiempo_experiencia_vendedor = request.POST.get('tiempo_experiencia_vendedor')
        conforme_beneficios = request.POST.get('conforme_beneficios')
        detalle_beneficios_otro = request.POST.get('detalle_beneficios_otro', '').strip()
        disponibilidad_horario = request.POST.get('disponibilidad_horario') == 'Si'
        discapacidad_enfermedad_cronica = request.POST.get('discapacidad_enfermedad_cronica', '').strip()
        dificultad_habla = request.POST.get('dificultad_habla') == 'Si'
        
        errors = {}
        
        # VALIDACIÓN DE CAMPOS OBLIGATORIOS (vacíos)
        campos_obligatorios = [dni, nombres_completos, telefono_whatsapp, distrito, experiencia_ventas_tipo, tiempo_experiencia_vendedor, conforme_beneficios, sede_id_seleccionada]
        
        if not all(campos_obligatorios):
             messages.error(request, 'Por favor, complete todos los campos obligatorios (*).')
             return redirect('registro_publico_completo')
             
        # VALIDACIÓN DE secundaria_completa (RESUELVE NOT NULL)
        if secundaria_completa_post is None:
             messages.error(request, 'El campo "¿Tienes secundaria completa?" es obligatorio. Por favor, selecciona Sí o No.')
             return redirect('registro_publico_completo')
             
        secundaria_completa = secundaria_completa_post == 'Si'

        # VALIDACIÓN DE FORMATO: DNI (8 DÍGITOS NUMÉRICOS)
        if not (dni and dni.isdigit() and len(dni) == 8):
            messages.error(request, 'El DNI debe tener exactamente 8 dígitos y contener solo números.')
            return redirect('registro_publico_completo')

        # VALIDACIÓN DE FORMATO: TELÉFONO (9 DÍGITOS NUMÉRICOS)
        if not (telefono_whatsapp and telefono_whatsapp.isdigit() and len(telefono_whatsapp) == 9):
            messages.error(request, 'El número de teléfono (WhatsApp) debe tener exactamente 9 dígitos y contener solo números.')
            return redirect('registro_publico_completo')
            
        # 3. Obtener el objeto Sede
        try:
             sede_seleccionada = Sede.objects.get(pk=sede_id_seleccionada)
        except Sede.DoesNotExist:
             messages.error(request, 'Error: La sede seleccionada no es válida o no existe.')
             return redirect('registro_publico_completo')
        except Exception as e:
             messages.error(request, f'Error al obtener la sede: {e}')
             return redirect('registro_publico_completo')
            
        # 4. Guardado en Transacción
        try:
            candidato = Candidato.objects.create(
                DNI=dni,
                nombres_completos=nombres_completos,
                edad = edad,
                telefono_whatsapp=telefono_whatsapp,
                email=email if email else None,
                distrito=distrito,
                sede_registro=sede_seleccionada, 
                estado_actual='REGISTRADO' 
            )
            
            DatosCualificacion.objects.create(
                candidato=candidato,
                distrito=distrito,
                secundaria_completa=secundaria_completa,
                experiencia_campanas_espanolas=experiencia_campanas_espanolas,
                experiencia_ventas_tipo=experiencia_ventas_tipo,
                empresa_vendedor=empresa_vendedor if empresa_vendedor else None,
                tiempo_experiencia_vendedor=tiempo_experiencia_vendedor,
                conforme_beneficios=conforme_beneficios,
                detalle_beneficios_otro=detalle_beneficios_otro if conforme_beneficios == 'OTRO' else None,
                disponibilidad_horario=disponibilidad_horario,
                discapacidad_enfermedad_cronica=discapacidad_enfermedad_cronica if discapacidad_enfermedad_cronica else None,
                dificultad_habla=dificultad_habla,
            )
            
        except IntegrityError as e:
            error_message = str(e)
            
            if 'DNI' in error_message or 'PRIMARY KEY' in error_message:
                msg = f'El DNI {dni} ya está registrado.'
            elif 'telefono_whatsapp' in error_message:
                msg = 'El número de teléfono ya está registrado con otro candidato.'
            elif 'email' in error_message:
                msg = 'El correo electrónico ya está registrado con otro candidato.'
            else:
                msg = f'Error de duplicidad no especificado. Contacte a soporte. Detalle: {error_message}'
                
            messages.error(request, msg)
            return redirect('registro_publico_completo')
        except ValidationError as e:
            messages.error(request, f'Error de validación: {e.message_dict}')
            return redirect('registro_publico_completo')
        except Exception as e:
            messages.error(request, f'Error inesperado al guardar datos: {e}')
            return redirect('registro_publico_completo')
            
        # 5. Respuesta de Éxito (Redirigir al formulario vacío con el mensaje)
        messages.success(request, '✅ ¡Tu registro y cualificación se completaron con éxito! Puedes registrar a alguien más si lo deseas.')
        return redirect('registro_publico_completo')
    

@login_required
@require_http_methods(["POST"])
def registrar_observacion(request):
    
    proceso_id = request.POST.get('proceso_id')
    observacion_texto = request.POST.get('observacion_texto', '').strip()
    
    if not proceso_id or not observacion_texto:
        return JsonResponse({'success': False, 'message': 'Faltan datos obligatorios.'}, status=400)

    if len(observacion_texto) > 500:
        return JsonResponse({'success': False, 'message': 'La observación excede el límite de 500 caracteres.'}, status=400)

    MAX_RETRIES = 3 
    
    for attempt in range(MAX_RETRIES):
        try:
            proceso = Proceso.objects.get(pk=proceso_id)

            ComentarioProceso.objects.create(
                proceso=proceso,
                texto=observacion_texto,
                registrado_por=request.user,
                fase_proceso=proceso.estado
            )
            
            return JsonResponse({
                'success': True, 
                'message': 'Observación guardada con éxito.' 
            })

        except (OperationalError, DatabaseError) as e:
            if "database is locked" not in str(e):
                raise
                
            if attempt < MAX_RETRIES - 1:
                print(f"Intento {attempt + 1} fallido (DB Locked). Reintentando...")
                time.sleep(0.2 * (attempt + 1)) 
            else:
                return JsonResponse(
                    {'success': False, 'message': f'Error interno en el servidor. Detalles: database is locked tras {MAX_RETRIES} intentos.'}, 
                    status=500
                )
        
        except Proceso.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'El proceso especificado no fue encontrado.'}, status=404)
        
        except Exception as e:
            print(f"Error grave al registrar observación: {e}") 
            return JsonResponse(
                {'success': False, 'message': f'Error interno en el servidor. Detalles: {str(e)}'}, 
                status=500
            )


@login_required
@require_http_methods(["POST"])
def registrar_test_archivo(request):
    
    # 1. Obtener datos del POST (Archivo y Metadatos)
    proceso_id = request.POST.get('proceso_id')
    tipo_test = request.POST.get('tipo_test')
    resultado_obtenido = request.POST.get('resultado_obtenido', '').strip()
    archivo = request.FILES.get('archivo')

    # 2. Validación obligatoria (Status 400)
    if not proceso_id or not tipo_test or not archivo:
        return JsonResponse({'success': False, 'message': 'Faltan datos obligatorios (ID de Proceso, Tipo de Test o Archivo).'}, status=400)

    MAX_RETRIES = 3 
    
    for attempt in range(MAX_RETRIES):
        try:
            # 3. Buscar el Proceso (Usamos get() para manejar 404 como JSON)
            proceso = Proceso.objects.get(pk=proceso_id)
            
            # El decorador @transaction.atomic YA NO ES NECESARIO AQUÍ
            # porque estamos manejando la lógica de reintento con try/except
            
            # 4. Crear el registro del test (Esta es la operación de escritura crítica)
            RegistroTest.objects.create(
                proceso=proceso,
                fase_proceso=proceso.estado,
                tipo_test=tipo_test,
                archivo_url=archivo, 
                resultado_obtenido=resultado_obtenido if resultado_obtenido else None,
                registrado_por=request.user
            )
            
            # 5. Retorno de éxito (Simple para evitar errores de serialización)
            return JsonResponse({
                'success': True, 
                'message': 'Archivo de Test registrado y subido con éxito.'
            })

        # 6. Captura de Error de Bloqueo de DB
        except (OperationalError, DatabaseError) as e:
            if "database is locked" not in str(e):
                raise
                
            if attempt < MAX_RETRIES - 1:
                print(f"Intento {attempt + 1} fallido (DB Locked en subida). Reintentando...")
                time.sleep(0.5 * (attempt + 1)) # Aumentamos la espera a 0.5s para archivos
            else:
                return JsonResponse(
                    {'success': False, 'message': f'Error interno en el servidor. Detalles: database is locked tras {MAX_RETRIES} intentos de subida.'}, 
                    status=500
                )
        
        # 7. Captura si el proceso no existe (Status 404)
        except Proceso.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'El proceso especificado no fue encontrado.'}, status=404)
        
        # 8. Captura cualquier otro error grave (incluidos errores de archivos/modelos)
        except Exception as e:
            print(f"Error grave al registrar test/archivo: {e}") 
            return JsonResponse(
                {'success': False, 'message': f'Error interno al procesar la subida. Detalles: {str(e)}'}, 
                status=500
            )
    

@require_http_methods(["POST"])
def actualizar_fecha_proceso(request, proceso_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'No autorizado.'}, status=401)
        
    try:
        proceso = Proceso.objects.get(pk=proceso_id)
        
        try:
            data = json.loads(request.body)
            date_type = data.get('date_type')
            new_date = data.get('new_date')
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Datos JSON inválidos.'}, status=400)

        field_map = {
            'inicio': 'fecha_inicio',
            'teorico': 'fecha_teorico',
            'practico': 'fecha_practico',
            'contratacion': 'fecha_contratacion',
        }
        
        if date_type not in field_map:
            return JsonResponse({'success': False, 'error': 'Tipo de fecha inválido.'}, status=400)
            
        field_name = field_map[date_type]
        
        try:
            new_date_obj = datetime.strptime(new_date, '%Y-%m-%d').date()
        except ValueError:
             return JsonResponse({'success': False, 'error': 'Formato de fecha inválido (debe ser YYYY-MM-DD).'}, status=400)

        current_state = proceso.estado
         
        allowed_changes = {
            'INICIADO': ['inicio', 'teorico'],
            'TEORIA': ['teorico', 'practico'],
            'PRACTICA': ['practico', 'contratacion'],
        }
        
        if date_type not in allowed_changes.get(current_state, []):
            return JsonResponse({
                'success': False, 
                'error': f'No puedes cambiar la fecha de {date_type.capitalize()} porque el proceso está actualmente en estado "{current_state}".'
            }, status=403) 
        
        if date_type == 'inicio':
            if proceso.fecha_teorico and proceso.fecha_teorico < new_date_obj:
                return JsonResponse({
                    'success': False, 
                    'error': f'La nueva Fecha de Inicio ({new_date}) es posterior a la Fecha Teórica actual ({proceso.fecha_teorico.strftime("%d/%m/%Y")}).'
                }, status=400)

        elif date_type == 'teorico':
            if proceso.fecha_inicio and new_date_obj < proceso.fecha_inicio:
                return JsonResponse({
                    'success': False, 
                    'error': f'La Fecha Teórica no puede ser anterior a la Fecha de Inicio ({proceso.fecha_inicio.strftime("%d/%m/%Y")}).'
                }, status=400)
            if proceso.fecha_practico and proceso.fecha_practico < new_date_obj:
                return JsonResponse({
                    'success': False, 
                    'error': f'La Fecha Teórica ({new_date}) es posterior a la Fecha Práctica actual ({proceso.fecha_practico.strftime("%d/%m/%Y")}).'
                }, status=400)
                
        elif date_type == 'practico':
            if proceso.fecha_teorico and new_date_obj < proceso.fecha_teorico:
                return JsonResponse({
                    'success': False, 
                    'error': f'La Fecha Práctica no puede ser anterior a la Fecha Teórica ({proceso.fecha_teorico.strftime("%d/%m/%Y")}).'
                }, status=400)

        setattr(proceso, field_name, new_date_obj)
        proceso.save()
        
        return JsonResponse({'success': True, 'message': 'Fecha actualizada correctamente.'})

    except Proceso.DoesNotExist:
        return JsonResponse({'success': False, 'error': f'Proceso con ID {proceso_id} no encontrado.'}, status=404)
    except Exception as e:
        print(f"Error al actualizar la fecha: {e}") 
        return JsonResponse({'success': False, 'error': 'Error interno del servidor.'}, status=500)



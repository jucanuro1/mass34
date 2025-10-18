from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, DetailView 
from django.db import IntegrityError
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Prefetch
from .models import Candidato, Proceso, Empresa, Sede, Supervisor, RegistroAsistencia,DatosCualificacion
from datetime import date, datetime
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.core.exceptions import ValidationError
import pandas as pd
import io

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

        nuevo_estado_proceso = request.POST.get('estado_proceso')

        objetivo_ventas = request.POST.get('objetivo_ventas_alcanzado') == 'on'
        factor_actitud = request.POST.get('factor_actitud_aplica') == 'on'

        estado_candidato_map = {
            'CONVOCADO': 'CONVOCADO', 
            'TEORIA': 'CAPACITACION_TEORICA',
            'PRACTICA': 'CAPACITACION_PRACTICA',
            'CONTRATADO': 'CONTRATADO',
            'NO_APTO': 'NO_APTO', 
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

                if nuevo_estado_proceso == 'CONTRATADO':
                    proceso.fecha_contratacion = date.today()

                proceso.save()

                nuevo_estado_maestro = estado_candidato_map.get(nuevo_estado_proceso)

                if nuevo_estado_maestro:
                    # Lógica de actualización de estado maestro (solo avanza o establece finales)
                    estado_orden = {state[0]: i for i, state in enumerate(Candidato.ESTADOS)}
                    current_order = estado_orden.get(candidato.estado_actual, -1)
                    new_order = estado_orden.get(nuevo_estado_maestro, -1)
                    
                    # Solo actualizamos el estado maestro si el nuevo estado es superior al actual
                    # O si es un estado final (CONTRATADO o NO_APTO)
                    if new_order > current_order or nuevo_estado_proceso in ['CONTRATADO', 'NO_APTO']:
                        candidato.estado_actual = nuevo_estado_maestro
                        candidato.save()
                        messages.success(request, f'Candidato {candidato.nombres_completos} actualizado a: **{candidato.get_estado_actual_display()}**.')
                    else:
                        messages.success(request, f'Proceso de {candidato.nombres_completos} actualizado a: {proceso.get_estado_display()}.')
                
                else:
                    messages.success(request, f'Proceso de {candidato.nombres_completos} actualizado a: {proceso.get_estado_display()}.')


        except Exception as e:
            messages.error(request, f'Error al actualizar el Proceso: {e}')

        return redirect('kanban_dashboard')

class KanbanDashboardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):

        search_query = request.GET.get('search')
        fecha_inicio_filter = request.GET.get('fecha_inicio')
        
        # 1. Optimización: Pre-obtener los últimos procesos
        latest_proceso_prefetch = Prefetch(
            # CORRECCIÓN: Usar el nuevo related_name 'procesos'
            'procesos', 
            queryset=Proceso.objects.order_by('-pk').select_related('empresa_proceso', 'supervisor'),
            to_attr='latest_proceso'
        )

        candidatos = Candidato.objects.prefetch_related(latest_proceso_prefetch).all()
        
        # 2. Manejo de Filtro por Fecha de Convocatoria 
        if fecha_inicio_filter:
            try:
                datetime.strptime(fecha_inicio_filter, '%Y-%m-%d').date() 

                # Filtramos los candidatos que tienen un proceso que coincide con la fecha
                candidatos = candidatos.filter(
                    # CORRECCIÓN: Usar 'procesos__fecha_inicio'
                    procesos__fecha_inicio=fecha_inicio_filter
                ).distinct()

            except ValueError:
                messages.error(request, "Formato de fecha de filtro inválido. Use AAAA-MM-DD.")
                fecha_inicio_filter = None
        
        # 3. Manejo de Búsqueda
        # ... (el resto del código se mantiene igual)
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

        kanban_data = {
            'REGISTRADO':[], 'CONVOCADO': [], 'CAPACITACION_TEORICA': [],
            'CAPACITACION_PRACTICA': [], 'CONTRATADO': [], 'NO_APTO': [], 
        }

        PROCESO_ESTADOS = getattr(Proceso, 'ESTADOS_PROCESO', None)

        for candidato in candidatos:
            estado = candidato.estado_actual

            if estado in kanban_data:
                # La lógica de acceso a latest_proceso (to_attr) se mantiene:
                proceso_actual = candidato.latest_proceso[0] if candidato.latest_proceso else None
                # ... (el resto de la lógica para construir kanban_data se mantiene igual)
                
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
        candidatos = Candidato.objects.filter(estado_actual=estado).order_by('fecha_registro')

        if not candidatos.exists():
            messages.info(request, f"No se encontraron candidatos en el estado: {estado}")
            return redirect('kanban_dashboard')

        data = []
        for c in candidatos:
            # Usamos el prefetch en la vista del dashboard, pero aquí lo hacemos individualmente
            ultimo_proceso = Proceso.objects.filter(candidato=c).order_by('-fecha_inicio').first()

            data.append({
                'DNI': c.DNI,
                'Nombres Completos': c.nombres_completos,
                'Teléfono / WhatsApp': c.telefono_whatsapp,
                'Email': c.email if c.email else '',
                'Estado Actual': c.get_estado_actual_display(), 
                'Fecha Registro': c.fecha_registro.strftime('%d/%m/%Y') if c.fecha_registro else '',
                'Sede de Registro': c.sede_registro.nombre if c.sede_registro else 'N/A',

                'Fecha Convocatoria': ultimo_proceso.fecha_inicio.strftime('%d/%m/%Y') if ultimo_proceso and ultimo_proceso.fecha_inicio else '',
                'Supervisor Asignado': ultimo_proceso.supervisor.nombre if ultimo_proceso and ultimo_proceso.supervisor else '',
                'Estado Proceso': ultimo_proceso.get_estado_display() if ultimo_proceso else 'N/A', 
                'Objetivo Ventas': 'Sí' if ultimo_proceso and ultimo_proceso.objetivo_ventas_alcanzado else ('No' if ultimo_proceso and ultimo_proceso.estado in ['CONTRATADO', 'NO_APTO'] else 'N/A'),
                'Factor Actitud': 'Sí' if ultimo_proceso and ultimo_proceso.factor_actitud_aplica else ('No' if ultimo_proceso and ultimo_proceso.estado in ['CONTRATADO', 'NO_APTO'] else 'N/A'),

            })

        df = pd.DataFrame(data)

        output = io.BytesIO()
        # Usamos openpyxl para compatibilidad
        writer = pd.ExcelWriter(output, engine='openpyxl') 

        nombre_hoja = f"Candidatos_{estado}"[:31]
        df.to_excel(writer, sheet_name=nombre_hoja, index=False)

        worksheet = writer.sheets[nombre_hoja]
        for col_idx, column in enumerate(df.columns):
            # Ajuste de ancho de columna
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


@require_POST
def registrar_asistencia_rapida(request):
    """
    Registra la asistencia diaria para un proceso activo basado en el ID enviado desde el modal.
    """
    # El ID del proceso se obtiene del campo oculto 'proceso_id' del formulario POST.
    proceso_id = request.POST.get('proceso_id')

    # Usamos 'kanban_dashboard' como nombre de redirección por defecto, ajústalo si es otro.
    REDIRECT_URL = 'kanban_dashboard' 

    if not proceso_id:
        messages.error(request, "Error: No se proporcionó el ID del Proceso para registrar la asistencia.")
        return redirect(REDIRECT_URL)

    try:
        # Usamos select_related para obtener el candidato en la misma consulta
        proceso = Proceso.objects.select_related('candidato').get(pk=proceso_id)
        candidato = proceso.candidato
        hoy = date.today()

        if RegistroAsistencia.objects.filter(proceso=proceso, fecha=hoy).exists():
            messages.warning(request, f"Advertencia: La asistencia para {candidato.nombres_completos} (DNI: {candidato.DNI}) ya estaba registrada hoy.")
            return redirect(REDIRECT_URL)

        RegistroAsistencia.objects.create(
            proceso=proceso,
            fecha=hoy,
        )
        
        messages.success(request, f"✅ Asistencia registrada con éxito para DNI: {candidato.DNI} - {candidato.nombres_completos}.")
        
    except Proceso.DoesNotExist:
        messages.error(request, f"Error: No se encontró un proceso activo con ID {proceso_id}.")
        
    except Exception as e:
        messages.error(request, f"Ocurrió un error al registrar la asistencia: {e}")

    return redirect(REDIRECT_URL)


class RegistroPublicoCompletoView(View):
    """
    Vista pública para registrar la información básica (Candidato) y la cualificación 
    (DatosCualificacion) en un solo envío de formulario.
    """
    
    # MÉTODO GET: Correcto, usa 'nombre' para las sedes.
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
        # 1. Captura de Datos
        # Datos del modelo Candidato
        dni = request.POST.get('DNI', '').strip()
        nombres_completos = request.POST.get('nombres_completos', '').strip()
        telefono_whatsapp = request.POST.get('telefono_whatsapp', '').strip()
        email = request.POST.get('email', '').strip()
        distrito = request.POST.get('distrito', '').strip() 
        sede_id_seleccionada = request.POST.get('sede_registro')
        
        # Datos del modelo DatosCualificacion
        # CAPTURA SEGURA (No la convertimos a bool todavía)
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
        
        # 2. Validación de campos obligatorios/formato
        errors = {}
        
        # Validación de campos generales
        campos_obligatorios = [dni, nombres_completos, telefono_whatsapp, distrito, experiencia_ventas_tipo, tiempo_experiencia_vendedor, conforme_beneficios, sede_id_seleccionada]
        if not all(campos_obligatorios):
             messages.error(request, 'Por favor, complete todos los campos obligatorios (*).')
             return redirect('registro_publico_completo')
             
        # VALIDACIÓN CLAVE: RESUELVE EL "NOT NULL constraint failed"
        if secundaria_completa_post is None:
             messages.error(request, 'El campo "¿Tienes secundaria completa?" es obligatorio. Por favor, selecciona Sí o No.')
             return redirect('registro_publico_completo')
             
        # Ahora que sabemos que el valor existe, lo convertimos a booleano
        secundaria_completa = secundaria_completa_post == 'Si'

        if dni and not dni.isdigit():
            errors['DNI'] = 'El DNI debe contener solo números.'
        
        if errors:
             messages.error(request, 'Corrija los errores de formato: DNI debe ser numérico.')
             return redirect('registro_publico_completo')
            
        # 3. Obtener el objeto Sede usando el ID capturado
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
            # 4.1 Crear Candidato
            candidato = Candidato.objects.create(
                DNI=dni,
                nombres_completos=nombres_completos,
                telefono_whatsapp=telefono_whatsapp,
                email=email if email else None,
                distrito=distrito,
                sede_registro=sede_seleccionada, 
                estado_actual='REGISTRADO' 
            )
            
            # 4.2 Crear DatosCualificacion
            DatosCualificacion.objects.create(
                candidato=candidato,
                distrito=distrito, # Asegúrate de que 'distrito' se guarde aquí también si el modelo lo pide
                secundaria_completa=secundaria_completa, # AHORA ES UN VALOR SEGURO (True/False)
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
            # MANEJO MEJORADO DE INTEGRITY ERROR (DNI/Teléfono/Email)
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
            
        # 5. Respuesta de Éxito
        messages.success(request, '✅ ¡Tu registro y cualificación se completaron con éxito! Pronto te contactaremos.')
        messages.success(request, '✅ ¡Tu registro y cualificación se completaron con éxito! Pronto te contactaremos.')
        return redirect('registro_publico_completo')
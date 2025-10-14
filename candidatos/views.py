from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View
from django.db import IntegrityError
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Prefetch
from .models import Candidato, Proceso, Empresa, Sede, Supervisor, RegistroAsistencia 
from datetime import date, datetime
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
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
            'TEORIA': 'CAPACITACION_TEORICA',
            'PRACTICA': 'CAPACITACION_PRACTICA',
            'CONTRATADO': 'CONTRATADO',
        }

        if not nuevo_estado_proceso:
            messages.error(request, "Debe seleccionar un nuevo estado para el proceso.")
            return redirect('kanban_dashboard')

        try:
            proceso.estado = nuevo_estado_proceso

            if nuevo_estado_proceso in ['CONTRATADO', 'NO_APTO']:
                proceso.objetivo_ventas_alcanzado = objetivo_ventas
                proceso.factor_actitud_aplica = factor_actitud

            if nuevo_estado_proceso == 'CONTRATADO':
                proceso.fecha_contratacion = date.today()

            proceso.save()

            nuevo_estado_maestro = estado_candidato_map.get(nuevo_estado_proceso)

            if nuevo_estado_maestro:
                estado_orden = {state[0]: i for i, state in enumerate(Candidato.ESTADOS)}

                current_order = estado_orden.get(candidato.estado_actual, -1)
                new_order = estado_orden.get(nuevo_estado_maestro, -1)

                if new_order > current_order:
                    candidato.estado_actual = nuevo_estado_maestro
                    candidato.save()
                    messages.success(request, f'Candidato {candidato.nombres_completos} promovido a: {candidato.get_estado_actual_display()}.')

            else:
                messages.success(request, f'Proceso de {candidato.nombres_completos} actualizado a: {proceso.get_estado_display()}.')

        except Exception as e:
            messages.error(request, f'Error al actualizar el Proceso: {e}')

        return redirect('kanban_dashboard')

class KanbanDashboardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):

        search_query = request.GET.get('search')
        fecha_inicio_filter = request.GET.get('fecha_inicio')
        
        latest_proceso_prefetch = Prefetch(
            'proceso_set',
            queryset=Proceso.objects.order_by('-pk').select_related('empresa_proceso', 'supervisor'),
            to_attr='latest_proceso'
        )

        candidatos = Candidato.objects.prefetch_related(latest_proceso_prefetch).all()

        if search_query:
            candidatos = candidatos.filter(
                Q(DNI__icontains=search_query) | 
                Q(nombres_completos__icontains=search_query)
            )
        
        if fecha_inicio_filter:
            try:
                datetime.strptime(fecha_inicio_filter, '%Y-%m-%d').date()

                candidatos_con_proceso_filtrado_ids = Proceso.objects.filter(
                    fecha_inicio=fecha_inicio_filter
                ).values_list('candidato_id', flat=True).distinct()

                candidatos = candidatos.filter(DNI__in=candidatos_con_proceso_filtrado_ids)

            except ValueError:
                messages.error(request, "Formato de fecha de filtro inválido.")
                fecha_inicio_filter = None
    
        convocatoria_dates = Proceso.objects.values('fecha_inicio') \
            .annotate(count=Count('candidato', distinct=True)) \
            .order_by('-fecha_inicio') \
            .filter(fecha_inicio__isnull=False)

        total_candidatos = candidatos.count()

        kanban_data = {
            'REGISTRADO':[], 'CONVOCADO': [], 'CAPACITACION_TEORICA': [],
            'CAPACITACION_PRACTICA': [], 'CONTRATADO': [],
        }

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

                if proceso_actual:
                    proceso_status_display = proceso_actual.get_estado_display()
                    proceso_id = proceso_actual.pk
                    empresa_nombre = proceso_actual.empresa_proceso.nombre if proceso_actual.empresa_proceso else 'N/A'
                    supervisor_nombre = proceso_actual.supervisor.nombre if proceso_actual.supervisor else 'N/A'
                    objetivo_alcanzado = 'true' if proceso_actual.objetivo_ventas_alcanzado else 'false'
                    factor_actitud = 'true' if proceso_actual.factor_actitud_aplica else 'false'


                kanban_data[estado].append({
                    'candidato': candidato,
                    'proceso': proceso_actual,
                    'proceso_status': proceso_status_display,
                    'proceso_id': proceso_id,
                    'empresa_nombre': empresa_nombre,
                    'supervisor_nombre': supervisor_nombre,
                    'objetivo_alcanzado': objetivo_alcanzado,
                    'factor_actitud': factor_actitud,
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
                return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

            dni = request.POST.get('dni')
            new_status_key = request.POST.get('new_status')

            if not dni or not new_status_key:
                return JsonResponse({'status': 'error', 'message': 'DNI and new status are required.'}, status=400)

            candidato = Candidato.objects.get(DNI=dni)

            proceso_activo = candidato.proceso_set.order_by('-fecha_inicio').first()

            if new_status_key in ['CAPACITACION_TEORICA', 'CAPACITACION_PRACTICA', 'CONTRATADO']:

                if not proceso_activo:
                    return JsonResponse({'status': 'error', 'message': f'No se encontró un proceso activo para el candidato {dni}.'}, status=400)

                proceso_estado_map = {
                    'CAPACITACION_TEORICA': 'TEORIA',
                    'CAPACITACION_PRACTICA': 'PRACTICA',
                    'CONTRATADO': 'CONTRATADO',
                }

                proceso_activo.estado = proceso_estado_map.get(new_status_key, proceso_activo.estado)
                proceso_activo.save()

            estado_orden = {state[0]: i for i, state in enumerate(Candidato.ESTADOS)}
            current_order = estado_orden.get(candidato.estado_actual, -1)
            new_order = estado_orden.get(new_status_key, -1)

            if new_order > current_order:
                candidato.estado_actual = new_status_key
                candidato.save()

            return JsonResponse({'status': 'success', 'message': f'Candidato {dni} movido a {new_status_key} con éxito.'})

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

            if proceso.estado != 'CAPACITACION_TEORICA' or candidato.estado_actual != 'CAPACITACION_TEORICA':
                messages.warning(request, f"Advertencia: El proceso {proceso_id} no está en el estado 'Teoría'. Estado actual: {proceso.estado}.")

            with transaction.atomic():
                proceso.supervisor = supervisor
                proceso.estado = 'CAPACITACION_PRACTICA'
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
            return HttpResponse(f"No se encontraron candidatos en el estado: {estado}", status=204)

        data = []
        for c in candidatos:
            ultimo_proceso = Proceso.objects.filter(candidato=c).order_by('-fecha_inicio').first()

            data.append({
                'DNI': c.DNI,
                'Nombres Completos': c.nombres_completos,
                'Teléfono / WhatsApp': c.telefono_whatsapp,
                'Email': c.email if c.email else '',
                'Estado Actual': c.estado_actual,
                'Fecha Registro': c.fecha_registro.strftime('%d/%m/%Y') if c.fecha_registro else '',
                'Sede de Registro': c.sede_registro.nombre if c.sede_registro else 'N/A',

                'Fecha Convocatoria': ultimo_proceso.fecha_inicio.strftime('%d/%m/%Y') if ultimo_proceso and ultimo_proceso.fecha_inicio else '',
                'Supervisor Asignado': ultimo_proceso.supervisor.nombre if ultimo_proceso and ultimo_proceso.supervisor else '',
                'Estado Proceso': ultimo_proceso.estado if ultimo_proceso else 'N/A',
            })

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


# ==============================================================================
#                 ⭐ NUEVA VISTA PARA REGISTRAR ASISTENCIA RÁPIDA ⭐
# ==============================================================================

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
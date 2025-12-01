from .view_imports import *

REDIRECT_URL = 'kanban_dashboard'

class RegistroCandidatoView(LoginRequiredMixin, View):
    
    def get(self, request):
        context = {
            'title': 'Registro Rápido de Candidato',
            'sedes': Sede.objects.all(),
            'tipos_documento': TipoDocumento.objects.all().order_by('nombre')
        }
        return render(request, 'registro_candidato.html', context)

    def post(self, request):
        tipo_documento_id = request.POST.get('tipo_documento', '').strip()
        
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
            'tipo_documento_id': tipo_documento_id, 
            'sedes': Sede.objects.all(),
            'tipos_documento': TipoDocumento.objects.all().order_by('nombre') # Re-cargar
        }

        if not all([tipo_documento_id, dni, nombres_completos, telefono_whatsapp, sede_id]):
            messages.error(request, 'Los campos **Tipo Doc., DNI**, Nombres, Teléfono y **Sede** son obligatorios.')
            return render(request, 'registro_candidato.html', context)

        if not dni:
            messages.error(request, 'El número de documento no puede estar vacío.')
            return render(request, 'registro_candidato.html', context)
        
        if not telefono_whatsapp.isdigit():
             messages.error(request, 'El teléfono debe contener solo números.')
             return render(request, 'registro_candidato.html', context)

        try:
            sede = get_object_or_404(Sede, pk=sede_id)
            tipo_documento = get_object_or_404(TipoDocumento, pk=tipo_documento_id)

            candidato, created = Candidato.objects.get_or_create(
                DNI=dni,
                defaults={
                    'nombres_completos': nombres_completos,
                    'telefono_whatsapp': telefono_whatsapp,
                    'email': correo_electronico if correo_electronico else None,
                    'sede_registro': sede,
                    'tipo_documento': tipo_documento,  
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
                    tipo_documento=tipo_documento, 
                )
                messages.warning(request, f'Candidato {candidato.nombres_completos} ya existía. Datos actualizados.')

            return redirect('kanban_dashboard')

        except Sede.DoesNotExist:
            messages.error(request, "La Sede de registro seleccionada no es válida.")
            return render(request, 'registro_candidato.html', context)
        except TipoDocumento.DoesNotExist: 
            messages.error(request, "El Tipo de Documento seleccionado no es válido.")
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

        estado_anterior = proceso.estado 

        nuevo_estado_proceso = request.POST.get('estado_proceso')

        objetivo_ventas = request.POST.get('objetivo_ventas_alcanzado') == 'on'
        factor_actitud = request.POST.get('factor_aptitud_aplica') == 'on'

        estado_candidato_map = {
            'CONVOCADO': 'CONVOCADO',
            'CONFIRMADO': 'CONFIRMADO', 
            'TEORIA': 'CAPACITACION_TEORICA',
            'PRACTICA': 'CAPACITACION_PRACTICA',
            'CONTRATADO': 'CONTRATADO',
            'NO_APTO': 'NO_APTO', 
            'ABANDONO': 'DESISTE'
        }

        if not nuevo_estado_proceso:
            messages.error(request, "Debe seleccionar un nuevo estado para el proceso.")
            return redirect('kanban_dashboard')

        try:
            with transaction.atomic():
                
                proceso.estado = nuevo_estado_proceso

                if nuevo_estado_proceso in ['CONTRATADO', 'NO_APTO']:
                    proceso.objetivo_ventas_alcanzado = objetivo_ventas
                    proceso.factor_aptitud_aplica = factor_actitud

                proceso.save()

                nuevo_estado_maestro = estado_candidato_map.get(nuevo_estado_proceso)

                if nuevo_estado_maestro:
                    estado_orden = {state[0]: i for i, state in enumerate(Candidato.ESTADOS)}
                    current_order = estado_orden.get(candidato.estado_actual, -1)
                    new_order = estado_orden.get(nuevo_estado_maestro, -1)
                    
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
        
        active_date_for_template = None 
        
        latest_proceso_prefetch = Prefetch(
            'procesos', 
            queryset=Proceso.objects.filter(kanban_activo=True).order_by('-pk').select_related('empresa_proceso', 'supervisor'),
            to_attr='latest_proceso'
        )

        candidatos = Candidato.objects.prefetch_related(latest_proceso_prefetch).all()
        candidatos = candidatos.exclude(estado_actual__in=ESTADOS_FINALES_OCULTOS)
        filtro_registrado = Q(estado_actual='REGISTRADO', kanban_activo=True)
        filtro_activo = Q(procesos__kanban_activo=True)
        candidatos = candidatos.filter(filtro_registrado | filtro_activo).distinct()
        
        if fecha_inicio_filter:
            try:
                active_date_for_template = datetime.strptime(fecha_inicio_filter, '%Y-%m-%d').date()

                candidatos = candidatos.filter(
                    procesos__fecha_inicio=fecha_inicio_filter
                ).distinct()

            except ValueError:
                messages.error(request, "Formato de fecha de filtro inválido. Use AAAA-MM-DD.")
                fecha_inicio_filter = None
                active_date_for_template = None 
            
        if search_query:
            normalized_query = re.sub(r'\D', '', search_query).strip()
            
            filtro = (
                Q(DNI__icontains=search_query) | 
                Q(nombres_completos__icontains=search_query)
            )

            if normalized_query:
                filtro |= Q(telefono_whatsapp__icontains=normalized_query)
            
            candidatos = candidatos.filter(filtro)

        convocatoria_dates = Proceso.objects.filter(
            kanban_activo=True
        ).values('fecha_inicio') \
            .annotate(count=Count('candidato', distinct=True)) \
            .order_by('-fecha_inicio') \
            .filter(fecha_inicio__isnull=False, count__gt=0)

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
                    factor_actitud = 'true' if proceso_actual.factor_aptitud_aplica else 'false'
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
            'active_date': active_date_for_template, 
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
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'Autenticación requerida.'}, status=401)
            
        try:
            if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Invalid request: Must be an AJAX POST.'}, status=400)
            
            dni_list = request.POST.getlist('dnis[]')
            new_status_key = request.POST.get('new_status') 
            fecha_inicio_str = request.POST.get('fecha_inicio') 
            motivo_descarte = request.POST.get('motivo_descarte') 

            if not dni_list or not new_status_key:
                return JsonResponse({'status': 'error', 'message': 'DNI list and new status are required.'}, status=400)

            fecha_inicio_nueva = None
            if fecha_inicio_str:
                try:
                    fecha_inicio_nueva = date.fromisoformat(fecha_inicio_str)
                except ValueError:
                    return JsonResponse({'status': 'error', 'message': 'Formato de fecha de inicio no válido. Use AAAA-MM-DD.'}, status=400)

            proceso_estado_map = {
                'CONVOCADO': 'CONVOCADO', 
                'CONFIRMADO': 'CONFIRMADO',
                'CAPACITACION_TEORICA': 'TEORIA',
                'CAPACITACION_PRACTICA': 'PRACTICA',
                'CONTRATADO': 'CONTRATADO',
                'NO_APTO': 'NO_APTO', 
            }

            proceso_status_to_update = proceso_estado_map.get(new_status_key)
            estado_orden = {state[0]: i for i, state in enumerate(Candidato.ESTADOS)}
            
            candidatos_actualizados = 0

            try:
                default_supervisor = Supervisor.objects.first()
                default_empresa = Empresa.objects.first()
                if not default_supervisor or not default_empresa:
                    raise Exception("Valores por defecto de Supervisor o Empresa no encontrados.")
            except Exception as e:
                 return JsonResponse({'status': 'error', 'message': f'Fallo de configuración: {str(e)}'}, status=500)


            with transaction.atomic():
                
                candidatos = Candidato.objects.filter(DNI__in=dni_list).prefetch_related(
                    Prefetch(
                        'procesos',
                        queryset=Proceso.objects.order_by('-fecha_inicio'), 
                        to_attr='latest_proceso'
                    )
                )
                
                is_to_convocado = new_status_key == 'CONVOCADO'
                if is_to_convocado and not fecha_inicio_nueva:
                    return JsonResponse({'status': 'error', 'message': 'La fecha de inicio es requerida para iniciar el proceso de convocatoria masiva.'}, status=400)

                
                for candidato in candidatos:
                    
                    current_order = estado_orden.get(candidato.estado_actual, -1)
                    new_order = estado_orden.get(new_status_key, -1)

                    if new_order > current_order or new_status_key in ['CONTRATADO', 'NO_APTO', 'DESISTE']:
                        
                        proceso_activo = candidato.latest_proceso[0] if candidato.latest_proceso else None
                        
                        if candidato.estado_actual == 'REGISTRADO' and is_to_convocado:
                            
                            Proceso.objects.create(
                                candidato=candidato,
                                fecha_inicio=fecha_inicio_nueva,
                                supervisor=default_supervisor, 
                                empresa_proceso=default_empresa, 
                                sede_proceso=candidato.sede_registro, 
                                estado='CONVOCADO'
                            )
                            candidato.estado_actual = new_status_key
                            
                        elif proceso_status_to_update:
                            if not proceso_activo:
                                print(f"Advertencia: Candidato {candidato.DNI} sin proceso activo para actualizar a {new_status_key}")
                                continue
                                
                            proceso_activo.estado = proceso_status_to_update
                            proceso_activo.save() 

                            candidato.estado_actual = new_status_key
                            
                        elif new_status_key in ['DESISTE', 'NO_APTO']:
                            candidato.estado_actual = new_status_key
                            
                            if motivo_descarte: 
                                candidato.motivo_descarte = motivo_descarte 
                            
                        else:
                            continue 

                        candidato.usuario_ultima_modificacion = request.user
                        candidato.save()
                        
                        candidatos_actualizados += 1
                        
                if candidatos_actualizados > 0:
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
            print(f"Error fatal en UpdateStatusMultipleView: {e}")
            return JsonResponse({'status': 'error', 'message': f'Error interno del servidor: {str(e)}'}, status=500)

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
        
        context['procesos'] = Proceso.objects.filter(candidato=candidato).order_by('-fecha_inicio').select_related('empresa_proceso', 'supervisor')
        context['title'] = f'Detalle: {candidato.nombres_completos}'
        
        context['ultimo_proceso'] = context['procesos'].first()
        
        if context['ultimo_proceso']:
            context['asistencias'] = RegistroAsistencia.objects.filter(proceso=context['ultimo_proceso']).order_by('-fecha')

        return context

class CandidatoSearchView(View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        results = []

        if query:
            candidatos = Candidato.objects.filter(
                Q(DNI__startswith=query) | 
                Q(nombres_completos__icontains=query) |
                Q(telefono_whatsapp__startswith=query)  
            ).values('DNI', 'nombres_completos', 'telefono_whatsapp')[:10]

            for c in candidatos:
                results.append({
                    'DNI': c['DNI'],
                    'nombres_completos': c['nombres_completos'],
                    'telefono_whatsapp': c['telefono_whatsapp'] if c.get('telefono_whatsapp') else 'N/A',
                })

        return JsonResponse(results, safe=False)

class AsistenciaDiariaCheckView(View):
    """
    REGISTRA la asistencia (Entrada/Salida) manteniendo la compatibilidad 
    con los campos 'estado' y 'estado_asistencia', y corrigiendo la puntualidad.
    """
    def post(self, request, *args, **kwargs):
        query_value = request.POST.get('dni') or request.POST.get('q') 
        
        if not query_value:
            return JsonResponse({'success': False, 'message': 'No se proporcionó valor de búsqueda.'}, status=400)
            
        normalized_query = re.sub(r'\D', '', query_value).strip()
        if not normalized_query:
            return JsonResponse({'success': False, 'message': 'Consulta inválida.'}, status=400)

        zona_horaria_servidor = timezone.get_current_timezone()
        momento_registro = timezone.localtime(timezone.now(), timezone=zona_horaria_servidor)
        hoy_date = momento_registro.date()
        
        try:
            candidato = Candidato.objects.filter(
                Q(DNI=normalized_query) | Q(telefono_whatsapp=normalized_query)
            ).first() 
            
            if not candidato:
                return JsonResponse({'success': False, 'message': f'Candidato no encontrado.'}, status=200)

            proceso_activo = candidato.procesos.filter(
                ~Q(estado__in=['CONTRATADO', 'NO_APTO', 'ABANDONO'])
            ).order_by('-fecha_inicio').first()
            
            if not proceso_activo:
                return JsonResponse({'success': False, 'message': f'Candidato {candidato.DNI} sin Proceso ACTIVO.'}, status=200)

            
            def get_aware_time(h, m):
                naive_time = datetime.combine(hoy_date, time(h, m))
                return make_aware(naive_time, zona_horaria_servidor) 

            hora_limite_entrada = get_aware_time(7, 0) 
            hora_limite_tardanza = get_aware_time(14, 0) 
            
            
            
            entrada_hoy_exists = RegistroAsistencia.objects.filter(
                proceso=proceso_activo,
                momento_registro__date=hoy_date,
                movimiento='ENTRADA' 
            ).exists()
            
            msg_accion = ""
            estado_final = 'A' 
            registrado_por_user = request.user if request.user.is_authenticated else None


            if entrada_hoy_exists:
                movimiento = 'SALIDA'
                
                if momento_registro < hora_limite_tardanza:
                    msg_accion = "⚠️ Se registró la SALIDA, pero fue TEMPRANO (antes de 14:00)."
                else:
                    msg_accion = "✅ Salida registrada con éxito."

            else:
                movimiento = 'ENTRADA'
                
                if momento_registro >= hora_limite_tardanza:
                    estado_final = 'F'
                    msg_accion = "❌ Registro FALLIDO: Es después de las 14:00 y no hay ENTRADA previa. Se marca como FALTA."
                
                elif momento_registro > hora_limite_entrada:
                    estado_final = 'T' 
                    msg_accion = "⚠️ Entrada registrada como TARDE."
                
                else:
                    estado_final = 'A' 
                    msg_accion = "✅ Entrada registrada como PUNTUAL."
            
                        
            FASE_MAP = {
                'CONVOCADO': 'CONFIRMADO', 'TEORIA': 'TEORIA', 'PRACTICA': 'PRACTICA',
            }
            fase_asistencia = FASE_MAP.get(proceso_activo.estado, 'TEORIA')
            
            registro = RegistroAsistencia.objects.create(
                proceso=proceso_activo, 
                
                estado_asistencia=estado_final, 
                estado=estado_final, 
                movimiento=movimiento, 
                fase_actual=fase_asistencia, 
                registrado_por=registrado_por_user,
                momento_registro=momento_registro
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Registro para {candidato.nombres_completos} ({candidato.DNI}): {msg_accion}',
                'dni': candidato.DNI,
                'movimiento': movimiento,
                'estado': estado_final
            }, status=200)

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error interno crítico en el servidor: {e}'}, status=500)

@csrf_exempt 
@require_http_methods(["POST"])
@transaction.atomic
def registrar_asistencia_rapida(request):
    """
    Registra asistencia (solo ENTRADA/SALIDA). CALCULA EL MOVIMIENTO automáticamente,
    corrige la clasificación de estados y mantiene la compatibilidad de campos.
    """
   
    if not request.user.is_authenticated:
        return JsonResponse(
            {'success': False, 'message': 'Fallo de autenticación. Sesión expirada. Recargue la página.'}, 
            status=403
        )

    zona_horaria_servidor = get_current_timezone()
    momento_registro = timezone.localtime(timezone.now(), timezone=zona_horaria_servidor)
    hoy = momento_registro.date()
    
    try:
        proceso_id = request.POST.get('proceso_id')
        fase_actual_key = request.POST.get('fase_actual') 
        
        if not all([proceso_id, fase_actual_key]):
            return JsonResponse(
                {'success': False, 'message': "Error de datos: Faltan campos obligatorios para el registro."}, 
                status=400
            )

        proceso = Proceso.objects.get(pk=proceso_id)
        candidato = proceso.candidato
        candidato_nombre = candidato.nombres_completos
        mensaje_exito = "" 
        estado_final = 'A'

        def get_aware_time(h, m):
            naive_time = datetime.combine(hoy, time(h, m))
            return make_aware(naive_time, zona_horaria_servidor) 
        
        
        falta_existente_hoy = RegistroAsistencia.objects.filter(
            proceso=proceso,
            momento_registro__date=hoy,
            estado='F' 
        ).exists()
        
        if falta_existente_hoy:
            return JsonResponse({
                'success': False, 
                'message': f'⚠️ El candidato {candidato_nombre} ya fue marcado como **FALTA** hoy. Contacte a soporte para corregir el estado.'
            }, status=409)


        entrada_registro = RegistroAsistencia.objects.filter(
            proceso=proceso,
            momento_registro__date=hoy,
            movimiento='ENTRADA' 
        ).first()

        salida_hoy_exists = RegistroAsistencia.objects.filter(
            proceso=proceso,
            momento_registro__date=hoy,
            movimiento='SALIDA' 
        ).exists()

        if entrada_registro is None:
            movimiento = 'ENTRADA'

            hora_limite_entrada = get_aware_time(7, 0)
            hora_limite_tardanza = get_aware_time(14, 0) # 2:00 PM
            
            if momento_registro >= hora_limite_tardanza:
                estado_final = 'F'
                mensaje_exito = f"❌ Registro de ENTRADA FALLIDO (> 14:00). Marcado como **FALTA**."
            elif momento_registro > hora_limite_entrada:
                estado_final = 'T' 
                mensaje_exito = f"⚠️ ENTRADA registrada para {candidato_nombre} como TARDE."
            else:
                estado_final = 'A'
                mensaje_exito = f"🟢 ENTRADA registrada para {candidato_nombre} como PUNTUAL."

        elif entrada_registro is not None and not salida_hoy_exists:
            movimiento = 'SALIDA'
            
            estado_final = entrada_registro.estado
            
            hora_limite_salida = get_aware_time(14, 0)
            
            if momento_registro < hora_limite_salida:
                mensaje_exito = f"⚠️ SALIDA registrada para {candidato_nombre} antes de la hora límite (14:00). Se considera Salida Temprana."
            else:
                mensaje_exito = f"✅ SALIDA registrada para {candidato_nombre} a tiempo. ¡Fin de Jornada!"

        else: 
             return JsonResponse({
                'success': False, 
                'message': f'⛔ El candidato {candidato_nombre} ya tiene registrado su ciclo de ENTRADA/SALIDA completo para hoy.'
            }, status=409)

        RegistroAsistencia.objects.create(
            proceso=proceso,
            candidato=candidato,
            fase_actual=fase_actual_key,
            movimiento=movimiento,
            
            estado_asistencia=estado_final,
            estado=estado_final,
            
            registrado_por=request.user,
            momento_registro=momento_registro
        )
        
        if proceso.estado == 'CONFIRMADO' and fase_actual_key == 'CONVOCADO':
            proceso.estado = 'TEORIA' 
            proceso.save()
            mensaje_exito = f"🎉 ¡Asistencia Registrada y Avance! {candidato_nombre} ha avanzado a la fase de TEORÍA."
            
        return JsonResponse({'success': True, 'message': mensaje_exito})

    except Proceso.DoesNotExist:
        return JsonResponse({'success': False, 'message': "Error: El proceso referenciado no existe o no es válido."}, status=404)

    except Exception as e:
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
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
            
        dni = request.POST.get('dni', '').strip()
        
        if not dni:
            return JsonResponse({'success': False, 'message': 'DNI no puede estar vacío.'})

        try:
            candidato = Candidato.objects.get(DNI=dni)
            
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

            fase_proceso = ultimo_proceso.estado
            
            requiere_entrada_salida = (fase_proceso == 'PRACTICA')
            
            movimiento_requerido = 'REGISTRO' 
            ultimo_registro_hoy = None 
            
            if requiere_entrada_salida:
                hoy = timezone.localdate()
                
                ultimo_registro_hoy = RegistroAsistencia.objects.filter(
                    proceso=ultimo_proceso, 
                    fase_actual=fase_proceso,
                    momento_registro__date=hoy 
                ).order_by('-momento_registro').first()

                if ultimo_registro_hoy and ultimo_registro_hoy.movimiento == 'ENTRADA':
                    movimiento_requerido = 'SALIDA'
                elif ultimo_registro_hoy and ultimo_registro_hoy.movimiento == 'SALIDA':
                    movimiento_requerido = 'ENTRADA'
                else:
                    movimiento_requerido = 'ENTRADA'

            if ultimo_registro_hoy:
                hora_local = timezone.localtime(ultimo_registro_hoy.momento_registro)
                ultimo_registro_str = f"{ultimo_registro_hoy.get_movimiento_display()} a las {hora_local.strftime('%H:%M:%S')}"
            else:
                ultimo_registro_str = '' 

            return JsonResponse({
                'success': True,
                'proceso_id': ultimo_proceso.pk,
                'candidato_nombre': candidato.nombres_completos,
                'candidato_dni': candidato.DNI,
                'fase_proceso': ultimo_proceso.get_estado_display(),
                'fase_proceso_key': fase_proceso,
                'movimiento_requerido': movimiento_requerido,
                'requiere_entrada_salida': requiere_entrada_salida,
                'ultimo_registro': ultimo_registro_str, 
            })

        except Candidato.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'DNI "{dni}" no encontrado en la base de datos.'}, status=404)
        
        except Exception as e:
            print(f"Error en asistencia_dashboard: {e}")
            return JsonResponse({'success': False, 'message': f'Error interno en el servidor: {e}'}, status=500)

    return render(request, 'asistencia_dashboard.html', {'today': date.today()})

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

            proceso_activo = candidato.procesos.order_by('-fecha_inicio').first() 

            proceso_estado_map = {
                'CONVOCADO': 'CONVOCADO',
                'CONFIRMADO':'CONFIRMADO',
                'CAPACITACION_TEORICA': 'TEORIA',
                'CAPACITACION_PRACTICA': 'PRACTICA',
                'CONTRATADO': 'CONTRATADO',
                'NO_APTO': 'NO_APTO', 
            }

            proceso_status_to_update = proceso_estado_map.get(new_status_key)

            current_candidato_estado = candidato.estado_actual

            with transaction.atomic():
                
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
                        estado='CONVOCADO'
                    )
                    proceso_activo = proceso_nuevo
                
                elif proceso_status_to_update and proceso_activo:
                    proceso_activo.estado = proceso_status_to_update
                    proceso_activo.save()

                estado_orden = {state[0]: i for i, state in enumerate(Candidato.ESTADOS)}
                current_order = estado_orden.get(current_candidato_estado, -1)
                new_order = estado_orden.get(new_status_key, -1)
                
                candidato_avanzado = False
                
                if new_order > current_order or new_status_key in ['CONTRATADO', 'NO_APTO']:
                    candidato.estado_actual = new_status_key
                    candidato.save()
                    candidato_avanzado = True
                    
                    proceso_id_respuesta = proceso_activo.pk if proceso_activo else None
                    
                    if new_status_key == 'CONVOCADO' and proceso_activo:
                        display_status_message = proceso_activo.get_estado_display()
                    else:
                        display_status_message = candidato.get_estado_actual_display()

                    return JsonResponse({
                        'status': 'success', 
                        'message': f'Candidato {dni} movido a **{display_status_message}** con éxito.', 
                        'proceso_id': proceso_id_respuesta,
                        'new_status': new_status_key,
                        'new_proceso_status': proceso_activo.get_estado_display() if proceso_activo else 'N/A'
                    })
                
                if not candidato_avanzado:
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
        
        if fecha_filtro_str:
            candidatos_qs = candidatos_qs.filter(procesos__fecha_inicio=fecha_filtro_str).distinct()

        candidatos_qs = candidatos_qs.order_by('fecha_registro').select_related(
            'sede_registro',
            'datoscualificacion' 
        )

        candidatos = candidatos_qs.prefetch_related(
            models.Prefetch('procesos', queryset=proceso_queryset, to_attr='latest_proceso_list')
        )
        
        candidatos_a_exportar = list(candidatos)
        
        if not candidatos_a_exportar:
           
            return redirect('kanban_dashboard')

        data = []
        
        def format_date(date_field):
            return date_field.strftime('%d/%m/%Y') if date_field else ''
        
        def format_bool(bool_field):
            if bool_field is True: return 'SÍ'
            if bool_field is False: return 'NO'
            return 'N/A' 
        
        for c in candidatos_a_exportar:
            ultimo_proceso = c.latest_proceso_list[0] if c.latest_proceso_list else None
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
                'Fecha_Confirmado': format_date(ultimo_proceso.fecha_confirmado) if ultimo_proceso else '',
                'Fecha_Teorico': format_date(ultimo_proceso.fecha_teorico) if ultimo_proceso else '',
                'Fecha_Practico': format_date(ultimo_proceso.fecha_practico) if ultimo_proceso else '',
                'Fecha_Contratacion': format_date(ultimo_proceso.fecha_contratacion) if ultimo_proceso else '',
                'Supervisor_Asignado': ultimo_proceso.supervisor.nombre if ultimo_proceso and ultimo_proceso.supervisor else '',
                'Estado_Proceso': ultimo_proceso.get_estado_display() if ultimo_proceso else 'N/A', 
            }
            
            data.append(row)

       
        column_names = list(data[0].keys()) 
        
        df = pd.DataFrame(data, columns=column_names)
        
        df = df.fillna('')
        df.columns = df.columns.astype(str) 

        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl') 
            
        nombre_hoja = f"Candidatos_{estado}"[:31]
        df.to_excel(writer, sheet_name=nombre_hoja, index=False)

        worksheet = writer.sheets[nombre_hoja]
        
        for col_idx, column in enumerate(df.columns):
            try:
                max_len = df[column].astype(str).str.len().max()
                
                final_width = min(max(max_len, len(column)) + 2, 40)
                
                col_letter = get_column_letter(col_idx + 1)
                worksheet.column_dimensions[col_letter].width = final_width
                
            except Exception:
                col_letter = get_column_letter(col_idx + 1)
                worksheet.column_dimensions[col_letter].width = 20
                continue
                
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
        tipos_documento_disponibles = TipoDocumento.objects.all().order_by('nombre') 

        context = {
            'title': 'Registro y Cualificación de Candidato',
            'is_public': True,
            'sedes': sedes_disponibles,
            'tipos_documento': tipos_documento_disponibles,
            'TIPO_VENTA_CHOICES': DatosCualificacion.TIPO_VENTA_CHOICES,
            'TIEMPO_EXP_CHOICES': DatosCualificacion.TIEMPO_EXP_CHOICES,
        }
        return render(request, 'registro_publico_completo.html', context)

    @transaction.atomic
    def post(self, request):
        tipo_documento_id = request.POST.get('tipo_documento')
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
        
        campos_obligatorios = [tipo_documento_id, dni, nombres_completos, telefono_whatsapp, distrito, experiencia_ventas_tipo, tiempo_experiencia_vendedor, conforme_beneficios, sede_id_seleccionada,email]
        
        if not all(campos_obligatorios):
             messages.error(request, 'Por favor, complete todos los campos obligatorios (*).')
             return redirect('registro_publico_completo')
             
        if secundaria_completa_post is None:
             messages.error(request, 'El campo "¿Tienes secundaria completa?" es obligatorio. Por favor, selecciona Sí o No.')
             return redirect('registro_publico_completo')
             
        secundaria_completa = secundaria_completa_post == 'Si'

        if not (dni and dni.isdigit() and len(dni) == 8):
            messages.error(request, 'El DNI debe tener exactamente 8 dígitos y contener solo números.')
            return redirect('registro_publico_completo')

        if not (telefono_whatsapp and telefono_whatsapp.isdigit() and len(telefono_whatsapp) == 9):
            messages.error(request, 'El número de teléfono (WhatsApp) debe tener exactamente 9 dígitos y contener solo números.')
            return redirect('registro_publico_completo')

        edad_int = int(edad)
        try:
            if edad_int > 35:
                messages.error(request, '❌ Por favor, **leer los requisitos** de postulación publicados para poder continuar')
                return redirect('registro_publico_completo')
        except ValueError:
            messages.error(request, 'La edad debe ser un número entero.')
            return redirect('registro_publico_completo')
        
        try:
             sede_seleccionada = Sede.objects.get(pk=sede_id_seleccionada)
        except Sede.DoesNotExist:
             messages.error(request, 'Error: La sede seleccionada no es válida o no existe.')
             return redirect('registro_publico_completo')
        except Exception as e:
             messages.error(request, f'Error al obtener la sede: {e}')
             return redirect('registro_publico_completo')
        
        try:
             tipo_documento_obj = TipoDocumento.objects.get(pk=tipo_documento_id)
        except TipoDocumento.DoesNotExist:
             messages.error(request, 'Error: El tipo de documento seleccionado no es válido o no existe.')
             return redirect('registro_publico_completo')
        except Exception as e:
             messages.error(request, f'Error en FK (Sede/TipoDoc): {e}')
             return redirect('registro_publico_completo')
            
        try:
            candidato = Candidato.objects.create(
                DNI=dni,
                nombres_completos=nombres_completos,
                edad = edad,
                telefono_whatsapp=telefono_whatsapp,
                email=email if email else None,
                distrito=distrito,
                sede_registro=sede_seleccionada, 
                tipo_documento=tipo_documento_obj,
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
    
    proceso_id = request.POST.get('proceso_id')
    tipo_test = request.POST.get('tipo_test')
    resultado_obtenido = request.POST.get('resultado_obtenido', '').strip()
    archivo = request.FILES.get('archivo')

    if not proceso_id or not tipo_test or not archivo:
        return JsonResponse({'success': False, 'message': 'Faltan datos obligatorios (ID de Proceso, Tipo de Test o Archivo).'}, status=400)

    MAX_RETRIES = 3 
    
    for attempt in range(MAX_RETRIES):
        try:
            proceso = Proceso.objects.get(pk=proceso_id)
            RegistroTest.objects.create(
                proceso=proceso,
                fase_proceso=proceso.estado,
                tipo_test=tipo_test,
                archivo_url=archivo, 
                resultado_obtenido=resultado_obtenido if resultado_obtenido else None,
                registrado_por=request.user
            )
            
            return JsonResponse({
                'success': True, 
                'message': 'Archivo de Test registrado y subido con éxito.'
            })

        except (OperationalError, DatabaseError) as e:
            if "database is locked" not in str(e):
                raise
                
            if attempt < MAX_RETRIES - 1:
                print(f"Intento {attempt + 1} fallido (DB Locked en subida). Reintentando...")
                time.sleep(0.5 * (attempt + 1))
            else:
                return JsonResponse(
                    {'success': False, 'message': f'Error interno en el servidor. Detalles: database is locked tras {MAX_RETRIES} intentos de subida.'}, 
                    status=500
                )
        
        except Proceso.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'El proceso especificado no fue encontrado.'}, status=404)
        
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
            'convocado': 'fecha_inicio',
            'confirmado': 'fecha_confirmado',
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
            'CONVOCADO': ['convocado', 'confirmado'],
            'CONFIRMADO': ['confirmado', 'teorico'], 
            'TEORIA': ['teorico', 'practico'],
            'PRACTICA': ['practico', 'contratacion'],
        }
        
        if date_type not in allowed_changes.get(current_state, []):
            return JsonResponse({
                'success': False, 
                'error': f'No puedes cambiar la fecha de {date_type.capitalize()} porque el proceso está actualmente en estado "{current_state}".'
            }, status=403) 
        
        if date_type == 'convocado':
            if proceso.fecha_confirmado and new_date_obj > proceso.fecha_confirmado:
                return JsonResponse({
                    'success': False, 
                    'error': f'La nueva Fecha de Inicio ({new_date}) es posterior a la Fecha Confirmado ({proceso.fecha_confirmado.strftime("%d/%m/%Y")}).'
                }, status=400)
            
        elif date_type == 'confirmado':
            if proceso.fecha_inicio and new_date_obj < proceso.fecha_inicio:
                return JsonResponse({
                    'success': False,
                    'error': f'La Fecha Confirmado no puede ser anterior a la Fecha de Inicio ({proceso.fecha_inicio.strftime("%d/%m/%Y")}).'
                }, status=400)
            if proceso.fecha_teorico and new_date_obj > proceso.fecha_teorico:
                return JsonResponse({
                    'success': False,
                    'error': f'La Fecha Confirmado no puede ser posterior a la Fecha Teórica actual ({proceso.fecha_teorico.strftime("%d/%m/%Y")}).'
                }, status=400)

        elif date_type == 'teorico':
            if proceso.fecha_confirmado and new_date_obj < proceso.fecha_confirmado:
                return JsonResponse({
                    'success': False, 
                    'error': f'La Fecha Teórica no puede ser anterior a la Fecha Confirmado ({proceso.fecha_confirmado.strftime("%d/%m/%Y")}).'
                }, status=400)
            if proceso.fecha_practico and new_date_obj > proceso.fecha_practico:
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

class DesactivarConvocatoriaView(LoginRequiredMixin, View):
    """
    Desactiva masivamente la visibilidad de todos los procesos de una fecha 
    de convocatoria específica en el Kanban, actualizando kanban_activo=False.
    """
    def post(self, request, *args, **kwargs):
        fecha_filtro_str = request.POST.get('fecha_filtro') 
        redirect_url = request.META.get('HTTP_REFERER', 'kanban_dashboard')
        
        if not fecha_filtro_str:
            messages.error(request, "Error: No se proporcionó una fecha de convocatoria para desactivar.")
            return redirect(redirect_url) 

        try:
            fecha_obj = datetime.strptime(fecha_filtro_str, '%Y-%m-%d').date()
            accion_tipo = request.POST.get('accion_tipo', 'DIA') 
            
            if accion_tipo == 'MES':
                count = Proceso.objects.filter(
                    fecha_inicio__year=fecha_obj.year,
                    fecha_inicio__month=fecha_obj.month,
                    kanban_activo=True
                ).update(kanban_activo=False)
                display_msg = f"Se han ocultado {count} procesos del MES: {fecha_obj.strftime('%B %Y')}"
            else: 
                 count = Proceso.objects.filter(
                    fecha_inicio=fecha_obj, 
                    kanban_activo=True
                 ).update(kanban_activo=False)
                 display_msg = f"Se han ocultado {count} procesos del DÍA: {fecha_filtro_str}"
            
            messages.success(request, f"🎉 ¡Éxito! {display_msg}. Los candidatos han sido archivados del Kanban.")
            
        except ValueError:
            messages.error(request, "Error de Formato de Fecha: La fecha proporcionada no es válida (debe ser YYYY-MM-DD).")
        except Exception as e:
            messages.error(request, f"Error CRÍTICO al desactivar la convocatoria: {e}")
            
        return redirect(redirect_url) 

class ActivarConvocatoriaView(LoginRequiredMixin, View):
    """
    Activa masivamente los procesos de una fecha de convocatoria para 
    que vuelvan a mostrarse en el Kanban, actualizando kanban_activo=True.
    """
    def post(self, request, *args, **kwargs):
        fecha_filtro_str = request.POST.get('fecha_filtro') 
        redirect_url = request.META.get('HTTP_REFERER', 'kanban_dashboard')
        
        if not fecha_filtro_str:
            messages.error(request, "Error: No se proporcionó una fecha de convocatoria para activar.")
            return redirect(redirect_url)
            
        try:
            fecha_obj = datetime.strptime(fecha_filtro_str, '%Y-%m-%d').date()
            accion_tipo = request.POST.get('accion_tipo', 'DIA') 

            if accion_tipo == 'MES':
                count = Proceso.objects.filter(
                    fecha_inicio__year=fecha_obj.year,
                    fecha_inicio__month=fecha_obj.month,
                    kanban_activo=False
                ).update(kanban_activo=True)
                display_msg = f"Se han reactivado {count} procesos del MES: {fecha_obj.strftime('%B %Y')}"
            else: 
                count = Proceso.objects.filter(
                    fecha_inicio=fecha_obj, 
                    kanban_activo=False
                ).update(kanban_activo=True)
                display_msg = f"Se han reactivado {count} procesos del DÍA: {fecha_filtro_str}"
            
            messages.success(request, f"✅ ¡Éxito! {display_msg}. Los candidatos han regresado al Kanban.")
            
        except ValueError:
            messages.error(request, "Error de Formato de Fecha: La fecha proporcionada no es válida (debe ser YYYY-MM-DD).")
        except Exception as e:
            messages.error(request, f"Error CRÍTICO al activar la convocatoria: {e}")
            
        return redirect(redirect_url)

class ListaConvocatoriasView(LoginRequiredMixin, View):
    """
    Muestra las convocatorias agrupadas por mes/año, permitiendo el filtrado por mes.
    Asegura que los nombres de los meses estén en español usando django.utils.formats.
    """
    def get(self, request, *args, **kwargs):
        
        month_year_str = request.GET.get('mes')
        
        if month_year_str:
            try:
                filter_date = datetime.strptime(month_year_str, '%Y-%m').date()
                year_filter = filter_date.year
                month_filter = filter_date.month
            except ValueError:
                filter_date = date.today()
                year_filter = filter_date.year
                month_filter = filter_date.month
                month_year_str = filter_date.strftime('%Y-%m')
        else:
            filter_date = date.today()
            year_filter = filter_date.year
            month_filter = filter_date.month
            month_year_str = filter_date.strftime('%Y-%m') 

        try:
            dates_and_status = Proceso.objects \
                .filter(
                    fecha_inicio__isnull=False,  
                    fecha_inicio__year=year_filter,
                    fecha_inicio__month=month_filter
                ) \
                .values('fecha_inicio') \
                .annotate(
                    is_active=Max('kanban_activo'), 
                    total_procesos=Count('pk')
                ) \
                .order_by('fecha_inicio')
                
        except Exception as e:
            print(f"Error en la consulta de Proceso Principal: {e}") 
            dates_and_status = []
            
        convocations_by_month = {}
        
        month_display_name = date_format(date(year_filter, month_filter, 1), "F \d\e Y").capitalize()

        if dates_and_status:
            for item in dates_and_status:
                fecha_inicio = item['fecha_inicio']
                month_key = fecha_inicio.strftime('%Y-%m')
                
                if month_key not in convocations_by_month:
                    convocations_by_month[month_key] = {'display': month_display_name, 'dates': []}
                    
                convocations_by_month[month_key]['dates'].append({
                    'fecha_obj': fecha_inicio, 
                    'fecha_str': fecha_inicio.strftime('%Y-%m-%d'),
                    'total_procesos': item['total_procesos'],
                    'is_active': item['is_active']
                })
        
        available_months = Proceso.objects \
            .filter(fecha_inicio__isnull=False) \
            .annotate(year=ExtractYear('fecha_inicio'), month=ExtractMonth('fecha_inicio')) \
            .values('year', 'month') \
            .distinct() \
            .order_by('-year', '-month')
            
        month_options = []
        for am in available_months:
            temp_date = date(am['year'], am['month'], 1)
            display_name = date_format(temp_date, "F \d\e Y").capitalize()
            
            month_options.append({
                'value': temp_date.strftime('%Y-%m'),
                'display': display_name,
                'selected': temp_date.strftime('%Y-%m') == month_year_str,
            })
            
        context = {
            'convocations_by_month': list(convocations_by_month.values()),
            'url_activar': 'activar_convocatoria',
            'url_desactivar': 'desactivar_convocatoria',
            'month_options': month_options, 
            'current_filter': month_year_str,
            'current_month_data': list(convocations_by_month.values())[0] if convocations_by_month else {'display': month_display_name},
        }
        
        return render(request, 'includes/modal_gestion_convocatorias.html', context)

ESTADOS_FINALES_OCULTOS = ['DESISTE', 'NO_APTO']
class CandidatoListView(LoginRequiredMixin, ListView):
    model = Candidato
    template_name = 'candidatos_list.html'
    context_object_name = 'candidatos'
    paginate_by = 25 
    ordering = ['-fecha_registro'] 

    def get_queryset(self):
        queryset = super().get_queryset()

        search_query = self.request.GET.get('search')
        estado_filter = self.request.GET.get('estado')
        motivo_descarte_filter = self.request.GET.get('descarte')
        fecha_inicio_str = self.request.GET.get('fecha_inicio')
        fecha_final_str = self.request.GET.get('fecha_final')
        
        if search_query:
            queryset = queryset.filter(
                Q(DNI__icontains=search_query) | 
                Q(nombres_completos__icontains=search_query)
            )
            
        if estado_filter:
            queryset = queryset.filter(estado_actual=estado_filter)
        
        if motivo_descarte_filter:
            queryset = queryset.filter(motivo_descarte=motivo_descarte_filter)
            
        if fecha_inicio_str:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                queryset = queryset.filter(fecha_registro__gte=fecha_inicio)
            except ValueError:
                pass 
        
        if fecha_final_str:
            try:
                fecha_final_date = datetime.strptime(fecha_final_str, '%Y-%m-%d').date()
                fecha_final_dt = datetime.combine(fecha_final_date, time.max)
                queryset = queryset.filter(fecha_registro__lte=fecha_final_dt)
            except ValueError:
                pass 

        if self.request.GET.get('asistencia') == 'presentes':
            pass
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pasar las opciones de filtro al template
        context['ESTADOS_CANDIDATO'] = Candidato.ESTADOS
        context['MOTIVOS_DESCARTE'] = MOTIVOS_DESCARTE 
        
        # Pasar los filtros activos para rellenar el formulario
        context['active_filters'] = self.request.GET.dict() 
        
        return context

def format_date(dt):
    if isinstance(dt, date):
        return dt.strftime('%Y-%m-%d')
    return ''

def format_bool(val):
    if val is True:
        return 'Sí'
    elif val is False:
        return 'No'
    return ''

class CandidatoExportView(LoginRequiredMixin, View):
    
    def get(self, request, *args, **kwargs):
        
        search_query = request.GET.get('search')
        estado_filter = request.GET.get('estado')
        motivo_descarte_filter = request.GET.get('descarte')
        fecha_inicio_str = request.GET.get('fecha_inicio')
        fecha_final_str = request.GET.get('fecha_final')
        
        candidatos_qs = Candidato.objects.all()
                
        # Aplicar filtros de texto y estado
        if search_query:
            candidatos_qs = candidatos_qs.filter(
                Q(DNI__icontains=search_query) | 
                Q(nombres_completos__icontains=search_query)
            )
            
        if estado_filter:
            candidatos_qs = candidatos_qs.filter(estado_actual=estado_filter)
        
        if motivo_descarte_filter:
            candidatos_qs = candidatos_qs.filter(motivo_descarte=motivo_descarte_filter)
            
        # Aplicar filtros de rango de fechas
        if fecha_inicio_str:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                candidatos_qs = candidatos_qs.filter(fecha_registro__gte=fecha_inicio)
            except ValueError:
                pass
        
        if fecha_final_str:
            try:
                fecha_final_date = datetime.strptime(fecha_final_str, '%Y-%m-%d').date()
                fecha_final_dt = datetime.combine(fecha_final_date, time.max)
                candidatos_qs = candidatos_qs.filter(fecha_registro__lte=fecha_final_dt)
            except ValueError:
                pass
        
        # Optimización
        proceso_queryset = Proceso.objects.order_by('-fecha_inicio').select_related('supervisor', 'empresa_proceso')
        
        candidatos_qs = candidatos_qs.order_by('fecha_registro').select_related(
            'sede_registro',
            'datoscualificacion' 
        ).prefetch_related(
            models.Prefetch('procesos', queryset=proceso_queryset, to_attr='latest_proceso_list')
        )
        
        candidatos_a_exportar = list(candidatos_qs)
        
        # FUNCIONES AUXILIARES
        def format_date(date_field):
            return date_field.strftime('%d/%m/%Y') if date_field else ''
        
        def format_bool(bool_field):
            if bool_field is True: return 'SÍ'
            if bool_field is False: return 'NO'
            return 'N/A' 
        
        # PREPARACIÓN DE DATOS
        data = []
        for c in candidatos_a_exportar:
            ultimo_proceso = c.latest_proceso_list[0] if c.latest_proceso_list else None
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
                'Fecha_Confirmado': format_date(ultimo_proceso.fecha_confirmado) if ultimo_proceso else '' ,
                'Fecha_Teorico': format_date(ultimo_proceso.fecha_teorico) if ultimo_proceso else '',
                'Fecha_Practico': format_date(ultimo_proceso.fecha_practico) if ultimo_proceso else '',
                'Fecha_Contratacion': format_date(ultimo_proceso.fecha_contratacion) if ultimo_proceso else '',
                'Supervisor_Asignado': ultimo_proceso.supervisor.nombre if ultimo_proceso and ultimo_proceso.supervisor else '',
                'Estado_Proceso': ultimo_proceso.get_estado_display() if ultimo_proceso else 'N/A', 
            }
            data.append(row)
        
        # GENERACIÓN DEL EXCEL
        column_names = [
            'DNI', 'Nombres_Completos', 'Telefono_Whatsapp', 'Email', 'Edad', 'Distrito_Candidato', 
            'Estado_Actual_Candidato', 'Fecha_Registro', 'Sede_Registro', 
            'Secundaria_Completa', 'Exp_Campanas_Espanolas', 'Tipo_Exp_Ventas', 
            'Empresa_Exp_Ventas', 'Tiempo_Experiencia_Vendedor', 'Conforme_Beneficios', 
            'Detalle_Beneficios_Otro', 'Disponibilidad_Horario', 'Discapacidad_Enfermedad_Cronica', 
            'Dificultad_Habla', 'Empresa_Cliente', 'Fecha_Convocatoria', 'Fecha_Confirmado', 
            'Fecha_Teorico', 'Fecha_Practico', 'Fecha_Contratacion', 'Supervisor_Asignado', 
            'Estado_Proceso'
        ]
        
        df = pd.DataFrame(data, columns=column_names)
        df = df.fillna('')
        df.columns = df.columns.astype(str) 

        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl') 
            
        nombre_hoja = f"Candidatos_Reporte"[:31]
        df.to_excel(writer, sheet_name=nombre_hoja, index=False)

        # AJUSTE ROBUSTO DE ANCHO DE COLUMNA
        worksheet = writer.sheets[nombre_hoja]
        
        for col_idx, column in enumerate(column_names):
            # Usamos el nombre de la columna para asegurar un ancho mínimo
            max_len = len(column) 
            
            # Si hay datos, calculamos la longitud máxima real
            if not df.empty:
                try:
                    max_data_len = df[column].astype(str).str.len().max()
                    max_len = max(max_len, max_data_len)
                except Exception:
                    pass
            
            final_width = min(max_len + 2, 40)
            col_letter = get_column_letter(col_idx + 1)
            worksheet.column_dimensions[col_letter].width = final_width
                
        writer.close() 

        output.seek(0)

        filename = f"candidatos_reporte_{date.today().strftime('%Y%m%d')}.xlsx"

        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

class CandidatoAsistenciaListView(LoginRequiredMixin, ListView):
    model = Candidato
    template_name = 'candidatos_asistencia_list.html'
    context_object_name = 'candidatos'
    paginate_by = 25 
    ordering = ['-total_registros', '-fecha_registro'] 

    def get_queryset(self):
        hoy = timezone.localdate()

        VALID_ATTENDANCE_STATES = ['CONVOCADO','CONFIRMADO', 'TEORIA', 'PRACTICA']
        DEFAULT_STATE_SUPERVISOR = 'PRACTICA' 
        
        proceso_filter_q = Q(procesos__estado__in=VALID_ATTENDANCE_STATES)
        
        latest_attendance = RegistroAsistencia.objects.filter(
            candidato=OuterRef('pk'),
            proceso__estado__in=VALID_ATTENDANCE_STATES
        ).order_by('-momento_registro').values(
            'momento_registro', 'fase_actual', 'movimiento', 'estado'
        )[:1]
        
        asistencia_hoy = RegistroAsistencia.objects.filter(
            candidato=OuterRef('pk'),
            momento_registro__date=hoy
        ).exclude(estado=None).order_by('-momento_registro').values('estado')[:1]
        
        queryset = Candidato.objects.annotate(
            total_registros=Count('registroasistencia', filter=proceso_filter_q, distinct=True),
            total_tardanzas=Count('registroasistencia', filter=Q(registroasistencia__estado='T') & proceso_filter_q),
            total_faltas=Count('registroasistencia', filter=Q(registroasistencia__estado='F') & proceso_filter_q),
            total_asistencias_puntuales=Count('registroasistencia', filter=Q(registroasistencia__estado='A') & proceso_filter_q),
            
            ultima_fase=Subquery(latest_attendance.values('fase_actual')[:1], output_field=models.CharField()),
            ultimo_movimiento=Subquery(latest_attendance.values('movimiento')[:1], output_field=models.CharField()),
            ultimo_registro_momento=Subquery(latest_attendance.values('momento_registro')[:1], output_field=models.DateTimeField()),
            asistencia_hoy=Subquery(asistencia_hoy, output_field=models.CharField())
        ).filter(
            procesos__estado__in=VALID_ATTENDANCE_STATES
        )
        
        search_query = self.request.GET.get('search')
        estado_filter = self.request.GET.get('estado')
        supervisor_filter = self.request.GET.get('supervisor')
        
        if supervisor_filter: 
            queryset = queryset.filter(
                procesos__estado=DEFAULT_STATE_SUPERVISOR,
                procesos__supervisor__pk=supervisor_filter
            )
        
        elif estado_filter:
            queryset = queryset.filter(procesos__estado=estado_filter)
            
        if search_query:
            queryset = queryset.filter(
                Q(DNI__icontains=search_query) | 
                Q(nombres_completos__icontains=search_query)
            )
            
        queryset = queryset.distinct() 
            
        return queryset.order_by(*self.ordering)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        VALID_ATTENDANCE_STATES = ['CONVOCADO','CONFIRMADO', 'TEORIA', 'PRACTICA']
        DEFAULT_STATE_SUPERVISOR = 'PRACTICA'
        
        estado_is_in_get = 'estado' in self.request.GET
        supervisor_is_in_get = 'supervisor' in self.request.GET
        is_initial_load = not estado_is_in_get and not supervisor_is_in_get

        active_filters = self.request.GET.dict().copy()
        
        if 'supervisor' in active_filters and active_filters.get('supervisor'):
            active_filters['estado'] = DEFAULT_STATE_SUPERVISOR
            
        context['active_filters'] = active_filters 
        
        context['SUPERVISORES'] = Supervisor.objects.all().order_by('nombre')
        
        context['ESTADOS_CANDIDATO'] = [
            (key, label) for key, label in Proceso.ESTADOS_PROCESO 
            if key in VALID_ATTENDANCE_STATES
        ] 
        
        candidato_dnies_activos = Candidato.objects.filter(
            procesos__estado__in=VALID_ATTENDANCE_STATES
        ).values_list('DNI', flat=True)

        conteo_global_registros = RegistroAsistencia.objects.filter(
            candidato__DNI__in=candidato_dnies_activos
        ).aggregate(
            A=Count('pk', filter=Q(estado='A')), 
            T=Count('pk', filter=Q(estado='T')), 
            F=Count('pk', filter=Q(estado='F')),
        )
        
        conteo_dict = {
            'A': conteo_global_registros.get('A', 0),
            'T': conteo_global_registros.get('T', 0),
            'F': conteo_global_registros.get('F', 0),
        }
        
        context['FASES_ASISTENCIA'] = RegistroAsistencia.FASE_ASISTENCIA 
        context['MOVIMIENTO_MAP'] = dict(RegistroAsistencia.TIPO_MOVIMIENTO) 
        
        context['total_candidatos'] = Candidato.objects.filter(procesos__estado__in=VALID_ATTENDANCE_STATES).count()
        context['conteo_asistencias'] = conteo_dict
        context['current_year'] = date.today().year

        return context

class RegistroAsistenciaDetailView(LoginRequiredMixin, DetailView):
    """ Devuelve SOLAMENTE el fragmento HTML del detalle de asistencia para el modal,
        manejando la autenticación de HTMX. """
        
    model = Candidato
    template_name = 'registro_asistencia_modal_fragment.html' 
    context_object_name = 'candidato'

    def handle_no_permission(self):
        if self.request.headers.get('Hx-Request') == 'true':
            response = HttpResponse(status=401) 
            response['HX-Redirect'] = self.get_login_url()
            return response
        
        return super().handle_no_permission()


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        candidato = self.get_object()
        
        all_registros = candidato.registroasistencia_set.all().select_related(
            'proceso', 'registrado_por','proceso__empresa_proceso'
        ).order_by('-momento_registro')
        
        registros_agrupados = {}
        for reg in all_registros:
            date_key = reg.momento_registro.date().isoformat()
            phase_key = reg.fase_actual
            group_key = f"{date_key}_{phase_key}"
            
            if group_key not in registros_agrupados:
                registros_agrupados[group_key] = {
                    'date': reg.momento_registro.date(),
                    'phase': reg.get_fase_actual_display(),
                    'registros': [] 
                }
            
            registros_agrupados[group_key]['registros'].append(reg)
        
        context['registros_agrupados'] = registros_agrupados.values()
        context['MOVIMIENTO_MAP'] = dict(RegistroAsistencia.TIPO_MOVIMIENTO) 
        
        return context
    
class RegistrarDocumentoView(LoginRequiredMixin, View):  
    def post(self, request, *args, **kwargs):
        if not request.POST or not request.FILES:
             return HttpResponseBadRequest("Faltan datos de formulario o archivos.")

        proceso_id = request.POST.get('proceso_id')
        tipo_documento = request.POST.get('tipo_documento')
        observaciones = request.POST.get('observaciones_doc')
        archivo = request.FILES.get('archivo_doc')
        
        if not proceso_id or not tipo_documento or not archivo:
            return HttpResponseBadRequest("Faltan campos obligatorios (Proceso ID, Tipo o Archivo).")

        try:
            proceso = get_object_or_404(Proceso, pk=proceso_id)
            candidato = proceso.candidato 
            
            DocumentoCandidato.objects.create(
                candidato=candidato,
                proceso=proceso,
                tipo_documento=tipo_documento,
                archivo=archivo,
                observaciones=observaciones,
                subido_por=request.user
            )

            response = HttpResponse(status=200)
            response['HX-Trigger'] = 'documentoSubidoExitosamente'
            return response
            
        except Proceso.DoesNotExist:
            return HttpResponseBadRequest("Proceso no encontrado.")
        except IntegrityError:
            return HttpResponseBadRequest("Error al guardar en la base de datos.")
        except Exception as e:
            return HttpResponse(f"Error interno del servidor: {e}", status=500)
        
class HistoryDetailView(LoginRequiredMixin, View):
    """
    Vista para obtener el historial detallado de un CANDIDATO específico (por DNI).
    """
    def get(self, request, dni):
        try:
            # Usamos .get() directo para controlar la excepción DoesNotExist
            candidato = Candidato.objects.get(DNI=dni)
            
            procesos = candidato.procesos.all().order_by('-fecha_inicio')
            procesos_data = []
            
            for index, proceso in enumerate(procesos):
                is_active = (index == 0) 
                
                proceso_detail = {
                    'proceso_id': proceso.pk,
                    'fecha_inicio': proceso.fecha_inicio.strftime('%d/%m/%Y'),
                    'estado_proceso': proceso.get_estado_display(),
                    'empresa_proceso': proceso.empresa_proceso.nombre if proceso.empresa_proceso else 'N/A',
                    'sede_proceso': proceso.sede_proceso.nombre if proceso.sede_proceso else 'N/A',
                    'supervisor_nombre': proceso.supervisor.nombre if proceso.supervisor else 'Pendiente',
                    'resultado_final': proceso.get_estado_display() if proceso.estado in ['CONTRATADO', 'NO_APTO', 'ABANDONO'] else 'En Curso',
                    'es_activo': is_active
                }

                if is_active:
                    ultima_momento_qs = proceso.registroasistencia_set.aggregate(Max('momento_registro'))
                    ultima_momento = ultima_momento_qs['momento_registro__max']
                    
                    proceso_detail['ultima_momento'] = (
                        ultima_momento.strftime('%d/%m/%Y %H:%M') 
                        if ultima_momento else 'Sin registro'
                    )
                    
                    # Validaciones seguras de relaciones
                    documentos_totales = getattr(proceso, 'documentocandidato_set', None)
                    documentos_count = documentos_totales.count() if documentos_totales else 0
                    proceso_detail['documentacion'] = f"{documentos_count} documentos subidos"
                    
                    comentarios_rel = getattr(proceso, 'comentarios', None)
                    proceso_detail['num_comentarios'] = comentarios_rel.count() if comentarios_rel else 0
                    
                    tests_rel = getattr(proceso, 'tests_registrados', None)
                    proceso_detail['num_tests'] = tests_rel.count() if tests_rel else 0
                    
                procesos_data.append(proceso_detail)

            response_data = {
                'status': 'success',
                'candidato_info': {
                    'dni': candidato.DNI,
                    'nombre': candidato.nombres_completos,
                    'estado_maestro': candidato.get_estado_actual_display(),
                },
                'procesos': procesos_data
            }
            
            return JsonResponse(response_data)

        except Candidato.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': f'Candidato con DNI {dni} no encontrado.'}, status=404)
            
        except Exception as e:
            print(f"Error CRÍTICO en HistoryDetailView: {e}") 
            return JsonResponse({'status': 'error', 'message': f'Error interno: {str(e)}'}, status=500)

class OcultarCandidatosView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        fecha_filtro_str = request.POST.get('fecha_filtro') 
        accion_tipo = request.POST.get('accion_tipo', 'DIA') 
        
        candidatos_con_proceso_iniciado = Proceso.objects.filter(
            candidato=OuterRef('pk'), 
            fecha_inicio__isnull=False
        )
        
        if not fecha_filtro_str:
            messages.error(request, "Error: No se proporcionó una fecha de registro para ocultar.")
            return redirect(REDIRECT_URL)
            
        try:
            fecha_obj = datetime.strptime(fecha_filtro_str, '%Y-%m-%d').date()
            
            base_qs = Candidato.objects.filter(
                estado_actual='REGISTRADO',
                kanban_activo=True
            ).exclude(
                Exists(candidatos_con_proceso_iniciado)
            )
            
            if accion_tipo == 'MES':
                qs = base_qs.filter(
                    fecha_registro__year=fecha_obj.year,
                    fecha_registro__month=fecha_obj.month,
                )
                filtro_display = fecha_obj.strftime('%B %Y')
            
            elif accion_tipo == 'DIA':
                qs = base_qs.filter(
                    fecha_registro=fecha_obj,
                )
                filtro_display = fecha_filtro_str
            
            else:
                messages.error(request, "Error: Tipo de acción masiva no válida.")
                return redirect(REDIRECT_URL)
            
            count = qs.update(kanban_activo=False)
            
            messages.success(request, 
                f"🎉 ¡Éxito! Se han ocultado **{count}** candidatos registrados en **{filtro_display}**."
            )
            
        except ValueError:
            messages.error(request, "Error de Formato de Fecha: La fecha proporcionada no es válida (debe ser YYYY-MM-DD).")
        except Exception as e:
            messages.error(request, f"Error CRÍTICO al ocultar candidatos: {e}")
            
        return HttpResponse(status=204)

class MostrarCandidatosView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        fecha_filtro_str = request.POST.get('fecha_filtro') 
        accion_tipo = request.POST.get('accion_tipo', 'DIA')
        
        candidatos_con_proceso_iniciado = Proceso.objects.filter(
            candidato=OuterRef('pk'), 
            fecha_inicio__isnull=False
        )
        
        if not fecha_filtro_str:
            messages.error(request, "Error: No se proporcionó una fecha de registro para mostrar.")
            return redirect(REDIRECT_URL)
            
        try:
            fecha_obj = datetime.strptime(fecha_filtro_str, '%Y-%m-%d').date()
            
            base_qs = Candidato.objects.filter(
                estado_actual='REGISTRADO',
                kanban_activo=False
            ).exclude(
                Exists(candidatos_con_proceso_iniciado)
            )
            
            if accion_tipo == 'MES':
                qs = base_qs.filter(
                    fecha_registro__year=fecha_obj.year,
                    fecha_registro__month=fecha_obj.month,
                )
                filtro_display = fecha_obj.strftime('%B %Y')
            
            elif accion_tipo == 'DIA':
                qs = base_qs.filter(
                    fecha_registro=fecha_obj,
                )
                filtro_display = fecha_filtro_str
            
            else:
                messages.error(request, "Error: Tipo de acción masiva no válida.")
                return redirect(REDIRECT_URL)

            count = qs.update(kanban_activo=True)
            
            messages.success(request, 
                f"✅ ¡Éxito! Se han reactivado **{count}** candidatos registrados en **{filtro_display}**. Han regresado al Kanban."
            )
            
        except ValueError:
            messages.error(request, "Error de Formato de Fecha: La fecha proporcionada no es válida (debe ser YYYY-MM-DD).")
        except Exception as e:
            messages.error(request, f"Error CRÍTICO al mostrar candidatos: {e}")
            
        return HttpResponse(status=204)      

def set_locale_es():
    try:
        if platform.system() == "Windows":
            locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
        else:
            locale.setlocale(locale.LC_TIME, 'es_ES.utf8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'es')
        except locale.Error:
            pass

MESES_ESPANOL = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto', 
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}
class ListaCandidatosPorFechaView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        
        month_year_str = request.GET.get('mes')
        
        if month_year_str:
            try:
                filter_date = datetime.strptime(month_year_str, '%Y-%m').date()
                year_filter = filter_date.year
                month_filter = filter_date.month
            except ValueError:
                now = date.today()
                year_filter = now.year
                month_filter = now.month
                month_year_str = now.strftime('%Y-%m')
        else:
            now = date.today()
            year_filter = now.year
            month_filter = now.month
            month_year_str = now.strftime('%Y-%m')

        candidatos_con_proceso_iniciado = Proceso.objects.filter(
            candidato=OuterRef('pk'), 
            fecha_inicio__isnull=False
        )

        dates_and_status = Candidato.objects \
            .filter(
                estado_actual='REGISTRADO',
                fecha_registro__year=year_filter,
                fecha_registro__month=month_filter,
            ) \
            .exclude(
                Exists(candidatos_con_proceso_iniciado)
            ) \
            .annotate(
                fecha_solo_dia=Cast('fecha_registro', output_field=DateField())
            ) \
            .values('fecha_solo_dia', 'kanban_activo') \
            .annotate(
                is_active=Max('kanban_activo'), 
                total_candidatos=Count('pk')
            ) \
            .order_by('-fecha_solo_dia')
            
        candidatos_by_month = {}
        current_month_name = MESES_ESPANOL.get(month_filter, month_year_str) 
        month_display_name = f"{current_month_name} {year_filter}"
        
        for item in dates_and_status:
            fecha_registro = item['fecha_solo_dia']
            if not fecha_registro: continue
                
            month_key = fecha_registro.strftime('%Y-%m')
            
            if month_key not in candidatos_by_month:
                candidatos_by_month[month_key] = {
                    'display': month_display_name,
                    'dates': []
                }
                
            candidatos_by_month[month_key]['dates'].append({
                'fecha_obj': fecha_registro,
                'fecha_str': fecha_registro.strftime('%Y-%m-%d'),
                'total_candidatos': item['total_candidatos'],
                'is_active': item['is_active']
            })
            
        available_months = Candidato.objects \
            .filter(estado_actual='REGISTRADO') \
            .exclude(Exists(candidatos_con_proceso_iniciado)) \
            .annotate(year=ExtractYear('fecha_registro'), month=ExtractMonth('fecha_registro')) \
            .values('year', 'month') \
            .distinct() \
            .order_by('-year', '-month')
            
        month_options = []
        for am in available_months:
            temp_date = date(am['year'], am['month'], 1)
            
            month_name = MESES_ESPANOL.get(am['month'], temp_date.strftime('%B'))
            display_name = f"{month_name} de {am['year']}"
            
            month_options.append({
                'value': temp_date.strftime('%Y-%m'),
                'display': display_name,
                'selected': temp_date.strftime('%Y-%m') == month_year_str,
            })
            
        context = {
            'candidatos_by_month': candidatos_by_month.values(),
            'url_mostrar': 'mostrar_candidatos',
            'url_ocultar': 'ocultar_candidatos',
            'title': f'Gestión de Candidatos Registrados ({month_display_name})',
            'month_options': month_options, 
            'current_filter': month_year_str,
        }
        
        return render(request, 'includes/modal_gestion_candidatos.html', context)
    
PROCESO_ESTADO_MAP = {
    'REGISTRADOS': 'REGISTRADO', 
    'CONVOCADOS': 'CONVOCADO',  
    'CONFIRMADOS': 'CONFIRMADO',   
    'TEORIA': 'TEORIA',           
    'PRACTICA': 'PRACTICA',       
    'CONTRATADOS': 'CONTRATADO',  
}

class MensajeriaDashboardView(LoginRequiredMixin, TemplateView):
    """Renderiza la interfaz principal del módulo de mensajería."""
    template_name = 'dashboard_mensajeria.html' # Ajusta a tu ruta real

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['procesos_opciones'] = [
            {'value': key, 'display': key.replace('_', ' ')} 
            for key in PROCESO_ESTADO_MAP.keys()
        ]
        
        return context
    
class MensajeriaAPIView(LoginRequiredMixin, View):
    """API para obtener fechas y contactos por proceso/fecha."""
    
    def get(self, request, *args, **kwargs):
        accion = request.GET.get('accion')
        proceso_tipo = request.GET.get('proceso')
        
        if not accion or not proceso_tipo:
             return JsonResponse({'status': 'error', 'message': 'Faltan parámetros.'}, status=400)

        if proceso_tipo not in PROCESO_ESTADO_MAP:
            return JsonResponse({'status': 'error', 'message': 'Tipo de proceso no válido.'}, status=400)
        
        estado_db = PROCESO_ESTADO_MAP[proceso_tipo]
        
        try:
            if accion == 'get_fechas':
                fechas_disponibles = self._get_fechas_disponibles(proceso_tipo, estado_db)
                return JsonResponse({'status': 'success', 'fechas': fechas_disponibles})
            
            elif accion == 'get_contactos':
                fecha_str = request.GET.get('fecha')
                if not fecha_str:
                    return JsonResponse({'status': 'error', 'message': 'Falta la fecha.'}, status=400)
                    
                contactos = self._get_contactos_por_filtro(proceso_tipo, estado_db, fecha_str)
                return JsonResponse({'status': 'success', 'contactos': contactos})
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        
        return JsonResponse({'status': 'error', 'message': 'Acción desconocida.'}, status=400)

    def _get_fechas_disponibles(self, proceso_tipo, estado_db):
        """
        Obtiene las fechas únicas disponibles para el estado seleccionado.
        """
        if proceso_tipo == 'REGISTRADOS':
            fechas = Candidato.objects.filter(
                estado_actual=estado_db, #
                kanban_activo=True, 
                telefono_whatsapp__isnull=False 
            ).dates('fecha_registro', 'day', order='DESC') 
            
        else:
          
            fechas = Proceso.objects.filter(
                estado=estado_db, 
                candidato__telefono_whatsapp__isnull=False 
            ).dates('fecha_inicio', 'day', order='DESC')
            
        return [f.strftime('%Y-%m-%d') for f in fechas]
    
    def _get_contactos_por_filtro(self, proceso_tipo, estado_db, fecha_str):
        """
        Obtiene la lista de contactos y anota la cantidad de mensajes exitosos 
        enviados a cada uno, sin aplicar filtros de exclusión.
        """
        try:
            fecha_obj = date.fromisoformat(fecha_str)
        except ValueError:
            return []
            
        if proceso_tipo == 'REGISTRADOS':
            qs = Candidato.objects.filter(
                estado_actual=estado_db,
                fecha_registro=fecha_obj,
                kanban_activo=True,
                telefono_whatsapp__isnull=False
            )
        else:
            qs = Candidato.objects.filter(
                procesos__estado=estado_db,
                procesos__fecha_inicio=fecha_obj,
                telefono_whatsapp__isnull=False
            ).distinct()
            
        estados_exitosos = ['ENVIADO', 'ENTREGADO', 'LEIDO']
        
        qs = qs.annotate(
            conteo_envios_exitosos=Count(
                'detalleenvio', 
                filter=Q(detalleenvio__estado_meta__in=estados_exitosos)
            )
        ).values('pk', 'DNI', 'nombres_completos', 'telefono_whatsapp', 'conteo_envios_exitosos')
        
        return list(qs)

class HistorialEnviosJsonView(ListView):
    """
    API: Retorna la lista general de tareas para el Modal.
    """
    model = TareaEnvioMasivo
    
    def get_queryset(self):
        return TareaEnvioMasivo.objects.annotate(
            tasa_exito_db=ExpressionWrapper(
                F('total_entregados') * 100.0 / F('total_contactos'),
                output_field=FloatField()
            )
        ).values(
            'id', 
            'total_entregados', 
            'total_contactos', 
            'fecha_origen', 
            'fecha_inicio',
            'estado',
            'tasa_exito_db',
            'proceso_tipo', 
            'mensaje_plantilla__titulo' 
        ).order_by('-fecha_inicio')

    def get(self, request, *args, **kwargs):
        object_list = self.get_queryset() 
        data = []
        
        for tarea in object_list:
            tasa_exito_valor = round(tarea['tasa_exito_db'], 1) if tarea['total_contactos'] else 0.0
            
            estado_obj = TareaEnvioMasivo(estado=tarea['estado'])
            proceso_obj = TareaEnvioMasivo(proceso_tipo=tarea['proceso_tipo'])
            
            data.append({
                'id': tarea['id'],
                'proceso': tarea['proceso_tipo'], 
                'proceso_display': f"{proceso_obj.get_proceso_tipo_display()}", 
                'fechaOrigen': tarea['fecha_origen'].strftime('%Y-%m-%d'),
                'enviados': tarea['total_entregados'],
                'total': tarea['total_contactos'],
                'tasa_exito': tasa_exito_valor,
                'fechaEnvio': timezone.localtime(tarea['fecha_inicio']).strftime('%d/%m/%Y %H:%M'),
                'estado': tarea['estado'], 
                'estado_display': estado_obj.get_estado_display()
            })
            
        return JsonResponse({'status': 'success', 'historialData': data})   

class DetalleTareaJsonView(LoginRequiredMixin, View):
    """
    API: Retorna la lista de personas (DetalleEnvio) de una Tarea específica.
    Se llama cuando das click en el botón de 'ojo' en la tabla.
    """
    def get(self, request, tarea_id):
        try:
            detalles = DetalleEnvio.objects.filter(tarea_envio_id=tarea_id).select_related('contacto').order_by('estado_meta')
            
            data_detalles = []
            for d in detalles:
                nombre = d.contacto.nombres_completos if d.contacto else "Contacto Eliminado"
                dni = d.contacto.DNI if d.contacto else "---"
                
                data_detalles.append({
                    'dni': dni,
                    'nombre': nombre,
                    'telefono': d.telefono,
                    'estado': d.get_estado_meta_display(),
                    'estado_codigo': d.estado_meta, 
                    'fecha_hora': timezone.localtime(d.fecha_envio).strftime('%H:%M:%S')
                })
            
            return JsonResponse({'status': 'success', 'detalles': data_detalles})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

ESTADOS_META_SIMULACION = ['ENTREGADO', 'LEIDO', 'ENVIADO']
def simular_tarea_celery(tarea_id, lista_candidatos_pks, mensaje_contenido_final):
    """
    Simulación de la función que Celery ejecutaría en segundo plano. 
    Guarda los DetalleEnvio para cada candidato y actualiza el conteo de la Tarea.
    """
    print(f"Tarea Celery ID {tarea_id} iniciada para {len(lista_candidatos_pks)} candidatos.")
    tarea = TareaEnvioMasivo.objects.get(pk=tarea_id)
    
    candidatos_qs = Candidato.objects.filter(pk__in=lista_candidatos_pks).distinct()
    
    total_entregados = 0
    total_fallidos = 0

    detalles_a_crear = []
    
    for candidato in candidatos_qs:
        estado_simulado = choice(ESTADOS_META_SIMULACION) 
        id_meta_simulado = f"wamid.{randint(100000000000, 999999999999)}" if estado_simulado != 'FALLIDO' else None
        
        if estado_simulado in ['ENTREGADO', 'LEIDO', 'ENVIADO']:
            total_entregados += 1
        else:
            total_fallidos += 1
            
        detalles_a_crear.append(DetalleEnvio(
            tarea_envio=tarea,
            contacto=candidato,
            telefono=candidato.telefono_whatsapp, 
            contenido_final=mensaje_contenido_final.replace('{nombres_completos}', candidato.nombres_completos), 
            estado_meta=estado_simulado,
            id_mensaje_meta=id_meta_simulado,
        ))

    DetalleEnvio.objects.bulk_create(detalles_a_crear)
    
    tarea.total_entregados = total_entregados
    tarea.total_fallidos = total_fallidos
    tarea.estado = 'COMPLETADO' 
    tarea.save()
    
    print(f"Tarea Celery ID {tarea_id} completada. Entregados: {total_entregados}, Fallidos: {total_fallidos}")

class IniciarEnvioMasivoView(View):
    def post(self, request, *args, **kwargs):
        mensaje_contenido = request.POST.get('mensaje_contenido')
        proceso_filtro = request.POST.get('proceso_filtro') 
        fecha_filtro_str = request.POST.get('fecha_filtro') 
        candidatos_seleccionados_pks = request.POST.getlist('candidatos_seleccionados[]')

        if not mensaje_contenido or not candidatos_seleccionados_pks or not proceso_filtro or not fecha_filtro_str:
            return JsonResponse({
                'success': False, 
                'message': 'Faltan parámetros esenciales (mensaje, contactos, proceso o fecha).'
            }, status=400) 
            
        try:
            plantilla, created = MensajePlantilla.objects.get_or_create(
                contenido_texto=mensaje_contenido, 
                defaults={
                    'titulo': f'MENSAJE AD HOC - {timezone.now().strftime("%Y%m%d%H%M%S")}-{request.user.pk}',
                    'creado_por': request.user, 
                }
            )
            fecha_origen = date.fromisoformat(fecha_filtro_str) 

            nueva_tarea = TareaEnvioMasivo.objects.create(
                usuario_que_envia=request.user,
                mensaje_plantilla=plantilla, 
                proceso_tipo=proceso_filtro,
                fecha_origen=fecha_origen,
                total_contactos=len(candidatos_seleccionados_pks),
                estado='PENDIENTE', 
            )
            
            task_id_simulado = f"celery-{nueva_tarea.id}-{timezone.now().timestamp()}"
            nueva_tarea.task_id = task_id_simulado
            nueva_tarea.estado = 'EN_PROCESO'
            nueva_tarea.save()
            
            simular_tarea_celery(
                nueva_tarea.id, 
                candidatos_seleccionados_pks, 
                mensaje_contenido 
            )
            
            return JsonResponse({
                'success': True, 
                'message': 'Envío masivo iniciado correctamente.',
                'tarea_id': nueva_tarea.id,
                'task_id': task_id_simulado
            }, status=202)

        except ValueError:
            return JsonResponse({'success': False, 'message': 'El formato de la fecha de filtro es inválido.'}, status=400)

        except Exception as e:
            print(f"Error al iniciar envío: {e}")
            return JsonResponse({'success': False, 'message': f'Error interno: {e}'}, status=500)

def actualizar_fila_y_contadores(request: HttpRequest, candidato_pk: int) -> HttpResponse:
    hoy = timezone.localdate()
    
    conteo_global = RegistroAsistencia.objects.filter(
        momento_registro__date=hoy
    ).exclude(estado=None).values('estado').annotate(count=Count('estado'))
    
    conteo_dict = {item['estado']: item['count'] for item in conteo_global}
    
    total_candidatos = Candidato.objects.exclude(procesos__estado__in=['CONTRATADO', 'NO_APTO', 'ABANDONO']).count() 

    latest_attendance = RegistroAsistencia.objects.filter(
        candidato=OuterRef('pk')
    ).order_by('-momento_registro').values(
        'momento_registro', 'fase_actual', 'movimiento', 'estado'
    )[:1]
    
    asistencia_hoy_subquery = RegistroAsistencia.objects.filter(
        candidato=OuterRef('pk'),
        momento_registro__date=hoy
    ).exclude(estado=None).order_by('-momento_registro').values('estado')[:1]

    proceso_filter_q = ~Q(procesos__estado__in=['CONTRATADO', 'NO_APTO', 'ABANDONO'])
    
    candidato = Candidato.objects.annotate(
        total_registros=Count('procesos__registroasistencia', filter=proceso_filter_q),
        total_tardanzas=Count('procesos__registroasistencia', filter=Q(procesos__registroasistencia__estado='T') & proceso_filter_q),
        total_faltas=Count('procesos__registroasistencia', filter=Q(procesos__registroasistencia__estado='F') & proceso_filter_q),
        total_asistencias_puntuales=Count('procesos__registroasistencia', filter=Q(procesos__registroasistencia__estado='A') & proceso_filter_q),
        
        ultima_fase=Subquery(latest_attendance.values('fase_actual'), output_field=models.CharField()),
        ultimo_movimiento=Subquery(latest_attendance.values('movimiento'), output_field=models.CharField()),
        ultimo_registro_momento=Subquery(latest_attendance.values('momento_registro'), output_field=models.DateTimeField()),
        asistencia_hoy=Subquery(asistencia_hoy_subquery, output_field=models.CharField())
    ).get(pk=candidato_pk)
    
    try:
        candidato.ultimo_registro = RegistroAsistencia.objects.filter(candidato=candidato).latest('momento_registro')
    except RegistroAsistencia.DoesNotExist:
        candidato.ultimo_registro = None
    
    contexto_fila = {
        'candidato': candidato, 
    }
    contexto_contador = {
        'total_candidatos': total_candidatos,
        'conteo_asistencias': conteo_dict
    }

    fila_html = render_to_string('candidatos/candidato_fila_parcial.html', contexto_fila, request=request)
    contador_html = render_to_string('candidatos/contador_global_parcial.html', contexto_contador, request=request)
    
    return JsonResponse({
        'success': True,
        'fila_html': fila_html,
        'contador_html': contador_html,
    })

@login_required
def registrar_asistencia_htmx(request, candidato_pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

    try:
        candidato = get_object_or_404(Candidato, pk=candidato_pk)
        data = json.loads(request.body)
        
        registrado_por_user = request.user if request.user.is_authenticated else None
        momento_registro = timezone.now() 
        zona_horaria_servidor = timezone.get_current_timezone()
        momento_registro_aware = timezone.localtime(momento_registro, timezone=zona_horaria_servidor)
        hoy_date = momento_registro_aware.date()
        
        proceso_activo = candidato.procesos.filter(
            ~Q(estado__in=['CONTRATADO', 'NO_APTO', 'ABANDONO'])
        ).order_by('-fecha_inicio').first()
        
        if not proceso_activo:
            return JsonResponse({'success': False, 'error': f'Candidato {candidato_pk} sin Proceso ACTIVO.'}, status=400)
        
        falta_existente_hoy = RegistroAsistencia.objects.filter(
            proceso=proceso_activo,
            momento_registro__date=hoy_date,
            estado='F' 
        ).exists()
        
        if falta_existente_hoy:
            return JsonResponse({
                'success': False, 
                'error': f'⚠️ El candidato {candidato.nombres_completos} ya fue marcado como **FALTA** hoy. Contacte a soporte para corregir el estado.'
            }, status=200)

        entrada_hoy = RegistroAsistencia.objects.filter(
            proceso=proceso_activo,
            momento_registro__date=hoy_date,
            movimiento='ENTRADA' 
        ).first() 
        
        salida_hoy_exists = RegistroAsistencia.objects.filter(
            proceso=proceso_activo,
            momento_registro__date=hoy_date,
            movimiento='SALIDA' 
        ).exists()
        
        msg_accion = ""
        
        
        if entrada_hoy and not salida_hoy_exists:
            movimiento = 'SALIDA'
            estado_final = entrada_hoy.estado 
            
            limite_salida_str = '14:00'
            limite_hora_salida, limite_minuto_salida = map(int, limite_salida_str.split(':'))
            hora_limite_salida_aware = make_aware(datetime.combine(hoy_date, time(limite_hora_salida, limite_minuto_salida)), get_current_timezone())
            
            if momento_registro_aware < hora_limite_salida_aware:
                msg_accion = "⚠️ Salida registrada antes de la hora límite (14:00). Se considera Salida Temprana."
            else:
                msg_accion = "✅ Salida registrada a tiempo (14:00 o después). Fin de Jornada."

        elif entrada_hoy and salida_hoy_exists:
            return JsonResponse({
                'success': False, 
                'error': f'⛔ El candidato {candidato.nombres_completos} ya tiene registrado su ciclo de ENTRADA/SALIDA completo para hoy.'
            }, status=200)

        else: 
            movimiento = 'ENTRADA'
            
            limite_entrada_str = getattr(settings, 'HORA_LIMITE_ASISTENCIA', '07:00')
            limite_hora_entrada, limite_minuto_entrada = map(int, limite_entrada_str.split(':'))
            
            hora_limite_aware = make_aware(datetime.combine(hoy_date, time(limite_hora_entrada, limite_minuto_entrada)), get_current_timezone())
            hora_limite_tardanza_aware = make_aware(datetime.combine(hoy_date, time(14, 0)), get_current_timezone())

            
            if momento_registro_aware > hora_limite_tardanza_aware:
                estado_final = 'F' 
                msg_accion = "❌ Registro de ENTRADA FALLIDO (> 14:00). Marcado como **FALTA**." 
            elif momento_registro_aware > hora_limite_aware:
                estado_final = 'T' 
                msg_accion = "⚠️ Asistencia registrada como TARDE."
            else:
                estado_final = 'A' 
                msg_accion = "✅ Asistencia registrada como PUNTUAL."
            
        
        FASE_MAP = {
            'CONVOCADO': 'CONVOCADO','CONFIRMADO': 'CONFIRMADO', 'TEORIA': 'TEORIA', 'PRACTICA': 'PRACTICA',
            'CONTRATADO': 'PRACTICA', 'NO_APTO': 'PRACTICA', 'ABANDONO': 'PRACTICA',
        }
        fase_asistencia = FASE_MAP.get(proceso_activo.estado, 'CONVOCADO')

        registro = RegistroAsistencia.objects.create(
            proceso=proceso_activo, 
            candidato=candidato,
            estado_asistencia=estado_final, 
            estado=estado_final, 
            
            movimiento=movimiento, 
            fase_actual=fase_asistencia, 
            registrado_por=registrado_por_user,
            momento_registro=momento_registro 
        )
            
        proceso_filter_q = ~Q(procesos__estado__in=['CONTRATADO', 'NO_APTO', 'ABANDONO'])
        candidato_actualizado = Candidato.objects.filter(pk=candidato_pk).annotate(
            total_registros=Count('procesos__registroasistencia', filter=proceso_filter_q),
            total_tardanzas=Count('procesos__registroasistencia', filter=Q(procesos__registroasistencia__estado='T') & proceso_filter_q),
            total_faltas=Count('procesos__registroasistencia', filter=Q(procesos__registroasistencia__estado='F') & proceso_filter_q),
            total_asistencias_puntuales=Count('procesos__registroasistencia', filter=Q(procesos__registroasistencia__estado='A') & proceso_filter_q),
        ).first()

        if candidato_actualizado:
            setattr(candidato_actualizado, 'pk', candidato_pk) 
            setattr(candidato_actualizado, 'asistencia_hoy', estado_final) 
            setattr(candidato_actualizado, 'ultimo_registro', registro)
            setattr(candidato_actualizado, 'ultimo_registro_momento', registro.momento_registro)
            setattr(candidato_actualizado, 'ultima_fase', fase_asistencia)
            setattr(candidato_actualizado, 'ultimo_movimiento', movimiento)
            
        conteo_asistencias_query = RegistroAsistencia.objects.filter(
            momento_registro__date=hoy_date,
        ).exclude(proceso__estado__in=['CONTRATADO', 'NO_APTO', 'ABANDONO']).values('estado').annotate(
            count=Count('estado')
        ).order_by('estado')

        conteo_dict = {item['estado']: item['count'] for item in conteo_asistencias_query}
        
        total_candidatos = Candidato.objects.exclude(procesos__estado__in=['CONTRATADO', 'NO_APTO', 'ABANDONO']).count() 

        fila_html = render_to_string(
            'candidatos/candidato_fila_parcial.html',
            {'candidato': candidato_actualizado},
            request=request
        )

        contador_html = render_to_string(
            'candidatos/contador_global_parcial.html',
            {'conteo_asistencias': conteo_dict, 'total_candidatos': total_candidatos},
            request=request
        )

        return JsonResponse({
            'success': True,
            'fila_html': fila_html,
            'contador_html': contador_html,
            'mensaje': msg_accion 
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Formato JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

class CandidatoPracticaSupervisorListView(ListView):
    model = Candidato
    template_name = 'candidatos/candidatos_practica_supervisor_list.html' 
    context_object_name = 'candidatos'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = super().get_queryset()

        proceso_filter_q = ~Q(procesos__estado__in=['CONTRATADO', 'NO_APTO', 'ABANDONO'])
        queryset = queryset.filter(
            proceso_filter_q, 
            procesos__estado='PRACTICA',
            procesos__supervisor__isnull=False 
        ).distinct() 

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(dni__icontains=search_query) | Q(nombre__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['active_filters'] = self.request.GET.copy()

        return context

def iniciar_envio_mensajes(request):
    if request.method == 'POST':
        candidatos_dnies = request.POST.getlist('candidatos_seleccionados[]')
        mensaje_contenido = request.POST.get('mensaje_contenido')
        
        resultados_envio = []

        for dni in candidatos_dnies:
            try:
                candidato = Candidato.objects.get(DNI=dni)
                telefono = candidato.telefono_whatsapp
                
                resultado_api = enviar_mensaje_whatsapp(telefono, mensaje_contenido)
                
                if resultado_api['success']:
                    DetalleEnvio.objects.create(
                        contacto=candidato,
                        mensaje=mensaje_contenido,
                        estado_meta='ACEPTADO', 
                        whatsapp_message_id=resultado_api['data']['messages'][0]['id']
                    )
                    resultados_envio.append({'dni': dni, 'status': 'Éxito', 'msg': 'Aceptado por Meta'})
                else:
                    DetalleEnvio.objects.create(
                        contacto=candidato,
                        mensaje=mensaje_contenido,
                        estado_meta='ERROR_API',
                    )
                    resultados_envio.append({'dni': dni, 'status': 'Error', 'msg': resultado_api['message']})

            except Candidato.DoesNotExist:
                resultados_envio.append({'dni': dni, 'status': 'Error', 'msg': 'Candidato no encontrado'})
            except Exception as e:
                resultados_envio.append({'dni': dni, 'status': 'Error', 'msg': f'Error interno: {e}'})

        return JsonResponse({
            'success': True,
            'message': f"Envío masivo iniciado. Se procesaron {len(candidatos_dnies)} contactos.",
            'details': resultados_envio
        }, status=200)

    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

WEBHOOK_VERIFY_TOKEN = 'TU_TOKEN_SECRETO_PARA_WEBHOOKS' 
class WhatsappWebhookView(View):

    def get(self, request, *args, **kwargs):

        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == WEBHOOK_VERIFY_TOKEN:
            return HttpResponse(challenge, status=200)
        else:
            return HttpResponse("Fallo en la verificación o token incorrecto.", status=403)

    def post(self, request, *args, **kwargs):
        return HttpResponse(status=200)
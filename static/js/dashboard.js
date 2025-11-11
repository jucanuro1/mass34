// ====================================================================
// CONFIGURACIÓN GLOBAL Y MAPEO DE ESTADOS
// ====================================================================

const updateUrl = AppConfig.updateUrl;
const massiveUpdateUrl = AppConfig.massiveUpdateUrl;
const API_ASISTENCIA_CHECK_URL = AppConfig.API_ASISTENCIA_CHECK_URL;
const csrfToken = AppConfig.csrfToken;
const historyApiUrl = AppConfig.historyApiUrl;
const urlGestionConvocatorias = AppConfig.gestionConvocatoriasUrl;
const urlListaCandidatosPorFecha = AppConfig.listaCandidatosPorFechaUrl;

const STATUS_MAP = {
    'column-REGISTRADO': 'REGISTRADO',
    'column-CONVOCADO': 'CONVOCADO',
    'column-CAPACITACION_TEORICA': 'CAPACITACION_TEORICA',
    'column-CAPACITACION_PRACTICA': 'CAPACITACION_PRACTICA',
    'column-CONTRATADO': 'CONTRATADO'
};
    
let selectedCards = []; 

// ====================================================================
// A. GESTIÓN DE SELECCIÓN DE TARJETAS (MODIFICADO)
// ====================================================================

function toggleCardSelection(cardElement) {
    const dni = cardElement.getAttribute('data-dni');
    const procesoId = cardElement.getAttribute('data-proceso-id');

    if (cardElement.classList.contains('dragging')) return;

    if (cardElement.classList.contains('selected')) {
        cardElement.classList.remove('selected', 'border-4', 'border-blue-500', 'ring-2', 'ring-blue-500'); 
        selectedCards = selectedCards.filter(card => card.dni !== dni);
    } else {
        cardElement.classList.add('selected', 'border-4', 'border-blue-500', 'ring-2', 'ring-blue-500');
        selectedCards.push({ dni: dni, proceso_id: procesoId });
    }
    
    updateMassActionButton(); 
    
    console.log(`Tarjetas seleccionadas: ${selectedCards.length}`, selectedCards);
}

// --------------------------------------------------------------------
// B. DRAG & DROP
// --------------------------------------------------------------------

function allowDrop(event) {
    event.preventDefault();
}

function drag(event) {
    const draggedDni = event.target.dataset.dni;
    
    if (selectedCards.length === 0) {
        event.dataTransfer.setData("text/mode", "individual");
        event.dataTransfer.setData("text/dni", draggedDni);
        event.dataTransfer.setData("text/current_status", event.target.closest('.kanban-column-body').dataset.status);
        return;
    }
    
    const isDraggedCardSelected = selectedCards.some(card => card.dni === draggedDni);
    
    if (isDraggedCardSelected) {
        event.dataTransfer.setData("text/mode", "multiple");
        event.dataTransfer.setData("text/dnis", JSON.stringify(selectedCards.map(c => c.dni)));
        
        const dragImage = document.createElement('div');
        dragImage.className = 'bg-blue-600 text-white p-2 rounded-lg shadow-xl font-bold';
        dragImage.textContent = `Moviendo ${selectedCards.length} candidatos`;
        document.body.appendChild(dragImage);
        event.dataTransfer.setDragImage(dragImage, 10, 10);
        setTimeout(() => document.body.removeChild(dragImage), 0);
        
    } else {
        clearSelection();
        event.dataTransfer.setData("text/mode", "individual");
        event.dataTransfer.setData("text/dni", draggedDni);
        event.dataTransfer.setData("text/current_status", event.target.closest('.kanban-column-body').dataset.status);
    }
}

function drop(event) {
    event.preventDefault();
    
    let dropTarget = event.target.closest('.kanban-column-body');
    if (!dropTarget) return;

    const targetColumnId = dropTarget.id;
    const newStatus = STATUS_MAP[targetColumnId];
    const mode = event.dataTransfer.getData("text/mode");
    
    if (mode === "multiple") {
        const dnisJson = event.dataTransfer.getData("text/dnis");
        const dnisArray = JSON.parse(dnisJson);
        
        if (dnisArray.length > 0) {
            const currentStatus = document.querySelector(`[data-dni="${dnisArray[0]}"]`).closest('.kanban-column-body').dataset.status;
            handleMultipleDrop(dnisArray, currentStatus, newStatus);
        }
        
    } else {
        const dni = event.dataTransfer.getData("text/dni");
        const currentStatus = event.dataTransfer.getData("text/current_status");
        
        if (currentStatus === newStatus) {
            return;
        }
        
        handleIndividualDrop(dni, currentStatus, newStatus);
    }
    
    clearSelection();
}

function handleIndividualDrop(dni, currentStatus, newStatus) {
    const card = document.querySelector(`[data-dni="${dni}"]`);
    if (!card) return;

    if (currentStatus === 'REGISTRADO' && newStatus === 'CONVOCADO') {
        const nombreCompleto = card.querySelector('h4').textContent.trim();
        const nombre = nombreCompleto.split('(')[0].trim();
        openInitProcessModal(dni, nombre); 
        return;
    }

    if (currentStatus === 'CAPACITACION_TEORICA' && newStatus === 'CAPACITACION_PRACTICA') {
        const nombreCompleto = card.querySelector('h4').textContent.trim();
        const nombre = nombreCompleto.split('(')[0].trim();
        const procesoId = card.dataset.procesoId;
        if (!procesoId || procesoId === 'None' || isNaN(parseInt(procesoId))) {
            alert('Error: El candidato no tiene un proceso activo válido. Revise la columna de CONVOCADO.');
            return;
        }
        openAssignSupervisorIndividualModal(procesoId, nombre);
        return;
    }
    
    confirmIndividualUpdate(dni, newStatus);
}

function handleMultipleDrop(dnisArray, currentStatus, newStatus) {
    const count = dnisArray.length;
    if (count === 0) return;
    
    if (currentStatus === newStatus) {
        alert('Las tarjetas seleccionadas ya se encuentran en ese estado.');
        return;
    }

    if (currentStatus === 'REGISTRADO' && newStatus === 'CONVOCADO') {
        openMassConvocatoriaModal(dnisArray);
        return;
    }

    if (currentStatus === 'CAPACITACION_TEORICA' && newStatus === 'CAPACITACION_PRACTICA') {
        openMassAssignSupervisorModal(dnisArray);
        return;
    }
    
    let confirmMessage = `¿Mover a **${count}** candidatos de **${currentStatus}** a **${newStatus}**?`;
    
    if (confirm(confirmMessage)) {
        confirmMassUpdate(dnisArray, newStatus, {});
    }
}

function triggerMassAction(targetStatus) {
    if (selectedCards.length === 0) {
        alert('Debes seleccionar al menos un candidato para la acción masiva.');
        return;
    }
    
    const dnisArray = selectedCards.map(c => c.dni); 
    
    const firstCardDni = dnisArray[0];
    const firstCardElement = document.querySelector(`[data-dni="${firstCardDni}"]`);
    
    if (!firstCardElement) {
        alert('Error: No se encontró la tarjeta del primer candidato seleccionado.');
        return;
    }
    
    const currentStatus = firstCardElement.closest('.kanban-column-body').dataset.status;
    
    const allInSameStatus = dnisArray.every(dni => {
        const cardElement = document.querySelector(`[data-dni="${dni}"]`);
        return cardElement && cardElement.closest('.kanban-column-body').dataset.status === currentStatus;
    });

    if (!allInSameStatus) {
        alert('Para la acción masiva, todos los candidatos deben estar en la misma columna de origen.');
        return;
    }

    const targetColumnId = `column-${targetStatus}`;
    const newStatus = STATUS_MAP[targetColumnId];

    handleMultipleDrop(dnisArray, currentStatus, newStatus);
    
    clearSelection();
}

// --------------------------------------------------------------------
// C. GESTIÓN CENTRALIZADA DE LA SELECCIÓN Y BOTÓN
// --------------------------------------------------------------------

function getSelectedDnis() {
    return selectedCards.map(card => card.dni); 
}

function clearSelection() {
    selectedCards = [];
    document.querySelectorAll('.kanban-card.selected').forEach(card => card.classList.remove('selected', 'border-4', 'border-blue-500', 'ring-2', 'ring-blue-500'));
    
    updateMassActionButton();
}

// --------------------------------------------------------------------
// D. LÓGICA DEL BOTÓN FLOTANTE Y MENÚ DE ACCIÓN MASIVA
// --------------------------------------------------------------------

function closeMassActionMenu() {
    document.getElementById('mass-action-menu').classList.add('hidden');
    const secondaryMenu = document.getElementById('massActionMenu');
    if (secondaryMenu) {
        secondaryMenu.classList.add('hidden');
    }
    
    document.removeEventListener('click', closeMenuOutside); 
    document.getElementById('descarte-motivo-select').value = "";
}

function closeMenuOutside(event) {
    const descarteMenu = document.getElementById('mass-action-menu');
    const button = document.getElementById('btn-mass-action');
    
    if (descarteMenu && button && !descarteMenu.contains(event.target) && !button.contains(event.target)) {
        closeMassActionMenu();
    }
}

function openMassActionMenu(event) {
    const dnisArray = getSelectedDnis(); 
    const selectedCount = dnisArray.length;
    const menu = document.getElementById('mass-action-menu');

    if (selectedCount === 0) {
        alert("Selecciona al menos un candidato para realizar una acción masiva.");
        return;
    }
    
    document.getElementById('menu-selected-count').innerText = selectedCount;
    
    menu.classList.remove('hidden');

    if (event) {
        event.stopPropagation();
    }
    
    document.addEventListener('click', closeMenuOutside);
}

function updateMassActionButton() {
    const dnisArray = getSelectedDnis(); 
    const selectedCount = dnisArray.length;
    
    const button = document.getElementById('btn-mass-action');
    const countSpan = document.getElementById('selected-count');

    if (!button || !countSpan) return;

    if (selectedCount > 0) {
        button.classList.remove('hidden'); // Usa classList para Tailwind
        button.style.display = 'flex'; // Mantener el display:flex para el layout si se usa style
        countSpan.innerText = selectedCount; 
        button.onclick = openMassActionMenu; // Asigna el evento de clic
        
    } else {
        button.classList.add('hidden');
        button.style.display = 'none'; 
        button.onclick = null; 
        
        // Cierra el menú si se deselecciona el último elemento
        const menu = document.getElementById('mass-action-menu');
        if (menu && !menu.classList.contains('hidden')) {
            closeMassActionMenu();
        }
    }
}

function confirmMassDescarte() {
    const dnisArray = getSelectedDnis(); 
    const motivoSelect = document.getElementById('descarte-motivo-select');
    const motivoKey = motivoSelect.value;
    
    if (dnisArray.length === 0) {
        alert("Error: No hay candidatos seleccionados.");
        return;
    }
    
    const newStatus = 'DESISTE'; 
    const extraData = {
        'motivo_descarte': motivoKey 
    };

    confirmMassUpdate(dnisArray, newStatus, extraData)
        .then(() => {
            closeMassActionMenu();
        })
        .catch(error => {
            console.error("Fallo al procesar descarte masivo:", error);
            alert("Ocurrió un error al intentar descartar a los candidatos.");
        });
}

// --------------------------------------------------------------------
// E. COMUNICACIÓN CON EL BACKEND (Fetch API)
// --------------------------------------------------------------------

function confirmIndividualUpdate(dni, newStatus) {
    fetch(updateUrl, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `dni=${dni}&new_status=${newStatus}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert(data.message); 
            window.location.reload(); 
        } else {
            alert('Error en D&D individual: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error de red en D&D individual:', error);
        alert('Error de red al actualizar el estado individual.');
    });
}
    
function confirmMassUpdate(dnisArray, newStatus, extraData) {
    const formData = new FormData();
    
    // 1. Validación de entrada
    if (dnisArray.length === 0) {
        alert("Error en actualización masiva: DNI list is required.");
        return Promise.reject(new Error("No DNI list"));
    }
    
    // 2. Construcción de FormData
    dnisArray.forEach(dni => {
        formData.append('dnis[]', dni); 
    });
    
    formData.append('new_status', newStatus);
    
    for (const key in extraData) {
        formData.append(key, extraData[key]);
    }

    // 3. Inicio de la petición con manejo robusto de red y respuesta
    return fetch(massiveUpdateUrl, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest', 
            // Nota: Con FormData, el 'Content-Type' se maneja automáticamente
        },
        body: formData
    })
    .then(async response => { // Usamos 'async' para el manejo de texto/JSON
        if (!response.ok) {
            // Si el status es 4xx o 5xx, intentamos leer el cuerpo para depuración
            const errorBody = await response.text();
            console.error(`Error HTTP ${response.status} en la petición. Cuerpo del error:`, errorBody);
            
            // Intentamos parsear el JSON de error (si existe) para un mensaje más limpio
            try {
                const errorData = JSON.parse(errorBody);
                throw new Error(errorData.message || `Petición fallida. Código: ${response.status}.`);
            } catch (e) {
                // Si falla JSON.parse (ej. HTML o texto plano), usamos un mensaje genérico
                throw new Error(`Petición fallida. Código: ${response.status}. Revise la consola.`);
            }
        }
        
        // 4. Solución al SyntaxError: Si la respuesta es OK (200), leemos el JSON
        // (Esto es donde puede fallar si Django no devuelve JSON, aunque response.ok lo mitiga)
        try {
            return response.json();
        } catch (e) {
            console.error('Error FATAL: La respuesta del servidor no es JSON válida.', e);
            throw new Error('Respuesta del servidor corrupta.');
        }
    })
    .then(data => {
        if (data.status === 'success') {
            window.location.reload(); 
            return data;
        } else {
            // Si el backend devuelve status: 'error' (como con el FOREIGN KEY), se atrapa aquí.
            alert(`❌ Error en actualización masiva: ${data.message}`);
            throw new Error(data.message);
        }
    })
    .catch(error => {
        // 5. Captura de Errores FATALES (incluido NetworkError)
        const errorMessage = error.message || String(error);
        
        if (errorMessage.includes("NetworkError") || errorMessage.includes("Failed to fetch")) {
             console.error('Error FATAL en la actualización masiva: Fallo de red/conexión.', error);
             alert(`🔴 Fallo de conexión. Verifique la URL (${massiveUpdateUrl}) o si el servidor está activo.`);
        } else {
             console.error('Error FATAL en la actualización masiva:', error);
             alert(`🔴 Fallo en la acción masiva. Mensaje: ${errorMessage}`);
        }
        throw error;
    });
}

// --------------------------------------------------------------------
// F. GESTIÓN DE MODALES (Funciones auxiliares)
// --------------------------------------------------------------------

function openMassConvocatoriaModal(dnisArray) {
    const count = dnisArray.length;
    document.getElementById('mass-convocatoria-count').textContent = count;
    document.getElementById('mass-convocatoria-dnis').value = JSON.stringify(dnisArray); 
    document.getElementById('massConvocatoriaModal').style.display = 'flex';
}

function closeMassConvocatoriaModal() {
    document.getElementById('massConvocatoriaModal').style.display = 'none';
    clearSelection();
}

document.getElementById('massConvocatoriaForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const dnis = JSON.parse(document.getElementById('mass-convocatoria-dnis').value);
    const newStatus = e.target.elements.new_status.value;
    const fechaInicio = e.target.elements.fecha_inicio.value;
    
    confirmMassUpdate(dnis, newStatus, { fecha_inicio: fechaInicio });
    closeMassConvocatoriaModal();
});

function openMassAssignSupervisorModal(dnisArray) {
    const count = dnisArray.length;
    document.getElementById('mass-supervisor-count').textContent = count;
    document.getElementById('mass-supervisor-dnis').value = JSON.stringify(dnisArray); 
    document.getElementById('massAssignSupervisorModal').style.display = 'flex';
}

function closeMassAssignSupervisorModal() {
    document.getElementById('massAssignSupervisorModal').style.display = 'none';
    clearSelection();
}

document.getElementById('massAssignSupervisorForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const dnis = JSON.parse(document.getElementById('mass-supervisor-dnis').value);
    const newStatus = e.target.elements.new_status.value;
    const supervisorId = e.target.elements.supervisor_id.value;
    
    confirmMassUpdate(dnis, newStatus, { supervisor_id: supervisorId });
    closeMassAssignSupervisorModal();
});

function openInitProcessModal(dni, nombre) {
    document.getElementById('init-candidato-dni').textContent = dni;
    document.getElementById('init-candidato-nombre').textContent = nombre;
    
    const form = document.getElementById('initProcessForm');
    const baseAction = form.dataset.baseAction || form.action.replace(dni, 'DNI_PLACEHOLDER');
    form.action = baseAction.replace('DNI_PLACEHOLDER', dni);
    
    document.getElementById('initProcessModal').style.display = 'flex';
}

function closeInitProcessModal() {
    document.getElementById('initProcessModal').style.display = 'none';
}

function openAssignSupervisorIndividualModal(procesoId, nombre) {
    document.getElementById('assign-proceso-id').value = procesoId;
    document.getElementById('assign-candidato-nombre').textContent = nombre;
    
    const form = document.getElementById('assignSupervisorIndividualForm');
    const baseAction = form.dataset.baseAction || form.action.replace(new RegExp(`/${procesoId}/$`), '/0/');
    form.action = baseAction.replace('/0/', `/${procesoId}/`); 
    
    document.getElementById('assignSupervisorIndividualModal').style.display = 'flex';
}

function closeAssignSupervisorIndividualModal() {
    document.getElementById('assignSupervisorIndividualModal').style.display = 'none';
}

function openUpdateProcessModal(procesoId, nombre, estado, empresa, supervisor, objetivo, actitud) {
    const ids = ['update-proceso-id', 'update-candidato-nombre', 'update-empresa-nombre', 'update-supervisor-nombre'];
    const values = [procesoId, nombre, empresa, supervisor];

    for (let i = 0; i < ids.length; i++) {
        const element = document.getElementById(ids[i]);
        if (element) {
            if (ids[i].includes('proceso-id')) {
                element.value = values[i];
            } else {
                element.textContent = values[i];
            }
        } else {
            console.warn(`Elemento HTML con ID ${ids[i]} no encontrado en el DOM.`);
        }
    }

    const form = document.getElementById('updateProcessForm');    
    document.getElementById('id_estado_proceso_update').value = estado;
    const updateSelect = document.getElementById('id_estado_proceso_update');
    const performanceFields = document.getElementById('performance-fields');
    
    if (updateSelect && performanceFields) {
        function togglePerformanceFields() {
            const selectedState = updateSelect.value;
            if (selectedState === 'CONTRATADO' || selectedState === 'NO_APTO') {
                performanceFields.style.display = 'block';
                if (document.getElementById('id_objetivo_ventas_alcanzado')) {
                    document.getElementById('id_objetivo_ventas_alcanzado').checked = objetivo === 'true';
                }
                if (document.getElementById('id_factor_actitud_aplica')) {
                    document.getElementById('id_factor_actitud_aplica').checked = actitud === 'true';
                }
            } else {
                performanceFields.style.display = 'none';
            }
        }

        updateSelect.onchange = togglePerformanceFields;
        togglePerformanceFields();
    }
    
    if (document.getElementById('updateProcessModal')) {
        document.getElementById('updateProcessModal').style.display = 'flex';
    }
}

function closeUpdateProcessModal() {
    document.getElementById('updateProcessModal').style.display = 'none';
}

function openHistoryModal(dni, nombre) {
    if (typeof closeHistoryModal !== 'function') {
        window.closeHistoryModal = function() {
            document.getElementById('historyModal').style.display = 'none';
        };
    }

    document.getElementById('history-candidato-dni').textContent = dni;
    document.getElementById('history-candidato-nombre').textContent = nombre;
    const historyContent = document.getElementById('history-content');
    historyContent.innerHTML = '<p class="text-center text-gray-500 py-4">Cargando historial...</p>';

    if (typeof historyApiUrl === 'undefined' || historyApiUrl.includes('{url')) {
        historyContent.innerHTML = '<p class="text-center text-red-700 font-bold py-4">Error JS: historyApiUrl no está definido correctamente. Revise la plantilla HTML.</p>';
        document.getElementById('historyModal').style.display = 'flex';
        return;
    }
    
    const url = historyApiUrl.replace('DNI_PLACEHOLDER', dni);

    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Respuesta de red no exitosa. Código: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            
            const raw_estado_maestro = data.candidato_info.estado_maestro.toUpperCase();
            
            let display_estado = raw_estado_maestro;
            let estado_color_class = 'text-indigo-700';
            let bg_color_class = 'bg-indigo-50 border-indigo-200';
            
            if (raw_estado_maestro.includes('INICIADO')) {
                display_estado = 'CONVOCADO / ' + raw_estado_maestro; 
                estado_color_class = 'text-green-700';
                bg_color_class = 'bg-green-50 border-green-200';
            } else if (raw_estado_maestro.includes('RECHAZADO') || raw_estado_maestro.includes('DESCALIFICADO')) {
                estado_color_class = 'text-red-700';
                bg_color_class = 'bg-red-50 border-red-200';
            }
            let html = `
                <div class="mb-6 p-4 rounded-xl ${bg_color_class} border-2 shadow-inner flex items-center justify-between">
                    <p class="text-sm font-semibold ${estado_color_class} flex items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 ${estado_color_class.replace('text', 'text').replace('-700', '-600')}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.24a2 2 0 010 2.83l-1.348 1.347a1 1 0 01-1.414 0l-.001-.001 3.535 3.536-1.347 1.347a2 2 0 01-2.828 0l-1.347-1.347-3.535 3.536a1 1 0 01-1.414 0l-.001-.001-1.347 1.347a2 2 0 01-2.828 0L2 19.5" />
                        </svg>
                        ESTADO MAESTRO
                    </p>
                    <p class="text-xl font-extrabold ${estado_color_class} tracking-wider">${display_estado}</p>
                </div>
                <h4 class="text-base font-extrabold text-gray-900 border-b-2 border-red-200 pb-2 mb-4 flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    CRÓNICA DE PROCESOS (${data.procesos.length})
                </h4>
            `;

            if (data.procesos && data.procesos.length > 0) {
                data.procesos.forEach((p, index) => {
                    const is_active = p.es_activo;
                    const border_class = is_active ? 'border-red-600 ring-2 ring-red-100 bg-white' : 'border-gray-300 bg-gray-50';
                    const active_label = is_active ? '✅ PROCESO ACTUAL (ACTIVO)' : 'Proceso Histórico';
                    const main_text_color = is_active ? 'text-red-700' : 'text-gray-700';
                    const result_color = p.resultado_final === 'APROBADO' ? 'text-green-600' : 'text-red-600';
                    const icon = is_active ? '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>' : '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>';


                    let active_details = '';
                    if (is_active) {
                        active_details = `
                            <div class="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-red-200">
                                <div class="flex items-center"><span class="font-bold text-gray-700 text-xs">Último Reg. Hora:</span> <span class="text-sm font-semibold ml-2">${p.ultima_momento || 'N/A'}</span></div>
                                <div class="flex items-center"><span class="font-bold text-gray-700 text-xs">Documentos:</span> <span class="text-sm font-semibold ml-2 text-red-600">${p.documentacion || '0 subidos'}</span></div>
                                <div class="flex items-center"><span class="font-bold text-gray-700 text-xs">Comentarios:</span> <span class="text-sm font-semibold ml-2">${p.num_comentarios || 0}</span></div>
                                <div class="flex items-center"><span class="font-bold text-gray-700 text-xs">Tests:</span> <span class="text-sm font-semibold ml-2">${p.num_tests || 0}</span></div>
                            </div>
                        `;
                    }

                    html += `
                        <div class="border-l-4 p-4 rounded-lg shadow-lg mb-6 transition duration-200 hover:shadow-xl ${border_class}">
                            <div class="flex justify-between items-start border-b pb-2 mb-2 ${is_active ? 'border-red-300' : 'border-gray-200'}">
                                <p class="text-sm font-extrabold flex items-center ${main_text_color}">
                                    ${icon} ${active_label}
                                </p>
                                <span class="text-xs font-bold px-3 py-1 rounded-full tracking-wider shadow-sm 
                                    ${is_active ? 'bg-red-200 text-red-800 border border-red-300' : 'bg-gray-200 text-gray-600 border border-gray-300'}">
                                    ${p.estado_proceso.toUpperCase()}
                                </span>
                            </div>
                            
                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-xs text-gray-600">
                                <div><span class="font-semibold text-gray-700">Empresa/Sede:</span> ${p.empresa_proceso} / ${p.sede_proceso}</div>
                                <div><span class="font-semibold text-gray-700">Fecha Convocatoria:</span> ${p.fecha_inicio}</div>
                                <div><span class="font-semibold text-gray-700">Supervisor:</span> ${p.supervisor_nombre}</div>
                                <div><span class="font-semibold text-gray-700">Resultado Final:</span> <span class="font-extrabold ${result_color}">${p.resultado_final.toUpperCase()}</span></div>
                            </div>
                            ${active_details}
                        </div>
                    `;
                });
            } else {
                html += '<p class="text-center text-gray-500 font-semibold py-8 bg-gray-50 rounded-xl border border-gray-200">No se encontró historial de procesos para este candidato.</p>';
            }
            historyContent.innerHTML = html;
        })
        .catch(error => {
            historyContent.innerHTML = `<p class="text-center text-red-600 font-extrabold p-6 bg-red-50 border border-red-300 rounded-xl">
                <span class="text-xl">⚠️</span> ¡Error Fatal! <span class="block text-sm font-normal mt-1">No pudimos cargar el historial: ${error.message}</span>
            </p>`;
            console.error('Error al cargar historial:', error);
        });

    document.getElementById('historyModal').style.display = 'flex';
}

function closeHistoryModal() {
    document.getElementById('historyModal').style.display = 'none';
}

function openConvocarModal(dni, nombre) {
    openInitProcessModal(dni, nombre);
}

function copyLink(buttonElement, linkToCopy) {
    
    if (navigator.clipboard) {
        navigator.clipboard.writeText(linkToCopy).then(() => {
            showCopyFeedback(buttonElement);
        }).catch(err => {
            console.error('Error al copiar (API Clipboard):', err);
        });
    } else {
        const tempInput = document.createElement('textarea');
        tempInput.value = linkToCopy;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);
        
        showCopyFeedback(buttonElement);
    }
}

function showCopyFeedback(buttonElement) {
    const messageSpan = buttonElement.querySelector('#copy-message');
    
    messageSpan.classList.remove('opacity-0');
    messageSpan.classList.add('opacity-100');

    setTimeout(() => {
        messageSpan.classList.remove('opacity-100');
        messageSpan.classList.add('opacity-0');
    }, 2000);
}


function openCandModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
    }
}

/**
 * Cierra el modal de gestión de Candidatos.
 */
function closeCandModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.kanban-column-body').forEach(column => {
        column.addEventListener('dragover', allowDrop);
        column.addEventListener('drop', drop);
        column.id = `column-${column.dataset.status}`;
    });
    
    document.querySelectorAll('.kanban-card').forEach(card => {
        card.addEventListener('dragstart', drag);
        
    });
    
    const messageContainer = document.getElementById('message-container');
    if (messageContainer) {
        setTimeout(() => {
            messageContainer.style.display = 'none';
        }, 2000); 
    }

    const messageAlerts = document.querySelectorAll('.message-alert');
    messageAlerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0'; 
            setTimeout(() => {
                alert.style.display = 'none';
            }, 500); 
        }, 5000); 
    });

    // 4. Filtros de fecha
    const dateButtons = document.querySelectorAll('.filter-date-btn');
    dateButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            const selectedDate = event.currentTarget.dataset.date;
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('fecha_inicio', selectedDate);
            window.location.href = currentUrl.toString();
        });
    });

    const allDatesButton = document.getElementById('all-dates-filter-btn');
    if (allDatesButton) {
        allDatesButton.addEventListener('click', (event) => {
            event.preventDefault(); 
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.delete('fecha_inicio');
            window.location.href = currentUrl.toString();
        });
    }
    
    // 5. Búsqueda por DNI 
    const dniSearchInput = document.getElementById('dni-search');

    function handleQuickSearch(e) {
        // Solo actuamos si se presiona la tecla Enter
        if (e.key !== 'Enter') {
            return;
        }

        e.preventDefault(); 
        
        const searchValue = dniSearchInput.value.trim();
        const currentUrl = new URL(window.location.href);
        
        // 1. Validaciones
        // Determina si es un ID (8-10 dígitos) o Teléfono (9-12 dígitos) para la búsqueda rápida.
        const isExactID = /^\d{8,10}$/.test(searchValue); 
        const isExactPhone = /^\d{9,12}$/.test(searchValue);
        
        // Si la búsqueda no coincide con un formato estricto (ID o Teléfono), vamos a la búsqueda general.
        if (!isExactID && !isExactPhone) {
            if (searchValue) {
                currentUrl.searchParams.set('search', searchValue);
            } else {
                currentUrl.searchParams.delete('search');
            }
            window.location.href = currentUrl.toString();
            return; // Salimos de la función
        }

        // 2. Ejecutar la Búsqueda Rápida (fetch)
        const apiUrl = `${API_ASISTENCIA_CHECK_URL}?q=${searchValue}`;
        
        fetch(apiUrl)
            .then(response => response.json())
            .then(data => {
                
                if (data.candidato_encontrado && !data.asistencia_registrada && data.proceso_id) {
                    
                    // Abrir el modal si el candidato está, la asistencia NO y hay proceso.
                    openAsistenciaModal(data.dni || searchValue, data.proceso_id);
                    
                    // Actualizar la URL sin recargar la página
                    const updatedUrl = new URL(window.location.href);
                    updatedUrl.searchParams.set('search', searchValue);
                    window.history.pushState({}, '', updatedUrl);

                } else {
                    // Si no hay match de asistencia o proceso, redirigir a la búsqueda general
                    // para ver los detalles del candidato en el dashboard.
                    currentUrl.searchParams.set('search', searchValue);
                    window.location.href = currentUrl.toString();
                }
            })
            .catch(error => {
                console.error('Error de red o API:', error);
                // En caso de error, redirigir a la búsqueda general como fallback
                currentUrl.searchParams.set('search', searchValue);
                window.location.href = currentUrl.toString();
            });
    }

    // Asignar el event listener a la nueva función
    dniSearchInput.addEventListener('keypress', handleQuickSearch);
/*
    const toggleHeader = document.getElementById('toggle-header');
    const collapsibleContent = document.getElementById('collapsible-content');
    const toggleIcon = document.getElementById('toggle-icon');
    
    if (toggleHeader && collapsibleContent && toggleIcon) {
        toggleHeader.addEventListener('click', function() {
            collapsibleContent.classList.toggle('hidden'); 
            toggleIcon.classList.toggle('rotate-180');
        });
    }*/


    // 7. Funcionalidad del Dropdown de Desactivación
    const menuButton = document.getElementById('');
    const dropdownMenu = document.getElementById('dropdown-menu');

    if (menuButton && dropdownMenu) {
        
        function toggleDropdown() {
            const isHidden = dropdownMenu.classList.contains('hidden');
            if (isHidden) {
                dropdownMenu.classList.remove('hidden');
                menuButton.setAttribute('aria-expanded', 'true');
            } else {
                dropdownMenu.classList.add('hidden');
                menuButton.setAttribute('aria-expanded', 'false');
            }
        }

        menuButton.addEventListener('click', function(event) {
            event.stopPropagation(); 
            toggleDropdown();
        });

        document.addEventListener('click', function (event) {
            if (!menuButton.contains(event.target) && !dropdownMenu.contains(event.target)) {
                if (!dropdownMenu.classList.contains('hidden')) {
                    dropdownMenu.classList.add('hidden');
                    menuButton.setAttribute('aria-expanded', 'false');
                }
            }
        });
        
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && !dropdownMenu.classList.contains('hidden')) {
                dropdownMenu.classList.add('hidden');
                menuButton.setAttribute('aria-expanded', 'false');
            }
        });
        
    }

    const btnGestionConvocatorias = document.getElementById('btn-gestionar-convocatorias');
    const modalConvocatorias = document.getElementById('convocatorias-modal');
    const modalContentAreaConvocatorias = document.getElementById('modal-content-area-convocatorias');

    let currentMonthFilter = null;


    async function loadConvocatoriasModalContent(monthFilter = null, isInitialLoad = true) {
        currentMonthFilter = monthFilter;

        if (isInitialLoad) { 
            modalContentAreaConvocatorias.innerHTML = '<div class="p-5 text-center"><p class="text-gray-500">Cargando convocatorias...</p></div>';
        }

        let url = urlGestionConvocatorias;
        if (monthFilter) {
            url += `?mes=${monthFilter}`;
        }

        try {
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`Error al cargar la gestión. Estado: ${response.status}`);
            }
            
            const htmlFragment = await response.text();
            
            modalContentAreaConvocatorias.innerHTML = htmlFragment;
            
            if (isInitialLoad) {
                setTimeout(() => {
                    modalContentAreaConvocatorias.classList.remove('scale-95', 'opacity-0');
                    modalContentAreaConvocatorias.classList.add('scale-100', 'opacity-100');
                }, 10);
            }
            
            initModalConvocatoriasListeners(); 
            
        } catch (error) {
            console.error("Error al cargar el modal de convocatorias:", error);
            modalContentAreaConvocatorias.innerHTML = `<div class="p-5 text-center text-red-600">Error al cargar la lista: ${error.message}</div>`;
        }
    }

    async function sendFormViaAjax(form) {
        const actionUrl = form.action;
        const formData = new FormData(form);
        
        const originalContent = modalContentAreaConvocatorias.innerHTML;
        modalContentAreaConvocatorias.innerHTML = `<div class="p-5 text-center text-xl text-red-600 font-bold">Aplicando acción... Por favor espere.</div>`;
        
        try {
            const response = await fetch(actionUrl, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Error en la acción. Estado: ${response.status}`);
            }

            await loadConvocatoriasModalContent(currentMonthFilter, false); 
            
        } catch (error) {
            console.error("Error al ejecutar la acción del formulario:", error);
            modalContentAreaConvocatorias.innerHTML = originalContent; 
            alert(`Ocurrió un error al aplicar la acción: ${error.message}`);
            initModalConvocatoriasListeners(); // Re-inicializa listeners si falló.
        }
    }


    function initModalConvocatoriasListeners() {
        const closeButton = modalContentAreaConvocatorias.querySelector('[data-modal-close]');
        if (closeButton) {
            closeButton.addEventListener('click', closeConvocatoriasModal);
        }
        
        const monthSelect = modalContentAreaConvocatorias.querySelector('#month-select');
        if (monthSelect) {
            currentMonthFilter = monthSelect.value;
            
            monthSelect.addEventListener('change', function() {
                loadConvocatoriasModalContent(this.value, false); 
            });
        }

        initConvocatoriasToggleListeners();
        initConvocatoriasMesListeners();
    }


    function initConvocatoriasToggleListeners() {
        const toggles = modalContentAreaConvocatorias.querySelectorAll('.toggle-checkbox');

        toggles.forEach(toggle => {
            toggle.addEventListener('change', function() {
                const dateSlug = this.getAttribute('data-fecha-str'); 
                const isChecked = this.checked;
                
                const formId = isChecked ? `form-activate-${dateSlug}` : `form-deactivate-${dateSlug}`;
                const targetForm = document.getElementById(formId);

                if (targetForm) {
                    sendFormViaAjax(targetForm);
                } else {
                    console.error("Formulario de acción no encontrado para:", formId);
                }
            });
        });
    }

    function initConvocatoriasMesListeners() {
        const mesForms = modalContentAreaConvocatorias.querySelectorAll('.form-action-mes');
        
        mesForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                e.preventDefault(); 
                
                const confirmMsg = this.getAttribute('data-confirm-msg');
                
                if (confirm(confirmMsg)) { 
                    
                    sendFormViaAjax(this);
                }
            });
        });
    }


    function closeConvocatoriasModal() {
        modalConvocatorias.classList.add('hidden');
        modalContentAreaConvocatorias.classList.remove('scale-100', 'opacity-100');
        modalContentAreaConvocatorias.classList.add('scale-95', 'opacity-0');

        setTimeout(() => {
            window.location.reload();
        }, 150); 
    }

    btnGestionConvocatorias.addEventListener('click', () => {
        modalConvocatorias.classList.remove('hidden');
        loadConvocatoriasModalContent(null, true); 
    });

    modalConvocatorias.addEventListener('click', (e) => {
        if (e.target === modalConvocatorias) {
            closeConvocatoriasModal();
        }
    });
    
    const btnGestionarCandidatos = document.getElementById('btn-gestionar-candidatos');
    const candModalContainer = document.getElementById('candidatos-modal'); 
    const candModalContent = document.getElementById('candidatos-modal-content'); 

    function loadCandidatesModalContent(url) {
        candModalContent.innerHTML = '<div class="text-center py-10"><svg class="animate-spin h-5 w-5 text-red-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg><p class="mt-2 text-sm text-gray-500">Cargando fechas de registro...</p></div>';

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok, Status: ' + response.status); 
                }
                return response.text();
            })
            .then(html => {
                candModalContent.innerHTML = html;
            })
            .catch(error => {
                console.error('Error fetching candidatos list:', error);
                candModalContent.innerHTML = '<div class="text-center p-4 text-red-600">Error al cargar las fechas. Intenta de nuevo.</div>';
            });
    }

    if (btnGestionarCandidatos) {
        btnGestionarCandidatos.addEventListener('click', function(e) {
            e.preventDefault();
            const modalId = this.getAttribute('data-modal-target');
            
            openCandModal(modalId);
            
            loadCandidatesModalContent(urlListaCandidatosPorFecha);
        });
    }
    
    if (candModalContainer) {
        
        // Delegación de Eventos para el Filtro de Mes
        candModalContainer.addEventListener('change', function(e) {
            if (e.target.id === 'month-select') {
                const selectedMonth = e.target.value;
                const newUrl = urlListaCandidatosPorFecha + (selectedMonth ? '?mes=' + selectedMonth : '');
                loadCandidatesModalContent(newUrl);
            }
        });

        candModalContainer.addEventListener('submit', function(e) {
            
            if (e.target.matches('form.form-gestion-candidato')) { 
                e.preventDefault(); 
                
                const form = e.target;
                const url = form.action;
                const formData = new FormData(form);

                const monthSelect = candModalContainer.querySelector('#month-select');
                const currentMonthFilter = monthSelect ? monthSelect.value : '';
                
                fetch(url, {
                    method: 'POST',
                    body: formData,
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Error en el servidor al procesar la acción.');
                    }
                    
                    let reloadUrl = urlListaCandidatosPorFecha;
                    if (currentMonthFilter) {
                        reloadUrl += '?mes=' + currentMonthFilter;
                    }
                    loadCandidatesModalContent(reloadUrl);
                })
                .catch(error => {
                    console.error('Error durante la activación/ocultación:', error);
                    alert('Hubo un error al realizar la operación.');
                });
            }
        });
        
        candModalContainer.addEventListener('click', function(e) {
                if (e.target.matches('[data-modal-close]') || e.target.closest('[data-modal-close]')) {
                    window.location.reload(); 
                }
            });
    }
});
// ====================================================================
// CONFIGURACIÓN GLOBAL Y MAPEO DE ESTADOS
// ====================================================================

const updateUrl = AppConfig.updateUrl;
const massiveUpdateUrl = AppConfig.massiveUpdateUrl;
const API_ASISTENCIA_CHECK_URL = AppConfig.API_ASISTENCIA_CHECK_URL;
const csrfToken = AppConfig.csrfToken;
const historyApiUrl = AppConfig.historyApiUrl; 


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
    document.getElementById('history-candidato-dni').textContent = dni;
    document.getElementById('history-candidato-nombre').textContent = nombre;
    const historyContent = document.getElementById('history-content');
    historyContent.innerHTML = '<p class="text-center text-gray-500">Cargando historial...</p>';

    const url = historyApiUrl.replace('DNI_PLACEHOLDER', dni);

    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            let html = '';
            if (data.procesos && data.procesos.length > 0) {
                data.procesos.forEach((p, index) => {
                    html += `
                        <div class="border p-3 rounded-lg shadow-sm ${index === 0 ? 'border-red-500 bg-red-50' : 'border-gray-300 bg-gray-50'}">
                            <p class="text-sm font-bold text-gray-800">${index === 0 ? 'ACTIVO (ÚLTIMO)' : 'Proceso Anterior'}</p>
                            <p class="text-xs text-gray-600 mt-1">
                                <span class="font-semibold">Convocatoria:</span> ${p.fecha_inicio} (${p.empresa_proceso.nombre} - ${p.sede_proceso.nombre})
                            </p>
                            <p class="text-xs text-gray-600">
                                <span class="font-semibold">Supervisor:</span> ${p.supervisor_nombre || 'Pendiente de Asignar'}
                            </p>
                            <p class="text-xs text-gray-600">
                                <span class="font-semibold">Resultado Final:</span> <span class="font-bold text-red-600">${p.estado}</span>
                            </p>
                        </div>
                    `;
                });
            } else {
                html = '<p class="text-center text-gray-500">No se encontró historial de procesos para este candidato.</p>';
            }
            historyContent.innerHTML = html;
        })
        .catch(error => {
            historyContent.innerHTML = `<p class="text-center text-red-500">Error al cargar el historial: ${error.message}</p>`;
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
        // Usamos 'q' como parámetro genérico para ser flexibles, asumiendo que el backend
        // de la API_ASISTENCIA_CHECK_URL ya busca por DNI o telefono_whatsapp en 'q'.
        // Si tu API sigue siendo estricta y solo acepta 'dni', usa `?dni=${searchValue}`.
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

    const toggleHeader = document.getElementById('toggle-header');
    const collapsibleContent = document.getElementById('collapsible-content');
    const toggleIcon = document.getElementById('toggle-icon');
    
    if (toggleHeader && collapsibleContent && toggleIcon) {
        toggleHeader.addEventListener('click', function() {
            collapsibleContent.classList.toggle('hidden'); 
            toggleIcon.classList.toggle('rotate-180');
        });
    }


    // 7. Funcionalidad del Dropdown de Desactivación
    const menuButton = document.getElementById('menu-button');
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
});
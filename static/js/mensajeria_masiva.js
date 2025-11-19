document.addEventListener('DOMContentLoaded', function() {
    // --- Referencias al DOM ---
    const selectProceso = document.getElementById('select-proceso');
    const selectFecha = document.getElementById('select-fecha');
    const totalDisponiblesText = document.getElementById('total-disponibles');
    const loadingSpinner = document.getElementById('loading-spinner');
    
    const selectDisponibles = document.getElementById('select-disponibles');
    const selectElegidos = document.getElementById('select-elegidos');
    const countDisponibles = document.getElementById('count-disponibles');
    const countElegidos = document.getElementById('count-elegidos');
    const filtroDisponibles = document.getElementById('filtro-disponibles');
    const filtroElegidos = document.getElementById('filtro-elegidos');

    const btnEnviar = document.getElementById('btn-enviar');
    const mensajeWhatsapp = document.getElementById('mensaje-whatsapp');

    // Botones de movimiento
    const btnMoverSeleccion = document.getElementById('btn-mover-seleccion');
    const btnRemoverSeleccion = document.getElementById('btn-remover-seleccion');
    const btnMoverTodos = document.getElementById('btn-mover-todos');
    const btnRemoverTodos = document.getElementById('btn-remover-todos');

    let contactosData = []; 

    // --- Funciones Auxiliares ---

    function toggleLoading(isLoading) {
        loadingSpinner.classList.toggle('hidden', !isLoading);
        // Solo deshabilitamos fecha si estamos cargando fechas, no contactos
        if (isLoading && selectFecha.options.length <= 1) {
             selectFecha.disabled = true;
             selectFecha.classList.add('bg-gray-100');
        }
        if (isLoading) {
            totalDisponiblesText.textContent = '...';
        }
    }

    function updateCounts() {
        // Filtramos visualmente cuántos hay en la lista (excluyendo ocultos por filtro de búsqueda)
        let visiblesDisponibles = 0;
        Array.from(selectDisponibles.options).forEach(opt => {
            if (opt.style.display !== 'none') visiblesDisponibles++;
        });

        countDisponibles.textContent = visiblesDisponibles;
        countElegidos.textContent = selectElegidos.options.length;
        
        const hasContacts = selectElegidos.options.length > 0;
        const hasMessage = mensajeWhatsapp.value.trim().length > 0;
        
        if (btnEnviar) {
            btnEnviar.disabled = !(hasContacts && hasMessage); 
        }
    }
    
    // --- FUNCIÓN 1: Cargar Fechas (Habilita el select) ---
    async function loadFechas() {
        const proceso = selectProceso.value;
        
        // Resetear UI
        selectFecha.innerHTML = '<option value="">Cargando...</option>';
        selectFecha.disabled = true;
        selectFecha.classList.add('bg-gray-100');
        
        // Limpiar contactos si cambia el proceso
        selectDisponibles.innerHTML = '';
        selectElegidos.innerHTML = '';
        totalDisponiblesText.textContent = '0';
        updateCounts();

        if (!proceso) {
            selectFecha.innerHTML = '<option value="">— Seleccione Fecha —</option>';
            return;
        }

        toggleLoading(true);

        try {
            // Usa la variable global urlMensajeriaApi definida en el template
            const response = await fetch(`${urlMensajeriaApi}?accion=get_fechas&proceso=${proceso}`);
            const data = await response.json();
            
            selectFecha.innerHTML = '<option value="">— Seleccione Fecha —</option>';
            
            if (data.status === 'success') {
                if (data.fechas && data.fechas.length > 0) {
                    data.fechas.forEach(fecha => {
                        // Formateo simple de fecha para display (opcional)
                        const partes = fecha.split('-');
                        const fechaDisplay = `${partes[2]}/${partes[1]}/${partes[0]}`;
                        const option = new Option(fechaDisplay, fecha); // text, value
                        selectFecha.add(option);
                    });
                    selectFecha.disabled = false; // HABILITAR AQUI
                    selectFecha.classList.remove('bg-gray-100');
                    selectFecha.classList.add('bg-white');
                } else {
                    selectFecha.innerHTML = '<option value="">— No hay fechas disponibles —</option>';
                }
            } else {
                alert('Error al cargar fechas: ' + data.message);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error de conexión al obtener fechas.');
        } finally {
            toggleLoading(false);
        }
    }

    // --- FUNCIÓN 2: Cargar Contactos (La que te faltaba) ---
    async function loadContactos() {
        const proceso = selectProceso.value;
        const fecha = selectFecha.value;
        
        selectDisponibles.innerHTML = '';
        selectElegidos.innerHTML = '';
        contactosData = [];
        updateCounts();

        // Actualizar inputs ocultos del formulario
        const inputProceso = document.getElementById('hidden-proceso-tipo');
        const inputFecha = document.getElementById('hidden-fecha-seleccionada');
        if(inputProceso) inputProceso.value = proceso;
        if(inputFecha) inputFecha.value = fecha;

        if (!proceso || !fecha) {
            totalDisponiblesText.textContent = '0';
            return;
        }

        toggleLoading(true);

        try {
            const response = await fetch(`${urlMensajeriaApi}?accion=get_contactos&proceso=${proceso}&fecha=${fecha}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                contactosData = data.contactos;
                let disponiblesReales = 0;
                
                contactosData.forEach(c => {
                    const displayText = `${c.nombres_completos} (${c.DNI}) - ${c.telefono_whatsapp}`; 
                    const option = new Option(displayText, c.DNI); // Value es el DNI (o ID si prefieres)

                    // Lógica visual para enviados
                    if (c.ya_enviado) {
                        option.text = `✅ (ENVIADO) ${displayText}`;
                        option.disabled = true; 
                        option.classList.add('text-gray-400', 'bg-gray-50', 'italic');
                    } else {
                        disponiblesReales++;
                    }
                    
                    selectDisponibles.add(option);
                });

                totalDisponiblesText.textContent = disponiblesReales;
                updateCounts();
            } else {
                alert('Error al cargar contactos: ' + data.message);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error de conexión al obtener contactos.');
        } finally {
            toggleLoading(false);
        }
    }

    // --- Funciones de Transferencia (Listbox) ---
    
    function transferOptions(sourceSelect, targetSelect) {
        // Convertimos a array para evitar problemas al mover nodos vivos
        const selectedOptions = Array.from(sourceSelect.selectedOptions);
        selectedOptions.forEach(option => {
            // No mover si está deshabilitado (ej. ya enviado)
            if (!option.disabled) {
                targetSelect.appendChild(option);
                option.selected = false; 
            }
        });
        updateCounts();
    }
    
    function transferAllOptions(sourceSelect, targetSelect) {
        Array.from(sourceSelect.options).forEach(option => {
            // Respetar filtro de búsqueda visible y estado disabled
            if (option.style.display !== 'none' && !option.disabled) {
                targetSelect.appendChild(option);
                option.selected = false;
            }
        });
        updateCounts();
    }
    
    function filterOptions(selectElement, filterInput) {
        const filterText = filterInput.value.toLowerCase();
        Array.from(selectElement.options).forEach(option => {
            const display = option.text.toLowerCase();
            option.style.display = display.includes(filterText) ? 'block' : 'none';
        });
        // Actualizar contadores visuales tras filtrar
        updateCounts(); 
    }

    // --- Event Listeners ---

    if (selectProceso) {
        selectProceso.addEventListener('change', loadFechas);
    }

    if (selectFecha) {
        selectFecha.addEventListener('change', loadContactos);
    }

    if (btnMoverSeleccion) btnMoverSeleccion.addEventListener('click', () => transferOptions(selectDisponibles, selectElegidos));
    if (btnRemoverSeleccion) btnRemoverSeleccion.addEventListener('click', () => transferOptions(selectElegidos, selectDisponibles));
    if (btnMoverTodos) btnMoverTodos.addEventListener('click', () => transferAllOptions(selectDisponibles, selectElegidos));
    if (btnRemoverTodos) btnRemoverTodos.addEventListener('click', () => transferAllOptions(selectElegidos, selectDisponibles));

    if (filtroDisponibles) filtroDisponibles.addEventListener('keyup', () => filterOptions(selectDisponibles, filtroDisponibles));
    if (filtroElegidos) filtroElegidos.addEventListener('keyup', () => filterOptions(selectElegidos, filtroElegidos));

    if (selectElegidos) selectElegidos.addEventListener('change', updateCounts);
    if (mensajeWhatsapp) mensajeWhatsapp.addEventListener('input', updateCounts);
    
    // Manejo del Envío del Formulario
    const formEnvio = document.getElementById('form-envio-masivo');
    if (formEnvio) {
        formEnvio.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Recolectar DNI/IDs de los elegidos
            const contactosAEnviar = Array.from(selectElegidos.options).map(opt => opt.value);
            const mensaje = mensajeWhatsapp.value.trim();
            const procesoFiltro = selectProceso.value;
            const fechaFiltro = selectFecha.value;

            if (contactosAEnviar.length === 0 || mensaje === "") {
                alert('Asegúrese de seleccionar contactos y escribir un mensaje.');
                return; 
            }
            
            // UI de Carga
            btnEnviar.disabled = true;
            const originalBtnText = btnEnviar.innerHTML;
            btnEnviar.innerHTML = '<svg class="animate-spin h-5 w-5 mr-2 inline" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Iniciando...';
            
            mensajeWhatsapp.disabled = true;
            selectDisponibles.disabled = true;
            selectElegidos.disabled = true;
            
            const progresoContainer = document.getElementById('progreso-container');
            const progresoTexto = document.getElementById('progreso-texto');
            
            if (progresoContainer) {
                progresoContainer.classList.remove('hidden', 'bg-green-50', 'border-green-500', 'text-green-800', 'bg-red-100', 'border-red-500', 'text-red-800');
                progresoContainer.classList.add('bg-blue-50', 'border-blue-500', 'text-blue-800');
                progresoTexto.textContent = `⏳ Enviando a ${contactosAEnviar.length} contactos...`;
            }

            const formData = new FormData();
            formData.append('proceso_filtro', procesoFiltro);
            formData.append('fecha_filtro', fechaFiltro);
            contactosAEnviar.forEach(dni => {
                formData.append('candidatos_seleccionados[]', dni); 
            });
            formData.append('mensaje_contenido', mensaje); 

            try {
                const response = await fetch(urlIniciarEnvio, { // Variable global definida en el template
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'), // Asegúrate de tener la función getCookie
                    },
                    body: formData,
                });

                const result = await response.json();
                
                if ((response.status === 200 || response.status === 202) && result.success) { 
                    if (progresoContainer) {
                        progresoContainer.classList.remove('bg-blue-50', 'border-blue-500', 'text-blue-800');
                        progresoContainer.classList.add('bg-green-50', 'border-green-500', 'text-green-800');
                        progresoTexto.innerHTML = `✅ **Éxito:** ${result.message} <a href="#" id="link-ver-historial" class="underline font-bold ml-2">Ver historial</a>.`;
                        
                        // Vincular el click del link generado dinámicamente
                        document.getElementById('link-ver-historial').addEventListener('click', (e) => {
                             e.preventDefault();
                             const btnHistorial = document.getElementById('btn-abrir-historial');
                             if(btnHistorial) btnHistorial.click();
                        });
                    }
                    
                    // Limpiar selección
                    selectElegidos.innerHTML = ''; 
                    mensajeWhatsapp.value = ''; 
                    // Recargar disponibles para actualizar marcas de "Enviado"
                    loadContactos(); 
                    
                } else {
                    throw new Error(result.message || 'Error desconocido');
                }

            } catch (error) {
                console.error('Error:', error);
                if (progresoContainer) {
                    progresoContainer.classList.remove('bg-blue-50', 'border-blue-500', 'text-blue-800');
                    progresoContainer.classList.add('bg-red-100', 'border-red-500', 'text-red-800');
                    progresoTexto.innerHTML = `❌ **Error:** ${error.message}`;
                }
            } finally {
                mensajeWhatsapp.disabled = false;
                selectDisponibles.disabled = false;
                selectElegidos.disabled = false;
                btnEnviar.disabled = false;
                btnEnviar.innerHTML = originalBtnText;
                updateCounts();
            }
        });
    }

    // Helper para CSRF (si no lo tienes global)
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Inicializar conteos
    updateCounts();
});
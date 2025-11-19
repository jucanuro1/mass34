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
    // Asegúrate de que urlMensajeriaApi y urlIniciarEnvio estén definidos en tu template HTML

    // --- Funciones Auxiliares ---

    function toggleLoading(isLoading) {
        loadingSpinner.classList.toggle('hidden', !isLoading);
        if (isLoading && selectFecha.options.length <= 1) {
             selectFecha.disabled = true;
             selectFecha.classList.add('bg-gray-100');
        }
        if (isLoading) {
            totalDisponiblesText.textContent = '...';
        }
    }

    function updateCounts() {
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

    // 🟢 NUEVA FUNCIÓN: Manejo de Tooltip/Mini-detalle
    function initTooltipHistorial() {
        // Usamos selectDisponibles porque es donde cargamos los detalles
        selectDisponibles.addEventListener('mousemove', handleTooltip);
        selectDisponibles.addEventListener('mouseleave', hideTooltip);

        // Creamos un div flotante para el tooltip (debe existir en el DOM o ser creado)
        let tooltipDiv = document.getElementById('historial-tooltip');
        if (!tooltipDiv) {
            tooltipDiv = document.createElement('div');
            tooltipDiv.id = 'historial-tooltip';
            // Clases de Tailwind para estilo y ocultar por defecto
            tooltipDiv.className = 'absolute z-50 p-2 text-xs bg-gray-800 text-white rounded shadow-xl pointer-events-none hidden max-w-xs transition-opacity duration-300';
            document.body.appendChild(tooltipDiv);
        }

        function handleTooltip(e) {
            const option = e.target;
            // Solo actuar si el target es una opción y es elegible (no deshabilitado)
            if (option.tagName === 'OPTION' && !option.disabled) {
                const conteo = parseInt(option.getAttribute('data-conteo'));
                
                if (conteo > 0) {
                    let content = `<p class="font-bold mb-1">Historial de Mensajes</p>`;
                    content += `<p>Total de envíos exitosos: <span class="${conteo > 4 ? 'text-red-400' : 'text-green-400'}">${conteo}</span></p>`;
                    content += `<p class="mt-1 text-gray-400">Selecciona para volver a enviar.</p>`;

                    tooltipDiv.innerHTML = content;
                    tooltipDiv.style.left = `${e.pageX + 10}px`;
                    tooltipDiv.style.top = `${e.pageY + 10}px`;
                    tooltipDiv.classList.remove('hidden');
                } else {
                    hideTooltip();
                }
            } else {
                hideTooltip();
            }
        }

        function hideTooltip() {
            tooltipDiv.classList.add('hidden');
        }
    }

    function renderizarListaContactos(lista) {
        selectDisponibles.innerHTML = '';
        selectElegidos.innerHTML = '';
        let disponiblesCount = 0;
        
        lista.forEach(c => { 
            const conteo = c.conteo_envios_exitosos || 0;
            let badgeTexto = '';
            let badgeClass = '';

            if (conteo > 0) {
                badgeTexto = `[${conteo} ENVÍO(S)] `;
                
                if (conteo === 1) {
                    badgeClass = 'bg-yellow-50 text-yellow-800'; 
                } else if (conteo < 5) {
                    badgeClass = 'bg-blue-50 text-blue-800';
                } else {
                    badgeClass = 'bg-red-50 text-red-800 font-bold';
                }
            }

            const displayText = `${badgeTexto}${c.nombres_completos} (${c.DNI})`; 
            const option = new Option(displayText, c.DNI); // <-- 'option' queda definida aquí
            
            option.setAttribute('data-conteo', conteo);

            if (conteo > 0) {
                const classesToAdd = badgeClass.split(' ');
                option.classList.add(...classesToAdd); 
            }

            selectDisponibles.add(option);
            disponiblesCount++; 
        }); 
        

        totalDisponiblesText.textContent = disponiblesCount;
        updateCounts();
    }

    
    async function loadFechas() {
        const proceso = selectProceso.value;
        
        selectFecha.innerHTML = '<option value="">Cargando...</option>';
        selectFecha.disabled = true;
        selectFecha.classList.add('bg-gray-100');
        
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
                        const partes = fecha.split('-');
                        const fechaDisplay = `${partes[2]}/${partes[1]}/${partes[0]}`;
                        const option = new Option(fechaDisplay, fecha); 
                        selectFecha.add(option);
                    });
                    selectFecha.disabled = false; 
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

    // --- FUNCIÓN 2: Cargar Contactos (Modificada para llamar a renderizarListaContactos) ---
    async function loadContactos() {
        const proceso = selectProceso.value;
        const fecha = selectFecha.value;
        
        selectDisponibles.innerHTML = '';
        selectElegidos.innerHTML = '';
        contactosData = [];
        updateCounts();

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
                
                // 🔴 USAMOS LA NUEVA FUNCIÓN PARA RENDERIZAR
                renderizarListaContactos(contactosData);
                
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
        const selectedOptions = Array.from(sourceSelect.selectedOptions);
        selectedOptions.forEach(option => {
            if (!option.disabled) {
                targetSelect.appendChild(option);
                option.selected = false; 
            }
        });
        updateCounts();
    }
    
    function transferAllOptions(sourceSelect, targetSelect) {
        Array.from(sourceSelect.options).forEach(option => {
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
    
    const formEnvio = document.getElementById('form-envio-masivo');
    if (formEnvio) {
        formEnvio.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const contactosAEnviar = Array.from(selectElegidos.options).map(opt => opt.value);
            const mensaje = mensajeWhatsapp.value.trim();
            const procesoFiltro = selectProceso.value;
            const fechaFiltro = selectFecha.value;

            if (contactosAEnviar.length === 0 || mensaje === "") {
                alert('Asegúrese de seleccionar contactos y escribir un mensaje.');
                return; 
            }
            
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
            // Si tenías campos de etapa, agrégalos aquí. Por ahora no son necesarios.

            try {
                const response = await fetch(urlIniciarEnvio, { 
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'), 
                    },
                    body: formData,
                });

                const result = await response.json();
                
                if ((response.status === 200 || response.status === 202) && result.success) { 
                    if (progresoContainer) {
                        progresoContainer.classList.remove('bg-blue-50', 'border-blue-500', 'text-blue-800');
                        progresoContainer.classList.add('bg-green-50', 'border-green-500', 'text-green-800');
                        progresoTexto.innerHTML = `✅ **Éxito:** ${result.message} <a href="#" id="link-ver-historial" class="underline font-bold ml-2">Ver historial</a>.`;
                        
                        document.getElementById('link-ver-historial').addEventListener('click', (e) => {
                             e.preventDefault();
                             const btnHistorial = document.getElementById('btn-abrir-historial');
                             if(btnHistorial) btnHistorial.click();
                        });
                    }
                    
                    selectElegidos.innerHTML = ''; 
                    mensajeWhatsapp.value = ''; 
                    loadContactos(); // Vuelve a cargar la lista para actualizar los estados de 'HISTORIAL PREVIO'
                    
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

    // 🟢 INICIALIZACIÓN DE TOOLTIP
    initTooltipHistorial();
    updateCounts();
});
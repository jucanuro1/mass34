// static/js/mensajeria_masiva.js

document.addEventListener('DOMContentLoaded', function() {
    
    // --- Variables Globales ---
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
    
    // Almacena la lista completa de contactos disponibles (para el filtro)
    let contactosData = []; 

    // --- Funciones de Utilidad ---

    function toggleLoading(isLoading) {
        loadingSpinner.classList.toggle('hidden', !isLoading);
        selectFecha.disabled = isLoading;
        if (isLoading) {
            selectFecha.classList.add('bg-gray-100');
            totalDisponiblesText.textContent = '...';
        }
    }

    function updateCounts() {
        countDisponibles.textContent = selectDisponibles.options.length;
        countElegidos.textContent = selectElegidos.options.length;
        
        // Habilitar/Deshabilitar botón de envío
        const hasContacts = selectElegidos.options.length > 0;
        const hasMessage = mensajeWhatsapp.value.trim().length > 0;
        btnEnviar.disabled = !(hasContacts && hasMessage);
    }
    
    // --- Lógica AJAX (Carga de Datos) ---

    async function loadFechas() {
        const proceso = selectProceso.value;
        selectFecha.innerHTML = '<option value="">Cargando...</option>';
        selectFecha.disabled = true;
        selectFecha.classList.add('bg-gray-100');
        
        if (!proceso) {
            selectFecha.innerHTML = '<option value="">-- Seleccione Fecha --</option>';
            return;
        }

        toggleLoading(true);

        try {
            const response = await fetch(`${urlMensajeriaApi}?accion=get_fechas&proceso=${proceso}`);
            const data = await response.json();
            
            selectFecha.innerHTML = '<option value="">-- Seleccione Fecha --</option>';
            if (data.status === 'success') {
                data.fechas.forEach(fecha => {
                    const option = new Option(fecha, fecha);
                    selectFecha.add(option);
                });
                selectFecha.disabled = false;
                selectFecha.classList.remove('bg-gray-100');
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

    async function loadContactos() {
        const proceso = selectProceso.value;
        const fecha = selectFecha.value;
        
        selectDisponibles.innerHTML = '';
        selectElegidos.innerHTML = '';
        contactosData = [];
        updateCounts();

        if (!proceso || !fecha) {
            totalDisponiblesText.textContent = '0';
            return;
        }

        toggleLoading(true);

        try {
            const response = await fetch(`${urlMensajeriaApi}?accion=get_contactos&proceso=${proceso}&fecha=${fecha}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                contactosData = data.contactos; // Almacenamos todos los contactos
                
                contactosData.forEach(c => {
                    const display = `${c.nombres_completos} (${c.DNI}) - ${c.telefono_whatsapp}`;
                    const option = new Option(display, c.DNI);
                    selectDisponibles.add(option);
                });

                totalDisponiblesText.textContent = contactosData.length;
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

    // --- Lógica de Transferencia de Elementos (Django Admin Style) ---

    function transferOptions(sourceSelect, targetSelect) {
        const selectedOptions = Array.from(sourceSelect.selectedOptions);
        selectedOptions.forEach(option => {
            targetSelect.appendChild(option);
            option.selected = false; // Deseleccionar después de mover
        });
        updateCounts();
    }
    
    function transferAllOptions(sourceSelect, targetSelect) {
        Array.from(sourceSelect.options).forEach(option => {
            targetSelect.appendChild(option);
            option.selected = false;
        });
        updateCounts();
    }
    
    // --- Lógica de Filtro ---

    function filterOptions(selectElement, filterInput) {
        const filterText = filterInput.value.toLowerCase();
        
        Array.from(selectElement.options).forEach(option => {
            const display = option.textContent.toLowerCase();
            option.style.display = display.includes(filterText) ? 'block' : 'none';
        });
    }

    // --- Event Listeners ---

    selectProceso.addEventListener('change', () => {
        loadFechas();
        selectFecha.value = ""; // Resetear la fecha al cambiar el proceso
        loadContactos();
        // Set hidden inputs
        document.getElementById('hidden-proceso-tipo').value = selectProceso.value;
        document.getElementById('hidden-fecha-seleccionada').value = '';
    });

    selectFecha.addEventListener('change', () => {
        loadContactos();
        // Set hidden inputs
        document.getElementById('hidden-fecha-seleccionada').value = selectFecha.value;
    });

    // Botones de Movimiento
    document.getElementById('btn-mover-seleccion').addEventListener('click', () => {
        transferOptions(selectDisponibles, selectElegidos);
    });
    document.getElementById('btn-remover-seleccion').addEventListener('click', () => {
        transferOptions(selectElegidos, selectDisponibles);
    });
    document.getElementById('btn-mover-todos').addEventListener('click', () => {
        transferAllOptions(selectDisponibles, selectElegidos);
    });
    document.getElementById('btn-remover-todos').addEventListener('click', () => {
        transferAllOptions(selectElegidos, selectDisponibles);
    });

    // Filtros
    filtroDisponibles.addEventListener('keyup', () => filterOptions(selectDisponibles, filtroDisponibles));
    filtroElegidos.addEventListener('keyup', () => filterOptions(selectElegidos, filtroElegidos));

    // Validar envío y mensaje
    selectElegidos.addEventListener('change', updateCounts);
    mensajeWhatsapp.addEventListener('input', updateCounts);
    
    // 🔑 Capturar Submit del Formulario
    document.getElementById('form-envio-masivo').addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Antes de enviar, asegurar que todos los contactos elegidos estén seleccionados
        // Esto es CLAVE para que Django los reciba en 'request.POST.getlist('contactos_seleccionados')'
        Array.from(selectElegidos.options).forEach(option => {
            option.selected = true;
        });
        
        // Aquí iría tu llamada AJAX POST a /mensajeria/enviar/
        // Opcionalmente, podrías iniciar el envío de forma asíncrona
        
        // Simulación del POST y progreso (reemplazar con Celery/Ajax real)
        btnEnviar.disabled = true;
        btnEnviar.innerHTML = '<svg class="animate-spin h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Iniciando Envío...';
        document.getElementById('progreso-container').classList.remove('hidden');
        document.getElementById('progreso-texto').textContent = 'Preparando lotes...';

        // **AQUÍ IRÍA EL FETCH POST REAL A TU ENDPOINT DE ENVÍO DE DJANGO**
        // Por ejemplo: 
        /*
        fetch(this.action, { method: 'POST', body: new FormData(this) })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Iniciar polling para progreso si usas Celery
                    // document.getElementById('progreso-texto').textContent = 'Envío iniciado. ID de Tarea: ' + data.task_id;
                    alert('Envío Masivo Iniciado. Los mensajes se enviarán en segundo plano.');
                } else {
                    alert('Error al iniciar el envío: ' + data.message);
                }
                // Resetear UI
                btnEnviar.disabled = false;
                btnEnviar.innerHTML = '<svg...> Iniciar Envío Masivo';
            })
            .catch(error => {
                console.error('Error de red:', error);
                alert('Error de conexión al intentar enviar.');
            });
        */
        
        // NOTA: Para el flujo completo de progreso, deberás implementar WebSockets o Polling AJAX.
    });

    // Inicialización al cargar la página
    updateCounts(); 
});
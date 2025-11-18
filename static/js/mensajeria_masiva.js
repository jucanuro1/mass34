document.addEventListener('DOMContentLoaded', function() {
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
    const selectPlantilla = document.getElementById('select-plantilla'); 

    let contactosData = []; 

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
        
        const hasContacts = selectElegidos.options.length > 0;
        const hasMessage = mensajeWhatsapp.value.trim().length > 0;
        btnEnviar.disabled = !(hasContacts && hasMessage); 
    }
    
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
                contactosData = data.contactos;
                
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
    
    function transferOptions(sourceSelect, targetSelect) {
        const selectedOptions = Array.from(sourceSelect.selectedOptions);
        selectedOptions.forEach(option => {
            targetSelect.appendChild(option);
            option.selected = false; 
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
    
    function filterOptions(selectElement, filterInput) {
        const filterText = filterInput.value.toLowerCase();
        
        Array.from(selectElement.options).forEach(option => {
            const display = option.textContent.toLowerCase();
            option.style.display = display.includes(filterText) ? 'block' : 'none';
        });
    }

    selectProceso.addEventListener('change', () => {
        loadFechas();
        selectFecha.value = ""; 
        loadContactos();
        document.getElementById('hidden-proceso-tipo').value = selectProceso.value;
        document.getElementById('hidden-fecha-seleccionada').value = '';
    });

    selectFecha.addEventListener('change', () => {
        loadContactos();
        document.getElementById('hidden-fecha-seleccionada').value = selectFecha.value;
    });

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

    filtroDisponibles.addEventListener('keyup', () => filterOptions(selectDisponibles, filtroDisponibles));
    filtroElegidos.addEventListener('keyup', () => filterOptions(selectElegidos, filtroElegidos));

    selectElegidos.addEventListener('change', updateCounts);
    mensajeWhatsapp.addEventListener('input', updateCounts);
    
    document.getElementById('form-envio-masivo').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const contactosAEnviarDNI = Array.from(selectElegidos.options).map(opt => opt.value); // Obtener DNI's
        const mensaje = mensajeWhatsapp.value.trim();

        const procesoFiltro = selectProceso.value;
        const fechaFiltro = selectFecha.value;

        if (contactosAEnviarDNI.length === 0 || mensaje === "") {
            alert('Asegúrese de seleccionar contactos y escribir un mensaje.');
            return; 
        }
        
        btnEnviar.disabled = true;
        btnEnviar.innerHTML = '<svg class="animate-spin h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> **Iniciando Tarea...**';
        
        mensajeWhatsapp.disabled = true;
        selectDisponibles.disabled = true;
        selectElegidos.disabled = true;
        
        const progresoContainer = document.getElementById('progreso-container');
        const progresoTexto = document.getElementById('progreso-texto');
        
        progresoContainer.classList.remove('hidden', 'bg-green-50', 'border-green-500', 'text-green-800', 'bg-red-100', 'border-red-500', 'text-red-800');
        progresoContainer.classList.add('bg-blue-50', 'border-blue-500', 'text-blue-800');
        progresoContainer.classList.remove('hidden');
        progresoTexto.textContent = `⏳ Preparando envío de ${contactosAEnviarDNI.length} contactos...`;

        const formData = new FormData();
        formData.append('proceso_filtro', procesoFiltro);
        formData.append('fecha_filtro', fechaFiltro);
        contactosAEnviarDNI.forEach(dni => {
            formData.append('candidatos_seleccionados[]', dni); 
        });
        formData.append('mensaje_contenido', mensaje); 

        try {
            const response = await fetch(urlIniciarEnvio, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken, 
                },
                body: formData,
            });

            const result = await response.json();
            
            if (response.status === 202 && result.success) { 
                
                progresoContainer.classList.remove('bg-blue-50', 'border-blue-500', 'text-blue-800');
                progresoContainer.classList.add('bg-green-50', 'border-green-500', 'text-green-800');
                progresoTexto.innerHTML = `✅ **Tarea Iniciada (ID: ${result.tarea_id})** Enviando ${contactosAEnviarDNI.length} mensajes en segundo plano. <a href="#" onclick="document.getElementById('btn-abrir-historial').click();" class="underline font-bold">Ver historial</a>.`;
                
                selectElegidos.innerHTML = ''; 
                mensajeWhatsapp.value = ''; 
                
            } else {
                progresoContainer.classList.remove('bg-blue-50', 'border-blue-500', 'text-blue-800');
                progresoContainer.classList.add('bg-red-100', 'border-red-500', 'text-red-800');
                progresoTexto.innerHTML = `❌ **Error al iniciar la tarea:** ${result.message || 'Error desconocido del servidor.'}`;
            }

        } catch (error) {
            console.error('Error de red o CORS:', error);
            progresoContainer.classList.remove('bg-blue-50', 'border-blue-500', 'text-blue-800');
            progresoContainer.classList.add('bg-red-100', 'border-red-500', 'text-red-800');
            progresoTexto.innerHTML = `❌ **Error de Conexión:** El servidor no respondió.`;
            setTimeout(() => {
                progresoContainer.classList.add('hidden');
            }, 5000);
        } finally {
            mensajeWhatsapp.disabled = false;
            selectDisponibles.disabled = false;
            selectElegidos.disabled = false;
            
            btnEnviar.disabled = false;
            btnEnviar.innerHTML = `<svg class="w-6 h-6 mr-2 fill-current" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><path d="M476.9 161.1C435 119.1 379.2 96 319.9 96C197.5 96 97.9 195.6 97.9 318C97.9 357.1 108.1 395.3 127.5 429L96 544L213.7 513.1C246.1 530.8 282.6 540.1 319.8 540.1L319.9 540.1C442.2 540.1 544 440.5 544 318.1C544 258.8 518.8 203.1 476.9 161.1zM319.9 502.7C286.7 502.7 254.2 493.8 225.9 477L219.2 473L149.4 491.3L168 423.2L163.6 416.2C145.1 386.8 135.4 352.9 135.4 318C135.4 216.3 218.2 133.5 320 133.5C369.3 133.5 415.6 152.7 450.4 187.6C485.2 222.5 506.6 268.8 506.5 318.1C506.5 419.9 421.6 502.7 319.9 502.7zM421.1 364.5C415.6 361.7 388.3 348.3 383.2 346.5C378.1 344.6 374.4 343.7 370.7 349.3C367 354.9 356.4 367.3 353.1 371.1C349.9 374.8 346.6 375.3 341.1 372.5C308.5 356.2 287.1 343.4 265.6 306.5C259.9 296.7 271.3 297.4 281.9 276.2C283.7 272.5 282.8 269.3 281.4 266.5C280 263.7 268.9 236.4 264.3 225.3C259.8 214.5 255.2 216 251.8 215.8C248.6 215.6 244.9 215.6 241.2 215.6C237.5 215.6 231.5 217 226.4 222.5C221.3 228.1 207 241.5 207 268.8C207 296.1 226.9 322.5 229.6 326.2C232.4 329.9 268.7 385.9 324.4 410C359.6 425.2 373.4 426.5 391 423.9C401.7 422.3 423.8 410.5 428.4 397.5C433 384.5 433 373.4 431.6 371.1C430.3 368.6 426.6 367.2 421.1 364.5z"/></svg> Enviar WhatsApp`;
            
            updateCounts(); 
            /*
            if (response.status !== 202) { 
                 setTimeout(() => {
                    progresoContainer.classList.add('hidden');
                }, 5000);
            }*/
        }

    });

    updateCounts(); 
});
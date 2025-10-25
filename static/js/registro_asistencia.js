const modal = document.getElementById('asistencia-modal');
const dniInput = document.getElementById('dni');

function openModal() {
    const currentTime = new Date().toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    document.getElementById('modal-current-time').textContent = currentTime;

    modal.classList.remove('hidden');
    setTimeout(() => {
        const modalContent = modal.querySelector('.bg-white');
        if (modalContent) {
            modalContent.classList.remove('scale-95', 'opacity-0');
            modalContent.classList.add('scale-100', 'opacity-100');
        }
    }, 50);
}


window.closeModal = function() {
    const modalContent = modal.querySelector('.bg-white');
    
    if (modalContent) {
        modalContent.classList.remove('scale-100', 'opacity-100');
        modalContent.classList.add('scale-95', 'opacity-0');
    }
    
    setTimeout(() => {
        modal.classList.add('hidden');
        dniInput.value = ''; 
        dniInput.focus();
    }, 300);
}

$(document).ready(function() {
    
    const movimientoDisplay = document.getElementById('movimiento-display');
    const searchButtonText = document.getElementById('search-text');
    const searchButton = $('#search-button');
    
    $('#dni-search-form').on('submit', function(e) {
        e.preventDefault(); 
        
        const dni = dniInput.value.trim();
        const form = $(this);

        if (dni.length !== 8) { 
            alert("Por favor, ingrese un DNI válido de 8 dígitos.");
            return;
        }
        
        searchButton.prop('disabled', true);
        searchButtonText.textContent = 'Buscando...'; 

        $.ajax({
            url: form.attr('action'),
            type: 'POST',
            data: form.serialize(),
            headers: {
                'X-Requested-With': 'XMLHttpRequest' 
            },
            dataType: 'json',
            success: function(response) {
                if (response.success) {
                    $('#modal-candidato-nombre').text(response.candidato_nombre);
                    $('#modal-candidato-dni').text(response.candidato_dni);
                    $('#modal-fase-proceso').text(response.fase_proceso);
                    $('#modal-proceso-id').val(response.proceso_id);
                    $('#modal-fase-actual').val(response.fase_proceso_key);
                    
                    const ultimoRegistroText = response.ultimo_registro ? `Último Registro Hoy: ${response.ultimo_registro}` : 'Aún no hay registros hoy.';
                    $('#modal-ultimo-registro').text(ultimoRegistroText);
                    
                    const movimiento = response.movimiento_requerido;
                    $('#modal-movimiento').val(movimiento);
                    
                    let buttonHtml = '';
                    let buttonText, buttonColor, buttonIcon;
                    
                    if (response.requiere_entrada_salida) {
                        const isEntrada = (movimiento === 'ENTRADA');
                        
                        buttonText = isEntrada ? 'Marcar ENTRADA' : 'Marcar SALIDA';
                        buttonColor = isEntrada ? 'bg-green-600 hover:bg-green-700 shadow-green-500/30' : 'bg-orange-600 hover:bg-orange-700 shadow-orange-500/30';
                        buttonIcon = isEntrada ? 
                            '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1-8a1 1 0 102 0V7a1 1 0 10-2 0v3zm0 4a1 1 0 102 0v-1a1 1 0 10-2 0v1z" clip-rule="evenodd" /></svg>' :
                            '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-8a1 1 0 10-2 0v1a1 1 0 102 0v-1zm-1-4a1 1 0 10-2 0v3a1 1 0 102 0V6z" clip-rule="evenodd" /></svg>';

                    } else {
                        buttonText = 'Confirmar ASISTENCIA';
                        buttonColor = 'bg-red-600 hover:bg-red-700 shadow-red-500/30';
                        buttonIcon = '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3a1 1 0 102 0V7z" clip-rule="evenodd" /></svg>';
                    }
                    
                    buttonHtml = `
                        <button type="submit" 
                                class="w-full py-2.5 ${buttonColor} text-white font-extrabold rounded-full transition duration-300 shadow-xl
                                        flex items-center justify-center px-5 uppercase tracking-wider transform hover:scale-[1.03] active:scale-95">
                            <div class="flex items-center">
                                ${buttonIcon}
                                <span class="text-xs">${buttonText}</span>
                            </div>
                        </button>
                    `;

                    movimientoDisplay.innerHTML = buttonHtml;
                    openModal(); 
                } else {
                    alert('⚠️ Error de Búsqueda: ' + response.message); 
                    dniInput.value = '';
                }
            },
            error: function(xhr) {
                alert('❌ Error de conexión con el servidor. Código: ' + xhr.status + (xhr.status === 404 ? ' (Ruta no encontrada)' : ''));
            },
            complete: function() {
                searchButton.prop('disabled', false);
                searchButtonText.textContent = 'Buscar Candidato (ENTER)';
                dniInput.focus();
            }
        });
    });

    dniInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' || e.key === 'Tab') {
            e.preventDefault();
            if (dniInput.value.trim().length >= 8) {
                $('#dni-search-form').submit(); 
            }
        }
    });

    $('#registro-asistencia-form').on('submit', function(e) {
        e.preventDefault(); 
        
        const form = $(this);
        const url = form.attr('action'); 
        const submitButton = form.find('button[type="submit"]');
        const originalHtml = submitButton.html(); 
        
        submitButton.prop('disabled', true).html('<div class="flex items-center justify-center"><svg class="animate-spin h-5 w-5 mr-3 text-white" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg><span class="text-sm">Registrando...</span></div>');


        $.ajax({
            url: url,
            type: 'POST',
            data: form.serialize(),
            headers: {
                'X-CSRFToken': form.find('[name="csrfmiddlewaretoken"]').val(),
                'X-Requested-With': 'XMLHttpRequest' 
            },
            dataType: 'json', 
            
            success: function(response) {
                alert('✅ Registro Exitoso: ' + response.message); 
                closeModal(); 
            },
            
            error: function(xhr) {
                let errorMessage = 'Error de conexión/servidor.';
                
                try {
                    const response = JSON.parse(xhr.responseText);
                    errorMessage = response.message || errorMessage;
                } catch (e) {
                    if (xhr.status === 403) {
                        errorMessage = 'ERROR DE AUTORIZACIÓN (403): Sesión expirada. Por favor, vuelva a iniciar sesión.';
                    } else {
                        errorMessage = `Error HTTP ${xhr.status}. Posible error en el servidor o formato de respuesta.`;
                    }
                }
                
                alert('❌ Fallo el registro: ' + errorMessage);
            },
            
            complete: function() {
                submitButton.prop('disabled', false).html(originalHtml);
            }
        });
    });

}); 
function openCommentModal(procesoId, candidatoNombre) {
    const modal = document.getElementById('comment-modal');
    const panel = document.getElementById('comment-panel');
    const overlay = document.getElementById('comment-upload-overlay');

    document.getElementById('comment-candidato-nombre').innerText = candidatoNombre;
    document.getElementById('comment-proceso-id-display').innerText = procesoId;
    document.getElementById('input-proceso-id-comentarios').value = procesoId;
    
    const textarea = document.getElementById('observacion_texto');
    textarea.value = '';
    document.getElementById('char-count').innerText = '0';

    modal.classList.remove('hidden');
    
    setTimeout(() => {
        panel.classList.remove('translate-x-full');
        overlay.classList.add('opacity-75');
        textarea.focus();
    }, 10);
}

function closeCommentModal() {
    const modal = document.getElementById('comment-modal');
    const panel = document.getElementById('comment-panel');
    const overlay = document.getElementById('comment-upload-overlay');
    
    panel.classList.add('translate-x-full');
    overlay.classList.remove('opacity-75');
    
    setTimeout(() => {
        modal.classList.add('hidden'); 
    }, 500); 
}

function openTestUploadModal(procesoId, candidatoNombre) {
    const modal = document.getElementById('test-upload-modal');
    const panel = document.getElementById('test-upload-panel');
    const overlay = document.getElementById('test-upload-overlay');

    document.getElementById('test-candidato-nombre').innerText = candidatoNombre;
    document.getElementById('test-proceso-id-display').innerText = procesoId;
    document.getElementById('input-proceso-id-test').value = procesoId;
    
    document.getElementById('registro-test-form').reset();
    
    modal.classList.remove('hidden');
    
    setTimeout(() => {
        panel.classList.remove('translate-x-full');
        overlay.classList.add('opacity-75');
    }, 10);
}

function closeTestUploadModal() {
    const modal = document.getElementById('test-upload-modal');
    const panel = document.getElementById('test-upload-panel');
    const overlay = document.getElementById('test-upload-overlay');
    
    panel.classList.add('translate-x-full');
    overlay.classList.remove('opacity-75');
    
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 500); 
}

function openDateEditModal(procesoId, dateType, currentDate, title, candidatoNombre) {
    document.getElementById('modal-proceso-id').value = procesoId;
    document.getElementById('modal-date-type').value = dateType;
    document.getElementById('modal-date-title').textContent = title;
    document.getElementById('modal-candidato-nombre').textContent = candidatoNombre;
    
    document.getElementById('new_date').value = currentDate;
    
    document.getElementById('dateEditModal').classList.remove('hidden');
}

function closeDateEditModal() {
    document.getElementById('dateEditModal').classList.add('hidden');
}

function openDocumentUploadModal(proceso_pk, nombre_candidato) {
    document.getElementById('document-upload-modal').classList.remove('hidden');
    setTimeout(() => {
        document.getElementById('document-upload-panel').classList.remove('translate-x-full');
    }, 10); 

    document.getElementById('doc-candidato-nombre').textContent = nombre_candidato;
    document.getElementById('doc-proceso-id-display').textContent = proceso_pk;
    
    document.getElementById('input-proceso-id-doc').value = proceso_pk;

    document.getElementById('registro-documento-form').reset();
}

function closeDocumentUploadModal() {
    document.getElementById('document-upload-panel').classList.add('translate-x-full');
    setTimeout(() => {
        document.getElementById('document-upload-modal').classList.add('hidden');
    }, 500); 
}

$(document).ready(function() {
    
    $('#observacion_texto').on('input', function() {
        const charCount = $(this).val().length;
        $('#char-count').text(charCount);
    });

    $('#registro-comentario-form').off('submit').on('submit', function(e) {
        e.preventDefault(); 
        const form = $(this);
        const submitBtn = $('#btn-guardar-comentario');
        
        submitBtn.prop('disabled', true).html('<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 2v4m0 12v4m9-9h-4M7 12H3m14.07-5.07l-2.83 2.83M6.76 17.24l-2.83-2.83m14.07 0l-2.83-2.83M6.76 6.76l-2.83 2.83"/></svg> Guardando...');
        
        $.ajax({
            type: 'POST',
            url: form.attr('action'),
            data: form.serialize(),
            dataType: 'json',
            success: function(response) {
                if (response.success) {
                    alert('✅ Éxito: ' + response.message); 
                    closeCommentModal();
                } else {
                    alert('❌ Error al registrar: ' + response.message);
                }
            },
            error: function(xhr) {
                let status = xhr.status;
                let defaultMessage = `Error ${status}: Fallo de comunicación con el servidor.`;
                let errorMessage = defaultMessage;

                try {
                    const responseJson = JSON.parse(xhr.responseText);
                    errorMessage = responseJson.message || defaultMessage;
                } catch (e) {}
                
                alert(`🔴 Fallo de registro (${status}): ${errorMessage}`);
            },
            complete: function() {
                submitBtn.prop('disabled', false).html('<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M18 10c0 3.866-3.134 7-7 7a6.96 6.96 0 01-3.692-.997l-3.53 1.059a.5.5 0 01-.63-.63l1.059-3.53A7 7 0 1118 10zm-6-4a1 1 0 10-2 0v2H8a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V6z" clip-rule="evenodd" /></svg> Guardar Observación');
            }
        });
    });

    $('#registro-test-form').off('submit').on('submit', function(e) {
        e.preventDefault(); 
        const form = $(this);
        const submitBtn = $('#btn-guardar-test');
        
        const formData = new FormData(this);
        
        submitBtn.prop('disabled', true).html('<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 2v4m0 12v4m9-9h-4M7 12H3m14.07-5.07l-2.83 2.83M6.76 17.24l-2.83-2.83m14.07 0l-2.83-2.83M6.76 6.76l-2.83 2.83"/></svg> Subiendo Archivo...');

        $.ajax({
            type: 'POST',
            url: form.attr('action'),
            data: formData,
            processData: false, 
            contentType: false, 
            dataType: 'json',
            success: function(response) {
                if (response.success) {
                    alert('✅ Éxito: ' + response.message); 
                    closeTestUploadModal();
                } else {
                    alert('❌ Error al subir: ' + response.message);
                }
            },
            error: function(xhr) {
                let status = xhr.status;
                let defaultMessage = `Error ${status}: Fallo de comunicación con el servidor.`;
                let errorMessage = defaultMessage;

                try {
                    const responseJson = JSON.parse(xhr.responseText);
                    errorMessage = responseJson.message || defaultMessage;
                } catch (e) {
                }
                
                alert(`🔴 Fallo en la subida (${status}): ${errorMessage}`);
            },
            complete: function() {
                submitBtn.prop('disabled', false).html('<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L6.707 6.707a1 1 0 01-1.414 0z" clip-rule="evenodd" /></svg> Subir y Registrar Test');
            }
        });
    });
    
    document.getElementById('dateEditForm').addEventListener('submit', function(event) {
        event.preventDefault(); 

        const procesoId = document.getElementById('modal-proceso-id').value;
        const dateType = document.getElementById('modal-date-type').value;
        const newDate = document.getElementById('new_date').value;
        
        const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value; 

        const url = `/api/proceso/${procesoId}/actualizar_fecha/`; 

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ 
                date_type: dateType, 
                new_date: newDate 
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { 
                    throw new Error(err.error || 'Error desconocido al procesar la solicitud.'); 
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                closeDateEditModal();
                alert('✅ Fecha actualizada con éxito: ' + data.message);
                window.location.reload(); 
            } else {
                alert('⚠️ Error de proceso: ' + (data.error || 'Hubo un problema.'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('❌ Error al guardar la fecha: ' + error.message);
        });
    });
});
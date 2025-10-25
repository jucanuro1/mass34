tailwind.config = {
    theme: {
        extend: {
            colors: {
                // Definiciones personalizadas
                'pink-700': '#ce0d17ff',
                'pink-800': '#d31c1cff',
                'pink-50': '#FFF0F7',
                'blue-600': '#3b82f6',
                'pink-300': '#F9B7E3'
            },
            fontFamily: {
                // Definición de fuente Inter
                sans: ['Inter', 'sans-serif'],
            },
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const radioOtro = document.querySelector('input[name="conforme_beneficios"][value="OTRO"]');
    const inputOtro = document.querySelector('input[name="detalle_beneficios_otro"]');

    if (radioOtro && inputOtro) {
        const toggleOtroInput = () => {
            if (radioOtro.checked) {
                inputOtro.disabled = false;
                inputOtro.focus();
            } else {
                inputOtro.disabled = true;
                inputOtro.value = ''; 
            }
        };

        document.querySelectorAll('input[name="conforme_beneficios"]').forEach(radio => {
            radio.addEventListener('change', toggleOtroInput);
        });
        toggleOtroInput(); 
    }
});
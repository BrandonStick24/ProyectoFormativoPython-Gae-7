// static/js_Vendedor/Layout_V.js

document.addEventListener('DOMContentLoaded', function() {
    // ==================== MANEJO DE MENÚS DESPLEGABLES ====================
    
    // Alternar menú desplegable del usuario
    const botonDesplegableUsuario = document.getElementById('botonDesplegableUsuario');
    const menuDesplegableUsuario = document.getElementById('menuDesplegableUsuario');

    if (botonDesplegableUsuario) {
        botonDesplegableUsuario.addEventListener('click', function(e) {
            e.stopPropagation();
            menuDesplegableUsuario.classList.toggle('mostrar');
        });
    }

    // Cerrar menú desplegable al hacer clic fuera
    document.addEventListener('click', function() {
        if (menuDesplegableUsuario) {
            menuDesplegableUsuario.classList.remove('mostrar');
        }
    });

    // ==================== ESTADO DEL NEGOCIO ====================
    
    // Alternar estado del negocio en la barra lateral
    const alternadorNegocio = document.getElementById('alternadorNegocio');
    const textoEstado = document.getElementById('textoEstado');
    
    let estadoNegocio = false; // false = Cerrado, true = Abierto

    if (alternadorNegocio && textoEstado) {
        alternadorNegocio.addEventListener('click', function() {
            estadoNegocio = !estadoNegocio;
            this.classList.toggle('activo');
            
            if (estadoNegocio) {
                textoEstado.textContent = 'Abierto';
                textoEstado.style.color = '#10b981';
                console.log('Negocio: ABIERTO');
                // Aquí puedes agregar lógica para actualizar el estado en el backend
            } else {
                textoEstado.textContent = 'Cerrado';
                textoEstado.style.color = '#6b7280';
                console.log('Negocio: CERRADO');
                // Aquí puedes agregar lógica para actualizar el estado en el backend
            }
        });
    }

    // ==================== MANEJO DE MODALES ====================
    
    // Modal de Programar Horario
    const botonProgramarHorario = document.getElementById('botonProgramarHorario');
    const modalProgramacion = document.getElementById('modalProgramacion');
    
    if (botonProgramarHorario && modalProgramacion) {
        botonProgramarHorario.addEventListener('click', function() {
            const modal = new bootstrap.Modal(modalProgramacion);
            modal.show();
        });
    }

    // Guardar programación de horario
    const guardarProgramacion = document.getElementById('guardarProgramacion');
    if (guardarProgramacion) {
        guardarProgramacion.addEventListener('click', function() {
            const horarioApertura = document.getElementById('horarioApertura').value;
            const horarioCierre = document.getElementById('horarioCierre').value;
            const habilitarProgramacion = document.getElementById('habilitarProgramacion').checked;

            if (!horarioApertura || !horarioCierre) {
                alert('Por favor, complete ambos horarios.');
                return;
            }

            // Aquí iría la lógica para guardar en el backend
            console.log('Programación guardada:', {
                apertura: horarioApertura,
                cierre: horarioCierre,
                automatica: habilitarProgramacion
            });

            // Cerrar modal
            const modal = bootstrap.Modal.getInstance(modalProgramacion);
            modal.hide();
            
            alert('Horario programado correctamente.');
        });
    }

    // Modal de Reportar Problema
    const botonReportarProblema = document.getElementById('botonReportarProblema');
    const modalReportarProblema = document.getElementById('modalReportarProblema');
    
    if (botonReportarProblema && modalReportarProblema) {
        botonReportarProblema.addEventListener('click', function() {
            const modal = new bootstrap.Modal(modalReportarProblema);
            modal.show();
        });
    }

    // Enviar reporte de problema
    const enviarReporte = document.getElementById('enviarReporte');
    if (enviarReporte) {
        enviarReporte.addEventListener('click', function() {
            const categoria = document.getElementById('categoriaProblema').value;
            const descripcion = document.getElementById('descripcionProblema').value;

            if (!categoria || !descripcion) {
                alert('Por favor, complete todos los campos.');
                return;
            }

            // Aquí iría la lógica para enviar al backend
            console.log('Reporte enviado:', {
                categoria: categoria,
                descripcion: descripcion
            });

            // Cerrar modal
            const modal = bootstrap.Modal.getInstance(modalReportarProblema);
            modal.hide();
            
            alert('Reporte enviado correctamente. Nos pondremos en contacto pronto.');
            
            // Limpiar formulario
            document.getElementById('formReportarProblema').reset();
        });
    }

    // ==================== NOTIFICACIONES ====================
    
    // Simular notificaciones
    const insigniaNotificacion = document.querySelector('.insignia-notificacion');
    const botonNotificaciones = document.getElementById('botonDesplegableNotificaciones');
    
    if (botonNotificaciones && insigniaNotificacion) {
        botonNotificaciones.addEventListener('click', function() {
            // Simular leer notificaciones
            setTimeout(function() {
                insigniaNotificacion.style.display = 'none';
                console.log('Notificaciones leídas');
            }, 1000);
        });
    }

    // ==================== INICIALIZACIÓN ====================
    
    // Inicializar estado del negocio desde el backend (simulado)
    function inicializarEstadoNegocio() {
        // Aquí iría una llamada al backend para obtener el estado actual
        // Por ahora simulamos que está cerrado
        estadoNegocio = false;
        if (textoEstado) {
            textoEstado.textContent = 'Cerrado';
            textoEstado.style.color = '#6b7280';
        }
        if (alternadorNegocio) {
            alternadorNegocio.classList.remove('activo');
        }
    }

    inicializarEstadoNegocio();
});
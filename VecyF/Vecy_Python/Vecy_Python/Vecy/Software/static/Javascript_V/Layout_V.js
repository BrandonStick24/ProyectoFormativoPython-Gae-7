// Layout_V.js - Versión Mejorada con Responsividad

document.addEventListener('DOMContentLoaded', function() {
    console.log('Layout VECY inicializado');

    // ==================== ELEMENTOS DEL DOM ====================
    const elementos = {
        // Header
        botonDesplegableUsuario: document.getElementById('botonDesplegableUsuario'),
        menuDesplegableUsuario: document.getElementById('menuDesplegableUsuario'),
        botonNotificaciones: document.getElementById('botonDesplegableNotificaciones'),
        insigniaNotificacion: document.querySelector('.insignia-notificacion'),
        
        // Sidebar
        barrLateral: document.querySelector('.barra-lateral'),
        alternadorNegocio: document.getElementById('alternadorNegocio'),
        textoEstado: document.getElementById('textoEstado'),
        botonProgramarHorario: document.getElementById('botonProgramarHorario'),
        botonReportarProblema: document.getElementById('botonReportarProblema'),
        itemsBarraLateral: document.querySelectorAll('.item-barra-lateral'),
        
        // Modales
        modalProgramacion: document.getElementById('modalProgramacion'),
        modalReportarProblema: document.getElementById('modalReportarProblema'),
        guardarProgramacion: document.getElementById('guardarProgramacion'),
        enviarReporte: document.getElementById('enviarReporte')
    };

    // ==================== ESTADO DE LA APLICACIÓN ====================
    let estadoApp = {
        negocioAbierto: false,
        menuMovilAbierto: false,
        notificacionesLeidas: false
    };

    // ==================== FUNCIONES DE UTILIDAD ====================
    
    /**
     * Muestra un mensaje toast (temporal)
     */
    function mostrarToast(mensaje, tipo = 'info') {
        // Si Bootstrap toast está disponible, úsalo
        // Sino, usa alert simple (puedes mejorar esto con una librería de toasts)
        console.log(`[${tipo.toUpperCase()}]: ${mensaje}`);
        
        // Crear elemento toast personalizado
        const toast = document.createElement('div');
        toast.className = `toast-custom toast-${tipo}`;
        toast.textContent = mensaje;
        toast.style.cssText = `
            position: fixed;
            top: 90px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${tipo === 'success' ? '#10b981' : tipo === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            border-radius: 0.5rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            z-index: 9999;
            animation: slideIn 0.3s ease-out;
            font-weight: 600;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    /**
     * Cierra todos los menús desplegables abiertos
     */
    function cerrarMenusDesplegables() {
        if (elementos.menuDesplegableUsuario) {
            elementos.menuDesplegableUsuario.classList.remove('mostrar');
        }
    }

    /**
     * Actualiza la URL activa en la barra lateral
     */
    function actualizarItemActivo() {
        const rutaActual = window.location.pathname;
        elementos.itemsBarraLateral.forEach(item => {
            if (item.getAttribute('href') === rutaActual) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }

    // ==================== MENÚ DE USUARIO ====================
    
    if (elementos.botonDesplegableUsuario && elementos.menuDesplegableUsuario) {
        elementos.botonDesplegableUsuario.addEventListener('click', function(e) {
            e.stopPropagation();
            elementos.menuDesplegableUsuario.classList.toggle('mostrar');
        });
    }

    // Cerrar menú al hacer clic fuera
    document.addEventListener('click', function(e) {
        if (elementos.menuDesplegableUsuario && 
            !elementos.menuDesplegableUsuario.contains(e.target) &&
            !elementos.botonDesplegableUsuario.contains(e.target)) {
            cerrarMenusDesplegables();
        }
    });

    // ==================== NOTIFICACIONES ====================
    
    if (elementos.botonNotificaciones && elementos.insigniaNotificacion) {
        elementos.botonNotificaciones.addEventListener('click', function(e) {
            e.stopPropagation();
            
            if (!estadoApp.notificacionesLeidas) {
                // Simular lectura de notificaciones
                setTimeout(() => {
                    elementos.insigniaNotificacion.style.display = 'none';
                    estadoApp.notificacionesLeidas = true;
                    mostrarToast('Notificaciones leídas', 'info');
                }, 500);
            }
            
            // Aquí puedes agregar lógica para mostrar panel de notificaciones
            console.log('Mostrando notificaciones...');
        });
    }

    // ==================== ESTADO DEL NEGOCIO ====================
    
    if (elementos.alternadorNegocio && elementos.textoEstado) {
        elementos.alternadorNegocio.addEventListener('click', async function() {
            // Toggle estado
            estadoApp.negocioAbierto = !estadoApp.negocioAbierto;
            
            // Actualizar UI
            this.classList.toggle('activo');
            
            if (estadoApp.negocioAbierto) {
                elementos.textoEstado.textContent = 'Abierto';
                elementos.textoEstado.style.color = 'var(--success)';
                mostrarToast('Negocio abierto al público', 'success');
            } else {
                elementos.textoEstado.textContent = 'Cerrado';
                elementos.textoEstado.style.color = 'var(--gray-500)';
                mostrarToast('Negocio cerrado temporalmente', 'info');
            }
            
            // Aquí deberías hacer una petición al backend para actualizar el estado
            try {
                // Ejemplo de petición (descomentar cuando tengas el endpoint)
                /*
                const response = await fetch('/api/negocio/estado/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        abierto: estadoApp.negocioAbierto
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Error al actualizar estado');
                }
                */
                
                console.log('Estado del negocio:', estadoApp.negocioAbierto ? 'ABIERTO' : 'CERRADO');
            } catch (error) {
                console.error('Error al actualizar estado:', error);
                mostrarToast('Error al actualizar el estado', 'error');
                
                // Revertir cambio en UI
                estadoApp.negocioAbierto = !estadoApp.negocioAbierto;
                this.classList.toggle('activo');
            }
        });
    }

    // ==================== MODAL DE PROGRAMACIÓN ====================
    
    if (elementos.botonProgramarHorario && elementos.modalProgramacion) {
        elementos.botonProgramarHorario.addEventListener('click', function() {
            const modal = new bootstrap.Modal(elementos.modalProgramacion);
            modal.show();
        });
    }

    if (elementos.guardarProgramacion) {
        elementos.guardarProgramacion.addEventListener('click', async function() {
            const horarioApertura = document.getElementById('horarioApertura')?.value;
            const horarioCierre = document.getElementById('horarioCierre')?.value;
            const habilitarProgramacion = document.getElementById('habilitarProgramacion')?.checked;

            // Validación
            if (!horarioApertura || !horarioCierre) {
                mostrarToast('Por favor, complete ambos horarios', 'error');
                return;
            }

            // Validar que el horario de cierre sea después del de apertura
            if (horarioApertura >= horarioCierre) {
                mostrarToast('El horario de cierre debe ser posterior al de apertura', 'error');
                return;
            }

            try {
                // Aquí iría la petición al backend
                /*
                const response = await fetch('/api/negocio/horario/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        apertura: horarioApertura,
                        cierre: horarioCierre,
                        automatico: habilitarProgramacion
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Error al guardar horario');
                }
                */

                console.log('Horario programado:', {
                    apertura: horarioApertura,
                    cierre: horarioCierre,
                    automatico: habilitarProgramacion
                });

                // Cerrar modal
                const modal = bootstrap.Modal.getInstance(elementos.modalProgramacion);
                modal.hide();
                
                mostrarToast('Horario programado correctamente', 'success');
                
                // Limpiar formulario
                document.getElementById('formProgramacion')?.reset();
            } catch (error) {
                console.error('Error al guardar horario:', error);
                mostrarToast('Error al guardar el horario', 'error');
            }
        });
    }

    // ==================== MODAL DE REPORTAR PROBLEMA ====================
    
    if (elementos.botonReportarProblema && elementos.modalReportarProblema) {
        elementos.botonReportarProblema.addEventListener('click', function() {
            const modal = new bootstrap.Modal(elementos.modalReportarProblema);
            modal.show();
        });
    }

    if (elementos.enviarReporte) {
        elementos.enviarReporte.addEventListener('click', async function() {
            const categoria = document.getElementById('categoriaProblema')?.value;
            const descripcion = document.getElementById('descripcionProblema')?.value;

            // Validación
            if (!categoria || !descripcion.trim()) {
                mostrarToast('Por favor, complete todos los campos', 'error');
                return;
            }

            if (descripcion.trim().length < 10) {
                mostrarToast('La descripción debe tener al menos 10 caracteres', 'error');
                return;
            }

            try {
                // Aquí iría la petición al backend
                /*
                const response = await fetch('/api/soporte/reporte/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        categoria: categoria,
                        descripcion: descripcion
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Error al enviar reporte');
                }
                */

                console.log('Reporte enviado:', {
                    categoria: categoria,
                    descripcion: descripcion,
                    fecha: new Date().toISOString()
                });

                // Cerrar modal
                const modal = bootstrap.Modal.getInstance(elementos.modalReportarProblema);
                modal.hide();
                
                mostrarToast('Reporte enviado. Nos pondremos en contacto pronto', 'success');
                
                // Limpiar formulario
                document.getElementById('formReportarProblema')?.reset();
            } catch (error) {
                console.error('Error al enviar reporte:', error);
                mostrarToast('Error al enviar el reporte', 'error');
            }
        });
    }

    // ==================== MENÚ MÓVIL ====================
    
    function crearBotonMenuMovil() {
        if (window.innerWidth <= 992 && !document.getElementById('botonMenuMovil')) {
            const boton = document.createElement('button');
            boton.id = 'botonMenuMovil';
            boton.className = 'boton-menu-movil';
            boton.innerHTML = '<i class="fas fa-bars"></i>';
            boton.style.cssText = `
                display: flex;
                margin-right: 1rem;
            `;
            
            const encabezadoIzquierda = document.querySelector('.encabezado-izquierda');
            if (encabezadoIzquierda) {
                encabezadoIzquierda.insertBefore(boton, encabezadoIzquierda.firstChild);
                
                boton.addEventListener('click', function() {
                    estadoApp.menuMovilAbierto = !estadoApp.menuMovilAbierto;
                    elementos.barrLateral?.classList.toggle('mostrar');
                    this.innerHTML = estadoApp.menuMovilAbierto ? 
                        '<i class="fas fa-times"></i>' : 
                        '<i class="fas fa-bars"></i>';
                });
            }
        }
    }

    // Cerrar sidebar móvil al hacer clic en un enlace
    elementos.itemsBarraLateral.forEach(item => {
        item.addEventListener('click', function() {
            if (window.innerWidth <= 992) {
                elementos.barrLateral?.classList.remove('mostrar');
                estadoApp.menuMovilAbierto = false;
                const botonMenu = document.getElementById('botonMenuMovil');
                if (botonMenu) {
                    botonMenu.innerHTML = '<i class="fas fa-bars"></i>';
                }
            }
        });
    });

    // Cerrar sidebar móvil al hacer clic fuera
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 992 && 
            estadoApp.menuMovilAbierto &&
            elementos.barrLateral &&
            !elementos.barrLateral.contains(e.target) &&
            !e.target.closest('#botonMenuMovil')) {
            
            elementos.barrLateral.classList.remove('mostrar');
            estadoApp.menuMovilAbierto = false;
            const botonMenu = document.getElementById('botonMenuMovil');
            if (botonMenu) {
                botonMenu.innerHTML = '<i class="fas fa-bars"></i>';
            }
        }
    });

    // ==================== UTILIDAD: OBTENER CSRF TOKEN ====================
    
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

    // ==================== INICIALIZACIÓN ====================
    
    function inicializar() {
        console.log('Inicializando layout...');
        
        // Actualizar item activo en sidebar
        actualizarItemActivo();
        
        // Crear botón de menú móvil si es necesario
        crearBotonMenuMovil();
        
        // Cargar estado del negocio desde el backend (simulado)
        cargarEstadoNegocio();
        
        console.log('Layout inicializado correctamente');
    }

    async function cargarEstadoNegocio() {
        try {
            // Aquí iría una petición al backend
            /*
            const response = await fetch('/api/negocio/estado/');
            const data = await response.json();
            estadoApp.negocioAbierto = data.abierto;
            */
            
            // Simulación: el negocio está cerrado por defecto
            estadoApp.negocioAbierto = false;
            
            if (elementos.textoEstado && elementos.alternadorNegocio) {
                elementos.textoEstado.textContent = estadoApp.negocioAbierto ? 'Abierto' : 'Cerrado';
                elementos.textoEstado.style.color = estadoApp.negocioAbierto ? 
                    'var(--success)' : 'var(--gray-500)';
                
                if (estadoApp.negocioAbierto) {
                    elementos.alternadorNegocio.classList.add('activo');
                } else {
                    elementos.alternadorNegocio.classList.remove('activo');
                }
            }
        } catch (error) {
            console.error('Error al cargar estado del negocio:', error);
        }
    }

    // ==================== EVENT LISTENERS GLOBALES ====================
    
    // Detectar cambios de tamaño de ventana
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            crearBotonMenuMovil();
            
            // Si la ventana se hace más grande, cerrar el menú móvil
            if (window.innerWidth > 992 && estadoApp.menuMovilAbierto) {
                elementos.barrLateral?.classList.remove('mostrar');
                estadoApp.menuMovilAbierto = false;
            }
        }, 250);
    });

    // Animación de carga de página
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.3s ease';
        document.body.style.opacity = '1';
    }, 100);

    // ==================== EJECUTAR INICIALIZACIÓN ====================
    inicializar();
});

// Agregar estilos CSS para las animaciones del toast
if (!document.getElementById('toast-styles')) {
    const style = document.createElement('style');
    style.id = 'toast-styles';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}
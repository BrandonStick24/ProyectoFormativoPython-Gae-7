// static/vendedor/js/Layout_V.js 

document.addEventListener('DOMContentLoaded', function() {
    console.log('Layout VECY inicializado - CON GESTIÓN COMPLETA DE HORARIOS CORREGIDA');

    // ==================== ELEMENTOS DEL DOM ====================
    const elementos = {
        alternadorNegocio: document.getElementById('alternadorNegocio'),
        textoEstado: document.getElementById('textoEstado'),
        botonProgramarHorario: document.getElementById('botonProgramarHorario'),
        modalProgramacion: document.getElementById('modalProgramacion'),
        guardarProgramacion: document.getElementById('guardarProgramacion'),
        horarioApertura: document.getElementById('horarioApertura'),
        horarioCierre: document.getElementById('horarioCierre'),
        habilitarProgramacion: document.getElementById('habilitarProgramacion'),
        btnProgramarCierre: document.getElementById('btnProgramarCierre'),
        btnProgramarApertura: document.getElementById('btnProgramarApertura'),
        // NUEVOS ELEMENTOS AGREGADOS
        botonDesplegableUsuario: document.getElementById('botonDesplegableUsuario'),
        menuDesplegableUsuario: document.getElementById('menuDesplegableUsuario'),
        botonDesplegableNotificaciones: document.getElementById('botonDesplegableNotificaciones'),
        botonReportarProblema: document.getElementById('botonReportarProblema')
    };

    // ==================== CONFIGURACIÓN Y ESTADO ====================
    let configuracionHorarios = {
        horarioApertura: '08:00',
        horarioCierre: '18:00',
        programacionAutomatica: false,
        estadoActual: 'cerrado',
        programaciones: [] // Array para programaciones específicas
    };

    // ==================== FUNCIONES PRINCIPALES ====================

    function cargarConfiguracion() {
        const guardado = localStorage.getItem('configuracionHorariosNegocio');
        if (guardado) {
            try {
                const configCargada = JSON.parse(guardado);
                configuracionHorarios = {
                    ...configuracionHorarios,
                    ...configCargada,
                    // Asegurar que las programaciones pendientes se mantengan
                    programaciones: configCargada.programaciones || []
                };
                console.log('Configuración cargada:', configuracionHorarios);
            } catch (e) {
                console.error('Error al cargar configuración:', e);
                configuracionHorarios = {
                    horarioApertura: '08:00',
                    horarioCierre: '18:00',
                    programacionAutomatica: false,
                    estadoActual: 'cerrado',
                    programaciones: []
                };
            }
        }
        actualizarUIEstadoNegocio();
        iniciarVerificadorAutomatico();
    }

    function guardarConfiguracion() {
        localStorage.setItem('configuracionHorariosNegocio', JSON.stringify(configuracionHorarios));
        console.log('Configuración guardada:', configuracionHorarios);
    }

    function actualizarUIEstadoNegocio() {
        if (elementos.textoEstado && elementos.alternadorNegocio) {
            const estaAbierto = configuracionHorarios.estadoActual === 'abierto';
            
            elementos.textoEstado.textContent = estaAbierto ? 'Abierto' : 'Cerrado';
            elementos.textoEstado.className = estaAbierto ? 'estado-abierto' : 'estado-cerrado';
            
            // Actualizar correctamente la clase del interruptor
            if (estaAbierto) {
                elementos.alternadorNegocio.classList.add('activo');
            } else {
                elementos.alternadorNegocio.classList.remove('activo');
            }
            
            console.log('UI actualizada - Estado:', configuracionHorarios.estadoActual, 'Clase activo:', elementos.alternadorNegocio.classList.contains('activo'));
        }
    }

    function cambiarEstadoNegocio(nuevoEstado, motivo = 'manual') {
        const estadoAnterior = configuracionHorarios.estadoActual;
        configuracionHorarios.estadoActual = nuevoEstado ? 'abierto' : 'cerrado';
        
        guardarConfiguracion();
        actualizarUIEstadoNegocio();
        
        // Registrar en historial
        registrarEnHistorial(nuevoEstado ? 'abierto' : 'cerrado', motivo);
        
        const mensaje = nuevoEstado ? 
            '✅ Negocio abierto al público' : 
            '🔒 Negocio cerrado temporalmente';
        mostrarToast(mensaje, 'success');
        
        console.log(`Estado cambiado: ${estadoAnterior} → ${configuracionHorarios.estadoActual} (${motivo})`);
    }

    function registrarEnHistorial(estado, tipo) {
        const historial = JSON.parse(localStorage.getItem('historialEstados') || '[]');
        historial.unshift({
            estado: estado,
            tipo: tipo,
            fecha: obtenerHoraBogota(),
            timestamp: Date.now()
        });
        
        // Mantener solo los últimos 50 registros
        if (historial.length > 50) {
            historial.length = 50;
        }
        
        localStorage.setItem('historialEstados', JSON.stringify(historial));
    }

    // ==================== HORA DE BOGOTÁ ====================

    function obtenerHoraBogota() {
        const ahora = new Date();
        const offsetBogota = -5 * 60;
        const offsetLocal = ahora.getTimezoneOffset();
        const diferencia = offsetBogota - offsetLocal;
        
        const horaBogota = new Date(ahora.getTime() + diferencia * 60000);
        return horaBogota.toLocaleString('es-CO', {
            timeZone: 'America/Bogota',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    function obtenerHoraActualBogota() {
        const ahora = new Date();
        const offsetBogota = -5 * 60;
        const offsetLocal = ahora.getTimezoneOffset();
        const diferencia = offsetBogota - offsetLocal;
        
        return new Date(ahora.getTime() + diferencia * 60000);
    }

    function obtenerHoraStringBogota() {
        const horaBogota = obtenerHoraActualBogota();
        return horaBogota.toTimeString().slice(0, 5);
    }

    function convertirHoraAMinutos(horaString) {
        const [horas, minutos] = horaString.split(':').map(Number);
        return horas * 60 + minutos;
    }

    // ==================== PROGRAMACIÓN AUTOMÁTICA CORREGIDA ====================

    function verificarEstadoAutomatico() {
        console.log('=== INICIANDO VERIFICACIÓN AUTOMÁTICA ===');
        
        // Primero verificar programaciones específicas
        const cambiosProgramaciones = verificarProgramacionesEspecificas();
        
        // Si no hubo cambios por programaciones específicas, verificar horario automático
        if (!cambiosProgramaciones && configuracionHorarios.programacionAutomatica) {
            verificarHorarioAutomatico();
        }
        
        console.log('=== VERIFICACIÓN AUTOMÁTICA COMPLETADA ===');
    }

    function verificarHorarioAutomatico() {
        const horaActual = obtenerHoraStringBogota();
        const horarioApertura = configuracionHorarios.horarioApertura;
        const horarioCierre = configuracionHorarios.horarioCierre;
        
        const minutosActual = convertirHoraAMinutos(horaActual);
        const minutosApertura = convertirHoraAMinutos(horarioApertura);
        const minutosCierre = convertirHoraAMinutos(horarioCierre);
        
        const deberiaEstarAbierto = minutosActual >= minutosApertura && minutosActual < minutosCierre;
        const estaAbierto = configuracionHorarios.estadoActual === 'abierto';
        
        console.log(`Verificación horario automático - Hora: ${horaActual}, Apertura: ${horarioApertura}, Cierre: ${horarioCierre}`);
        console.log(`Debería estar abierto: ${deberiaEstarAbierto}, Está abierto: ${estaAbierto}`);
        
        if (deberiaEstarAbierto !== estaAbierto) {
            console.log(`Cambio automático necesario: ${estaAbierto ? 'Cerrando' : 'Abriendo'}`);
            cambiarEstadoNegocio(deberiaEstarAbierto, 'automatico');
            return true;
        }
        return false;
    }

    function verificarProgramacionesEspecificas() {
        const ahora = obtenerHoraActualBogota();
        const timestampActual = ahora.getTime();
        
        let cambiosRealizados = false;
        const programacionesAEliminar = [];
        
        console.log('Verificando programaciones específicas...');
        
        configuracionHorarios.programaciones.forEach((programacion, index) => {
            if (programacion.timestamp <= timestampActual && programacion.estado === 'pendiente') {
                console.log(`⏰ Ejecutando programación: ${programacion.tipo} programado para ${new Date(programacion.timestamp).toLocaleString('es-CO')}`);
                
                // Ejecutar la programación
                cambiarEstadoNegocio(programacion.tipo === 'apertura', 'programado');
                cambiosRealizados = true;
                
                // Marcar como completada
                programacion.estado = 'completada';
                
                // Si es solo para hoy, programar eliminación
                if (programacion.soloHoy) {
                    programacionesAEliminar.push(programacion.id);
                }
            }
        });
        
        // Eliminar programaciones de "solo hoy" que ya se ejecutaron
        if (programacionesAEliminar.length > 0) {
            configuracionHorarios.programaciones = configuracionHorarios.programaciones.filter(
                p => !programacionesAEliminar.includes(p.id)
            );
        }
        
        if (cambiosRealizados) {
            guardarConfiguracion();
            actualizarListaProgramaciones();
        }
        
        return cambiosRealizados;
    }

    function programarAperturaCierre(tipo, fechaHora, soloHoy = true) {
        const timestamp = fechaHora.getTime();
        const ahora = Date.now();
        
        // Validar que la programación sea en el futuro
        if (timestamp <= ahora) {
            mostrarToast('❌ La hora programada debe ser en el futuro', 'error');
            return null;
        }

        const programacion = {
            id: Date.now() + Math.random(),
            tipo: tipo,
            timestamp: timestamp,
            fechaHora: fechaHora.toLocaleString('es-CO', {
                timeZone: 'America/Bogota',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }),
            soloHoy: soloHoy,
            estado: 'pendiente'
        };
        
        configuracionHorarios.programaciones.push(programacion);
        guardarConfiguracion();
        
        const mensaje = tipo === 'apertura' ? 
            `✅ Apertura programada para ${programacion.fechaHora}` :
            `✅ Cierre programado para ${programacion.fechaHora}`;
            
        mostrarToast(mensaje, 'success');
        
        console.log('Programación agregada:', programacion);
        actualizarListaProgramaciones();
        return programacion.id;
    }

    function programarCierreEnMinutos(minutos) {
        const fechaProgramada = new Date();
        fechaProgramada.setMinutes(fechaProgramada.getMinutes() + minutos);
        
        const idProgramacion = programarAperturaCierre('cierre', fechaProgramada, true);
        
        if (idProgramacion) {
            mostrarToast(`🔒 Cierre programado en ${minutos} minutos`, 'info');
        }
        
        return idProgramacion;
    }

    function programarAperturaEnMinutos(minutos) {
        const fechaProgramada = new Date();
        fechaProgramada.setMinutes(fechaProgramada.getMinutes() + minutos);
        
        const idProgramacion = programarAperturaCierre('apertura', fechaProgramada, true);
        
        if (idProgramacion) {
            mostrarToast(`🟢 Apertura programada en ${minutos} minutos`, 'info');
        }
        
        return idProgramacion;
    }

    function obtenerProgramacionesPendientes() {
        const ahora = Date.now();
        return configuracionHorarios.programaciones.filter(p => 
            p.estado === 'pendiente' && p.timestamp > ahora
        );
    }

    function cancelarProgramacion(id) {
        const programacionIndex = configuracionHorarios.programaciones.findIndex(p => p.id === id);
        if (programacionIndex !== -1) {
            const programacion = configuracionHorarios.programaciones[programacionIndex];
            configuracionHorarios.programaciones.splice(programacionIndex, 1);
            guardarConfiguracion();
            mostrarToast(`❌ Programación de ${programacion.tipo} cancelada`, 'info');
            actualizarListaProgramaciones();
            return true;
        }
        return false;
    }

    // ==================== MODAL DE PROGRAMACIÓN MEJORADO ====================

    function inicializarModalProgramacion() {
        if (elementos.botonProgramarHorario && elementos.modalProgramacion) {
            elementos.botonProgramarHorario.addEventListener('click', function() {
                cargarConfiguracionEnModal();
                const modal = new bootstrap.Modal(elementos.modalProgramacion);
                modal.show();
            });
        }

        // Botones de programación rápida
        const btnCierre5Min = document.getElementById('btnCierre5Min');
        const btnCierre15Min = document.getElementById('btnCierre15Min');
        const btnApertura5Min = document.getElementById('btnApertura5Min');
        
        if (btnCierre5Min) {
            btnCierre5Min.addEventListener('click', () => programarCierreEnMinutos(5));
        }
        if (btnCierre15Min) {
            btnCierre15Min.addEventListener('click', () => programarCierreEnMinutos(15));
        }
        if (btnApertura5Min) {
            btnApertura5Min.addEventListener('click', () => programarAperturaEnMinutos(5));
        }

        // Botones de programación desde modal
        if (elementos.btnProgramarCierre) {
            elementos.btnProgramarCierre.addEventListener('click', function() {
                programarDesdeModal('cierre');
            });
        }
        
        if (elementos.btnProgramarApertura) {
            elementos.btnProgramarApertura.addEventListener('click', function() {
                programarDesdeModal('apertura');
            });
        }

        // Guardar configuración principal
        if (elementos.guardarProgramacion) {
            elementos.guardarProgramacion.addEventListener('click', function() {
                guardarConfiguracionDesdeModal();
            });
        }
    }

    function cargarConfiguracionEnModal() {
        if (elementos.horarioApertura) {
            elementos.horarioApertura.value = configuracionHorarios.horarioApertura;
        }
        if (elementos.horarioCierre) {
            elementos.horarioCierre.value = configuracionHorarios.horarioCierre;
        }
        if (elementos.habilitarProgramacion) {
            elementos.habilitarProgramacion.checked = configuracionHorarios.programacionAutomatica;
        }
        
        actualizarListaProgramaciones();
    }

    function programarDesdeModal(tipo) {
        const inputHora = document.getElementById('horaProgramacion');
        if (!inputHora || !inputHora.value) {
            mostrarToast('❌ Selecciona una hora para programar', 'error');
            return;
        }

        const ahora = obtenerHoraActualBogota();
        const [horas, minutos] = inputHora.value.split(':');
        const fechaProgramada = new Date(ahora);
        fechaProgramada.setHours(parseInt(horas), parseInt(minutos), 0, 0);

        // Si la hora ya pasó hoy, programar para mañana
        if (fechaProgramada <= ahora) {
            fechaProgramada.setDate(fechaProgramada.getDate() + 1);
            mostrarToast('⚠️ La hora ya pasó hoy, programando para mañana', 'info');
        }

        programarAperturaCierre(tipo, fechaProgramada, true);
        inputHora.value = '';
    }

    function guardarConfiguracionDesdeModal() {
        const horarioApertura = elementos.horarioApertura?.value;
        const horarioCierre = elementos.horarioCierre?.value;
        const habilitarProgramacion = elementos.habilitarProgramacion?.checked;

        if (!horarioApertura || !horarioCierre) {
            mostrarToast('❌ Completa ambos horarios', 'error');
            return;
        }

        const minutosApertura = convertirHoraAMinutos(horarioApertura);
        const minutosCierre = convertirHoraAMinutos(horarioCierre);
        
        if (minutosCierre <= minutosApertura) {
            mostrarToast('❌ El horario de cierre debe ser después del horario de apertura', 'error');
            return;
        }

        if (minutosApertura === minutosCierre) {
            mostrarToast('❌ Los horarios de apertura y cierre no pueden ser iguales', 'error');
            return;
        }

        configuracionHorarios.horarioApertura = horarioApertura;
        configuracionHorarios.horarioCierre = horarioCierre;
        configuracionHorarios.programacionAutomatica = habilitarProgramacion;
        
        guardarConfiguracion();
        
        const modal = bootstrap.Modal.getInstance(elementos.modalProgramacion);
        if (modal) {
            modal.hide();
        }
        
        mostrarToast('✅ Configuración de horarios guardada correctamente', 'success');
        
        // Verificar inmediatamente si hay que cambiar el estado
        setTimeout(verificarEstadoAutomatico, 1000);
    }

    function actualizarListaProgramaciones() {
        const lista = document.getElementById('listaProgramaciones');
        if (!lista) return;

        const programacionesPendientes = obtenerProgramacionesPendientes();
        
        if (programacionesPendientes.length === 0) {
            lista.innerHTML = '<div class="text-muted text-center py-3">No hay programaciones activas</div>';
            return;
        }

        lista.innerHTML = programacionesPendientes.map(programacion => {
            const fechaProgramada = new Date(programacion.timestamp);
            const ahora = new Date();
            const diferenciaMs = programacion.timestamp - ahora.getTime();
            const diferenciaMin = Math.max(0, Math.floor(diferenciaMs / 60000));
            
            return `
            <div class="programacion-item d-flex justify-content-between align-items-center p-3 border">
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center mb-1">
                        <strong class="${programacion.tipo === 'apertura' ? 'text-success' : 'text-warning'} me-2">
                            ${programacion.tipo === 'apertura' ? '🟢 Apertura' : '🔴 Cierre'}
                        </strong>
                        <small class="badge bg-secondary">en ${diferenciaMin} min</small>
                    </div>
                    <small class="text-muted d-block">${programacion.fechaHora}</small>
                    ${programacion.soloHoy ? '<small class="text-info">⏰ Solo hoy</small>' : ''}
                </div>
                <button class="btn btn-sm btn-outline-danger ms-2" onclick="window.cancelarProgramacion(${programacion.id})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            `;
        }).join('');
    }

    // ==================== FUNCIONES DE UTILIDAD ====================

    function mostrarToast(mensaje, tipo = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast-custom toast-${tipo}`;
        toast.textContent = mensaje;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 4000);
    }

    function iniciarVerificadorAutomatico() {
        // Verificar cada 30 segundos
        setInterval(verificarEstadoAutomatico, 30000);
        
        // Verificar inmediatamente al cargar
        setTimeout(verificarEstadoAutomatico, 2000);
        
        console.log('✅ Verificador automático iniciado - Hora Bogotá:', obtenerHoraStringBogota());
    }

    // ==================== FUNCIONALIDADES DEL HEADER ====================

    function inicializarHeader() {
        // Menú desplegable del usuario
        if (elementos.botonDesplegableUsuario && elementos.menuDesplegableUsuario) {
            elementos.botonDesplegableUsuario.addEventListener('click', function(e) {
                e.stopPropagation();
                elementos.menuDesplegableUsuario.classList.toggle('mostrar');
            });

            // Cerrar menú al hacer clic fuera
            document.addEventListener('click', function(e) {
                if (!elementos.botonDesplegableUsuario.contains(e.target) && 
                    !elementos.menuDesplegableUsuario.contains(e.target)) {
                    elementos.menuDesplegableUsuario.classList.remove('mostrar');
                }
            });

            // Prevenir que el clic dentro del menú lo cierre
            elementos.menuDesplegableUsuario.addEventListener('click', function(e) {
                e.stopPropagation();
            });
        }

        // Botón de notificaciones
        if (elementos.botonDesplegableNotificaciones) {
            elementos.botonDesplegableNotificaciones.addEventListener('click', function() {
                mostrarToast('🔔 No hay nuevas notificaciones', 'info');
            });
        }

        // Botón reportar problema
        if (elementos.botonReportarProblema) {
            elementos.botonReportarProblema.addEventListener('click', function() {
                const modalReportar = new bootstrap.Modal(document.getElementById('modalReportarProblema'));
                modalReportar.show();
            });
        }

        // Inicializar envío de reporte
        const enviarReporte = document.getElementById('enviarReporte');
        if (enviarReporte) {
            enviarReporte.addEventListener('click', function() {
                const categoria = document.getElementById('categoriaProblema').value;
                const descripcion = document.getElementById('descripcionProblema').value;
                
                if (!categoria || !descripcion) {
                    mostrarToast('❌ Completa todos los campos del reporte', 'error');
                    return;
                }
                
                // Simular envío de reporte
                mostrarToast('✅ Reporte enviado correctamente. Te contactaremos pronto.', 'success');
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalReportarProblema'));
                modal.hide();
                
                // Limpiar formulario
                document.getElementById('categoriaProblema').value = '';
                document.getElementById('descripcionProblema').value = '';
            });
        }
    }

    // ==================== EVENT LISTENERS PRINCIPALES ====================

    if (elementos.alternadorNegocio) {
        elementos.alternadorNegocio.addEventListener('click', function() {
            const nuevoEstado = configuracionHorarios.estadoActual !== 'abierto';
            cambiarEstadoNegocio(nuevoEstado, 'manual');
        });
    }

    // ==================== INICIALIZACIÓN ====================

    function inicializar() {
        console.log('🚀 Inicializando gestión de horarios...');
        console.log('🕐 Hora actual Bogotá:', obtenerHoraStringBogota());
        
        cargarConfiguracion();
        inicializarModalProgramacion();
        inicializarHeader(); // <-- NUEVA FUNCIÓN AGREGADA
        
        console.log('✅ Gestión de horarios inicializada correctamente');
        console.log('📊 Estado actual:', configuracionHorarios.estadoActual);
        console.log('📋 Programaciones pendientes:', obtenerProgramacionesPendientes().length);
    }

    // Hacer funciones globales para los event listeners
    window.cancelarProgramacion = cancelarProgramacion;
    window.programarCierreEnMinutos = programarCierreEnMinutos;
    window.programarAperturaEnMinutos = programarAperturaEnMinutos;

    // ==================== EJECUTAR INICIALIZACIÓN ====================
    inicializar();
});
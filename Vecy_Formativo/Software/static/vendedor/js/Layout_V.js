document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Layout VECY inicializado - SISTEMA COMPLETO CORREGIDO');

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
        btnApertura1Hora: document.getElementById('btnApertura1Hora'),
        btnApertura2Horas: document.getElementById('btnApertura2Horas'),
        btnCierre1Hora: document.getElementById('btnCierre1Hora'),
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
        programaciones: []
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
                    programaciones: configCargada.programaciones || []
                };
                console.log('✅ Configuración cargada:', configuracionHorarios);
            } catch (e) {
                console.error('❌ Error al cargar configuración:', e);
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
        console.log('💾 Configuración guardada:', configuracionHorarios);
    }

    function actualizarUIEstadoNegocio() {
        if (elementos.textoEstado && elementos.alternadorNegocio) {
            const estaAbierto = configuracionHorarios.estadoActual === 'abierto';
            
            // Actualizar texto
            elementos.textoEstado.textContent = estaAbierto ? 'Abierto' : 'Cerrado';
            
            // Actualizar clases CSS
            if (estaAbierto) {
                elementos.textoEstado.classList.add('estado-abierto');
                elementos.textoEstado.classList.remove('estado-cerrado');
                elementos.alternadorNegocio.classList.add('activo');
            } else {
                elementos.textoEstado.classList.add('estado-cerrado');
                elementos.textoEstado.classList.remove('estado-abierto');
                elementos.alternadorNegocio.classList.remove('activo');
            }
            
            console.log('🔄 UI actualizada - Estado:', configuracionHorarios.estadoActual);
        }
    }

    function cambiarEstadoNegocio(nuevoEstado, motivo = 'manual') {
        const estadoAnterior = configuracionHorarios.estadoActual;
        configuracionHorarios.estadoActual = nuevoEstado ? 'abierto' : 'cerrado';
        
        guardarConfiguracion();
        actualizarUIEstadoNegocio();
        
        registrarEnHistorial(nuevoEstado ? 'abierto' : 'cerrado', motivo);
        
        const mensaje = nuevoEstado ? 
            '✅ Negocio ABIERTO al público' : 
            '🔒 Negocio CERRADO temporalmente';
        mostrarToast(mensaje, 'success');
        
        console.log(`🔄 Estado cambiado: ${estadoAnterior} → ${configuracionHorarios.estadoActual} (${motivo})`);
    }

    function registrarEnHistorial(estado, tipo) {
        const historial = JSON.parse(localStorage.getItem('historialEstados') || '[]');
        historial.unshift({
            estado: estado,
            tipo: tipo,
            fecha: obtenerHoraBogota(),
            timestamp: Date.now()
        });
        
        if (historial.length > 50) {
            historial.length = 50;
        }
        
        localStorage.setItem('historialEstados', JSON.stringify(historial));
    }

    // ==================== HORA DE BOGOTÁ ====================

    function obtenerHoraBogota() {
        return new Date().toLocaleString('es-CO', {
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
        return new Date(new Date().toLocaleString('en-US', { timeZone: 'America/Bogota' }));
    }

    function obtenerHoraStringBogota() {
        const horaBogota = obtenerHoraActualBogota();
        return horaBogota.toTimeString().slice(0, 5);
    }

    function obtenerFechaHoraBogota() {
        return obtenerHoraActualBogota();
    }

    function convertirHoraAMinutos(horaString) {
        const [horas, minutos] = horaString.split(':').map(Number);
        return horas * 60 + minutos;
    }

    // ==================== SISTEMA DE VERIFICACIÓN AUTOMÁTICA ====================

    function verificarEstadoAutomatico() {
        console.log('⏰ INICIANDO VERIFICACIÓN AUTOMÁTICA - Hora:', obtenerHoraStringBogota());
        
        // Primero verificar programaciones específicas
        const cambiosProgramaciones = verificarProgramacionesEspecificas();
        
        // Si no hubo cambios por programaciones, verificar horario automático
        if (!cambiosProgramaciones && configuracionHorarios.programacionAutomatica) {
            verificarHorarioAutomatico();
        }
        
        console.log('✅ VERIFICACIÓN COMPLETADA - Estado actual:', configuracionHorarios.estadoActual);
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
        
        console.log(`📊 Verificación horario automático:`);
        console.log(`   - Hora actual: ${horaActual}`);
        console.log(`   - Apertura: ${horarioApertura}`);
        console.log(`   - Cierre: ${horarioCierre}`);
        console.log(`   - Debería estar abierto: ${deberiaEstarAbierto}`);
        console.log(`   - Está abierto: ${estaAbierto}`);
        
        if (deberiaEstarAbierto !== estaAbierto) {
            console.log(`🔄 Cambio automático necesario: ${estaAbierto ? 'Cerrando' : 'Abriendo'}`);
            cambiarEstadoNegocio(deberiaEstarAbierto, 'automatico');
            return true;
        }
        return false;
    }

    function verificarProgramacionesEspecificas() {
        const ahora = obtenerFechaHoraBogota();
        const timestampActual = ahora.getTime();
        
        let cambiosRealizados = false;
        const programacionesAEliminar = [];
        
        console.log('🔍 Verificando programaciones específicas...');
        console.log('   - Hora actual:', ahora.toLocaleString('es-CO'));
        console.log('   - Programaciones pendientes:', configuracionHorarios.programaciones.filter(p => p.estado === 'pendiente').length);
        
        configuracionHorarios.programaciones.forEach((programacion) => {
            if (programacion.estado === 'pendiente' && programacion.timestamp <= timestampActual) {
                console.log(`⏰ EJECUTANDO PROGRAMACIÓN: ${programacion.tipo} programado para ${new Date(programacion.timestamp).toLocaleString('es-CO')}`);
                
                // Ejecutar la programación
                cambiarEstadoNegocio(programacion.tipo === 'apertura', 'programado');
                cambiosRealizados = true;
                
                // Marcar como completada
                programacion.estado = 'completada';
                
                // Si es solo para hoy, marcar para eliminar
                if (programacion.soloHoy) {
                    programacionesAEliminar.push(programacion.id);
                }
            }
        });
        
        // Eliminar programaciones completadas de "solo hoy"
        if (programacionesAEliminar.length > 0) {
            configuracionHorarios.programaciones = configuracionHorarios.programaciones.filter(
                p => !programacionesAEliminar.includes(p.id)
            );
            console.log(`🗑️ Eliminadas ${programacionesAEliminar.length} programaciones completadas`);
        }
        
        if (cambiosRealizados) {
            guardarConfiguracion();
            actualizarListaProgramaciones();
        }
        
        return cambiosRealizados;
    }

    // ==================== SISTEMA DE PROGRAMACIÓN ====================

    function programarAperturaCierre(tipo, fechaHora, soloHoy = true) {
        const timestamp = fechaHora.getTime();
        const ahora = obtenerFechaHoraBogota().getTime();
        
        console.log(`📅 Intentando programar ${tipo}:`);
        console.log(`   - Fecha programada: ${fechaHora.toLocaleString('es-CO')}`);
        console.log(`   - Timestamp programado: ${timestamp}`);
        console.log(`   - Timestamp actual: ${ahora}`);
        
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
            `✅ APERTURA programada para ${programacion.fechaHora}` :
            `✅ CIERRE programado para ${programacion.fechaHora}`;
            
        mostrarToast(mensaje, 'success');
        
        console.log('📅 Programación agregada:', programacion);
        actualizarListaProgramaciones();
        return programacion.id;
    }

    function programarCierreEnHoras(horas) {
        const fechaProgramada = new Date(obtenerFechaHoraBogota());
        fechaProgramada.setHours(fechaProgramada.getHours() + horas);
        
        const idProgramacion = programarAperturaCierre('cierre', fechaProgramada, true);
        
        if (idProgramacion) {
            mostrarToast(`🔒 Cierre programado en ${horas} hora(s)`, 'info');
        }
        
        return idProgramacion;
    }

    function programarAperturaEnHoras(horas) {
        const fechaProgramada = new Date(obtenerFechaHoraBogota());
        fechaProgramada.setHours(fechaProgramada.getHours() + horas);
        
        const idProgramacion = programarAperturaCierre('apertura', fechaProgramada, true);
        
        if (idProgramacion) {
            mostrarToast(`🟢 Apertura programada en ${horas} hora(s)`, 'info');
        }
        
        return idProgramacion;
    }

    function obtenerProgramacionesPendientes() {
        const ahora = obtenerFechaHoraBogota().getTime();
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

    // ==================== MODAL DE PROGRAMACIÓN ====================

    function inicializarModalProgramacion() {
        if (elementos.botonProgramarHorario && elementos.modalProgramacion) {
            elementos.botonProgramarHorario.addEventListener('click', function() {
                cargarConfiguracionEnModal();
                const modal = new bootstrap.Modal(elementos.modalProgramacion);
                modal.show();
            });
        }

        // Botones de programación rápida
        if (elementos.btnApertura1Hora) {
            elementos.btnApertura1Hora.addEventListener('click', () => programarAperturaEnHoras(1));
        }
        if (elementos.btnApertura2Horas) {
            elementos.btnApertura2Horas.addEventListener('click', () => programarAperturaEnHoras(2));
        }
        if (elementos.btnCierre1Hora) {
            elementos.btnCierre1Hora.addEventListener('click', () => programarCierreEnHoras(1));
        }

        // Botones de programación específica
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

        // Inicializar fecha actual en el modal
        const fechaInput = document.getElementById('fechaProgramacion');
        if (fechaInput) {
            const hoy = new Date().toISOString().split('T')[0];
            fechaInput.value = hoy;
            fechaInput.min = hoy;
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
        const fechaInput = document.getElementById('fechaProgramacion');
        const horaInput = document.getElementById('horaProgramacion');
        
        if (!fechaInput || !fechaInput.value || !horaInput || !horaInput.value) {
            mostrarToast('❌ Selecciona fecha y hora para programar', 'error');
            return;
        }

        // Crear fecha en zona horaria de Bogotá
        const [anio, mes, dia] = fechaInput.value.split('-');
        const [horas, minutos] = horaInput.value.split(':');
        
        // Crear fecha en la zona horaria local pero con los valores de Bogotá
        const fechaProgramada = new Date(anio, mes - 1, dia, horas, minutos, 0, 0);
        
        // Convertir a timestamp de Bogotá
        const fechaBogota = new Date(fechaProgramada.toLocaleString('en-US', { timeZone: 'America/Bogota' }));
        const ahoraBogota = obtenerFechaHoraBogota();

        console.log('📅 Programación desde modal:');
        console.log('   - Fecha programada (local):', fechaProgramada.toLocaleString('es-CO'));
        console.log('   - Fecha programada (Bogotá):', fechaBogota.toLocaleString('es-CO'));
        console.log('   - Ahora (Bogotá):', ahoraBogota.toLocaleString('es-CO'));

        if (fechaBogota <= ahoraBogota) {
            mostrarToast('❌ La fecha y hora deben ser en el futuro', 'error');
            return;
        }

        programarAperturaCierre(tipo, fechaBogota, false);
        
        // Limpiar campos
        horaInput.value = '';
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

        configuracionHorarios.horarioApertura = horarioApertura;
        configuracionHorarios.horarioCierre = horarioCierre;
        configuracionHorarios.programacionAutomatica = habilitarProgramacion;
        
        guardarConfiguracion();
        
        const modal = bootstrap.Modal.getInstance(elementos.modalProgramacion);
        if (modal) {
            modal.hide();
        }
        
        mostrarToast('✅ Configuración de horarios guardada correctamente', 'success');
        
        // Verificar inmediatamente
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
            const ahora = obtenerFechaHoraBogota();
            const diferenciaMs = programacion.timestamp - ahora.getTime();
            const diferenciaHoras = Math.max(0, Math.floor(diferenciaMs / (1000 * 60 * 60)));
            const diferenciaMin = Math.max(0, Math.floor((diferenciaMs % (1000 * 60 * 60)) / 60000));
            
            let tiempoRestante = '';
            if (diferenciaHoras > 0) {
                tiempoRestante = `en ${diferenciaHoras}h ${diferenciaMin}m`;
            } else {
                tiempoRestante = `en ${diferenciaMin} min`;
            }
            
            const tipoTexto = programacion.tipo === 'apertura' ? 'Apertura' : 'Cierre';
            const tipoClase = programacion.tipo === 'apertura' ? 'success' : 'warning';
            const icono = programacion.tipo === 'apertura' ? '🟢' : '🔴';
            
            return `
            <div class="programacion-item d-flex justify-content-between align-items-center p-3 border mb-2 rounded">
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center mb-1">
                        <strong class="text-${tipoClase} me-2">
                            ${icono} ${tipoTexto}
                        </strong>
                        <small class="badge bg-secondary">${tiempoRestante}</small>
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
        // Crear contenedor de toasts si no existe
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 300px;
            `;
            document.body.appendChild(toastContainer);
        }

        const toast = document.createElement('div');
        toast.className = `alert alert-${tipo === 'error' ? 'danger' : tipo} alert-dismissible fade show`;
        toast.style.cssText = 'margin-bottom: 10px; animation: slideInRight 0.3s ease;';
        toast.innerHTML = `
            ${mensaje}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        toastContainer.appendChild(toast);
        
        // Auto-eliminar después de 5 segundos
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 5000);
    }

    function iniciarVerificadorAutomatico() {
        // Verificar cada 10 segundos para mejor respuesta
        setInterval(verificarEstadoAutomatico, 10000);
        
        // Verificar inmediatamente al cargar
        setTimeout(verificarEstadoAutomatico, 1000);
        
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

            document.addEventListener('click', function(e) {
                if (!elementos.botonDesplegableUsuario.contains(e.target) && 
                    !elementos.menuDesplegableUsuario.contains(e.target)) {
                    elementos.menuDesplegableUsuario.classList.remove('mostrar');
                }
            });

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
                
                mostrarToast('✅ Reporte enviado correctamente. Te contactaremos pronto.', 'success');
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalReportarProblema'));
                modal.hide();
                
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
        console.log('📅 Fecha actual Bogotá:', obtenerFechaHoraBogota().toLocaleString('es-CO'));
        
        cargarConfiguracion();
        inicializarModalProgramacion();
        inicializarHeader();
        
        console.log('✅ Gestión de horarios inicializada correctamente');
        console.log('📊 Estado actual:', configuracionHorarios.estadoActual);
        console.log('📋 Programaciones pendientes:', obtenerProgramacionesPendientes().length);
        
        // Mostrar estado inicial
        mostrarToast(`Negocio ${configuracionHorarios.estadoActual === 'abierto' ? 'ABIERTO' : 'CERRADO'}`, 'info');
    }

    // Hacer funciones globales para los event listeners
    window.cancelarProgramacion = cancelarProgramacion;
    window.programarCierreEnHoras = programarCierreEnHoras;
    window.programarAperturaEnHoras = programarAperturaEnHoras;

    // ==================== EJECUTAR INICIALIZACIÓN ====================
    inicializar();
});
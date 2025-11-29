// static/vendedor/js/Layout_V.js
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
        botonReportarProblema: document.getElementById('botonReportarProblema'),
        botonMenuMovil: document.getElementById('botonMenuMovil'),
        // Elementos del modal de perfil
        modalEditarPerfil: document.getElementById('modalEditarPerfil'),
        formEditarPerfil: document.getElementById('formEditarPerfil'),
        guardarPerfil: document.getElementById('guardarPerfil'),
        btnCambiarFoto: document.getElementById('btnCambiarFoto'),
        inputFotoPerfil: document.getElementById('inputFotoPerfil'),
        fotoPerfilPreview: document.getElementById('fotoPerfilPreview')
    };

    // ==================== CONFIGURACIÓN Y ESTADO ====================
    let configuracionHorarios = {
        horarioApertura: '08:00',
        horarioCierre: '18:00',
        programacionAutomatica: false,
        estadoActual: 'cerrado',
        programaciones: [],
        diasServicio: [] // ← NUEVO: Array para días de servicio
    };

    // ==================== FUNCIONES PRINCIPALES ====================

    function cargarConfiguracion() {
        // Primero cargar desde localStorage como respaldo
        const guardado = localStorage.getItem('configuracionHorariosNegocio');
        if (guardado) {
            try {
                const configCargada = JSON.parse(guardado);
                configuracionHorarios = {
                    ...configuracionHorarios,
                    ...configCargada,
                    programaciones: configCargada.programaciones || [],
                    diasServicio: configCargada.diasServicio || [] // ← NUEVO: Cargar días de servicio
                };
                console.log('✅ Configuración cargada de localStorage:', configuracionHorarios);
            } catch (e) {
                console.error('❌ Error al cargar configuración:', e);
            }
        }
        
        // ✅ NUEVO: Cargar configuración completa desde el servidor
        cargarConfiguracionDesdeServidor().then(() => {
            iniciarVerificadorAutomatico();
        });
    }

    // ✅ NUEVA FUNCIÓN: Cargar configuración completa desde el servidor
    function cargarConfiguracionDesdeServidor() {
        return new Promise((resolve) => {
            // Primero cargar días de servicio
            fetch('/auth/vendedor/obtener-dias-servicio/')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.dias_servicio) {
                    configuracionHorarios.diasServicio = data.dias_servicio;
                    console.log('✅ Días de servicio cargados desde servidor:', data.dias_servicio);
                } else {
                    console.warn('⚠️ No se pudieron cargar días de servicio del servidor');
                }
                
                // Luego cargar estado de apertura
                return fetch('/auth/vendedor/obtener-estado-apertura/');
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.estado_apertura) {
                    configuracionHorarios.estadoActual = data.estado_apertura;
                    console.log('✅ Estado de apertura cargado desde servidor:', data.estado_apertura);
                } else {
                    console.warn('⚠️ No se pudo cargar estado del servidor, usando local');
                }
                
                // ✅ CARGAR HORARIOS DESDE EL SERVIDOR
                return cargarHorariosDesdeServidor();
            })
            .then(() => {
                // Sincronizar localStorage
                guardarConfiguracion();
                actualizarUIEstadoNegocio();
                resolve();
            })
            .catch(error => {
                console.error('❌ Error cargando configuración del servidor:', error);
                // Usar configuración local como fallback
                resolve();
            });
        });
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
        
        // ✅ NUEVO: Enviar el estado al servidor via AJAX
        enviarEstadoAperturaServidor(configuracionHorarios.estadoActual);
    }

    // ✅ NUEVA FUNCIÓN: Enviar estado de apertura al servidor
    function enviarEstadoAperturaServidor(estadoApertura) {
        fetch('/auth/vendedor/actualizar-estado-apertura/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                estado_apertura: estadoApertura
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('✅ Estado de apertura actualizado en servidor:', estadoApertura);
            } else {
                console.error('❌ Error al actualizar estado en servidor:', data.error);
                mostrarToast('❌ Error al guardar estado en servidor', 'error');
            }
        })
        .catch(error => {
            console.error('❌ Error en petición:', error);
            mostrarToast('❌ Error de conexión', 'error');
        });
    }

    // ✅ NUEVA FUNCIÓN: Obtener cookie CSRF
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
        
        // Primero verificar si hoy es día de servicio
        const esDiaServicio = esDiaDeServicio();
        
        if (!esDiaServicio) {
            console.log('📅 Hoy NO es día de servicio, verificando si debemos cerrar');
            // Si no es día de servicio y está abierto, cerrar
            if (configuracionHorarios.estadoActual === 'abierto') {
                console.log('🔒 Cerrando negocio porque hoy no es día de servicio');
                cambiarEstadoNegocio(false, 'no_es_dia_servicio');
            }
            return;
        }
        
        // Si es día de servicio, continuar con la verificación normal
        const cambiosProgramaciones = verificarProgramacionesEspecificas();
        
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
        cargarDiasServicio(); // ← NUEVO: Cargar días de servicio en el modal
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

        // Actualizar configuración local
        configuracionHorarios.horarioApertura = horarioApertura;
        configuracionHorarios.horarioCierre = horarioCierre;
        configuracionHorarios.programacionAutomatica = habilitarProgramacion;
        
        // Guardar en localStorage
        guardarConfiguracion();
        
        // ✅ ENVIAR HORARIOS AL SERVIDOR
        enviarHorariosServidor(horarioApertura, horarioCierre, habilitarProgramacion);
        
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

    // ==================== GESTIÓN DE DÍAS DE SERVICIO ====================

    function inicializarDiasServicio() {
        console.log('🔄 Inicializando gestión de días de servicio');
        
        // Cargar días guardados al abrir el modal
        if (elementos.modalProgramacion) {
            elementos.modalProgramacion.addEventListener('show.bs.modal', function() {
                cargarDiasServicio();
            });
        }
        
        // Event listeners para los botones de días
        document.querySelectorAll('.btn-dia-servicio').forEach(btn => {
            btn.addEventListener('click', function() {
                const dia = this.getAttribute('data-dia');
                toggleDiaServicio(dia, this);
            });
        });
        
        // Guardar días al guardar la configuración
        if (elementos.guardarProgramacion) {
            elementos.guardarProgramacion.addEventListener('click', function() {
                guardarDiasServicio();
            });
        }
    }

    function toggleDiaServicio(dia, elemento) {
        const estaSeleccionado = elemento.classList.contains('btn-primary');
        
        if (estaSeleccionado) {
            // Deseleccionar
            elemento.classList.remove('btn-primary');
            elemento.classList.add('btn-outline-primary');
        } else {
            // Seleccionar
            elemento.classList.remove('btn-outline-primary');
            elemento.classList.add('btn-primary');
        }
        
        actualizarListaDiasSeleccionados();
    }

    function actualizarListaDiasSeleccionados() {
        const contenedor = document.getElementById('listaDiasSeleccionados');
        if (!contenedor) return;
        
        const diasSeleccionados = obtenerDiasSeleccionados();
        
        if (diasSeleccionados.length === 0) {
            contenedor.innerHTML = '<span class="text-muted">No hay días seleccionados</span>';
            return;
        }
        
        contenedor.innerHTML = diasSeleccionados.map(dia => {
            const diaTexto = dia.charAt(0).toUpperCase() + dia.slice(1);
            return `
                <span class="badge bg-primary d-flex align-items-center">
                    ${diaTexto}
                    <button type="button" class="btn-close btn-close-white ms-1" style="font-size: 0.7rem;" data-dia="${dia}"></button>
                </span>
            `;
        }).join('');
        
        // Event listeners para eliminar días
        contenedor.querySelectorAll('.btn-close').forEach(btn => {
            btn.addEventListener('click', function() {
                const dia = this.getAttribute('data-dia');
                const botonDia = document.querySelector(`.btn-dia-servicio[data-dia="${dia}"]`);
                if (botonDia) {
                    botonDia.classList.remove('btn-primary');
                    botonDia.classList.add('btn-outline-primary');
                    actualizarListaDiasSeleccionados();
                }
            });
        });
    }

    function obtenerDiasSeleccionados() {
        const dias = [];
        document.querySelectorAll('.btn-dia-servicio.btn-primary').forEach(btn => {
            dias.push(btn.getAttribute('data-dia'));
        });
        return dias;
    }

    function cargarDiasServicio() {
        console.log('📅 Cargando días de servicio guardados');
        
        // Resetear todos los botones
        document.querySelectorAll('.btn-dia-servicio').forEach(btn => {
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-outline-primary');
        });
        
        // Cargar desde la configuración
        if (configuracionHorarios.diasServicio && Array.isArray(configuracionHorarios.diasServicio)) {
            configuracionHorarios.diasServicio.forEach(dia => {
                const botonDia = document.querySelector(`.btn-dia-servicio[data-dia="${dia}"]`);
                if (botonDia) {
                    botonDia.classList.remove('btn-outline-primary');
                    botonDia.classList.add('btn-primary');
                }
            });
        }
        
        actualizarListaDiasSeleccionados();
    }

    function guardarDiasServicio() {
        const diasSeleccionados = obtenerDiasSeleccionados();
        configuracionHorarios.diasServicio = diasSeleccionados;
        
        console.log('💾 Guardando días de servicio:', diasSeleccionados);
        
        // Guardar en localStorage
        guardarConfiguracion();
        
        // Enviar al servidor via AJAX
        enviarDiasServicioServidor(diasSeleccionados);
    }

    function enviarDiasServicioServidor(diasServicio) {
        fetch('/auth/vendedor/actualizar-dias-servicio/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                dias_servicio: diasServicio
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('✅ Días de servicio actualizados en servidor:', diasServicio);
                mostrarToast('✅ Días de servicio guardados correctamente', 'success');
            } else {
                console.error('❌ Error al actualizar días de servicio:', data.error);
                mostrarToast('❌ Error al guardar días de servicio', 'error');
            }
        })
        .catch(error => {
            console.error('❌ Error en petición:', error);
            mostrarToast('❌ Error de conexión', 'error');
        });
    }

    // Nueva función para verificar si hoy es día de servicio
    function esDiaDeServicio() {
        if (!configuracionHorarios.diasServicio || configuracionHorarios.diasServicio.length === 0) {
            console.log('📅 No hay días de servicio configurados, asumiendo todos los días');
            return true; // Si no hay configuración, asumir todos los días
        }
        
        const diasSemana = ['domingo', 'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado'];
        const hoy = new Date().getDay();
        const diaHoy = diasSemana[hoy];
        
        const esDiaValido = configuracionHorarios.diasServicio.includes(diaHoy);
        console.log(`📅 Verificación día de servicio: Hoy es ${diaHoy}, ¿es día de servicio? ${esDiaValido}`);
        
        return esDiaValido;
    }

    // ==================== MODAL DE EDITAR PERFIL ====================

    function inicializarModalPerfil() {
        // ==================== FUNCIONALIDAD DE FOTO DE PERFIL ====================
        if (elementos.btnCambiarFoto && elementos.inputFotoPerfil) {
            elementos.btnCambiarFoto.addEventListener('click', function() {
                elementos.inputFotoPerfil.click();
            });

            elementos.inputFotoPerfil.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    if (file.type.startsWith('image/')) {
                        const reader = new FileReader();
                        reader.onload = function(e) {
                            elementos.fotoPerfilPreview.src = e.target.result;
                            mostrarToast('✅ Foto de perfil cargada correctamente', 'success');
                        };
                        reader.readAsDataURL(file);
                    } else {
                        mostrarToast('❌ Por favor selecciona una imagen válida', 'error');
                    }
                }
            });
        }

        // ==================== FUNCIONALIDAD DE MOSTRAR/OCULTAR CONTRASEÑA ====================
        const btnTogglePasswords = document.querySelectorAll('.btn-toggle-password');
        if (btnTogglePasswords) {
            btnTogglePasswords.forEach(btn => {
                btn.addEventListener('click', function() {
                    const targetId = this.getAttribute('data-target');
                    const input = document.getElementById(targetId);
                    
                    if (input.type === 'password') {
                        input.type = 'text';
                        this.innerHTML = '<i class="fas fa-eye-slash"></i>';
                    } else {
                        input.type = 'password';
                        this.innerHTML = '<i class="fas fa-eye"></i>';
                    }
                });
            });
        }

        // ==================== VALIDACIÓN DEL FORMULARIO ====================
        if (elementos.guardarPerfil && elementos.formEditarPerfil) {
            elementos.guardarPerfil.addEventListener('click', function() {
                if (validarFormularioPerfil()) {
                    guardarPerfil();
                }
            });
        }

        // ==================== INICIALIZACIÓN DEL MODAL ====================
        if (elementos.modalEditarPerfil) {
            elementos.modalEditarPerfil.addEventListener('show.bs.modal', function() {
                console.log('🔄 Abriendo modal de editar perfil');
                // Limpiar campos de contraseña al abrir el modal
                document.getElementById('claveActual').value = '';
                document.getElementById('nuevaClave').value = '';
                document.getElementById('confirmarClave').value = '';
            });
        }
    }

    function validarFormularioPerfil() {
        const nombre = document.getElementById('nombre').value.trim();
        const apellido = document.getElementById('apellido').value.trim();
        const email = document.getElementById('email').value.trim();
        const claveActual = document.getElementById('claveActual').value;
        const nuevaClave = document.getElementById('nuevaClave').value;
        const confirmarClave = document.getElementById('confirmarClave').value;

        // Validar campos obligatorios
        if (!nombre) {
            mostrarToast('❌ El nombre es obligatorio', 'error');
            document.getElementById('nombre').focus();
            return false;
        }

        if (!apellido) {
            mostrarToast('❌ El apellido es obligatorio', 'error');
            document.getElementById('apellido').focus();
            return false;
        }

        if (!email) {
            mostrarToast('❌ El email es obligatorio', 'error');
            document.getElementById('email').focus();
            return false;
        }

        // Validar formato de email
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            mostrarToast('❌ Por favor ingresa un email válido', 'error');
            document.getElementById('email').focus();
            return false;
        }

        // Validar cambio de contraseña (solo si se intenta cambiar)
        if (nuevaClave || confirmarClave) {
            if (!claveActual) {
                mostrarToast('❌ Para cambiar la contraseña debes ingresar la contraseña actual', 'error');
                document.getElementById('claveActual').focus();
                return false;
            }

            if (nuevaClave.length < 8) {
                mostrarToast('❌ La nueva contraseña debe tener al menos 8 caracteres', 'error');
                document.getElementById('nuevaClave').focus();
                return false;
            }

            if (nuevaClave !== confirmarClave) {
                mostrarToast('❌ Las contraseñas no coinciden', 'error');
                document.getElementById('confirmarClave').focus();
                return false;
            }
        }

        return true;
    }

    function guardarPerfil() {
        console.log('💾 Guardando perfil...');

        // Mostrar loading en el botón
        const btnGuardar = elementos.guardarPerfil;
        const originalText = btnGuardar.innerHTML;
        btnGuardar.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Guardando...';
        btnGuardar.disabled = true;

        // Simular envío de datos (aquí iría la llamada AJAX real)
        setTimeout(() => {
            // Restaurar botón
            btnGuardar.innerHTML = originalText;
            btnGuardar.disabled = false;

            mostrarToast('✅ Perfil actualizado correctamente', 'success');
            
            // Cerrar el modal después de guardar
            const modal = bootstrap.Modal.getInstance(elementos.modalEditarPerfil);
            if (modal) {
                modal.hide();
            }

            // Actualizar el nombre en el header si cambió
            const nuevoNombre = document.getElementById('nombre').value;
            const nombreUsuarioHeader = document.querySelector('.nombre-usuario');
            if (nombreUsuarioHeader && nuevoNombre) {
                nombreUsuarioHeader.textContent = nuevoNombre;
            }
        }, 1500);
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
        // Botón hamburguesa para móvil
        const botonMenuMovil = document.getElementById('botonMenuMovil');
        const barraLateral = document.querySelector('.barra-lateral');
        
        if (botonMenuMovil && barraLateral) {
            botonMenuMovil.addEventListener('click', function() {
                barraLateral.classList.toggle('mostrar');
                
                // Opcional: cerrar el menú al hacer clic fuera
                if (barraLateral.classList.contains('mostrar')) {
                    setTimeout(() => {
                        document.addEventListener('click', cerrarMenuAlClicExterno);
                    }, 100);
                }
            });
        }
        
        function cerrarMenuAlClicExterno(e) {
            const barraLateral = document.querySelector('.barra-lateral');
            const botonMenuMovil = document.getElementById('botonMenuMovil');
            
            if (!barraLateral.contains(e.target) && !botonMenuMovil.contains(e.target)) {
                barraLateral.classList.remove('mostrar');
                document.removeEventListener('click', cerrarMenuAlClicExterno);
            }
        }

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
        inicializarModalPerfil();
        inicializarHeader();
        inicializarDiasServicio(); // ← AÑADIR ESTA LÍNEA
        
        console.log('✅ Gestión de horarios inicializada correctamente');
        console.log('📊 Estado actual:', configuracionHorarios.estadoActual);
        console.log('📋 Programaciones pendientes:', obtenerProgramacionesPendientes().length);
        console.log('📅 Días de servicio:', configuracionHorarios.diasServicio || 'No configurados');
        
        // Mostrar estado inicial
        mostrarToast(`Negocio ${configuracionHorarios.estadoActual === 'abierto' ? 'ABIERTO' : 'CERRADO'}`, 'info');
    }

    // Hacer funciones globales para los event listeners
    window.cancelarProgramacion = cancelarProgramacion;
    window.programarCierreEnHoras = programarCierreEnHoras;
    window.programarAperturaEnHoras = programarAperturaEnHoras;

    // ==================== EJECUTAR INICIALIZACIÓN ====================
    inicializar();

    // ✅ NUEVA FUNCIÓN: Enviar horarios al servidor
    function enviarHorariosServidor(horarioApertura, horarioCierre, programacionAutomatica) {
        fetch('/auth/vendedor/actualizar-horarios/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                horario_apertura: horarioApertura,
                horario_cierre: horarioCierre,
                programacion_automatica: programacionAutomatica
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('✅ Horarios actualizados en servidor:', {
                    horario_apertura: horarioApertura,
                    horario_cierre: horarioCierre,
                    programacion_automatica: programacionAutomatica
                });
            } else {
                console.error('❌ Error al actualizar horarios:', data.error);
                mostrarToast('❌ Error al guardar horarios en servidor', 'error');
            }
        })
        .catch(error => {
            console.error('❌ Error en petición:', error);
            mostrarToast('❌ Error de conexión', 'error');
        });
    }

    // ✅ NUEVA FUNCIÓN: Cargar horarios desde el servidor
    function cargarHorariosDesdeServidor() {
        return fetch('/auth/vendedor/obtener-horarios/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Actualizar configuración local con datos del servidor
                    if (data.horario_apertura) {
                        configuracionHorarios.horarioApertura = data.horario_apertura;
                        if (elementos.horarioApertura) {
                            elementos.horarioApertura.value = data.horario_apertura;
                        }
                    }
                    if (data.horario_cierre) {
                        configuracionHorarios.horarioCierre = data.horario_cierre;
                        if (elementos.horarioCierre) {
                            elementos.horarioCierre.value = data.horario_cierre;
                        }
                    }
                    if (data.programacion_automatica !== undefined) {
                        configuracionHorarios.programacionAutomatica = data.programacion_automatica;
                        if (elementos.habilitarProgramacion) {
                            elementos.habilitarProgramacion.checked = data.programacion_automatica;
                        }
                    }
                    console.log('✅ Horarios cargados desde servidor:', data);
                } else {
                    console.warn('⚠️ No se pudieron cargar horarios del servidor');
                }
            })
            .catch(error => {
                console.error('❌ Error cargando horarios del servidor:', error);
            });
    }
});
// static/vendedor/js/Negocios_V.js
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // ==================== BÚSQUEDA Y FILTROS ====================
    const inputBusqueda = document.getElementById('inputBusqueda');
    const selectFiltro = document.getElementById('selectFiltro');
    
    function aplicarFiltros() {
        const filtro = selectFiltro ? selectFiltro.value : 'todos';
        const texto = inputBusqueda ? inputBusqueda.value.toLowerCase() : '';
        const negociosCards = document.querySelectorAll('.negocio-card-item');
        const negocioActivo = document.querySelector('.negocio-activo-card');
        
        let negociosVisibles = 0;
        
        negociosCards.forEach(card => {
            const negocioNombre = card.querySelector('.negocio-card-title').textContent.toLowerCase();
            const negocioDescripcion = card.querySelector('.negocio-card-descripcion').textContent.toLowerCase();
            const estado = card.getAttribute('data-estado');
            
            const textoCompleto = negocioNombre + ' ' + negocioDescripcion;
            
            let mostrar = true;
            
            // Aplicar filtro seleccionado
            if (filtro !== 'todos' && estado !== filtro) {
                mostrar = false;
            }
            
            // Aplicar búsqueda de texto
            if (mostrar && texto && !textoCompleto.includes(texto)) {
                mostrar = false;
            }
            
            card.style.display = mostrar ? 'block' : 'none';
            
            if (mostrar) {
                negociosVisibles++;
                card.style.animation = 'fadeInUp 0.5s ease';
            }
        });
        
        // Mostrar mensaje si no hay resultados
        const mensajeNoResultados = document.getElementById('mensajeNoResultados');
        const tieneActivo = negocioActivo && negocioActivo.style.display !== 'none';
        
        if (negociosVisibles === 0 && !tieneActivo) {
            if (!mensajeNoResultados) {
                const mensaje = document.createElement('div');
                mensaje.id = 'mensajeNoResultados';
                mensaje.className = 'text-center py-5 w-100';
                mensaje.innerHTML = `
                    <i class="fas fa-search fa-3x text-muted mb-3"></i>
                    <h4 class="text-muted">No se encontraron negocios</h4>
                    <p class="text-muted">Intenta con otros términos de búsqueda o filtros.</p>
                `;
                document.querySelector('.contenedor-negocios-grid').appendChild(mensaje);
            }
        } else if (mensajeNoResultados) {
            mensajeNoResultados.remove();
        }
    }

    // Inicializar filtros
    if (selectFiltro) {
        selectFiltro.addEventListener('change', aplicarFiltros);
    }
    
    if (inputBusqueda) {
        inputBusqueda.addEventListener('input', aplicarFiltros);
        
        // Limpiar búsqueda con icono
        const iconoBusqueda = document.querySelector('.icono-busqueda');
        if (iconoBusqueda) {
            iconoBusqueda.addEventListener('click', function() {
                inputBusqueda.value = '';
                aplicarFiltros();
                inputBusqueda.focus();
            });
        }
    }

    // ==================== VALIDACIÓN DE FORMULARIOS ====================
    function validarNIT(nit) {
        return nit.length >= 8 && nit.length <= 11 && /^\d+$/.test(nit);
    }

    const formAgregar = document.getElementById('formAgregarNegocio');
    if (formAgregar) {
        formAgregar.addEventListener('submit', function(e) {
            const nit = document.getElementById('nit_neg').value.trim();
            
            if (!validarNIT(nit)) {
                e.preventDefault();
                mostrarAlerta('El NIT debe tener entre 8 y 11 caracteres numéricos', 'error');
                document.getElementById('nit_neg').focus();
                return false;
            }
            
            const descripcion = document.getElementById('desc_neg').value;
            if (descripcion.length > 500) {
                e.preventDefault();
                mostrarAlerta('La descripción no puede exceder los 500 caracteres', 'error');
                document.getElementById('desc_neg').focus();
                return false;
            }
            
            return true;
        });
    }

    // ==================== CONFIGURACIÓN DE MODALES ====================
    
    // Modal para activar/desactivar
    const modalEstado = document.getElementById('modalEstadoNegocio');
    if (modalEstado) {
        modalEstado.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const negocioId = button.getAttribute('data-negocio-id');
            const negocioNombre = button.getAttribute('data-negocio-nombre');
            const negocioEstado = button.getAttribute('data-negocio-estado');
            
            const modalBodyInput = modalEstado.querySelector('#estado_negocio_id');
            const modalBodyText = modalEstado.querySelector('#textoEstadoNegocio');
            const modalInfo = modalEstado.querySelector('#infoEstadoNegocio');
            
            modalBodyInput.value = negocioId;
            
            if (negocioEstado === 'activo') {
                modalBodyText.textContent = `¿Estás seguro que deseas desactivar el negocio "${negocioNombre}"?`;
                modalInfo.textContent = 'Los clientes no podrán ver tu negocio ni tus productos mientras esté desactivado.';
            } else {
                modalBodyText.textContent = `¿Estás seguro que deseas activar el negocio "${negocioNombre}"?`;
                modalInfo.textContent = 'Los clientes podrán ver tu negocio y productos nuevamente.';
            }
        });
    }

    // Modal para eliminar negocio
    const modalEliminar = document.getElementById('modalEliminarNegocio');
    if (modalEliminar) {
        modalEliminar.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const negocioId = button.getAttribute('data-negocio-id');
            const negocioNombre = button.getAttribute('data-negocio-nombre');
            
            const modalBodyInput = modalEliminar.querySelector('#eliminar_negocio_id');
            const modalBodyText = modalEliminar.querySelector('#textoEliminarNegocio');
            const btnEliminar = modalEliminar.querySelector('#btnEliminarConfirmar');
            const checkbox = modalEliminar.querySelector('#confirmarEliminacion');
            
            modalBodyInput.value = negocioId;
            modalBodyText.textContent = `¿Estás absolutamente seguro que deseas eliminar permanentemente el negocio "${negocioNombre}"?`;
            
            // Resetear checkbox y botón
            checkbox.checked = false;
            btnEliminar.disabled = true;
            
            checkbox.addEventListener('change', function() {
                btnEliminar.disabled = !this.checked;
            });
        });
    }

    // ==================== MODAL DE EDICIÓN ====================
    const modalEditar = document.getElementById('modalEditarNegocio');
    if (modalEditar) {
        modalEditar.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const negocioId = button.getAttribute('data-negocio-id');
            const negocioNombre = button.getAttribute('data-negocio-nombre');
            const negocioNIT = button.getAttribute('data-negocio-nit');
            const negocioDireccion = button.getAttribute('data-negocio-direccion');
            const negocioDescripcion = button.getAttribute('data-negocio-descripcion');
            const negocioTipo = button.getAttribute('data-negocio-tipo');
            const negocioImagen = button.getAttribute('data-negocio-imagen');
            
            console.log('Cargando datos del negocio:', {
                id: negocioId,
                nombre: negocioNombre,
                nit: negocioNIT,
                direccion: negocioDireccion,
                descripcion: negocioDescripcion,
                tipo: negocioTipo,
                imagen: negocioImagen
            });
            
            // Actualizar formulario
            document.getElementById('editar_negocio_id').value = negocioId;
            document.getElementById('editar_nom_neg').value = negocioNombre || '';
            document.getElementById('editar_nit_neg').value = negocioNIT || '';
            document.getElementById('editar_direcc_neg').value = negocioDireccion || '';
            document.getElementById('editar_desc_neg').value = negocioDescripcion || '';
            document.getElementById('editar_fktiponeg_neg').value = negocioTipo || '';
            
            // Actualizar acción del formulario
            const form = document.getElementById('formEditarNegocio');
            const actionUrl = form.getAttribute('action').replace('/0', '/' + negocioId);
            form.setAttribute('action', actionUrl);
            
            // Manejar imagen actual
            const imagenActual = document.getElementById('editar_imagen_actual');
            const noImagen = document.getElementById('editar_no_image');
            
            if (negocioImagen && negocioImagen !== 'None' && negocioImagen !== '') {
                imagenActual.src = negocioImagen;
                imagenActual.style.display = 'block';
                noImagen.style.display = 'none';
                console.log('Imagen cargada:', negocioImagen);
            } else {
                imagenActual.style.display = 'none';
                noImagen.style.display = 'flex';
                console.log('No hay imagen disponible');
            }
            
            // Actualizar título del modal
            document.getElementById('modalEditarNegocioLabel').innerHTML = 
                `<i class="fas fa-edit me-2"></i>Configurar: "${negocioNombre}"`;
                
            // Manejar error de imagen
            imagenActual.onerror = function() {
                console.log('Error al cargar la imagen');
                this.style.display = 'none';
                noImagen.style.display = 'flex';
            };
        });
    }

    // Validación del formulario de edición
    const formEditar = document.getElementById('formEditarNegocio');
    if (formEditar) {
        formEditar.addEventListener('submit', function(e) {
            const nombre = document.getElementById('editar_nom_neg').value.trim();
            const nit = document.getElementById('editar_nit_neg').value.trim();
            const tipo = document.getElementById('editar_fktiponeg_neg').value;
            const direccion = document.getElementById('editar_direcc_neg').value.trim();
            const descripcion = document.getElementById('editar_desc_neg').value;
            
            let errores = [];
            
            if (!nombre) {
                errores.push('El nombre del negocio es obligatorio');
            }
            
            if (!nit) {
                errores.push('El NIT es obligatorio');
            } else if (!validarNIT(nit)) {
                errores.push('El NIT debe tener entre 8 y 11 caracteres numéricos');
            }
            
            if (!tipo) {
                errores.push('Debes seleccionar un tipo de negocio');
            }
            
            if (!direccion) {
                errores.push('La dirección es obligatoria');
            }
            
            if (descripcion.length > 500) {
                errores.push('La descripción no puede exceder los 500 caracteres');
            }
            
            if (errores.length > 0) {
                e.preventDefault();
                mostrarAlerta('Por favor, corrige los siguientes errores:\n\n• ' + errores.join('\n• '), 'error');
                return false;
            }
        });
    }

    // Vista previa de imagen en el modal de edición
    const inputImagenEditar = document.getElementById('editar_img_neg');
    if (inputImagenEditar) {
        inputImagenEditar.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Validar tamaño (5MB máximo)
                if (file.size > 5 * 1024 * 1024) {
                    mostrarAlerta('La imagen es demasiado grande. Máximo 5MB permitido.', 'error');
                    e.target.value = '';
                    return;
                }
                
                // Validar tipo
                const tiposPermitidos = ['image/jpeg', 'image/png', 'image/gif'];
                if (!tiposPermitidos.includes(file.type)) {
                    mostrarAlerta('Solo se permiten imágenes JPG, PNG o GIF.', 'error');
                    e.target.value = '';
                    return;
                }
                
                console.log('Imagen válida seleccionada para edición:', file.name);
                
                // Opcional: Mostrar vista previa de la nueva imagen
                const reader = new FileReader();
                reader.onload = function(e) {
                    const imagenActual = document.getElementById('editar_imagen_actual');
                    const noImagen = document.getElementById('editar_no_image');
                    
                    imagenActual.src = e.target.result;
                    imagenActual.style.display = 'block';
                    noImagen.style.display = 'none';
                    
                    document.getElementById('editar_texto_imagen').textContent = 'Vista previa de la nueva imagen';
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // ==================== MEJORAS DE USABILIDAD ====================
    
    // Efectos hover mejorados
    const cards = document.querySelectorAll('.negocio-card-item, .estadistica-card, .boton-accion');
    cards.forEach(elemento => {
        elemento.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        elemento.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Limitar NIT a 11 caracteres numéricos
    const inputsNIT = document.querySelectorAll('input[name="nit_neg"], input[name="editar_nit_neg"]');
    inputsNIT.forEach(input => {
        input.addEventListener('input', function(e) {
            this.value = this.value.replace(/\D/g, '');
            if (this.value.length > 11) {
                this.value = this.value.substring(0, 11);
            }
        });
    });

    // Contador de caracteres para descripción
    const textareasDescripcion = document.querySelectorAll('#desc_neg, #editar_desc_neg');
    textareasDescripcion.forEach(textarea => {
        const contador = document.createElement('div');
        contador.className = 'form-text text-end';
        contador.innerHTML = '<span class="contador">0</span>/500 caracteres';
        textarea.parentNode.appendChild(contador);
        
        textarea.addEventListener('input', function() {
            const contadorSpan = contador.querySelector('.contador');
            contadorSpan.textContent = this.value.length;
            
            if (this.value.length > 500) {
                contador.classList.add('text-danger');
                contadorSpan.classList.add('text-danger');
            } else {
                contador.classList.remove('text-danger');
                contadorSpan.classList.remove('text-danger');
            }
        });
        
        // Inicializar contador
        const evento = new Event('input');
        textarea.dispatchEvent(evento);
    });

    // ==================== FUNCIONES AUXILIARES ====================
    function mostrarAlerta(mensaje, tipo = 'info') {
        // Primero, eliminar alertas existentes
        const alertasExistentes = document.querySelectorAll('.alert');
        alertasExistentes.forEach(alerta => {
            if (alerta.parentNode && !alerta.classList.contains('alert-dismissible')) {
                alerta.remove();
            }
        });
        
        const alerta = document.createElement('div');
        alerta.className = `alert alert-${tipo} alert-dismissible fade show`;
        alerta.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-${tipo === 'error' ? 'exclamation-triangle' : tipo === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                <div>${mensaje}</div>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const tarjetaBienvenida = document.querySelector('.tarjeta-bienvenida');
        if (tarjetaBienvenida && tarjetaBienvenida.parentNode) {
            tarjetaBienvenida.parentNode.insertBefore(alerta, tarjetaBienvenida.nextSibling);
        }
        
        // Auto-eliminar después de 5 segundos
        setTimeout(() => {
            if (alerta.parentNode) {
                alerta.remove();
            }
        }, 5000);
    }

    // ==================== EVENT LISTENERS PARA BOTONES DE EDICIÓN ====================
    
    // Agregar event listeners a todos los botones de edición
    const botonesEditar = document.querySelectorAll('.btn-editar-negocio');
    botonesEditar.forEach(boton => {
        boton.addEventListener('click', function() {
            console.log('Botón editar clickeado:', {
                id: this.getAttribute('data-negocio-id'),
                nombre: this.getAttribute('data-negocio-nombre')
            });
        });
    });

    // ==================== MANEJO DE ERRORES DE IMAGEN ====================
    
    // Manejar errores de imagen en toda la página
    document.querySelectorAll('img').forEach(img => {
        img.addEventListener('error', function() {
            console.log('Error al cargar imagen:', this.src);
            // Puedes agregar lógica adicional aquí si es necesario
        });
    });

    // ==================== INICIALIZACIÓN ====================
    console.log('Negocios_V.js cargado correctamente - Versión Modal de Edición');
    aplicarFiltros();
    
    // Debug: Verificar que los botones de edición estén funcionando
    console.log('Botones de edición encontrados:', document.querySelectorAll('.btn-editar-negocio').length);
});
// static/vendedor/js/Crud_V.js - VERSIÓN MEJORADA SIN AJAX - COMPLETAMENTE CORREGIDA

document.addEventListener('DOMContentLoaded', function () {
    console.log("=== DEBUG: Crud_V.js cargado correctamente ===");
    
    // Inicializar tooltips de Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Funcionalidad de acordeón para variantes
    const productosHeaders = document.querySelectorAll('.producto-header');
    
    productosHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const productoCard = this.closest('.producto-card');
            const variantesSection = productoCard.querySelector('.variantes-section');
            const flecha = this.querySelector('.flecha-acordeon');
            
            // Cerrar otros acordeones
            document.querySelectorAll('.variantes-section.active').forEach(section => {
                if (section !== variantesSection) {
                    section.classList.remove('active');
                    const otraFlecha = section.closest('.producto-card').querySelector('.flecha-acordeon');
                    if (otraFlecha) otraFlecha.classList.remove('rotada');
                }
            });
            
            // Alternar acordeón actual
            if (variantesSection) {
                variantesSection.classList.toggle('active');
                if (flecha) {
                    flecha.classList.toggle('rotada');
                }
            }
        });
    });

    // Filtros y búsqueda
    const selectFiltro = document.getElementById('selectFiltro');
    const inputBusqueda = document.getElementById('inputBusqueda');
    
    function aplicarFiltros() {
        const filtro = selectFiltro ? selectFiltro.value : 'todos';
        const texto = inputBusqueda ? inputBusqueda.value.toLowerCase() : '';
        const productosCards = document.querySelectorAll('.producto-card');
        
        productosCards.forEach(card => {
            const productoNombre = card.querySelector('.producto-details h5').textContent.toLowerCase();
            const productoDescripcion = card.querySelector('.producto-descripcion').textContent.toLowerCase();
            const stockElement = card.querySelector('.stock');
            const stock = stockElement ? parseInt(stockElement.textContent.replace('Stock: ', '')) || 0 : 0;
            const esOferta = card.querySelector('.badge-oferta') !== null;
            const textoCompleto = productoNombre + ' ' + productoDescripcion;
            
            let mostrar = true;
            
            // Aplicar filtro seleccionado
            switch (filtro) {
                case 'oferta':
                    if (!esOferta) mostrar = false;
                    break;
                case 'disponible':
                    if (stock === 0) mostrar = false;
                    break;
                case 'sin-stock':
                    if (stock > 0) mostrar = false;
                    break;
                case 'stock-bajo':
                    if (stock > 5 || stock === 0) mostrar = false;
                    break;
            }
            
            // Aplicar búsqueda de texto
            if (mostrar && texto && !textoCompleto.includes(texto)) {
                mostrar = false;
            }
            
            card.style.display = mostrar ? 'block' : 'none';
            
            // Animación suave
            if (mostrar) {
                card.style.animation = 'fadeInUp 0.5s ease';
            }
        });
        
        // Mostrar mensaje si no hay resultados
        const productosVisibles = document.querySelectorAll('.producto-card[style="display: block"]').length;
        const mensajeNoResultados = document.getElementById('mensajeNoResultados');
        
        if (productosVisibles === 0) {
            if (!mensajeNoResultados) {
                const mensaje = document.createElement('div');
                mensaje.id = 'mensajeNoResultados';
                mensaje.className = 'text-center py-5';
                mensaje.innerHTML = `
                    <i class="fas fa-search fa-3x text-muted mb-3"></i>
                    <h4 class="text-muted">No se encontraron productos</h4>
                    <p class="text-muted">Intenta con otros términos de búsqueda o filtros.</p>
                `;
                document.querySelector('.contenedor-productos').appendChild(mensaje);
            }
        } else if (mensajeNoResultados) {
            mensajeNoResultados.remove();
        }
    }

    // Inicializar filtros si existen
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

    // Lógica para calcular stock final en ajuste de stock
    const tipoAjuste = document.getElementById('tipo_ajuste');
    const cantidadAjuste = document.getElementById('cantidad_ajuste');
    const stockActual = document.getElementById('stock_actual');
    const stockFinal = document.getElementById('stock_final');
    const textoAyuda = document.getElementById('texto_ayuda');
    const campoStockFinal = document.getElementById('campo_stock_final');

    function calcularStockFinal() {
        if (!tipoAjuste || !cantidadAjuste || !stockActual) return;
        
        const stockActualVal = parseInt(stockActual.value) || 0;
        const cantidadVal = parseInt(cantidadAjuste.value) || 0;
        const tipo = tipoAjuste.value;

        let stockFinalVal = stockActualVal;
        
        if (tipo === 'entrada') {
            stockFinalVal = stockActualVal + cantidadVal;
            if (textoAyuda) {
                textoAyuda.textContent = `Se sumarán ${cantidadVal} unidades al stock actual`;
                textoAyuda.className = 'form-text text-success';
            }
        } else if (tipo === 'salida') {
            stockFinalVal = stockActualVal - cantidadVal;
            if (textoAyuda) {
                textoAyuda.textContent = `Se restarán ${cantidadVal} unidades al stock actual`;
                textoAyuda.className = stockFinalVal < 0 ? 'form-text text-danger' : 'form-text text-warning';
            }
        } else {
            stockFinalVal = cantidadVal;
            if (textoAyuda) {
                textoAyuda.textContent = `El stock se establecerá en ${cantidadVal} unidades`;
                textoAyuda.className = 'form-text text-info';
            }
        }

        if (stockFinal) {
            stockFinal.value = stockFinalVal;
        }
        
        // Mostrar/ocultar campo de stock final
        if (campoStockFinal) {
            if (cantidadVal > 0) {
                campoStockFinal.style.display = 'block';
                if (stockFinal) {
                    stockFinal.className = `form-control ${stockFinalVal < 0 ? 'is-invalid' : (stockFinalVal <= 5 ? 'is-warning' : 'is-valid')}`;
                }
            } else {
                campoStockFinal.style.display = 'none';
            }
        }
    }

    if (tipoAjuste && cantidadAjuste) {
        tipoAjuste.addEventListener('change', calcularStockFinal);
        cantidadAjuste.addEventListener('input', calcularStockFinal);
    }

    // Efectos visuales mejorados
    const botonesAccion = document.querySelectorAll('.boton-accion, .btn');
    botonesAccion.forEach(boton => {
        boton.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        boton.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Cerrar acordeones al hacer clic fuera
    document.addEventListener('click', function(event) {
        if (!event.target.closest('.producto-card')) {
            document.querySelectorAll('.variantes-section.active').forEach(section => {
                section.classList.remove('active');
            });
            document.querySelectorAll('.flecha-acordeon.rotada').forEach(flecha => {
                flecha.classList.remove('rotada');
            });
        }
    });

    // Inicializar funcionalidad del modal de eliminación
    inicializarModalEliminacion();

    // Debug: Verificar que los modales se cargan correctamente
    console.log("=== DEBUG: Modales disponibles ===");
    console.log("Modal Editar:", document.getElementById('modalEditarProducto'));
    console.log("Modal Stock:", document.getElementById('modalAjustarStock'));
    console.log("Modal Eliminar:", document.getElementById('modalEliminarProducto'));
});

// ==================== FUNCIONES GLOBALES ====================

// Funciones globales para cargar datos en los modales
function cargarDatosProducto(id, nombre, precio, stock, estado, categoria, descripcion) {
    console.log(`=== DEBUG: Cargando datos producto ID ${id} ===`);
    console.log(`Nombre: ${nombre}, Precio: ${precio}, Stock: ${stock}, Estado: ${estado}, Categoria: ${categoria}`);
    
    document.getElementById('producto_id_editar').value = id;
    document.getElementById('nom_prod_editar').value = nombre;
    document.getElementById('precio_prod_editar').value = precio;
    document.getElementById('stock_prod_editar').value = stock;
    document.getElementById('estado_prod_editar').value = estado;
    document.getElementById('categoria_prod_editar').value = categoria;
    document.getElementById('desc_prod_editar').value = descripcion;
    
    // Configurar la acción del formulario - CORREGIDO
    document.getElementById('formEditarProducto').action = `/auth/vendedor/productos/editar/${id}/`;
    console.log(`Form action edit: ${document.getElementById('formEditarProducto').action}`);
}

function cargarDatosStock(id, nombre, stock) {
    console.log(`=== DEBUG: Cargando datos stock ID ${id} ===`);
    console.log(`Nombre: ${nombre}, Stock actual: ${stock}`);
    
    document.getElementById('producto_id_stock').value = id;
    document.getElementById('nombre_producto_stock').textContent = nombre;
    document.getElementById('stock_actual').value = stock;
    
    // Resetear campos
    document.getElementById('cantidad_ajuste').value = '';
    document.getElementById('stock_final').value = '';
    document.getElementById('tipo_ajuste').value = 'entrada';
    document.getElementById('motivo_ajuste').value = 'compra_proveedor';
    if (document.getElementById('campo_stock_final')) {
        document.getElementById('campo_stock_final').style.display = 'none';
    }
    
    // Configurar la acción del formulario - CORREGIDO
    document.getElementById('formAjustarStock').action = `/auth/vendedor/productos/ajustar-stock/${id}/`;
    console.log(`Form action stock: ${document.getElementById('formAjustarStock').action}`);
    
    // Recalcular stock final
    if (typeof calcularStockFinal === 'function') {
        setTimeout(calcularStockFinal, 100);
    }
}

function cargarDatosEliminar(id, nombre) {
    console.log(`=== DEBUG: Cargando datos eliminar ID ${id} ===`);
    
    document.getElementById('producto_id_eliminar').value = id;
    document.getElementById('nombre_producto_eliminar').textContent = nombre;
    
    // Configurar la acción del formulario
    document.getElementById('formEliminarProducto').action = `/auth/vendedor/productos/eliminar/${id}/`;
    console.log(`Form action delete: ${document.getElementById('formEliminarProducto').action}`);
    
    // Resetear campos del modal de eliminación
    resetearModalEliminacion();
    
    // ✅ ACTUALIZAR MENSAJE PARA REFLEJAR LA NUEVA FUNCIONALIDAD
    const mensajeEliminar = document.querySelector('#modalEliminarProducto .modal-body p');
    const alertaEliminar = document.querySelector('#modalEliminarProducto .alert-warning');
    
    if (mensajeEliminar) {
        mensajeEliminar.innerHTML = `¿Estás seguro de que deseas <strong>eliminar permanentemente</strong> el producto?`;
    }
    
    if (alertaEliminar) {
        alertaEliminar.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <strong>Advertencia:</strong> Esta acción no se puede deshacer. 
            Se eliminarán también todas las variantes del producto y se registrará 
            el movimiento en el historial de stock.
        `;
    }
}

// ==================== FUNCIONALIDAD DEL MODAL DE ELIMINACIÓN ====================

function inicializarModalEliminacion() {
    const motivoSelect = document.getElementById('motivo_eliminacion');
    const motivoPersonalizadoDiv = document.getElementById('campo_motivo_personalizado');
    const motivoPersonalizadoInput = document.getElementById('motivo_personalizado');
    const confirmCheckbox = document.getElementById('confirmar_eliminacion');
    const submitBtn = document.getElementById('btn_confirmar_eliminacion');

    // Mostrar/ocultar campo de motivo personalizado
    if (motivoSelect && motivoPersonalizadoDiv) {
        motivoSelect.addEventListener('change', function() {
            if (this.value === 'Otro motivo') {
                motivoPersonalizadoDiv.style.display = 'block';
                if (motivoPersonalizadoInput) {
                    motivoPersonalizadoInput.required = true;
                }
            } else {
                motivoPersonalizadoDiv.style.display = 'none';
                if (motivoPersonalizadoInput) {
                    motivoPersonalizadoInput.required = false;
                    motivoPersonalizadoInput.value = '';
                }
            }
            actualizarBotonEliminacion();
        });
    }

    // Habilitar/deshabilitar botón de confirmación
    if (confirmCheckbox && submitBtn) {
        confirmCheckbox.addEventListener('change', function() {
            actualizarBotonEliminacion();
        });
    }

    // Validar campo de motivo personalizado
    if (motivoPersonalizadoInput) {
        motivoPersonalizadoInput.addEventListener('input', function() {
            actualizarBotonEliminacion();
        });
    }

    // Validación antes de enviar el formulario
    const formEliminar = document.getElementById('formEliminarProducto');
    if (formEliminar) {
        formEliminar.addEventListener('submit', function(e) {
            if (!validarFormularioEliminacion()) {
                e.preventDefault();
                return;
            }

            // Mostrar loading en el botón
            if (submitBtn) {
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Eliminando...';
                submitBtn.disabled = true;
            }
        });
    }

    // Resetear formulario cuando se cierre el modal
    const modalEliminar = document.getElementById('modalEliminarProducto');
    if (modalEliminar) {
        modalEliminar.addEventListener('hidden.bs.modal', function() {
            resetearModalEliminacion();
        });
    }
}

function validarFormularioEliminacion() {
    const motivoSelect = document.getElementById('motivo_eliminacion');
    const motivoPersonalizadoInput = document.getElementById('motivo_personalizado');
    const confirmCheckbox = document.getElementById('confirmar_eliminacion');

    if (!motivoSelect || !motivoSelect.value) {
        showAlert('Por favor selecciona un motivo de eliminación.', 'warning');
        motivoSelect.focus();
        return false;
    }

    if (!confirmCheckbox || !confirmCheckbox.checked) {
        showAlert('Debes confirmar que entiendes las consecuencias de esta acción.', 'warning');
        return false;
    }

    // Si es "Otro motivo", validar que se especifique
    if (motivoSelect.value === 'Otro motivo') {
        if (!motivoPersonalizadoInput || !motivoPersonalizadoInput.value.trim()) {
            showAlert('Por favor especifica el motivo de eliminación.', 'warning');
            motivoPersonalizadoInput.focus();
            return false;
        }
    }

    return true;
}

function actualizarBotonEliminacion() {
    const motivoSelect = document.getElementById('motivo_eliminacion');
    const motivoPersonalizadoInput = document.getElementById('motivo_personalizado');
    const confirmCheckbox = document.getElementById('confirmar_eliminacion');
    const submitBtn = document.getElementById('btn_confirmar_eliminacion');

    if (!submitBtn) return;

    const motivoValido = motivoSelect && motivoSelect.value;
    const motivoPersonalizadoValido = motivoSelect.value !== 'Otro motivo' || 
                                    (motivoPersonalizadoInput && motivoPersonalizadoInput.value.trim());
    const confirmado = confirmCheckbox && confirmCheckbox.checked;

    submitBtn.disabled = !(motivoValido && motivoPersonalizadoValido && confirmado);
}

function resetearModalEliminacion() {
    const motivoSelect = document.getElementById('motivo_eliminacion');
    const motivoPersonalizadoDiv = document.getElementById('campo_motivo_personalizado');
    const motivoPersonalizadoInput = document.getElementById('motivo_personalizado');
    const confirmCheckbox = document.getElementById('confirmar_eliminacion');
    const submitBtn = document.getElementById('btn_confirmar_eliminacion');

    if (motivoSelect) motivoSelect.value = '';
    if (motivoPersonalizadoDiv) motivoPersonalizadoDiv.style.display = 'none';
    if (motivoPersonalizadoInput) {
        motivoPersonalizadoInput.value = '';
        motivoPersonalizadoInput.required = false;
    }
    if (confirmCheckbox) confirmCheckbox.checked = false;
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-trash-alt me-1"></i> Confirmar Eliminación';
    }
    
    // Remover alertas temporales
    const modalEliminar = document.getElementById('modalEliminarProducto');
    if (modalEliminar) {
        const alerts = modalEliminar.querySelectorAll('.alert:not(.alert-warning):not(.alert-info)');
        alerts.forEach(alert => alert.remove());
    }
}

function showAlert(message, type) {
    // Crear alerta temporal
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insertar al inicio del modal body
    const modalBody = document.querySelector('#modalEliminarProducto .modal-body');
    if (modalBody) {
        modalBody.insertBefore(alertDiv, modalBody.firstChild);
        
        // Auto-remover después de 5 segundos
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// ==================== FUNCIONES UTILITARIAS ====================

// Función para debug adicional
function debugForms() {
    console.log("=== DEBUG FORMS ===");
    const forms = document.querySelectorAll('form');
    forms.forEach((form, index) => {
        console.log(`Form ${index}:`, form.action, form.method);
    });
}

// Función para mostrar notificaciones toast
function mostrarToast(mensaje, tipo = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;

    const toastId = 'toast-' + Date.now();
    const bgColor = tipo === 'success' ? 'bg-success' : 
                   tipo === 'error' ? 'bg-danger' : 
                   tipo === 'warning' ? 'bg-warning' : 'bg-info';

    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgColor} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${mensaje}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();

    // Remover del DOM después de que se oculte
    toastElement.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

// Ejecutar debug al cargar
setTimeout(debugForms, 1000);
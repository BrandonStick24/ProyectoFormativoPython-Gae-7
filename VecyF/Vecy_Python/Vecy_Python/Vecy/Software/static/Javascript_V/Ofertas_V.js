// static/Javascript_V/Ofertas_V.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('Sistema de ofertas cargado correctamente');
    
    // Funcionalidad para el toggle de estado del negocio
    const businessToggle = document.getElementById('businessToggle');
    if (businessToggle) {
        businessToggle.addEventListener('click', function () {
            const statusText = document.getElementById('statusText');
            const isActive = this.classList.toggle('active');
            statusText.textContent = isActive ? 'Abierto' : 'Cerrado';
            statusText.style.color = isActive ? '#10b981' : '#6b7280';
        });
    }

    // Funcionalidades de botones principales
    const btnAddOffer = document.getElementById('btnAddOffer');
    if (btnAddOffer) {
        btnAddOffer.addEventListener('click', function () {
            // Scroll a la sección de productos disponibles
            const contenedorProductos = document.getElementById('contenedorProductos');
            if (contenedorProductos) {
                contenedorProductos.scrollIntoView({ 
                    behavior: 'smooth' 
                });
            }
        });
    }

    const btnImportOffers = document.getElementById('btnImportOffers');
    if (btnImportOffers) {
        btnImportOffers.addEventListener('click', function () {
            alert('Funcionalidad de Importar Ofertas - Próximamente disponible');
        });
    }

    const btnExportOffers = document.getElementById('btnExportOffers');
    if (btnExportOffers) {
        btnExportOffers.addEventListener('click', function () {
            alert('Funcionalidad de Exportar Ofertas - Próximamente disponible');
        });
    }

    // Funcionalidades para botones de la tabla
    document.addEventListener('click', function (e) {
        // Botón editar
        if (e.target.closest('.btn-edit')) {
            const row = e.target.closest('tr');
            const id = row.cells[0].textContent;
            const name = row.cells[1].textContent;
            alert(`Editar oferta: ${name} (ID: ${id}) - Próximamente disponible`);
        }

        // Botón eliminar
        if (e.target.closest('.btn-delete')) {
            const row = e.target.closest('tr');
            const name = row.cells[1].textContent;
            if (confirm(`¿Estás seguro de que deseas eliminar la oferta "${name}"?`)) {
                // Aquí iría la lógica real de eliminación
                alert('Oferta eliminada correctamente');
            }
        }

        // Botón cambiar estado
        if (e.target.closest('.btn-status')) {
            const row = e.target.closest('tr');
            const badge = row.querySelector('.status-badge');
            const button = e.target.closest('.btn-status');

            if (badge.classList.contains('status-active')) {
                badge.classList.remove('status-active');
                badge.classList.add('status-inactive');
                badge.textContent = 'Inactiva';
                button.innerHTML = '<i class="fas fa-toggle-off"></i>';
            } else if (badge.classList.contains('status-inactive')) {
                badge.classList.remove('status-inactive');
                badge.classList.add('status-active');
                badge.textContent = 'Activa';
                button.innerHTML = '<i class="fas fa-toggle-on"></i>';
            }
        }
    });

    // Modificar la función de selección de productos para incluir variantes
    document.querySelectorAll('.seleccionar-producto').forEach(button => {
        button.addEventListener('click', function() {
            const productoId = this.getAttribute('data-producto-id');
            
            // Verificar si el producto tiene variantes
            fetch(`/vendedor/productos/${productoId}/tiene-variantes/`)
                .then(response => response.json())
                .then(data => {
                    if (data.tiene_variantes) {
                        // Mostrar selector de variante
                        mostrarSelectorVariante(productoId, this);
                    } else {
                        // Seleccionar producto directamente
                        seleccionarProductoDirecto(this);
                    }
                })
                .catch(error => {
                    console.error('Error verificando variantes:', error);
                    seleccionarProductoDirecto(this);
                });
        });
    });

    // Auto-actualización de estado de ofertas cada 5 minutos
    setInterval(function() {
        console.log('Verificando estado de ofertas...');
        // Aquí podrías agregar una llamada AJAX para actualizar el estado
    }, 300000); // 5 minutos
});

// Mostrar selector de variante
function mostrarSelectorVariante(productoId, button) {
    fetch(`/vendedor/productos/${productoId}/variantes-oferta/`)
        .then(response => response.json())
        .then(data => {
            const modalHTML = `
                <div class="modal fade" id="modalSelectorVariante" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Seleccionar Variante</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <p>Este producto tiene variantes. Selecciona cuál quieres poner en oferta:</p>
                                <div class="list-group">
                                    <button type="button" class="list-group-item list-group-item-action" 
                                            onclick="seleccionarParaOferta(${productoId}, null, this)">
                                        <strong>Producto Base</strong><br>
                                        <small>Precio: $${data.precio_base} | Stock: ${data.stock_base}</small>
                                    </button>
                                    ${data.variantes.map(variante => `
                                        <button type="button" class="list-group-item list-group-item-action" 
                                                onclick="seleccionarParaOferta(${productoId}, ${variante.id}, this)">
                                            <strong>${variante.nombre}</strong><br>
                                            <small>Precio: $${variante.precio_total} | Stock: ${variante.stock}</small>
                                        </button>
                                    `).join('')}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Agregar modal al DOM
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            const modal = new bootstrap.Modal(document.getElementById('modalSelectorVariante'));
            modal.show();
            
            // Remover modal después de cerrar
            document.getElementById('modalSelectorVariante').addEventListener('hidden.bs.modal', function() {
                this.remove();
            });
        })
        .catch(error => {
            console.error('Error cargando variantes:', error);
            seleccionarProductoDirecto(button);
        });
}

// Seleccionar producto/variante para oferta
function seleccionarParaOferta(productoId, varianteId, element) {
    const button = document.querySelector(`.seleccionar-producto[data-producto-id="${productoId}"]`);
    const productoData = {
        id: productoId,
        nombre: button.getAttribute('data-producto-nombre'),
        precio: parseFloat(button.getAttribute('data-producto-precio')),
        stock: parseInt(button.getAttribute('data-producto-stock')),
        categoria: button.getAttribute('data-producto-categoria'),
        variante_id: varianteId
    };
    
    // Si hay variante, actualizar nombre y precio
    if (varianteId) {
        const varianteNombre = element.querySelector('strong').textContent;
        const variantePrecio = parseFloat(element.querySelector('small').textContent.match(/\$(\d+)/)[1]);
        
        productoData.nombre += ` - ${varianteNombre}`;
        productoData.precio = variantePrecio;
    }
    
    // Agregar a productos seleccionados (usando la función existente)
    if (typeof productosSeleccionados !== 'undefined') {
        productosSeleccionados.push(productoData);
        actualizarConfiguraciones();
        actualizarContador();
        
        // Deshabilitar el botón
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-check me-1"></i>Seleccionado';
        button.classList.remove('btn-outline-primary');
        button.classList.add('btn-outline-success');
    }
    
    // Cerrar modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('modalSelectorVariante'));
    if (modal) {
        modal.hide();
    }
}

// Seleccionar producto directamente (sin variantes)
function seleccionarProductoDirecto(button) {
    const productoId = button.getAttribute('data-producto-id');
    const varianteId = button.getAttribute('data-variante-id') || '';
    const productoKey = `${productoId}-${varianteId}`;
    
    // Verificar si ya está seleccionado
    if (typeof productosSeleccionados !== 'undefined' && productosSeleccionados.find(p => p.key === productoKey)) {
        alert('Este producto/variante ya está seleccionado');
        return;
    }

    const producto = {
        key: productoKey,
        id: productoId,
        nombre: button.getAttribute('data-producto-nombre'),
        precio: parseFloat(button.getAttribute('data-producto-precio')),
        stock: parseInt(button.getAttribute('data-producto-stock')),
        categoria: button.getAttribute('data-producto-categoria'),
        variante_id: varianteId
    };

    if (typeof productosSeleccionados !== 'undefined') {
        productosSeleccionados.push(producto);
        actualizarConfiguraciones();
        actualizarContador();
        
        // Deshabilitar el botón
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-check me-1"></i>Seleccionado';
        button.classList.remove('btn-outline-primary', 'btn-outline-info');
        button.classList.add('btn-outline-success');
    }
}

// Funciones auxiliares globales
function mostrarDetallesOferta(ofertaId) {
    alert(`Mostrando detalles de oferta ID: ${ofertaId} - Próximamente disponible`);
}

function duplicarOferta(ofertaId) {
    if (confirm('¿Deseas duplicar esta oferta?')) {
        alert(`Duplicando oferta ID: ${ofertaId} - Próximamente disponible`);
    }
}

// Funciones para manejo de errores
function manejarErrorOferta(error) {
    console.error('Error en sistema de ofertas:', error);
    alert('Ha ocurrido un error al procesar la oferta. Por favor, intenta nuevamente.');
}

// Funciones para validaciones adicionales
function validarFechasOferta(fechaInicio, fechaFin, horaInicio = '00:00', horaFin = '23:59') {
    const hoy = new Date().toISOString().split('T')[0];
    if (fechaInicio < hoy) {
        alert('La fecha de inicio no puede ser en el pasado');
        return false;
    }
    
    const fechaHoraInicio = new Date(`${fechaInicio}T${horaInicio}`);
    const fechaHoraFin = new Date(`${fechaFin}T${horaFin}`);
    
    if (fechaHoraInicio >= fechaHoraFin) {
        alert('La fecha y hora de fin deben ser posteriores al inicio');
        return false;
    }
    return true;
}

function validarStockOferta(stockOferta, stockDisponible) {
    if (stockOferta <= 0) {
        alert('El stock de oferta debe ser mayor a 0');
        return false;
    }
    if (stockOferta > stockDisponible) {
        alert(`El stock de oferta no puede ser mayor al stock disponible (${stockDisponible})`);
        return false;
    }
    return true;
}

// Función para formatear precios
function formatearPrecio(precio) {
    return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        minimumFractionDigits: 0
    }).format(precio);
}

// Función para calcular descuentos
function calcularPrecioConDescuento(precioOriginal, porcentajeDescuento) {
    return precioOriginal * (1 - porcentajeDescuento / 100);
}

// Función para mostrar notificaciones
function mostrarNotificacion(mensaje, tipo = 'success') {
    const alertClass = tipo === 'success' ? 'alert-success' : 
                      tipo === 'error' ? 'alert-danger' : 
                      tipo === 'warning' ? 'alert-warning' : 'alert-info';
    
    const notificacionHTML = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${mensaje}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Insertar al inicio del contenido principal
    const mainContent = document.querySelector('.container-fluid');
    if (mainContent) {
        mainContent.insertAdjacentHTML('afterbegin', notificacionHTML);
        
        // Auto-eliminar después de 5 segundos
        setTimeout(() => {
            const alert = document.querySelector('.alert');
            if (alert) {
                alert.remove();
            }
        }, 5000);
    }
}

// Función para calcular fecha y hora de expiración
function calcularExpiracionOferta(fechaFin, horaFin) {
    const ahora = new Date();
    const expiracion = new Date(`${fechaFin}T${horaFin}`);
    const diferencia = expiracion - ahora;
    
    if (diferencia <= 0) {
        return 'Expirada';
    }
    
    const horas = Math.floor(diferencia / (1000 * 60 * 60));
    const minutos = Math.floor((diferencia % (1000 * 60 * 60)) / (1000 * 60));
    
    return `${horas}h ${minutos}m`;
}

// Función para verificar ofertas próximas a expirar
function verificarOfertasProximasExpiracion() {
    const ofertas = document.querySelectorAll('.oferta-activa');
    const ahora = new Date();
    
    ofertas.forEach(oferta => {
        const fechaFin = oferta.getAttribute('data-fecha-fin');
        const horaFin = oferta.getAttribute('data-hora-fin');
        
        if (fechaFin && horaFin) {
            const expiracion = new Date(`${fechaFin}T${horaFin}`);
            const diferencia = expiracion - ahora;
            const horasRestantes = diferencia / (1000 * 60 * 60);
            
            if (horasRestantes <= 4 && horasRestantes > 0) {
                oferta.classList.add('oferta-proxima-expiracion');
            }
        }
    });
}

// Exportar funciones para uso global (si es necesario)
if (typeof window !== 'undefined') {
    window.mostrarDetallesOferta = mostrarDetallesOferta;
    window.duplicarOferta = duplicarOferta;
    window.manejarErrorOferta = manejarErrorOferta;
    window.validarFechasOferta = validarFechasOferta;
    window.validarStockOferta = validarStockOferta;
    window.formatearPrecio = formatearPrecio;
    window.calcularPrecioConDescuento = calcularPrecioConDescuento;
    window.mostrarNotificacion = mostrarNotificacion;
    window.calcularExpiracionOferta = calcularExpiracionOferta;
    window.verificarOfertasProximasExpiracion = verificarOfertasProximasExpiracion;
}

// Verificar ofertas próximas a expirar cada minuto
setInterval(verificarOfertasProximasExpiracion, 60000);

// Ejecutar al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    verificarOfertasProximasExpiracion();
});
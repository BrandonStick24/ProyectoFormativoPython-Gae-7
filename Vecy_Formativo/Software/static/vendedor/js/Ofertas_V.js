// static/Javascript_V/Ofertas_V.js

// Función para mostrar selector de variante
function mostrarSelectorVariante(productoId, button) {
    // Implementación básica - puedes expandir esto según necesites
    console.log(`Mostrar selector de variante para producto ${productoId}`);
    
    // Aquí deberías hacer una llamada AJAX para obtener las variantes
    // Por ahora, vamos a seleccionar directamente
    seleccionarProductoDirecto(button);
}

// Seleccionar producto directamente (sin variantes)
function seleccionarProductoDirecto(button) {
    const productoId = button.getAttribute('data-producto-id');
    const varianteId = button.getAttribute('data-variante-id') || '';
    const productoKey = `${productoId}-${varianteId}`;
    
    // Verificar si ya está seleccionado
    if (typeof window.productosSeleccionados !== 'undefined' && 
        window.productosSeleccionados.find(p => p.key === productoKey)) {
        mostrarNotificacion('Este producto/variante ya está seleccionado', 'warning');
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

    if (typeof window.productosSeleccionados !== 'undefined') {
        window.productosSeleccionados.push(producto);
        
        // Actualizar configuraciones si la función existe
        if (typeof window.actualizarConfiguraciones === 'function') {
            window.actualizarConfiguraciones();
        }
        
        // Actualizar contador si la función existe
        if (typeof window.actualizarContador === 'function') {
            window.actualizarContador();
        }
        
        // Guardar selección si la función existe
        if (typeof window.guardarSeleccion === 'function') {
            window.guardarSeleccion();
        }
        
        // Deshabilitar el botón
        button.disabled = true;
        button.classList.add('seleccionado');
        
        mostrarNotificacion(`"${producto.nombre}" agregado a configuración`, 'success');
    }
}

// Seleccionar producto/variante para oferta
function seleccionarParaOferta(productoId, varianteId, element) {
    // Esta función se mantiene para compatibilidad
    const button = document.querySelector(`.seleccionar-producto[data-producto-id="${productoId}"]`);
    if (button) {
        seleccionarProductoDirecto(button);
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

// Función para mostrar notificaciones (compatibilidad con código existente)
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

// Exportar funciones para uso global
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
    window.mostrarSelectorVariante = mostrarSelectorVariante;
    window.seleccionarProductoDirecto = seleccionarProductoDirecto;
    window.seleccionarParaOferta = seleccionarParaOferta;
}

// Ejecutar al cargar la página (solo si estamos en la página de ofertas)
document.addEventListener('DOMContentLoaded', function() {
    console.log('JavaScript de ofertas cargado');
    
    // Solo ejecutar funciones específicas si estamos en la página de ofertas
    if (window.location.pathname.includes('ofertas')) {
        verificarOfertasProximasExpiracion();
        
        // Auto-actualización cada minuto
        setInterval(verificarOfertasProximasExpiracion, 60000);
    }
});
// static/vendedor/js/Crud_V.js - VERSIÓN MEJORADA SIN AJAX - CORREGIDA

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

    // Debug: Verificar que los modales se cargan correctamente
    console.log("=== DEBUG: Modales disponibles ===");
    console.log("Modal Editar:", document.getElementById('modalEditarProducto'));
    console.log("Modal Stock:", document.getElementById('modalAjustarStock'));
    console.log("Modal Eliminar:", document.getElementById('modalEliminarProducto'));
});

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
    document.getElementById('formAjustarStock').action = `/auth/vendedor/stock/ajustar/${id}/`;
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
    
    // Configurar la acción del formulario - CORREGIDO
    document.getElementById('formEliminarProducto').action = `/auth/vendedor/productos/eliminar/${id}/`;
    console.log(`Form action delete: ${document.getElementById('formEliminarProducto').action}`);
}

// Función para debug adicional
function debugForms() {
    console.log("=== DEBUG FORMS ===");
    const forms = document.querySelectorAll('form');
    forms.forEach((form, index) => {
        console.log(`Form ${index}:`, form.action, form.method);
    });
}

// Ejecutar debug al cargar
setTimeout(debugForms, 1000);
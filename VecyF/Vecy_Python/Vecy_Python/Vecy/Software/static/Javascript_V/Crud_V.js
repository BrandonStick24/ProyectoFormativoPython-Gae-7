// static/javascript_V/Crud_V.js
// JAVASCRIPT SIMPLIFICADO PARA EL CRUD DE PRODUCTOS - SIN AJAX

document.addEventListener('DOMContentLoaded', function () {
    // Inicializar tooltips de Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Filtros y búsqueda
    const selectFiltro = document.getElementById('selectFiltro');
    const inputBusqueda = document.getElementById('inputBusqueda');
    
    function aplicarFiltros() {
        const filtro = selectFiltro.value;
        const texto = inputBusqueda.value.toLowerCase();
        const filas = document.querySelectorAll('#cuerpoTablaProductos tr');
        
        filas.forEach(fila => {
            if (fila.cells.length < 2) return;
            
            const textoFila = fila.textContent.toLowerCase();
            const esOferta = fila.classList.contains('producto-oferta');
            const stock = parseInt(fila.cells[3].querySelector('.fw-bold').textContent) || 0;
            const estado = fila.cells[4].textContent.toLowerCase();
            
            let mostrar = true;
            
            // Aplicar filtro seleccionado
            if (filtro === 'oferta' && !esOferta) {
                mostrar = false;
            } else if (filtro === 'disponible' && (stock === 0 || estado.includes('agotado'))) {
                mostrar = false;
            } else if (filtro === 'sin-stock' && stock > 0) {
                mostrar = false;
            }
            
            // Aplicar búsqueda de texto
            if (mostrar && texto && !textoFila.includes(texto)) {
                mostrar = false;
            }
            
            fila.style.display = mostrar ? '' : 'none';
        });
    }

    if (selectFiltro && inputBusqueda) {
        selectFiltro.addEventListener('change', aplicarFiltros);
        inputBusqueda.addEventListener('input', aplicarFiltros);
    }

    // Ordenamiento
    let ordenAscendente = true;
    const btnOrdenAsc = document.getElementById('btnOrdenAsc');
    if (btnOrdenAsc) {
        btnOrdenAsc.addEventListener('click', function() {
            ordenAscendente = !ordenAscendente;
            this.innerHTML = ordenAscendente ? '<i class="fas fa-sort-amount-up"></i>' : '<i class="fas fa-sort-amount-down"></i>';
        });
    }

    // Funcionalidad de botones de acción
    const btnImportarExcel = document.getElementById('btnImportarExcel');
    if (btnImportarExcel) {
        btnImportarExcel.addEventListener('click', function() {
            alert('Funcionalidad de Importar Excel - Aquí se abriría un selector de archivos');
        });
    }

    const btnExportar = document.getElementById('btnExportar');
    if (btnExportar) {
        btnExportar.addEventListener('click', function() {
            alert('Funcionalidad de Exportar - Aquí se exportarían los datos a Excel o CSV');
        });
    }

    // Lógica para calcular stock final en ajuste de stock
    const tipoAjuste = document.getElementById('tipo_ajuste');
    const cantidadAjuste = document.getElementById('cantidad_ajuste');
    const stockActual = document.getElementById('stock_actual');
    const stockFinal = document.getElementById('stock_final');
    const textoAyuda = document.getElementById('texto_ayuda');
    const campoStockFinal = document.getElementById('campo_stock_final');

    function calcularStockFinal() {
        const stockActualVal = parseInt(stockActual.value) || 0;
        const cantidadVal = parseInt(cantidadAjuste.value) || 0;
        const tipo = tipoAjuste.value;

        let stockFinalVal = stockActualVal;
        
        if (tipo === 'entrada') {
            stockFinalVal = stockActualVal + cantidadVal;
            textoAyuda.textContent = `Se sumarán ${cantidadVal} unidades al stock actual`;
        } else if (tipo === 'salida') {
            stockFinalVal = stockActualVal - cantidadVal;
            textoAyuda.textContent = `Se restarán ${cantidadVal} unidades al stock actual`;
            if (stockFinalVal < 0) {
                textoAyuda.innerHTML = `<span class="text-danger">⚠️ El stock final no puede ser negativo</span>`;
            }
        } else {
            stockFinalVal = cantidadVal;
            textoAyuda.textContent = `El stock se establecerá en ${cantidadVal} unidades`;
        }

        stockFinal.value = stockFinalVal;
        
        // Mostrar/ocultar campo de stock final
        if (cantidadVal > 0) {
            campoStockFinal.style.display = 'block';
            stockFinal.className = `form-control ${stockFinalVal < 0 ? 'is-invalid' : (stockFinalVal <= 5 ? 'is-warning' : 'is-valid')}`;
        } else {
            campoStockFinal.style.display = 'none';
        }
    }

    if (tipoAjuste && cantidadAjuste) {
        tipoAjuste.addEventListener('change', calcularStockFinal);
        cantidadAjuste.addEventListener('input', calcularStockFinal);
    }
});
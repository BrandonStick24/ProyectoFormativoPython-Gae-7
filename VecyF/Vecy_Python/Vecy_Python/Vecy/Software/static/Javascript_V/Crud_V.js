// static/javascript_V/Crud_V.js
// JAVASCRIPT SIMPLIFICADO PARA EL CRUD DE PRODUCTOS

document.addEventListener('DOMContentLoaded', function () {
    // Inicializar tooltips de Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Variables globales para los modales
    let modalEditar = null;
    let modalStock = null;
    let modalEstado = null;
    let modalEliminar = null;

    // Inicializar Select2 para categorías en AGREGAR
    function inicializarSelectCategorias() {
        $('#categoria_prod').select2({
            placeholder: "Busca o selecciona una categoría...",
            allowClear: true,
            width: '100%',
            language: {
                noResults: function () {
                    return "No se encontraron categorías";
                },
                searching: function () {
                    return "Buscando...";
                }
            },
            dropdownParent: $('#modalAgregarProducto')
        });
    }

    // Inicializar Select2 para el modal de EDITAR
    function inicializarSelectEditar() {
        $('#categoria_prod_editar').select2({
            placeholder: "Busca o selecciona una categoría...",
            allowClear: true,
            width: '100%',
            language: {
                noResults: function () {
                    return "No se encontraron categorías";
                },
                searching: function () {
                    return "Buscando...";
                }
            },
            dropdownParent: $('#modalEditarProducto')
        });
    }

    // Inicializar modales
    function inicializarModales() {
        modalEditar = new bootstrap.Modal(document.getElementById('modalEditarProducto'));
        modalStock = new bootstrap.Modal(document.getElementById('modalAjustarStock'));
        modalEstado = new bootstrap.Modal(document.getElementById('modalCambiarEstado'));
        modalEliminar = new bootstrap.Modal(document.getElementById('modalEliminarProducto'));
    }

    // Función auxiliar para escapar HTML - CORREGIDA
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Funciones para cargar datos de productos - SIMPLIFICADA
    // Funciones para cargar datos de productos - SIMPLIFICADA
    function cargarDatosProducto(productoId) {
        console.log('Cargando datos del producto ID:', productoId);

        fetch(`/vendedor/productos/datos/${productoId}/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error en la respuesta del servidor: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }

                console.log('Datos del producto recibidos:', data);

                // Llenar el formulario con los datos - USANDO LA FUNCIÓN escapeHtml CORREGIDA
                const contenido = `
            <input type="hidden" name="producto_id" value="${data.pkid_prod}">
            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <label for="nom_prod_editar" class="form-label">Nombre del Producto *</label>
                        <input type="text" class="form-control" id="nom_prod_editar" name="nom_prod" 
                               value="${escapeHtml(data.nom_prod)}" required>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-3">
                        <label for="precio_prod_editar" class="form-label">Precio *</label>
                        <div class="input-group">
                            <span class="input-group-text">$</span>
                            <input type="text" class="form-control" id="precio_prod_editar" name="precio_prod"
                                   value="${escapeHtml(data.precio_prod)}" required>
                        </div>
                        <div class="form-text">Máximo: $99'999.999</div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <label for="categoria_prod_editar" class="form-label">Categoría *</label>
                        <select class="form-control" id="categoria_prod_editar" name="categoria_prod" required>
                            <option value="">Selecciona una categoría...</option>
                        </select>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-3">
                        <label for="stock_prod_editar" class="form-label">Stock</label>
                        <input type="number" class="form-control" id="stock_prod_editar" name="stock_prod" 
                               min="0" value="${data.stock_prod || 0}">
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <label for="estado_prod_editar" class="form-label">Estado del Producto</label>
                        <select class="form-control" id="estado_prod_editar" name="estado_prod">
                            <option value="disponible" ${data.estado_prod === 'disponible' ? 'selected' : ''}>Disponible</option>
                            <option value="no_disponible" ${data.estado_prod === 'no_disponible' ? 'selected' : ''}>No Disponible</option>
                            <option value="agotado" ${data.estado_prod === 'agotado' ? 'selected' : ''}>Agotado</option>
                        </select>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-3">
                        <label for="img_prod_editar" class="form-label">Imagen del Producto</label>
                        <input type="file" class="form-control" id="img_prod_editar" name="img_prod" accept="image/*">
                        <div class="form-text">
                            ${data.img_prod_actual ? 'Imagen actual: ' + escapeHtml(data.img_prod_actual.split('/').pop()) : 'Sin imagen actual'}
                        </div>
                    </div>
                </div>
            </div>

            <div class="mb-3">
                <label for="desc_prod_editar" class="form-label">Descripción</label>
                <textarea class="form-control" id="desc_prod_editar" name="desc_prod" rows="3"
                          placeholder="Describe tu producto...">${escapeHtml(data.desc_prod || '')}</textarea>
            </div>
        `;

                document.getElementById('contenidoEditarProducto').innerHTML = contenido;

                // Actualizar la acción del formulario con el ID correcto
                const form = document.getElementById('formEditarProducto');
                form.action = `/vendedor/editar-producto/${productoId}/`;

                // Inicializar Select2 y establecer la categoría seleccionada
                setTimeout(() => {
                    $('#categoria_prod_editar').select2({
                        placeholder: "Busca o selecciona una categoría...",
                        allowClear: true,
                        width: '100%',
                        dropdownParent: $('#modalEditarProducto')
                    });

                    // COPIAR LAS CATEGORÍAS DEL MODAL DE AGREGAR (QUE YA FUNCIONAN)
                    const categoriasDelModalAgregar = $('#categoria_prod').html();
                    $('#categoria_prod_editar').html(categoriasDelModalAgregar);

                    // Establecer la categoría seleccionada
                    if (data.categoria_prod) {
                        $('#categoria_prod_editar').val(data.categoria_prod).trigger('change');
                    }
                }, 100);

            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error al cargar los datos del producto: ' + error.message);
            });
    }

    // Funciones para abrir modales
    function abrirModalEditar(productoId) {
        if (!modalEditar) {
            modalEditar = new bootstrap.Modal(document.getElementById('modalEditarProducto'));
        }

        // Limpiar contenido anterior
        document.getElementById('contenidoEditarProducto').innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
                <p class="mt-2">Cargando información del producto...</p>
            </div>
        `;

        modalEditar.show();
        cargarDatosProducto(productoId);
    }

    function abrirModalStock(productoId) {
        // Buscar el producto en la tabla para obtener los datos
        const botonStock = document.querySelector(`.ajustar-stock[data-id="${productoId}"]`);
        if (!botonStock) {
            console.error('No se encontró el botón de stock para el producto:', productoId);
            return;
        }

        const fila = botonStock.closest('tr');
        const nombreProducto = fila.querySelector('td:nth-child(2)').textContent.trim();

        // Obtener el stock actual del tooltip
        const tooltipText = botonStock.getAttribute('data-bs-title');
        let stockActual = 0;

        if (tooltipText && tooltipText.includes('Stock actual:')) {
            stockActual = parseInt(tooltipText.replace('Stock actual:', '').trim());
        }

        // Llenar el modal de ajustar stock
        document.getElementById('producto_id_stock').value = productoId;
        document.getElementById('nombre_producto_stock').textContent = nombreProducto;
        document.getElementById('stock_actual').value = stockActual;
        document.getElementById('nuevo_stock').value = stockActual;
        document.getElementById('nuevo_stock').focus();

        document.getElementById('formAjustarStock').action = `/vendedor/productos/ajustar-stock/${productoId}/`;

        if (!modalStock) {
            modalStock = new bootstrap.Modal(document.getElementById('modalAjustarStock'));
        }
        modalStock.show();
    }

    function abrirModalEstado(productoId) {
        // Buscar el producto en la tabla para obtener los datos
        const botonEstado = document.querySelector(`.cambiar-estado[data-id="${productoId}"]`);
        if (!botonEstado) {
            console.error('No se encontró el botón de estado para el producto:', productoId);
            return;
        }

        const fila = botonEstado.closest('tr');
        const nombreProducto = fila.querySelector('td:nth-child(2)').textContent.trim();
        const estadoActual = fila.querySelector('td:nth-child(5) .insignia-estado').textContent.trim();

        // Llenar el modal de cambiar estado
        document.getElementById('producto_id_estado').value = productoId;
        document.getElementById('nombre_producto_estado').textContent = nombreProducto;
        document.getElementById('estado_actual').textContent = estadoActual;

        // Aplicar clase según el estado
        const badge = document.getElementById('estado_actual');
        badge.className = 'badge ';
        if (estadoActual === 'Activo') {
            badge.classList.add('bg-success');
        } else if (estadoActual === 'Inactivo') {
            badge.classList.add('bg-secondary');
        } else {
            badge.classList.add('bg-warning');
        }

        document.getElementById('formCambiarEstado').action = `/vendedor/cambiar-estado-producto/${productoId}/`;

        if (!modalEstado) {
            modalEstado = new bootstrap.Modal(document.getElementById('modalCambiarEstado'));
        }
        modalEstado.show();
    }

    function abrirModalEliminar(productoId, nombreProducto) {
        document.getElementById('producto_id_eliminar').value = productoId;
        document.getElementById('nombre_producto_eliminar').textContent = nombreProducto;
        document.getElementById('formEliminarProducto').action = `/vendedor/eliminar-producto/${productoId}/`;

        if (!modalEliminar) {
            modalEliminar = new bootstrap.Modal(document.getElementById('modalEliminarProducto'));
        }
        modalEliminar.show();
    }

    // Manejar todos los botones de opciones
    document.addEventListener('click', function (e) {
        if (e.target.closest('.boton-opcion')) {
            const button = e.target.closest('.boton-opcion');
            const id = button.getAttribute('data-id');
            const action = button.getAttribute('data-action');
            const nombre = button.getAttribute('data-nombre');

            switch (action) {
                case 'editar':
                    e.preventDefault();
                    abrirModalEditar(id);
                    break;
                case 'stock':
                    e.preventDefault();
                    abrirModalStock(id);
                    break;
                case 'estado':
                    e.preventDefault();
                    abrirModalEstado(id);
                    break;
                case 'eliminar':
                    e.preventDefault();
                    abrirModalEliminar(id, nombre);
                    break;
            }
        }
    });

    // Búsqueda en tiempo real
    document.getElementById('inputBusqueda').addEventListener('input', function (e) {
        const textoBusqueda = e.target.value.toLowerCase();
        const filas = document.querySelectorAll('#cuerpoTablaProductos tr');

        filas.forEach(fila => {
            const textoFila = fila.textContent.toLowerCase();
            if (textoFila.includes(textoBusqueda)) {
                fila.style.display = '';
            } else {
                fila.style.display = 'none';
            }
        });
    });

    // Funcionalidad de ordenamiento
    let ordenAscendente = true;
    document.getElementById('btnOrdenAsc').addEventListener('click', function () {
        ordenAscendente = !ordenAscendente;
        this.innerHTML = ordenAscendente ? '<i class="fas fa-sort-amount-up"></i>' : '<i class="fas fa-sort-amount-down"></i>';
    });

    // Funcionalidad de botones de acción
    document.getElementById('btnImportarExcel').addEventListener('click', function () {
        alert('Funcionalidad de Importar Excel - Aquí se abriría un selector de archivos');
    });

    document.getElementById('btnExportar').addEventListener('click', function () {
        alert('Funcionalidad de Exportar - Aquí se exportarían los datos a Excel o CSV');
    });

    // Inicializar cuando se abre el modal de agregar
    $('#modalAgregarProducto').on('shown.bs.modal', function () {
        inicializarSelectCategorias();
    });

    // Limpiar contenido cuando se cierra el modal de editar
    $('#modalEditarProducto').on('hidden.bs.modal', function () {
        document.getElementById('contenidoEditarProducto').innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
                <p class="mt-2">Cargando información del producto...</p>
            </div>
        `;
    });

    // Inicializar modales al cargar la página
    inicializarModales();

    // Inicializar Select2 para el modal de agregar si ya está abierto
    if ($('#modalAgregarProducto').hasClass('show')) {
        inicializarSelectCategorias();
    }
});
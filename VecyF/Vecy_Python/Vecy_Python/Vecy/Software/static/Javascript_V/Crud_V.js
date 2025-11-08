// static/javascript_V/Crud_V.js
// JAVASCRIPT ESPECÍFICO PARA EL CRUD DE PRODUCTOS

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

    // Inicializar Select2 para categorías
    function inicializarSelectCategorias() {
        $('.select2-categoria').select2({
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

    // Inicializar Select2 para el modal de editar
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

    // Funciones para cargar datos de productos
    // Funciones para cargar datos de productos
    function cargarDatosProducto(productoId) {
        fetch(`/vendedor/productos/datos/${productoId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }

                // Llenar el formulario con los datos
                const contenido = `
                <input type="hidden" name="producto_id" value="${data.pkid_prod}">
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="nom_prod_editar" class="form-label">Nombre del Producto *</label>
                            <input type="text" class="form-control" id="nom_prod_editar" name="nom_prod" 
                                   value="${data.nom_prod}" required>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="precio_prod_editar" class="form-label">Precio *</label>
                            <div class="input-group">
                                <span class="input-group-text">$</span>
                                <input type="text" class="form-control" id="precio_prod_editar" name="precio_prod"
                                       value="${parseFloat(data.precio_prod).toLocaleString('es-CO')}" required>
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
                                {% for categoria in categorias %}
                                <option value="{{ categoria.pkid_cp }}">{{ categoria.desc_cp }}</option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="stock_prod_editar" class="form-label">Stock</label>
                            <input type="number" class="form-control" id="stock_prod_editar" name="stock_prod" 
                                   min="0" value="${data.stock_prod}">
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
                                ${data.img_prod_actual ? 'Imagen actual: ' + data.img_prod_actual.split('/').pop() : 'Sin imagen actual'}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="mb-3">
                    <label for="desc_prod_editar" class="form-label">Descripción</label>
                    <textarea class="form-control" id="desc_prod_editar" name="desc_prod" rows="3"
                              placeholder="Describe tu producto...">${data.desc_prod || ''}</textarea>
                </div>
            `;

                document.getElementById('contenidoEditarProducto').innerHTML = contenido;
                document.getElementById('formEditarProducto').action = `/vendedor/editar-producto/${productoId}/`;

                // Seleccionar la categoría correcta después de cargar el contenido
                setTimeout(() => {
                    document.getElementById('categoria_prod_editar').value = data.categoria_prod;
                }, 100);
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error al cargar los datos del producto');
            });
    }

    // Funciones para abrir modales
    function abrirModalEditar(productoId) {
        if (!modalEditar) {
            modalEditar = new bootstrap.Modal(document.getElementById('modalEditarProducto'));
        }
        modalEditar.show();
        cargarDatosProducto(productoId);
    }

    function abrirModalStock(productoId) {
        // Buscar el producto en la tabla para obtener los datos
        const fila = document.querySelector(`[data-id="${productoId}"]`).closest('tr');
        const nombreProducto = fila.querySelector('td:nth-child(2)').textContent.trim();

        // Obtener el stock actual del atributo data
        const stockActual = fila.querySelector('.ajustar-stock').getAttribute('data-bs-title').replace('Stock actual: ', '');

        // Llenar el modal de ajustar stock
        document.getElementById('producto_id_stock').value = productoId;
        document.getElementById('nombre_producto_stock').textContent = nombreProducto;
        document.getElementById('stock_actual').value = stockActual;
        document.getElementById('nuevo_stock').value = stockActual;

        // Actualizar el action del formulario
        document.getElementById('formAjustarStock').action = `/vendedor/ajustar-stock-producto/${productoId}/`;

        if (!modalStock) {
            modalStock = new bootstrap.Modal(document.getElementById('modalAjustarStock'));
        }
        modalStock.show();
    }

    function abrirModalEstado(productoId) {
        // Buscar el producto en la tabla para obtener los datos
        const fila = document.querySelector(`[data-id="${productoId}"]`).closest('tr');
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

        // Actualizar el action del formulario
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
    document.querySelectorAll('.boton-opcion').forEach(button => {
        button.addEventListener('click', function () {
            const id = this.getAttribute('data-id');
            const action = this.getAttribute('data-action');
            const nombre = this.getAttribute('data-nombre');

            switch (action) {
                case 'editar':
                    abrirModalEditar(id);
                    break;
                case 'stock':
                    abrirModalStock(id);
                    break;
                case 'estado':
                    abrirModalEstado(id);
                    break;
                case 'eliminar':
                    abrirModalEliminar(id, nombre);
                    break;
            }
        });
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
        // Aquí iría la lógica de ordenamiento real
    });

    // Funcionalidad de botones de acción
    document.getElementById('btnImportarExcel').addEventListener('click', function () {
        alert('Funcionalidad de Importar Excel - Aquí se abriría un selector de archivos');
    });

    document.getElementById('btnExportar').addEventListener('click', function () {
        alert('Funcionalidad de Exportar - Aquí se exportarían los datos a Excel o CSV');
    });

    // Limpiar contenido de modales al cerrarse
    const modales = ['modalEditarProducto', 'modalCambiarEstado', 'modalAjustarStock', 'modalEliminarProducto'];

    modales.forEach(modalId => {
        const modalElement = document.getElementById(modalId);
        if (modalElement) {
            modalElement.addEventListener('hidden.bs.modal', function () {
                // Limpiar contenido si es necesario
                if (modalId === 'modalEditarProducto') {
                    document.getElementById('contenidoEditarProducto').innerHTML = `
                        <div class="text-center py-4">
                            <div class="spinner-border" role="status">
                                <span class="visually-hidden">Cargando...</span>
                            </div>
                            <p class="mt-2">Cargando información del producto...</p>
                        </div>
                    `;
                }
            });
        }
    });

    // Inicializar cuando se abre el modal de agregar
    $('#modalAgregarProducto').on('shown.bs.modal', function () {
        inicializarSelectCategorias();
    });

    // Inicializar modales al cargar la página
    inicializarModales();

    // Inicializar Select2 para el modal de agregar si ya está abierto
    if ($('#modalAgregarProducto').hasClass('show')) {
        inicializarSelectCategorias();
    }
});
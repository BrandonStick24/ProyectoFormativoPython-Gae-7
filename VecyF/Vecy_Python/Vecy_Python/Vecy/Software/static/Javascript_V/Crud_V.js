// Alternar menú desplegable del usuario
        document.getElementById('botonDesplegableUsuario').addEventListener('click', function (e) {
            e.stopPropagation();
            document.getElementById('menuDesplegableUsuario').classList.toggle('mostrar');
        });

        // Cerrar menú desplegable al hacer clic fuera
        document.addEventListener('click', function () {
            document.getElementById('menuDesplegableUsuario').classList.remove('mostrar');
        });

        // Alternar estado del negocio
        const alternadorNegocio = document.getElementById('alternadorNegocio');
        const textoEstado = document.getElementById('textoEstado');
        let estaAbierto = false;

        alternadorNegocio.addEventListener('click', function () {
            estaAbierto = !estaAbierto;
            this.classList.toggle('activo');
            textoEstado.textContent = estaAbierto ? 'Abierto' : 'Cerrado';
            textoEstado.style.color = estaAbierto ? '#10b981' : '#6b7280';
        });

        // Funcionalidad de búsqueda (solo para demostración)
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

        // Funcionalidad de ordenamiento (solo para demostración)
        let ordenAscendente = true;
        document.getElementById('btnOrdenAsc').addEventListener('click', function () {
            ordenAscendente = !ordenAscendente;
            this.innerHTML = ordenAscendente ? '<i class="fas fa-sort-amount-up"></i>' : '<i class="fas fa-sort-amount-down"></i>';
        });

        // Funcionalidad de botones de acción (solo para demostración)
        document.getElementById('btnAgregarProducto').addEventListener('click', function () {
            alert('Funcionalidad de Agregar Producto - Aquí se abriría un modal o formulario');
        });

        document.getElementById('btnImportarExcel').addEventListener('click', function () {
            alert('Funcionalidad de Importar Excel - Aquí se abriría un selector de archivos');
        });

        document.getElementById('btnExportar').addEventListener('click', function () {
            alert('Funcionalidad de Exportar - Aquí se exportarían los datos a Excel o CSV');
        });

        // Funcionalidad de botones de opciones en la tabla (solo para demostración)
        document.addEventListener('click', function (e) {
            if (e.target.closest('.boton-opcion.editar')) {
                const fila = e.target.closest('tr');
                const id = fila.cells[0].textContent;
                const nombre = fila.cells[1].textContent;
                alert(`Editar producto: ${nombre} (ID: ${id})`);
            }

            if (e.target.closest('.boton-opcion.eliminar')) {
                const fila = e.target.closest('tr');
                const nombre = fila.cells[1].textContent;
                if (confirm(`¿Estás seguro de que deseas eliminar "${nombre}"?`)) {
                    alert('Producto eliminado correctamente (en una implementación real, se eliminaría de la base de datos)');
                }
            }

            if (e.target.closest('.boton-opcion.cambiar-estado')) {
                const fila = e.target.closest('tr');
                const insignia = fila.querySelector('.insignia-estado');
                const boton = e.target.closest('.boton-opcion');

                if (insignia.classList.contains('activo')) {
                    insignia.classList.remove('activo');
                    insignia.classList.add('inactivo');
                    insignia.textContent = 'Inactivo';
                    boton.innerHTML = '<i class="fas fa-toggle-off"></i> Estado';
                } else {
                    insignia.classList.remove('inactivo');
                    insignia.classList.add('activo');
                    insignia.textContent = 'Activo';
                    boton.innerHTML = '<i class="fas fa-toggle-on"></i> Estado';
                }
            }

            if (e.target.closest('.boton-opcion.ajustar-stock')) {
                const fila = e.target.closest('tr');
                const nombre = fila.cells[1].textContent;
                const stockActual = fila.querySelector('.insignia-stock').textContent;

                const nuevoStock = prompt(`Ajustar stock para "${nombre}"\nStock actual: ${stockActual}\n\nSeleccione el nuevo estado de stock:\n1. Con stock\n2. Poco stock\n3. Sin stock`, stockActual);

                if (nuevoStock !== null) {
                    const insigniaStock = fila.querySelector('.insignia-stock');

                    // Actualizar estado de stock
                    insigniaStock.className = 'insignia-stock';

                    if (nuevoStock.includes('Con stock') || nuevoStock === '1') {
                        insigniaStock.classList.add('con-stock');
                        insigniaStock.textContent = 'Con stock';
                    } else if (nuevoStock.includes('Poco stock') || nuevoStock === '2') {
                        insigniaStock.classList.add('poco-stock');
                        insigniaStock.textContent = 'Poco stock';
                    } else if (nuevoStock.includes('Sin stock') || nuevoStock === '3') {
                        insigniaStock.classList.add('sin-stock');
                        insigniaStock.textContent = 'Sin stock';
                    }

                    alert(`Stock actualizado correctamente para "${nombre}"`);
                }
            }
        });
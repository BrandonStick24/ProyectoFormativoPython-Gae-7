// static/js_Vendedor/Negocios_V.js

document.addEventListener('DOMContentLoaded', function() {
    // ==================== BÚSQUEDA EN TIEMPO REAL ====================
    const inputBusqueda = document.getElementById('inputBusqueda');
    if (inputBusqueda) {
        inputBusqueda.addEventListener('input', function(e) {
            const textoBusqueda = e.target.value.toLowerCase();
            const tarjetas = document.querySelectorAll('.negocio-card');
            
            tarjetas.forEach(tarjeta => {
                const textoNegocio = tarjeta.textContent.toLowerCase();
                const contenedorPadre = tarjeta.closest('.col-xl-3, .col-lg-4, .col-md-6, .col-sm-6');
                
                if (textoNegocio.includes(textoBusqueda)) {
                    contenedorPadre.style.display = '';
                } else {
                    contenedorPadre.style.display = 'none';
                }
            });
        });
    }

    // ==================== MODAL DE EDITAR NEGOCIO ====================
    const modalEditar = document.getElementById('modalEditarNegocio');
    if (modalEditar) {
        modalEditar.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const negocioId = button.getAttribute('data-negocio-id');
            const negocioNombre = button.getAttribute('data-negocio-nombre');
            const negocioRut = button.getAttribute('data-negocio-nit');
            const negocioDireccion = button.getAttribute('data-negocio-direccion');
            const negocioDescripcion = button.getAttribute('data-negocio-descripcion');
            const negocioTipo = button.getAttribute('data-negocio-tipo');
            const negocioImagen = button.getAttribute('data-negocio-imagen');
    
            // Actualizar el formulario
            document.getElementById('editar_nom_neg').value = negocioNombre;
            document.getElementById('editar_nit_neg').value = negocioRut;
            document.getElementById('editar_direcc_neg').value = negocioDireccion;
            document.getElementById('editar_desc_neg').value = negocioDescripcion || '';
            document.getElementById('editar_fktiponeg_neg').value = negocioTipo;

            // Actualizar action del formulario
            const form = document.getElementById('formEditarNegocio');
            form.action = `/vendedor/configurar-negocio/${negocioId}/`;

            // Manejar la imagen
            const imagenActual = document.getElementById('editar_imagen_actual');
            const noImagen = document.getElementById('editar_no_image');

            if (negocioImagen && negocioImagen !== 'None') {
                imagenActual.src = negocioImagen;
                imagenActual.style.display = 'block';
                noImagen.style.display = 'none';
            } else {
                imagenActual.style.display = 'none';
                noImagen.style.display = 'flex';
            }
        });
    }

    // ==================== VALIDACIÓN SIMPLE DE RUT ====================
    
    // Cambiar: de 8-14 a 8-11 caracteres para coincidir con la BD
    function validarRUT(rut) {
        return rut.length >= 8 && rut.length <= 11;
    }

    // Validación formulario agregar
    const formAgregar = document.getElementById('formAgregarNegocio');
    if (formAgregar) {
        formAgregar.addEventListener('submit', function(e) {
            const rut = document.getElementById('nit_neg').value.trim();
            
            if (!validarRUT(rut)) {
                e.preventDefault();
                alert('El RUT debe tener entre 8 y 11 caracteres');
                document.getElementById('nit_neg').focus();
                return false;
            }
            return true;
        });
    }

    // Validación formulario editar
    const formEditar = document.getElementById('formEditarNegocio');
    if (formEditar) {
        formEditar.addEventListener('submit', function(e) {
            const rut = document.getElementById('editar_nit_neg').value.trim();
            
            if (!validarRUT(rut)) {
                e.preventDefault();
                alert('El RUT debe tener entre 8 y 11 caracteres');
                document.getElementById('editar_nit_neg').focus();
                return false;
            }
            return true;
        });
    }

    // ==================== CONFIGURACIÓN DE OTROS MODALES ====================
    
    // Modal para activar/desactivar
    const modalEstado = document.getElementById('modalEstadoNegocio');
    if (modalEstado) {
        modalEstado.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const negocioId = button.getAttribute('data-negocio-id');
            const negocioNombre = button.getAttribute('data-negocio-nombre');
            const negocioEstado = button.getAttribute('data-negocio-estado');
            
            const modalTitle = modalEstado.querySelector('.modal-title');
            const modalBodyInput = modalEstado.querySelector('#estado_negocio_id');
            const modalBodyText = modalEstado.querySelector('#textoEstadoNegocio');
            
            modalBodyInput.value = negocioId;
            
            if (negocioEstado === 'activo') {
                modalTitle.textContent = 'Desactivar Negocio';
                modalBodyText.textContent = `¿Estás seguro que deseas desactivar el negocio "${negocioNombre}"? Los clientes no podrán verlo mientras esté desactivado.`;
            } else {
                modalTitle.textContent = 'Activar Negocio';
                modalBodyText.textContent = `¿Estás seguro que deseas activar el negocio "${negocioNombre}"? Los clientes podrán verlo nuevamente.`;
            }
        });
    }

    // Modal para cerrar negocio
    const modalCerrar = document.getElementById('modalCerrarNegocio');
    if (modalCerrar) {
        modalCerrar.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const negocioId = button.getAttribute('data-negocio-id');
            const negocioNombre = button.getAttribute('data-negocio-nombre');
            
            const modalBodyInput = modalCerrar.querySelector('#cerrar_negocio_id');
            const modalBodyText = modalCerrar.querySelector('#textoCerrarNegocio');
            
            modalBodyInput.value = negocioId;
            modalBodyText.textContent = `¿Estás seguro que deseas cerrar permanentemente el negocio "${negocioNombre}"? Esta acción no se puede deshacer y todos los productos asociados serán removidos.`;
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
            modalBodyText.textContent = `¿Estás absolutamente seguro que deseas eliminar permanentemente el negocio "${negocioNombre}"? Esta acción eliminará todos los productos, reseñas y datos asociados.`;
            
            // Resetear checkbox y botón
            checkbox.checked = false;
            btnEliminar.disabled = true;
            
            // Habilitar botón solo cuando el checkbox esté marcado
            checkbox.addEventListener('change', function() {
                btnEliminar.disabled = !this.checked;
            });
        });
    }

    // ==================== MEJORAS DE USABILIDAD ====================
    
    // Efecto hover mejorado en tarjetas
    const tarjetasNegocio = document.querySelectorAll('.negocio-card');
    tarjetasNegocio.forEach(tarjeta => {
        tarjeta.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
            this.style.boxShadow = '0 6px 12px rgba(0,0,0,0.15)';
        });
        
        tarjeta.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '';
        });
    });

    // Cambiar: Limitar RUT a 11 caracteres en tiempo real
    const inputsRUT = document.querySelectorAll('input[name="nit_neg"], input[name="editar_nit_neg"]');
    inputsRUT.forEach(input => {
        input.addEventListener('input', function(e) {
            if (this.value.length > 11) {
                this.value = this.value.substring(0, 11);
            }
        });
    });

   

    console.log('Negocios_V.js cargado correctamente');
});
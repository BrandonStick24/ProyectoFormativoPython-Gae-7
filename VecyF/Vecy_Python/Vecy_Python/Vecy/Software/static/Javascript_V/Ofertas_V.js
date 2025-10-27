
        // Toggle business status
        document.getElementById('businessToggle').addEventListener('click', function() {
            const statusText = document.getElementById('statusText');
            const isActive = this.classList.toggle('active');
            
            statusText.textContent = isActive ? 'Abierto' : 'Cerrado';
            statusText.style.color = isActive ? '#10b981' : '#6b7280';
        });

        // Button actions (static functionality)
        document.getElementById('btnAddOffer').addEventListener('click', function() {
            alert('Funcionalidad de Crear Oferta - Aquí se abriría un formulario para crear una nueva oferta');
        });

        document.getElementById('btnImportOffers').addEventListener('click', function() {
            alert('Funcionalidad de Importar Ofertas - Aquí se abriría un selector de archivos');
        });

        document.getElementById('btnExportOffers').addEventListener('click', function() {
            alert('Funcionalidad de Exportar - Aquí se exportarían las ofertas a Excel o CSV');
        });

        // Table button actions
        document.addEventListener('click', function(e) {
            if (e.target.closest('.btn-edit')) {
                const row = e.target.closest('tr');
                const id = row.cells[0].textContent;
                const name = row.cells[1].textContent;
                alert(`Editar oferta: ${name} (ID: ${id})`);
            }
            
            if (e.target.closest('.btn-delete')) {
                const row = e.target.closest('tr');
                const name = row.cells[1].textContent;
                if (confirm(`¿Estás seguro de que deseas eliminar la oferta "${name}"?`)) {
                    alert('Oferta eliminada correctamente (en una implementación real, se eliminaría de la base de datos)');
                }
            }
            
            if (e.target.closest('.btn-status')) {
                const row = e.target.closest('tr');
                const badge = row.querySelector('.status-badge');
                const button = e.target.closest('.btn-status');
                
                // Cambiar entre estados activo/inactivo
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
                // Para ofertas programadas o expiradas, solo cambiar el icono
                else if (badge.classList.contains('status-scheduled') || badge.classList.contains('status-expired')) {
                    if (button.innerHTML.includes('fa-toggle-on')) {
                        button.innerHTML = '<i class="fas fa-toggle-off"></i>';
                    } else {
                        button.innerHTML = '<i class="fas fa-toggle-on"></i>';
                    }
                }
            }
        });
 
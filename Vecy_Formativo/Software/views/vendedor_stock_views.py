# Software/vendedor_stock_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import connection
from datetime import datetime
from Software.models import Productos, Negocios
from .vendedor_views import obtener_datos_vendedor

# ==================== VISTAS DE STOCK ====================
@login_required(login_url='login')
def Stock_V(request):
    """Vista principal de gestión de stock con gráficas"""
    try:
        print("=== DEBUG STOCK_V: INICIANDO ===")
        datos = obtener_datos_vendedor(request)
        print(f"DEBUG: Datos obtenidos: {datos}")
        
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('inicio')
        
        negocio = datos['negocio_activo']
        print(f"DEBUG: Negocio activo: {negocio.nom_neg} (ID: {negocio.pkid_neg})")
        
        # Obtener productos con stock bajo usando el ORM de Django
        try:
            productos_stock_bajo = Productos.objects.filter(
                fknegocioasociado_prod=negocio.pkid_neg,
                stock_prod__lte=5
            ).select_related('fkcategoria_prod')
            print(f"DEBUG: Productos stock bajo: {productos_stock_bajo.count()}")
        except Exception as e:
            print(f"DEBUG: Error obteniendo productos stock bajo: {e}")
            productos_stock_bajo = []

        # Estadísticas usando el ORM de Django
        try:
            total_productos = Productos.objects.filter(
                fknegocioasociado_prod=negocio.pkid_neg
            ).count()
            
            sin_stock = Productos.objects.filter(
                fknegocioasociado_prod=negocio.pkid_neg,
                stock_prod=0
            ).count()
            
            stock_bajo = Productos.objects.filter(
                fknegocioasociado_prod=negocio.pkid_neg,
                stock_prod__range=(1, 5)
            ).count()
            
            stock_normal = Productos.objects.filter(
                fknegocioasociado_prod=negocio.pkid_neg,
                stock_prod__gt=5
            ).count()
            
            print(f"DEBUG: Estadísticas - Total: {total_productos}, Normal: {stock_normal}, Bajo: {stock_bajo}, Sin: {sin_stock}")
            
        except Exception as e:
            print(f"DEBUG: Error en estadísticas: {e}")
            total_productos = sin_stock = stock_bajo = stock_normal = 0

        # Movimientos recientes - adaptado para MySQL
        movimientos_recientes = []
        try:
            with connection.cursor() as cursor:
                # Verificar si la tabla existe
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = DATABASE() AND table_name = 'movimientos_stock'
                """)
                tabla_existe = cursor.fetchone()[0]
                
                if tabla_existe:
                    cursor.execute("""
                        SELECT ms.fecha_movimiento, p.nom_prod, ms.tipo_movimiento, 
                               ms.motivo, ms.cantidad, ms.stock_anterior, ms.stock_nuevo,
                               COALESCE(u.first_name, 'Sistema') as usuario_nombre
                        FROM movimientos_stock ms
                        JOIN productos p ON ms.producto_id = p.pkid_prod
                        LEFT JOIN usuario_perfil up ON ms.usuario_id = up.id
                        LEFT JOIN auth_user u ON up.fkuser_id = u.id
                        WHERE ms.negocio_id = %s
                        ORDER BY ms.fecha_movimiento DESC
                        LIMIT 10
                    """, [negocio.pkid_neg])
                    
                    resultados = cursor.fetchall()
                    print(f"DEBUG: Movimientos encontrados: {len(resultados)}")
                    
                    for row in resultados:
                        movimientos_recientes.append({
                            'fecha': row[0].strftime('%d/%m/%Y %H:%M') if row[0] else 'N/A',
                            'producto': row[1] or 'Producto Desconocido',
                            'tipo': row[2] or 'ajuste',
                            'motivo': row[3] or 'Sin motivo',
                            'cantidad': row[4] or 0,
                            'stock_anterior': row[5] or 0,
                            'stock_nuevo': row[6] or 0,
                            'usuario': row[7] or 'Sistema'
                        })
                else:
                    print("DEBUG: Tabla movimientos_stock no existe")
                    # Crear tabla si no existe
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS movimientos_stock (
                            id_movimiento INT AUTO_INCREMENT PRIMARY KEY,
                            producto_id INT NOT NULL,
                            negocio_id INT NOT NULL,
                            tipo_movimiento ENUM('entrada', 'salida', 'ajuste') NOT NULL,
                            motivo VARCHAR(50) NOT NULL,
                            cantidad INT NOT NULL,
                            stock_anterior INT NOT NULL,
                            stock_nuevo INT NOT NULL,
                            usuario_id INT NOT NULL,
                            fecha_movimiento DATETIME DEFAULT CURRENT_TIMESTAMP,
                            pedido_id INT NULL,
                            FOREIGN KEY (producto_id) REFERENCES productos(pkid_prod),
                            FOREIGN KEY (negocio_id) REFERENCES negocios(pkid_neg),
                            FOREIGN KEY (usuario_id) REFERENCES usuario_perfil(id),
                            FOREIGN KEY (pedido_id) REFERENCES pedidos(pkid_pedido)
                        )
                    """)
                    print("DEBUG: Tabla movimientos_stock creada")
                    
        except Exception as e:
            print(f"DEBUG: Error en movimientos: {e}")

        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': negocio,
            'productos_stock_bajo': productos_stock_bajo,
            'total_productos': total_productos,
            'sin_stock': sin_stock,
            'stock_bajo': stock_bajo,
            'stock_normal': stock_normal,
            'movimientos_recientes': movimientos_recientes,
        }
        
        return render(request, 'Vendedor/Stock_V.html', contexto)
        
    except Exception as e:
        print(f"DEBUG: ERROR en Stock_V: {str(e)}")
        messages.error(request, f"Error al cargar el stock: {str(e)}")
        return redirect('inicio')

@login_required(login_url='login')
def ajustar_stock_producto(request, producto_id):
    """Vista para ajustar manualmente el stock de un producto"""
    if request.method == 'POST':
        try:
            nuevo_stock = int(request.POST.get('nuevo_stock'))
            motivo = request.POST.get('motivo_ajuste', 'ajuste manual')
            
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('inicio')
            
            negocio = datos['negocio_activo']
            
            with connection.cursor() as cursor:
                # Verificar que el producto pertenece al negocio
                cursor.execute("""
                    SELECT stock_prod, nom_prod FROM productos 
                    WHERE pkid_prod = %s AND fknegocioasociado_prod = %s
                """, [producto_id, negocio.pkid_neg])
                
                resultado = cursor.fetchone()
                if not resultado:
                    messages.error(request, "Producto no encontrado")
                    return redirect('Crud_V')
                
                stock_anterior, nombre_producto = resultado
                diferencia = nuevo_stock - stock_anterior
                
                # Actualizar stock
                cursor.execute("""
                    UPDATE productos 
                    SET stock_prod = %s,
                        estado_prod = CASE 
                            WHEN %s <= 0 THEN 'agotado'
                            WHEN %s > 0 THEN 'disponible'
                            ELSE estado_prod
                        END
                    WHERE pkid_prod = %s AND fknegocioasociado_prod = %s
                """, [nuevo_stock, nuevo_stock, nuevo_stock, producto_id, negocio.pkid_neg])
                
                # Determinar tipo de movimiento
                tipo_movimiento = 'ajuste'
                if diferencia > 0:
                    tipo_movimiento = 'entrada'
                elif diferencia < 0:
                    tipo_movimiento = 'salida'
                
                # Registrar movimiento de stock
                cursor.execute("""
                    INSERT INTO movimientos_stock 
                    (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                     stock_anterior, stock_nuevo, usuario_id, fecha_movimiento)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    producto_id, negocio.pkid_neg, tipo_movimiento, motivo, 
                    abs(diferencia), stock_anterior, nuevo_stock,
                    datos['perfil'].id, datetime.now()
                ])
                
                messages.success(request, f"✅ Stock de '{nombre_producto}' actualizado: {stock_anterior} → {nuevo_stock}")
                
        except Exception as e:
            print(f"ERROR al ajustar stock: {str(e)}")
            messages.error(request, f"Error al ajustar stock: {str(e)}")
    
    return redirect('Stock_V')

@login_required(login_url='login')
def entrada_stock_producto(request, producto_id):
    """Vista para registrar entrada de stock (compra a proveedor)"""
    if request.method == 'POST':
        try:
            cantidad_entrada = int(request.POST.get('cantidad_entrada'))
            motivo = request.POST.get('motivo_entrada', 'compra_proveedor')
            
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('inicio')
            
            negocio = datos['negocio_activo']
            
            with connection.cursor() as cursor:
                # Obtener stock actual
                cursor.execute("""
                    SELECT stock_prod, nom_prod FROM productos 
                    WHERE pkid_prod = %s AND fknegocioasociado_prod = %s
                """, [producto_id, negocio.pkid_neg])
                
                resultado = cursor.fetchone()
                if not resultado:
                    messages.error(request, "Producto no encontrado")
                    return redirect('Stock_V')
                
                stock_anterior, nombre_producto = resultado
                stock_nuevo = stock_anterior + cantidad_entrada
                
                # Actualizar stock
                cursor.execute("""
                    UPDATE productos 
                    SET stock_prod = %s,
                        estado_prod = CASE 
                            WHEN %s <= 0 THEN 'agotado'
                            WHEN %s > 0 THEN 'disponible'
                            ELSE estado_prod
                        END
                    WHERE pkid_prod = %s AND fknegocioasociado_prod = %s
                """, [stock_nuevo, stock_nuevo, stock_nuevo, producto_id, negocio.pkid_neg])
                
                # Registrar movimiento de entrada
                cursor.execute("""
                    INSERT INTO movimientos_stock 
                    (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                     stock_anterior, stock_nuevo, usuario_id, fecha_movimiento)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    producto_id, negocio.pkid_neg, 'entrada', motivo, 
                    cantidad_entrada, stock_anterior, stock_nuevo,
                    datos['perfil'].id, datetime.now()
                ])
                
                messages.success(request, f"✅ Entrada registrada: '{nombre_producto}' +{cantidad_entrada} unidades")
                
        except Exception as e:
            print(f"ERROR al registrar entrada: {str(e)}")
            messages.error(request, f"Error al registrar entrada: {str(e)}")
    
    return redirect('Stock_V')

@login_required(login_url='login')
def reporte_movimientos_stock(request):
    """Vista para ver reporte completo de movimientos de stock"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('inicio')
        
        negocio = datos['negocio_activo']
        
        # Filtros
        fecha_desde = request.GET.get('fecha_desde', '')
        fecha_hasta = request.GET.get('fecha_hasta', '')
        tipo_movimiento = request.GET.get('tipo_movimiento', '')
        
        # Consulta de movimientos con filtros
        movimientos = []
        query = """
            SELECT 
                ms.fecha_movimiento, 
                p.nom_prod, 
                ms.tipo_movimiento, 
                ms.motivo, 
                ms.cantidad, 
                ms.stock_anterior, 
                ms.stock_nuevo,
                COALESCE(u.first_name, 'Sistema') as usuario_nombre,
                COALESCE(ped.pkid_pedido, 'N/A') as pedido_id,
                COALESCE(ms.variante_id, 'N/A') as variante_id,
                COALESCE(ms.descripcion_variante, '') as descripcion_variante
            FROM movimientos_stock ms
            JOIN productos p ON ms.producto_id = p.pkid_prod
            LEFT JOIN usuario_perfil up ON ms.usuario_id = up.id
            LEFT JOIN auth_user u ON up.fkuser_id = u.id
            LEFT JOIN pedidos ped ON ms.pedido_id = ped.pkid_pedido
            WHERE ms.negocio_id = %s
        """
        params = [negocio.pkid_neg]
        
        if fecha_desde:
            query += " AND DATE(ms.fecha_movimiento) >= %s"
            params.append(fecha_desde)
        
        if fecha_hasta:
            query += " AND DATE(ms.fecha_movimiento) <= %s"
            params.append(fecha_hasta)
            
        if tipo_movimiento:
            query += " AND ms.tipo_movimiento = %s"
            params.append(tipo_movimiento)
            
        query += " ORDER BY ms.fecha_movimiento DESC"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            
            for row in cursor.fetchall():
                # Determinar si es variante o producto principal
                variante_info = 'Producto principal'
                if row[9] != 'N/A' and row[10]:  # Si tiene variante_id y descripción
                    variante_info = row[10]
                
                movimientos.append({
                    'fecha': row[0].strftime('%d/%m/%Y %H:%M') if row[0] else 'N/A',
                    'producto': row[1],
                    'variante': variante_info,
                    'tipo': row[2],
                    'motivo': row[3],
                    'cantidad': row[4],
                    'stock_anterior': row[5],
                    'stock_nuevo': row[6],
                    'usuario': row[7],
                    'pedido_id': row[8],
                    'variante_id': row[9],
                    'descripcion_variante': row[10]
                })
        
        # Estadísticas para el reporte
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_movimientos,
                    SUM(CASE WHEN tipo_movimiento = 'entrada' THEN cantidad ELSE 0 END) as total_entradas,
                    SUM(CASE WHEN tipo_movimiento = 'salida' THEN cantidad ELSE 0 END) as total_salidas,
                    SUM(CASE WHEN tipo_movimiento = 'ajuste' THEN cantidad ELSE 0 END) as total_ajustes
                FROM movimientos_stock 
                WHERE negocio_id = %s
            """, [negocio.pkid_neg])
            
            stats = cursor.fetchone()
            estadisticas = {
                'total_movimientos': stats[0] or 0,
                'total_entradas': stats[1] or 0,
                'total_salidas': stats[2] or 0,
                'total_ajustes': stats[3] or 0,
            }
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': negocio,
            'movimientos': movimientos,
            'estadisticas': estadisticas,
            'filtros': {
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta,
                'tipo_movimiento': tipo_movimiento,
            }
        }
        return render(request, 'Vendedor/reporte_stock.html', contexto)
        
    except Exception as e:
        print(f"ERROR en reporte_movimientos_stock: {str(e)}")
        messages.error(request, f"Error: {str(e)}")
        return redirect('inicio')

# Función para registrar movimientos automáticos por pedidos
def registrar_movimiento_pedido(pedido_id, tipo_movimiento, motivo):
    """Función para registrar movimientos de stock automáticamente por pedidos"""
    try:
        with connection.cursor() as cursor:
            # Obtener detalles del pedido
            cursor.execute("""
                SELECT dp.fkproducto_detalle, dp.cantidad_detalle, p.fknegocioasociado_prod,
                       p.stock_prod, p.nom_prod
                FROM detalles_pedido dp
                JOIN productos p ON dp.fkproducto_detalle = p.pkid_prod
                WHERE dp.fkpedido_detalle = %s
            """, [pedido_id])
            
            detalles = cursor.fetchall()
            
            for detalle in detalles:
                producto_id, cantidad, negocio_id, stock_actual, nombre_producto = detalle
                
                if tipo_movimiento == 'salida':
                    nuevo_stock = stock_actual - cantidad
                else:  # entrada por cancelación
                    nuevo_stock = stock_actual + cantidad
                
                # Actualizar stock del producto
                cursor.execute("""
                    UPDATE productos 
                    SET stock_prod = %s,
                        estado_prod = CASE 
                            WHEN %s <= 0 THEN 'agotado'
                            WHEN %s > 0 THEN 'disponible'
                            ELSE estado_prod
                        END
                    WHERE pkid_prod = %s
                """, [nuevo_stock, nuevo_stock, nuevo_stock, producto_id])
                
                # Registrar movimiento
                cursor.execute("""
                    INSERT INTO movimientos_stock 
                    (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                     stock_anterior, stock_nuevo, usuario_id, pedido_id, fecha_movimiento)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    producto_id, negocio_id, tipo_movimiento, motivo, 
                    cantidad, stock_actual, nuevo_stock,
                    1,  # Usuario sistema
                    pedido_id, 
                    datetime.now()
                ])
                
        return True
    except Exception as e:
        print(f"Error registrando movimiento de pedido: {e}")
        return False
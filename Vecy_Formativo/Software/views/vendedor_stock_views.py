# Software/views/vendedor_stock_views.py
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
    """Vista principal de gestión de stock con gráficas - CORREGIDA PARA MOSTRAR ELIMINACIONES"""
    try:
        print("=== DEBUG STOCK_V: INICIANDO ===")
        datos = obtener_datos_vendedor(request)
        print(f"DEBUG: Datos obtenidos: {datos}")
        
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('principal')
        
        negocio = datos['negocio_activo']
        print(f"DEBUG: Negocio activo: {negocio.nom_neg} (ID: {negocio.pkid_neg})")
        
        # Obtener productos del negocio
        productos = Productos.objects.filter(fknegocioasociado_prod=negocio)
        
        # Obtener productos con stock bajo usando el ORM de Django
        try:
            productos_stock_bajo = Productos.objects.filter(
                fknegocioasociado_prod=negocio,
                stock_prod__lte=5
            ).select_related('fkcategoria_prod')
            print(f"DEBUG: Productos stock bajo: {productos_stock_bajo.count()}")
        except Exception as e:
            print(f"DEBUG: Error obteniendo productos stock bajo: {e}")
            productos_stock_bajo = []

        # Estadísticas usando el ORM de Django
        try:
            total_productos = productos.count()
            sin_stock = productos.filter(stock_prod=0).count()
            stock_bajo = productos.filter(stock_prod__range=(1, 5)).count()
            stock_normal = productos.filter(stock_prod__gt=5).count()
            
            print(f"DEBUG: Estadísticas - Total: {total_productos}, Normal: {stock_normal}, Bajo: {stock_bajo}, Sin: {sin_stock}")
            
        except Exception as e:
            print(f"DEBUG: Error en estadísticas: {e}")
            total_productos = sin_stock = stock_bajo = stock_normal = 0

        # Obtener productos en oferta
        productos_oferta = []
        productos_oferta_count = 0
        productos_en_oferta_ids = set()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        p.nom_prod as producto_nombre,
                        pr.porcentaje_descuento,
                        p.precio_prod as precio_original,
                        (p.precio_prod * (1 - pr.porcentaje_descuento / 100)) as precio_oferta,
                        pr.stock_oferta,
                        p.pkid_prod
                    FROM promociones pr
                    JOIN productos p ON pr.fkproducto_id = p.pkid_prod
                    WHERE pr.fknegocio_id = %s 
                    AND pr.estado_promo = 'activa'
                    AND pr.fecha_fin >= CURDATE()
                """, [negocio.pkid_neg])
                
                for row in cursor.fetchall():
                    productos_oferta.append({
                        'producto_nombre': row[0],
                        'descuento': float(row[1]),
                        'precio_original': float(row[2]),
                        'precio_oferta': float(row[3]),
                        'stock_oferta': row[4]
                    })
                    productos_en_oferta_ids.add(row[5])
                    productos_oferta_count += 1
        except Exception as e:
            print(f"Error obteniendo ofertas: {e}")

        # ✅ MOVIMIENTOS RECIENTES - CONSULTA CORREGIDA PARA MOSTRAR ELIMINACIONES
        movimientos_recientes = []
        movimientos_hoy = 0
        
        try:
            with connection.cursor() as cursor:
                # ✅ CONSULTA MEJORADA: Incluye productos eliminados y maneja mejor los tipos
                cursor.execute("""
                    SELECT 
                        ms.fecha_movimiento,
                        COALESCE(p.nom_prod, 'PRODUCTO ELIMINADO') as producto,
                        COALESCE(v.nombre_variante, 'Producto principal') as variante,
                        ms.tipo_movimiento,
                        ms.cantidad,
                        ms.motivo,
                        ms.descripcion_variante,
                        COALESCE(u.first_name, 'Sistema') as usuario_nombre,
                        ms.variante_id
                    FROM movimientos_stock ms
                    LEFT JOIN productos p ON ms.producto_id = p.pkid_prod
                    LEFT JOIN variantes_producto v ON ms.variante_id = v.id_variante
                    LEFT JOIN usuario_perfil up ON ms.usuario_id = up.id
                    LEFT JOIN auth_user u ON up.fkuser_id = u.id
                    WHERE ms.negocio_id = %s
                    ORDER BY ms.fecha_movimiento DESC
                    LIMIT 8
                """, [negocio.pkid_neg])
                
                resultados = cursor.fetchall()
                print(f"DEBUG: Movimientos encontrados: {len(resultados)}")
                
                for row in resultados:
                    fecha, producto, variante, tipo, cantidad, motivo, descripcion, usuario, variante_id = row
                    
                    # ✅ MEJORAR LA VISUALIZACIÓN DE MOTIVOS DE ELIMINACIÓN
                    if 'eliminacion_producto:' in motivo:
                        motivo_display = f"🚫 ELIMINACIÓN: {motivo.replace('eliminacion_producto:', '')}"
                        tipo_display = "eliminacion"
                        icono = "🗑️"
                    elif 'eliminacion_variante:' in motivo:
                        motivo_display = f"🗑️ VARIANTE ELIMINADA: {motivo.replace('eliminacion_variante:', '')}"
                        tipo_display = "eliminacion"
                        icono = "🗑️"
                    else:
                        motivo_display = motivo
                        tipo_display = tipo
                        if tipo == 'entrada':
                            icono = "📥"
                        elif tipo == 'salida':
                            icono = "📤"
                        else:
                            icono = "⚙️"
                    
                    movimientos_recientes.append({
                        'fecha': fecha.strftime('%H:%M'),
                        'producto': producto,
                        'variante': variante,
                        'tipo': tipo_display,
                        'cantidad': cantidad,
                        'motivo': f"{icono} {motivo_display}",
                        'descripcion': descripcion or '',
                        'usuario': usuario,
                        'variante_id': variante_id
                    })
                
                # Movimientos de hoy
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM movimientos_stock 
                    WHERE negocio_id = %s 
                    AND DATE(fecha_movimiento) = CURDATE()
                """, [negocio.pkid_neg])
                resultado_movimientos_hoy = cursor.fetchone()
                movimientos_hoy = resultado_movimientos_hoy[0] if resultado_movimientos_hoy else 0
                    
        except Exception as e:
            print(f"DEBUG: Error en movimientos: {e}")
            movimientos_recientes = []
            movimientos_hoy = 0

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
            'movimientos_hoy': movimientos_hoy,
            'productos_oferta': productos_oferta,
            'productos_oferta_count': productos_oferta_count,
            'productos_en_oferta_ids': productos_en_oferta_ids,
        }
        
        return render(request, 'Vendedor/Stock_V.html', contexto)
        
    except Exception as e:
        print(f"DEBUG: ERROR en Stock_V: {str(e)}")
        messages.error(request, f"Error al cargar el stock: {str(e)}")
        return redirect('principal')

@login_required(login_url='login')
def entrada_stock_producto(request, producto_id):
    """Vista para registrar entrada de stock (compra a proveedor) - REDIRIGE A STOCK"""
    if request.method == 'POST':
        try:
            cantidad_entrada = int(request.POST.get('cantidad_entrada'))
            motivo = request.POST.get('motivo_entrada', 'compra_proveedor')
            
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('Stock_V')
            
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
    
    # IMPORTANTE: Esta función redirige a Stock_V porque se usa desde el dashboard de stock
    return redirect('Stock_V')


@login_required(login_url='login')
def reporte_movimientos_stock(request):
    """Vista para ver reporte completo de movimientos de stock - MEJORADA PARA VARIANTES"""
    try:
        print("🔄 DEBUG: reporte_movimientos_stock - INICIANDO")
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('Stock_V')
        
        negocio = datos['negocio_activo']
        print(f"🔄 DEBUG: Negocio: {negocio.nom_neg}, ID: {negocio.pkid_neg}")
        
        # Filtros
        fecha_desde = request.GET.get('fecha_desde', '')
        fecha_hasta = request.GET.get('fecha_hasta', '')
        tipo_movimiento = request.GET.get('tipo_movimiento', '')
        
        print(f"🔄 DEBUG: Filtros - Desde: {fecha_desde}, Hasta: {fecha_hasta}, Tipo: {tipo_movimiento}")
        
        # ✅ CONSULTA DE MOVIMIENTOS CORREGIDA - ORDEN DE COLUMNAS ARREGLADO
        movimientos = []
        query = """
            SELECT 
                ms.fecha_movimiento, 
                COALESCE(p.nom_prod, 'PRODUCTO ELIMINADO') as producto_nombre,
                ms.tipo_movimiento, 
                ms.motivo, 
                ms.cantidad, 
                ms.stock_anterior, 
                ms.stock_nuevo,
                COALESCE(u.first_name, 'Sistema') as usuario_nombre,
                COALESCE(ped.pkid_pedido, 'N/A') as pedido_id,
                ms.variante_id,
                COALESCE(vp.nombre_variante, 'Producto principal') as nombre_variante,
                COALESCE(ms.descripcion_variante, '') as descripcion_variante
            FROM movimientos_stock ms
            LEFT JOIN productos p ON ms.producto_id = p.pkid_prod
            LEFT JOIN variantes_producto vp ON ms.variante_id = vp.id_variante
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
        
        print(f"🔄 DEBUG: Ejecutando consulta movimientos")
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            resultados = cursor.fetchall()
            print(f"🔄 DEBUG: Movimientos encontrados: {len(resultados)}")
            
            for row in resultados:
                # ✅ CORRECCIÓN: Solo 12 valores, no 13
                # El orden debe coincidir exactamente con el SELECT
                fecha, producto, tipo, motivo, cantidad, stock_anterior, stock_nuevo, usuario, pedido_id, variante_id, nombre_variante, descripcion_variante = row
                
                # ✅ CONVERTIR VALORES NUMÉRICOS DE FORMA SEGURA
                try:
                    cantidad_int = int(cantidad) if cantidad is not None else 0
                    stock_anterior_int = int(stock_anterior) if stock_anterior is not None else 0
                    stock_nuevo_int = int(stock_nuevo) if stock_nuevo is not None else 0
                except (ValueError, TypeError):
                    cantidad_int = 0
                    stock_anterior_int = 0
                    stock_nuevo_int = 0
                
                # ✅ DETERMINAR SI ES VARIANTE O PRODUCTO PRINCIPAL
                variante_info = 'Producto principal'
                es_variante = False
                if variante_id and variante_id != 'N/A' and nombre_variante and nombre_variante != 'Producto principal':
                    variante_info = nombre_variante
                    es_variante = True
                
                # ✅ MEJORAR VISUALIZACIÓN DE MOTIVOS
                motivo_display = str(motivo) if motivo else "Sin motivo"
                
                # Motivos de importación Excel
                if 'importacion_excel_variante' in motivo_display:
                    motivo_display = "📥 IMPORTACIÓN EXCEL (Variante)"
                elif 'importacion_excel_producto' in motivo_display:
                    motivo_display = "📥 IMPORTACIÓN EXCEL (Producto)"
                elif 'creacion_variante' in motivo_display:
                    motivo_display = "🆕 CREACIÓN VARIANTE"
                elif 'pedido_entregado_variante' in motivo_display:
                    motivo_display = "📦 PEDIDO ENTREGADO (Variante)"
                elif 'pedido_entregado' in motivo_display:
                    motivo_display = "📦 PEDIDO ENTREGADO"
                elif 'eliminacion_producto:' in motivo_display:
                    motivo_display = f"🗑️ ELIMINACIÓN PRODUCTO: {motivo_display.replace('eliminacion_producto:', '')}"
                elif 'eliminacion_variante:' in motivo_display:
                    motivo_display = f"🗑️ ELIMINACIÓN VARIANTE: {motivo_display.replace('eliminacion_variante:', '')}"
                elif 'ajuste_stock_variante' in motivo_display:
                    motivo_display = "⚙️ AJUSTE STOCK VARIANTE"
                elif 'ajuste manual' in motivo_display.lower():
                    motivo_display = "⚙️ AJUSTE MANUAL"
                elif 'compra_proveedor' in motivo_display:
                    motivo_display = "📦 COMPRA PROVEEDOR"
                elif 'devolucion_cliente' in motivo_display:
                    motivo_display = "🔄 DEVOLUCIÓN CLIENTE"
                
                movimientos.append({
                    'fecha': fecha.strftime('%d/%m/%Y %H:%M') if fecha else 'N/A',
                    'producto': producto,
                    'variante': variante_info,
                    'es_variante': es_variante,
                    'tipo': tipo,
                    'motivo': motivo_display,
                    'cantidad': cantidad_int,
                    'stock_anterior': stock_anterior_int,
                    'stock_nuevo': stock_nuevo_int,
                    'usuario': usuario,
                    'pedido_id': pedido_id,
                    'variante_id': variante_id,
                    'descripcion_variante': descripcion_variante,
                    # 'fecha_completa' se eliminó porque no existe en la consulta
                })
        
        # ✅ ESTADÍSTICAS PARA EL REPORTE - COMPLETAMENTE CORREGIDAS
        print(f"🔄 DEBUG: Calculando estadísticas")
        estadisticas = {
            'total_movimientos': 0,
            'total_cantidad': 0,
            'total_entradas': 0,
            'total_salidas': 0,
            'total_ajustes': 0,
            'total_eliminaciones': 0,
            'movimientos_variantes': 0,
            'movimientos_productos': 0,
        }
        
        try:
            with connection.cursor() as cursor:
                # CONSULTA SIMPLIFICADA Y SEGURA - CORREGIDA
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_movimientos,
                        COALESCE(SUM(cantidad), 0) as total_cantidad,
                        COALESCE(SUM(CASE WHEN tipo_movimiento = 'entrada' THEN cantidad ELSE 0 END), 0) as total_entradas,
                        COALESCE(SUM(CASE WHEN tipo_movimiento = 'salida' THEN cantidad ELSE 0 END), 0) as total_salidas,
                        COALESCE(SUM(CASE WHEN tipo_movimiento = 'ajuste' THEN cantidad ELSE 0 END), 0) as total_ajustes,
                        SUM(CASE WHEN motivo LIKE '%%eliminacion%%' THEN 1 ELSE 0 END) as total_eliminaciones,
                        SUM(CASE WHEN variante_id IS NOT NULL THEN 1 ELSE 0 END) as movimientos_variantes,
                        SUM(CASE WHEN variante_id IS NULL THEN 1 ELSE 0 END) as movimientos_productos
                    FROM movimientos_stock 
                    WHERE negocio_id = %s
                """, [str(negocio.pkid_neg)])
                
                stats = cursor.fetchone()
                print(f"🔄 DEBUG: Stats raw: {stats}")
                
                if stats:
                    estadisticas = {
                        'total_movimientos': int(stats[0]) if stats[0] is not None else 0,
                        'total_cantidad': int(stats[1]) if stats[1] is not None else 0,
                        'total_entradas': int(stats[2]) if stats[2] is not None else 0,
                        'total_salidas': int(stats[3]) if stats[3] is not None else 0,
                        'total_ajustes': int(stats[4]) if stats[4] is not None else 0,
                        'total_eliminaciones': int(stats[5]) if stats[5] is not None else 0,
                        'movimientos_variantes': int(stats[6]) if stats[6] is not None else 0,
                        'movimientos_productos': int(stats[7]) if stats[7] is not None else 0,
                    }
        except Exception as e:
            print(f"❌ ERROR en consulta de estadísticas: {e}")
        
        print(f"🔄 DEBUG: Estadísticas procesadas: {estadisticas}")
        
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
        
        print("✅ DEBUG: Renderizando reporte_stock.html")
        return render(request, 'Vendedor/reporte_stock.html', contexto)
        
    except Exception as e:
        print(f"❌ ERROR en reporte_movimientos_stock: {str(e)}")
        import traceback
        print(f"❌ TRACEBACK: {traceback.format_exc()}")
        messages.error(request, f"Error al cargar el reporte: {str(e)}")
        return redirect('Stock_V')

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
    

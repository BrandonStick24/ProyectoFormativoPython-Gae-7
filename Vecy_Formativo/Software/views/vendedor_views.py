# Software/views/vendedor_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction, connection
from datetime import datetime
import json
import os
from django.conf import settings
import pandas as pd
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from django.utils.text import slugify

# Importar modelos
from Software.models import (
    Negocios, TipoNegocio, UsuarioPerfil, 
    Productos, CategoriaProductos, Pedidos, DetallesPedido,
    ResenasNegocios
)

# Importar función auxiliar de categorías
from .vendedor_categorias_views import obtener_categorias_por_tiponegocio

# ==================== FUNCIONES AUXILIARES VENDEDOR ====================
def obtener_datos_vendedor(request):
    """Función auxiliar para obtener datos del vendedor con negocio seleccionado"""
    try:
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        
        # Obtener el negocio seleccionado de la sesión
        negocio_seleccionado_id = request.session.get('negocio_seleccionado_id')
        negocio_seleccionado = None
        
        if negocio_seleccionado_id:
            try:
                negocio_seleccionado = Negocios.objects.get(
                    pkid_neg=negocio_seleccionado_id, 
                    fkpropietario_neg=perfil
                )
            except Negocios.DoesNotExist:
                # Si el negocio de la sesión no existe, limpiar la sesión
                del request.session['negocio_seleccionado_id']
        
        # Si no hay negocio seleccionado, usar el primero activo
        if not negocio_seleccionado:
            negocio_seleccionado = Negocios.objects.filter(
                fkpropietario_neg=perfil, 
                estado_neg='activo'
            ).first()
            
            # Guardar en sesión si encontramos uno
            if negocio_seleccionado:
                request.session['negocio_seleccionado_id'] = negocio_seleccionado.pkid_neg
        
        return {
            'nombre_usuario': request.user.first_name,
            'perfil': perfil,
            'negocio_activo': negocio_seleccionado,
        }
    except UsuarioPerfil.DoesNotExist:
        return {}

# ==================== VISTA PARA SELECCIONAR NEGOCIO ====================
@login_required(login_url='login')
def seleccionar_negocio(request, negocio_id):
    """Vista para cambiar el negocio seleccionado en sesión"""
    try:
        # Verificar que el negocio pertenezca al usuario
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        
        negocio = Negocios.objects.get(
            pkid_neg=negocio_id, 
            fkpropietario_neg=perfil
        )
        
        # Guardar en sesión
        request.session['negocio_seleccionado_id'] = negocio.pkid_neg
        
        messages.success(request, f"Negocio '{negocio.nom_neg}' seleccionado correctamente.")
        return redirect('dash_vendedor')
        
    except Negocios.DoesNotExist:
        messages.error(request, "No tienes permisos para acceder a este negocio.")
        return redirect('Negocios_V')
    except Exception as e:
        messages.error(request, f"Error al seleccionar negocio: {str(e)}")
        return redirect('Negocios_V')

# ==================== VISTA PARA REGISTRAR NUEVO NEGOCIO por vendedor  ====================
@login_required(login_url='login')
def registrar_negocio_vendedor(request):
    """Vista para que vendedores registrados agreguen nuevos negocios"""
    
    print("=== DEBUG: INICIANDO REGISTRO NEGOCIO ===")
    
    if request.method == 'POST':
        try:
            print("DEBUG: Es método POST")
            print("DEBUG: request.POST contents:", dict(request.POST))
            print("DEBUG: request.FILES contents:", dict(request.FILES))
            
            perfil = UsuarioPerfil.objects.get(fkuser=request.user)
            
            # Obtener datos del formulario
            nit = request.POST.get('nit_neg')
            nombre = request.POST.get('nom_neg')
            direccion = request.POST.get('direcc_neg')
            descripcion = request.POST.get('desc_neg')
            tipo_neg = request.POST.get('fktiponeg_neg')
            imagen = request.FILES.get('img_neg')
            
            print(f"DEBUG: nit_neg value: '{nit}'")
            print(f"DEBUG: nom_neg value: '{nombre}'")
            print(f"DEBUG: fktiponeg_neg value: '{tipo_neg}'")
            
            # Validar campos requeridos
            if not nit:
                print("DEBUG: ERROR - nit_neg está vacío")
                messages.error(request, "El campo NIT es obligatorio.")
                return redirect('Negocios_V')
                
            if not nombre:
                print("DEBUG: ERROR - nom_neg está vacío")
                messages.error(request, "El campo Nombre es obligatorio.")
                return redirect('Negocios_V')
                
            if not tipo_neg:
                print("DEBUG: ERROR - fktiponeg_neg está vacío")
                messages.error(request, "El campo Tipo de Negocio es obligatorio.")
                return redirect('Negocios_V')
            
            # Validar que el NIT no exista
            if Negocios.objects.filter(nit_neg=nit).exists():
                print(f"DEBUG: NIT {nit} ya existe")
                messages.error(request, "El NIT ya está registrado.")
                return redirect('Negocios_V')
            
            print("DEBUG: Todos los campos válidos, creando negocio...")
            
            # Crear el negocio
            nuevo_negocio = Negocios.objects.create(
                nit_neg=nit,
                nom_neg=nombre,
                direcc_neg=direccion,
                desc_neg=descripcion,
                fktiponeg_neg_id=tipo_neg,
                fkpropietario_neg=perfil,
                estado_neg='activo',
                fechacreacion_neg=timezone.now(),
                img_neg=imagen
            )
            
            print(f"DEBUG: Negocio creado exitosamente - ID: {nuevo_negocio.pkid_neg}")
            
            # Seleccionar automáticamente el nuevo negocio
            request.session['negocio_seleccionado_id'] = nuevo_negocio.pkid_neg
            
            messages.success(request, f"Negocio '{nombre}' registrado exitosamente.")
            return redirect('dash_vendedor')
            
        except Exception as e:
            print(f"DEBUG: ERROR - {str(e)}")
            import traceback
            print("DEBUG: Traceback:", traceback.format_exc())
            messages.error(request, f"Error al registrar negocio: {str(e)}")
            return redirect('Negocios_V')
    
    return redirect('Negocios_V')

# ==================== VISTAS VENDEDOR - DASHBOARD ====================
# En Software/views/vendedor_views.py - actualizar la vista vendedor_dash

@login_required(login_url='login')
def vendedor_dash(request):
    try:
        datos = obtener_datos_vendedor(request)
        if not datos:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('principal')
        
        negocio = datos['negocio_activo']
        if not negocio:
            messages.error(request, "No tienes un negocio activo registrado.")
            return redirect('registro_negocios')
        
        # ==================== DATOS REALES PARA EL DASHBOARD ====================
        
        # 1. VENTAS HOY
        with connection.cursor() as cursor:
            # Ventas de hoy
            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(total_pedido), 0) 
                FROM pedidos 
                WHERE fknegocio_pedido = %s 
                AND DATE(fecha_pedido) = CURDATE()
                AND estado_pedido = 'entregado'
            """, [negocio.pkid_neg])
            resultado = cursor.fetchone()
            ventas_hoy = resultado[0] if resultado else 0
            total_ventas_hoy = float(resultado[1]) if resultado and resultado[1] else 0.0
            
            # Ingresos mensuales
            cursor.execute("""
                SELECT COALESCE(SUM(total_pedido), 0) 
                FROM pedidos 
                WHERE fknegocio_pedido = %s 
                AND MONTH(fecha_pedido) = MONTH(CURDATE())
                AND YEAR(fecha_pedido) = YEAR(CURDATE())
                AND estado_pedido = 'entregado'
            """, [negocio.pkid_neg])
            ingresos_mensuales = float(cursor.fetchone()[0] or 0)
            
            # Crecimiento de ingresos (vs mes anterior)
            cursor.execute("""
                SELECT COALESCE(SUM(total_pedido), 0) 
                FROM pedidos 
                WHERE fknegocio_pedido = %s 
                AND MONTH(fecha_pedido) = MONTH(CURDATE() - INTERVAL 1 MONTH)
                AND YEAR(fecha_pedido) = YEAR(CURDATE() - INTERVAL 1 MONTH)
                AND estado_pedido = 'entregado'
            """, [negocio.pkid_neg])
            ingresos_mes_anterior = float(cursor.fetchone()[0] or 0)
            
            if ingresos_mes_anterior > 0:
                crecimiento_ingresos = round(((ingresos_mensuales - ingresos_mes_anterior) / ingresos_mes_anterior) * 100, 1)
            else:
                crecimiento_ingresos = 100.0 if ingresos_mensuales > 0 else 0.0
        
        # 2. CLIENTES ACTIVOS
        with connection.cursor() as cursor:
            # Clientes únicos en los últimos 30 días
            cursor.execute("""
                SELECT COUNT(DISTINCT fkusuario_pedido) 
                FROM pedidos 
                WHERE fknegocio_pedido = %s 
                AND fecha_pedido >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """, [negocio.pkid_neg])
            clientes_activos = cursor.fetchone()[0] or 0
            
            # Crecimiento de clientes (vs semana anterior)
            cursor.execute("""
                SELECT COUNT(DISTINCT fkusuario_pedido) 
                FROM pedidos 
                WHERE fknegocio_pedido = %s 
                AND fecha_pedido BETWEEN DATE_SUB(CURDATE(), INTERVAL 14 DAY) AND DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            """, [negocio.pkid_neg])
            clientes_semana_anterior = cursor.fetchone()[0] or 0
            
            if clientes_semana_anterior > 0:
                crecimiento_clientes = round(((clientes_activos - clientes_semana_anterior) / clientes_semana_anterior) * 100, 1)
            else:
                crecimiento_clientes = 100.0 if clientes_activos > 0 else 0.0
        
        # 3. PRODUCTOS
        with connection.cursor() as cursor:
            # Total de productos
            cursor.execute("""
                SELECT COUNT(*) FROM productos 
                WHERE fknegocioasociado_prod = %s
            """, [negocio.pkid_neg])
            total_productos = cursor.fetchone()[0] or 0
            
            # Productos con stock bajo (<= 5)
            cursor.execute("""
                SELECT COUNT(*) FROM productos 
                WHERE fknegocioasociado_prod = %s 
                AND stock_prod <= 5 AND stock_prod > 0
            """, [negocio.pkid_neg])
            productos_stock_bajo = cursor.fetchone()[0] or 0
            
            # Productos sin stock
            cursor.execute("""
                SELECT COUNT(*) FROM productos 
                WHERE fknegocioasociado_prod = %s 
                AND stock_prod = 0
            """, [negocio.pkid_neg])
            productos_sin_stock = cursor.fetchone()[0] or 0
            
            # Productos disponibles
            productos_disponibles = total_productos - productos_stock_bajo - productos_sin_stock
        
        # 4. GRÁFICO DE VENTAS ÚLTIMOS 7 DÍAS
        ventas_labels = []
        ventas_data = []
        
        with connection.cursor() as cursor:
            for i in range(6, -1, -1):
                cursor.execute("""
                    SELECT COALESCE(SUM(total_pedido), 0) 
                    FROM pedidos 
                    WHERE fknegocio_pedido = %s 
                    AND DATE(fecha_pedido) = DATE_SUB(CURDATE(), INTERVAL %s DAY)
                    AND estado_pedido = 'entregado'
                """, [negocio.pkid_neg, i])
                total_dia = float(cursor.fetchone()[0] or 0)
                
                # Formatear fecha
                cursor.execute("SELECT DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL %s DAY), '%%d/%%m')", [i])
                fecha_label = cursor.fetchone()[0]
                
                ventas_labels.append(f'"{fecha_label}"')
                ventas_data.append(total_dia)
        
        # 5. GRÁFICO DE VENTAS POR CATEGORÍA
        categorias_labels = []
        categorias_data = []
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.desc_cp, COALESCE(SUM(pd.precio_unitario * pd.cantidad_detalle), 0) as total
                FROM categoria_productos c
                LEFT JOIN productos pr ON c.pkid_cp = pr.fkcategoria_prod
                LEFT JOIN detalles_pedido pd ON pr.pkid_prod = pd.fkproducto_detalle
                LEFT JOIN pedidos p ON pd.fkpedido_detalle = p.pkid_pedido
                WHERE pr.fknegocioasociado_prod = %s 
                AND p.estado_pedido = 'entregado'
                AND p.fecha_pedido >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                GROUP BY c.pkid_cp, c.desc_cp
                ORDER BY total DESC
                LIMIT 8
            """, [negocio.pkid_neg])
            
            for row in cursor.fetchall():
                categorias_labels.append(f'"{row[0]}"')
                categorias_data.append(float(row[1] or 0))
        
        # 6. ESTADO DE PEDIDOS
        with connection.cursor() as cursor:
            # Pedidos pendientes
            cursor.execute("""
                SELECT COUNT(*) FROM pedidos 
                WHERE fknegocio_pedido = %s 
                AND estado_pedido IN ('pendiente', 'confirmado')
            """, [negocio.pkid_neg])
            pedidos_pendientes = cursor.fetchone()[0] or 0
            
            # Pedidos en proceso
            cursor.execute("""
                SELECT COUNT(*) FROM pedidos 
                WHERE fknegocio_pedido = %s 
                AND estado_pedido IN ('preparando', 'enviado')
            """, [negocio.pkid_neg])
            pedidos_proceso = cursor.fetchone()[0] or 0
            
            # Pedidos completados
            cursor.execute("""
                SELECT COUNT(*) FROM pedidos 
                WHERE fknegocio_pedido = %s 
                AND estado_pedido = 'entregado'
                AND fecha_pedido >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """, [negocio.pkid_neg])
            pedidos_completados = cursor.fetchone()[0] or 0
        
        # 7. PRODUCTOS DESTACADOS (más vendidos)
        productos_destacados = []
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.pkid_prod, p.nom_prod, p.precio_prod, p.stock_prod, p.img_prod
                FROM productos p
                LEFT JOIN detalles_pedido dp ON p.pkid_prod = dp.fkproducto_detalle
                LEFT JOIN pedidos ped ON dp.fkpedido_detalle = ped.pkid_pedido
                WHERE p.fknegocioasociado_prod = %s
                AND ped.estado_pedido = 'entregado'
                AND ped.fecha_pedido >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                GROUP BY p.pkid_prod, p.nom_prod, p.precio_prod, p.stock_prod, p.img_prod
                ORDER BY SUM(dp.cantidad_detalle) DESC
                LIMIT 5
            """, [negocio.pkid_neg])
            
            for row in cursor.fetchall():
                productos_destacados.append({
                    'pkid_prod': row[0],
                    'nom_prod': row[1],
                    'precio_prod': float(row[2]),
                    'stock_prod': row[3],
                    'img_prod': row[4]
                })
        
        # 8. PEDIDOS RECIENTES
        pedidos_recientes = []
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    p.pkid_pedido,
                    p.estado_pedido,
                    p.total_pedido,
                    p.fecha_pedido,
                    u.first_name,
                    u.username
                FROM pedidos p
                JOIN usuario_perfil up ON p.fkusuario_pedido = up.id
                JOIN auth_user u ON up.fkuser_id = u.id
                WHERE p.fknegocio_pedido = %s
                ORDER BY p.fecha_pedido DESC
                LIMIT 5
            """, [negocio.pkid_neg])
            
            for row in cursor.fetchall():
                pedidos_recientes.append({
                    'id': row[0],
                    'estado': row[1],
                    'total': float(row[2]),
                    'fecha_creacion': row[3],
                    'cliente_nombre': row[4] or row[5] or f"Usuario {row[0]}"
                })
        
        # 9. MOVIMIENTOS RECIENTES
        movimientos_recientes = []
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    ms.fecha_movimiento,
                    COALESCE(p.nom_prod, 'PRODUCTO ELIMINADO') as producto,
                    ms.tipo_movimiento,
                    ms.motivo,
                    ms.cantidad,
                    COALESCE(u.first_name, 'Sistema') as usuario_nombre
                FROM movimientos_stock ms
                LEFT JOIN productos p ON ms.producto_id = p.pkid_prod
                LEFT JOIN usuario_perfil up ON ms.usuario_id = up.id
                LEFT JOIN auth_user u ON up.fkuser_id = u.id
                WHERE ms.negocio_id = %s
                ORDER BY ms.fecha_movimiento DESC
                LIMIT 8
            """, [negocio.pkid_neg])
            
            for row in cursor.fetchall():
                movimientos_recientes.append({
                    'fecha': row[0],
                    'producto': row[1],
                    'tipo': row[2],
                    'motivo': row[3],
                    'cantidad': row[4],
                    'usuario': row[5]
                })
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': negocio,
            
            # Métricas principales
            'ventas_hoy': ventas_hoy,
            'total_ventas_hoy': total_ventas_hoy,
            'clientes_activos': clientes_activos,
            'crecimiento_clientes': crecimiento_clientes,
            'total_productos': total_productos,
            'productos_stock_bajo': productos_stock_bajo,
            'productos_sin_stock': productos_sin_stock,
            'productos_disponibles': productos_disponibles,
            'ingresos_mensuales': ingresos_mensuales,
            'crecimiento_ingresos': crecimiento_ingresos,
            
            # Datos para gráficos
            'ventas_labels': ventas_labels,
            'ventas_data': ventas_data,
            'categorias_labels': categorias_labels,
            'categorias_data': categorias_data,
            'pedidos_pendientes': pedidos_pendientes,
            'pedidos_proceso': pedidos_proceso,
            'pedidos_completados': pedidos_completados,
            
            # Listas
            'productos_destacados': productos_destacados,
            'pedidos_recientes': pedidos_recientes,
            'movimientos_recientes': movimientos_recientes,
        }
        
        return render(request, 'Vendedor/Dashboard_V.html', contexto)
        
    except Exception as e:
        print(f"ERROR en vendedor_dash: {str(e)}")
        messages.error(request, f"Error al cargar el dashboard: {str(e)}")
        return redirect('principal')

# ==================== VISTAS VENDEDOR - PRODUCTOS ====================
@login_required(login_url='login')
def Crud_V(request):
    """Vista principal de productos CON VARIANTES"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('principal')
        
        negocio = datos['negocio_activo']
        if not negocio:
            messages.error(request, "No tienes un negocio activo registrado.")
            return redirect('registro_negocios')
        
        # Obtener productos del negocio
        productos = Productos.objects.filter(fknegocioasociado_prod=negocio)
        
        # Obtener variantes para cada producto
        productos_con_variantes = []
        for producto in productos:
            # Obtener variantes del producto
            variantes = []
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id_variante, nombre_variante, precio_adicional, stock_variante, estado_variante
                    FROM variantes_producto 
                    WHERE producto_id = %s
                    ORDER BY nombre_variante
                """, [producto.pkid_prod])
                
                for row in cursor.fetchall():
                    precio_total = float(producto.precio_prod) + float(row[2])
                    variantes.append({
                        'id': row[0],
                        'nombre': row[1],
                        'precio_adicional': float(row[2]),
                        'precio_total': precio_total,
                        'stock': row[3],
                        'estado': row[4]
                    })
            
            productos_con_variantes.append({
                'producto': producto,
                'variantes': variantes,
                'total_variantes': len(variantes),
                'stock_total_variantes': sum(v['stock'] for v in variantes)
            })
        
        # Calcular estadísticas
        productos_disponibles = productos.filter(estado_prod='disponible', stock_prod__gt=0)
        productos_sin_stock = productos.filter(stock_prod=0) | productos.filter(estado_prod='agotado')
        
        # Obtener productos en oferta
        productos_en_oferta_ids = set()
        if negocio:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT fkproducto_id 
                    FROM promociones 
                    WHERE fknegocio_id = %s AND estado_promo = 'activa'
                    AND fecha_fin >= CURDATE()
                """, [negocio.pkid_neg])
                resultados = cursor.fetchall()
                productos_en_oferta_ids = {row[0] for row in resultados}
        
        # Obtener categorías filtradas por tipo de negocio
        categorias_filtradas = []
        if negocio and negocio.fktiponeg_neg:
            categorias_filtradas = obtener_categorias_por_tiponegocio(negocio.fktiponeg_neg.pkid_tiponeg)
        else:
            # Fallback: todas las categorías
            categorias_generales = CategoriaProductos.objects.all().order_by('desc_cp')
            for categoria in categorias_generales:
                categorias_filtradas.append({
                    'id': categoria.pkid_cp,
                    'descripcion': categoria.desc_cp
                })
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': negocio,
            'productos_con_variantes': productos_con_variantes,
            'productos_disponibles': productos_disponibles,
            'productos_sin_stock': productos_sin_stock,
            'categorias': categorias_filtradas,
            'productos_en_oferta': productos_en_oferta_ids,
        }
        return render(request, 'Vendedor/Crud_V.html', contexto)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('principal')

@login_required(login_url='login')
def gestionar_variantes(request, producto_id):
    """Vista para gestionar variantes de un producto específico"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('principal')
        
        negocio = datos['negocio_activo']
        
        # Verificar que el producto pertenece al negocio
        producto = get_object_or_404(Productos, pkid_prod=producto_id, fknegocioasociado_prod=negocio)
        
        # Obtener variantes del producto
        variantes = []
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id_variante, nombre_variante, precio_adicional, stock_variante, estado_variante, sku_variante
                FROM variantes_producto 
                WHERE producto_id = %s
                ORDER BY nombre_variante
            """, [producto_id])
            
            for row in cursor.fetchall():
                precio_total = float(producto.precio_prod) + float(row[2])
                variantes.append({
                    'id': row[0],
                    'nombre': row[1],
                    'precio_adicional': float(row[2]),
                    'precio_total': precio_total,
                    'stock': row[3],
                    'estado': row[4],
                    'sku': row[5]
                })
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': negocio,
            'producto': producto,
            'variantes': variantes,
        }
        
        return render(request, 'Vendedor/gestion_variantes.html', contexto)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('Crud_V')


# ==================== VISTAS VENDEDOR - CHATS ====================
@login_required(login_url='login')
def Chats_V(request):
    try:
        datos = obtener_datos_vendedor(request)
        if not datos:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('principal')
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': datos['negocio_activo']
        }
        return render(request, 'Vendedor/Chats_V.html', contexto)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('principal')

# ==================== VISTAS VENDEDOR - STOCK ====================
@login_required(login_url='login')
def Stock_V(request):
    """Vista para dashboard de stock - MEJORADA"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('principal')
        
        negocio = datos['negocio_activo']
        
        # Obtener productos del negocio
        productos = Productos.objects.filter(fknegocioasociado_prod=negocio)
        total_productos = productos.count() 
        # Calcular stock total incluyendo variantes
        stock_total = 0
        productos_stock_bajo = []

        for producto in productos:
            # Stock del producto principal
            stock_producto = producto.stock_prod
    
            # Stock de variantes
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT SUM(stock_variante) 
                    FROM variantes_producto 
                    WHERE producto_id = %s AND estado_variante = 'activa'
                """, [producto.pkid_prod])
                resultado = cursor.fetchone()
                stock_variantes = resultado[0] if resultado[0] else 0
    
            stock_total_producto = stock_producto + stock_variantes
    
            if stock_total_producto <= 5 and stock_total_producto > 0:
             productos_stock_bajo.append({
                    'producto': producto,
                    'stock_total': stock_total_producto,
                    'tiene_variantes': stock_variantes > 0,
                    'stock_variantes': stock_variantes
                })
    
            stock_total += stock_total_producto     
        
        # Calcular estadísticas
        sin_stock = productos.filter(stock_prod=0).count()
        stock_bajo = len(productos_stock_bajo)
        stock_normal = total_productos - sin_stock - stock_bajo
        
        # Obtener productos en oferta
        productos_oferta = []
        productos_oferta_count = 0
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        p.nom_prod as producto_nombre,
                        pr.porcentaje_descuento,
                        p.precio_prod as precio_original,
                        (p.precio_prod * (1 - pr.porcentaje_descuento / 100)) as precio_oferta,
                        pr.stock_oferta
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
                    productos_oferta_count += 1
        except Exception as e:
            print(f"Error obteniendo ofertas: {e}")
        
        # Obtener movimientos recientes (incluyendo variantes)
        movimientos_recientes = []
        movimientos_hoy = 0
        try:
            with connection.cursor() as cursor:
                # Movimientos recientes
                cursor.execute("""
                    SELECT 
                        ms.fecha_movimiento,
                        p.nom_prod,
                        COALESCE(v.nombre_variante, 'Producto principal') as variante,
                        ms.tipo_movimiento,
                        ms.cantidad,
                        ms.motivo
                    FROM movimientos_stock ms
                    JOIN productos p ON ms.producto_id = p.pkid_prod
                    LEFT JOIN variantes_producto v ON ms.variante_id = v.id_variante
                    WHERE ms.negocio_id = %s
                    ORDER BY ms.fecha_movimiento DESC
                    LIMIT 8
                """, [negocio.pkid_neg])
                
                for row in cursor.fetchall():
                    movimientos_recientes.append({
                        'fecha': row[0].strftime('%H:%M'),
                        'producto': row[1],
                        'variante': row[2],
                        'tipo': row[3],
                        'cantidad': row[4],
                        'motivo': row[5]
                    })
                
                # Movimientos de hoy
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM movimientos_stock 
                    WHERE negocio_id = %s 
                    AND DATE(fecha_movimiento) = CURDATE()
                """, [negocio.pkid_neg])
                movimientos_hoy = cursor.fetchone()[0] or 0
                
        except Exception as e:
            print(f"Error obteniendo movimientos: {e}")
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': negocio,
            'total_productos': total_productos,
            'stock_total': stock_total,
            'stock_normal': stock_normal,
            'stock_bajo': stock_bajo,
            'sin_stock': sin_stock,
            'productos_stock_bajo': productos_stock_bajo,
            'movimientos_recientes': movimientos_recientes,
            'movimientos_hoy': movimientos_hoy,
            'productos_oferta': productos_oferta,
            'productos_oferta_count': productos_oferta_count,
        }
        
        return render(request, 'Vendedor/Stock_V.html', contexto)
        
    except Exception as e:
        print(f"ERROR en Stock_V: {str(e)}")
        messages.error(request, f"Error: {str(e)}")
        return redirect('principal')

# ==================== VISTAS VENDEDOR - CREAR PRODUCTO ====================
@login_required(login_url='login')
def crear_producto_P(request):
    """Vista para crear nuevo producto usando categorías filtradas por tipo de negocio - CON REGISTRO DE STOCK"""
    if request.method == 'POST':
        try:
            perfil = UsuarioPerfil.objects.get(fkuser=request.user)
            
            # USAR EL NEGOCIO SELECCIONADO EN SESIÓN
            negocio_seleccionado_id = request.session.get('negocio_seleccionado_id')
            if not negocio_seleccionado_id:
                messages.error(request, "No tienes un negocio seleccionado.")
                return redirect('Crud_V')
            
            negocio = Negocios.objects.get(
                pkid_neg=negocio_seleccionado_id, 
                fkpropietario_neg=perfil,
                estado_neg='activo'
            )
            
            # Obtener datos del formulario
            nom_prod = request.POST.get('nom_prod')
            precio_prod = request.POST.get('precio_prod')
            desc_prod = request.POST.get('desc_prod')
            stock_prod = request.POST.get('stock_prod')
            img_prod = request.FILES.get('img_prod')
            categoria_id = request.POST.get('categoria_prod')
            estado_prod = request.POST.get('estado_prod', 'disponible')
            
            # Validar campos obligatorios
            if not nom_prod or not precio_prod or not categoria_id:
                messages.error(request, "Nombre, precio y categoría son obligatorios.")
                return redirect('Crud_V')
            
            # OBTENER CATEGORÍA EXISTENTE
            try:
                categoria = CategoriaProductos.objects.get(pkid_cp=categoria_id)
            except CategoriaProductos.DoesNotExist:
                messages.error(request, "La categoría seleccionada no existe.")
                return redirect('Crud_V')
            
            # Convertir stock a entero
            stock_inicial = int(stock_prod) if stock_prod else 0
            
            # Crear el producto
            producto = Productos.objects.create(
                nom_prod=nom_prod,
                precio_prod=precio_prod,
                desc_prod=desc_prod or "",
                fkcategoria_prod=categoria,
                stock_prod=stock_inicial,
                stock_minimo=5,
                fknegocioasociado_prod=negocio,
                estado_prod=estado_prod,
                fecha_creacion=timezone.now()
            )
            
            # Manejar imagen si se subió
            if img_prod:
                import os
                from uuid import uuid4
                
                productos_dir = 'media/productos'
                if not os.path.exists(productos_dir):
                    os.makedirs(productos_dir)
                
                ext = os.path.splitext(img_prod.name)[1]
                filename = f"producto_{uuid4()}{ext}"
                filepath = os.path.join(productos_dir, filename)
                
                with open(filepath, 'wb+') as destination:
                    for chunk in img_prod.chunks():
                        destination.write(chunk)
                
                producto.img_prod = f"productos/{filename}"
                producto.save()
            
            # REGISTRAR MOVIMIENTO DE STOCK POR CREACIÓN DEL PRODUCTO
            if stock_inicial > 0:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO movimientos_stock 
                            (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                             stock_anterior, stock_nuevo, usuario_id, fecha_movimiento)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, [
                            producto.pkid_prod, 
                            negocio.pkid_neg, 
                            'entrada', 
                            'creacion_producto', 
                            stock_inicial, 
                            0,  # Stock anterior era 0 (producto nuevo)
                            stock_inicial, 
                            perfil.id, 
                            datetime.now()
                        ])
                except Exception as e:
                    print(f"Error registrando movimiento al crear producto (puede ignorarse): {e}")
            
            messages.success(request, f"Producto '{nom_prod}' creado exitosamente.")
            return redirect('Crud_V')
            
        except Negocios.DoesNotExist:
            messages.error(request, "El negocio seleccionado no existe o no tienes permisos.")
            return redirect('Crud_V')
        except Exception as e:
            import traceback
            print("ERROR DETALLADO:")
            print(traceback.format_exc())
            messages.error(request, f"Error al crear producto: {str(e)}")
    
    return redirect('Crud_V')

# ==================== VISTAS VENDEDOR - EDITAR PRODUCTO ====================
@login_required(login_url='login')
def editar_producto_P(request, producto_id):
    """Vista para editar producto existente usando categorías filtradas por tipo de negocio"""
    if request.method == 'POST':
        try:
            # Verificar permisos y obtener negocio seleccionado
            perfil = UsuarioPerfil.objects.get(fkuser=request.user)
            
            # USAR EL NEGOCIO SELECCIONADO EN SESIÓN
            negocio_seleccionado_id = request.session.get('negocio_seleccionado_id')
            if not negocio_seleccionado_id:
                messages.error(request, "No tienes un negocio seleccionado.")
                return redirect('Crud_V')
            
            negocio = Negocios.objects.get(
                pkid_neg=negocio_seleccionado_id, 
                fkpropietario_neg=perfil
            )
            
            # Obtener el producto
            producto = Productos.objects.get(
                pkid_prod=producto_id, 
                fknegocioasociado_prod=negocio
            )
            
            # Obtener datos del formulario
            nom_prod = request.POST.get('nom_prod')
            precio_prod = request.POST.get('precio_prod')
            desc_prod = request.POST.get('desc_prod')
            stock_prod = request.POST.get('stock_prod')
            img_prod = request.FILES.get('img_prod')
            categoria_id = request.POST.get('categoria_prod')  # Ahora recibe ID
            estado_prod = request.POST.get('estado_prod', 'disponible')
            
            # Validar campos obligatorios
            if not nom_prod or not precio_prod or not categoria_id:
                messages.error(request, "Nombre, precio y categoría son obligatorios.")
                return redirect('Crud_V')
            
            # OBTENER CATEGORÍA EXISTENTE
            try:
                categoria = CategoriaProductos.objects.get(pkid_cp=categoria_id)
            except CategoriaProductos.DoesNotExist:
                messages.error(request, "La categoría seleccionada no existe.")
                return redirect('Crud_V')
            
            # Actualizar el producto
            producto.nom_prod = nom_prod
            producto.precio_prod = precio_prod
            producto.desc_prod = desc_prod or ""
            producto.fkcategoria_prod = categoria
            producto.stock_prod = int(stock_prod) if stock_prod else 0
            producto.estado_prod = estado_prod
            
            # Manejar la imagen si se subió una nueva
            if img_prod:
                import os
                from uuid import uuid4
                
                productos_dir = 'media/productos'
                if not os.path.exists(productos_dir):
                    os.makedirs(productos_dir)
                
                ext = os.path.splitext(img_prod.name)[1]
                filename = f"producto_{uuid4()}{ext}"
                filepath = os.path.join(productos_dir, filename)
                
                with open(filepath, 'wb+') as destination:
                    for chunk in img_prod.chunks():
                        destination.write(chunk)
                
                producto.img_prod = f"productos/{filename}"
            
            producto.save()
            
            messages.success(request, f"Producto '{nom_prod}' actualizado exitosamente.")
            return redirect('Crud_V')
            
        except Productos.DoesNotExist:
            messages.error(request, "El producto no existe o no tienes permisos para editarlo.")
        except Negocios.DoesNotExist:
            messages.error(request, "El negocio seleccionado no existe o no tienes permisos.")
        except Exception as e:
            messages.error(request, f"Error al actualizar producto: {str(e)}")
    
    return redirect('Crud_V')

# ==================== VISTAS VENDEDOR - OBTENER DATOS PRODUCTO ====================
@login_required(login_url='login')
def obtener_datos_producto_P(request, producto_id):
    """Vista para obtener datos del producto - SIMPLIFICADA"""
    try:
        # Verificar permisos
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        
        # USAR EL NEGOCIO SELECCIONADO EN SESIÓN
        negocio_seleccionado_id = request.session.get('negocio_seleccionado_id')
        if not negocio_seleccionado_id:
            return JsonResponse({'error': 'No tienes un negocio seleccionado'}, status=400)
        
        negocio = Negocios.objects.get(
            pkid_neg=negocio_seleccionado_id, 
            fkpropietario_neg=perfil
        )
        
        producto = Productos.objects.get(
            pkid_prod=producto_id, 
            fknegocioasociado_prod=negocio
        )
        
        # Obtener categorías filtradas por tipo de negocio
        categorias_filtradas = []
        if negocio and negocio.fktiponeg_neg:
            categorias_filtradas = obtener_categorias_por_tiponegocio(negocio.fktiponeg_neg.pkid_tiponeg)
        else:
            # Fallback: todas las categorías
            categorias_generales = CategoriaProductos.objects.all()
            for categoria in categorias_generales:
                categorias_filtradas.append({
                    'id': categoria.pkid_cp,
                    'descripcion': categoria.desc_cp
                })
        
        # Preparar datos para JSON - SIMPLIFICADO
        datos_producto = {
            'pkid_prod': producto.pkid_prod,
            'nom_prod': producto.nom_prod,
            'precio_prod': str(producto.precio_prod),
            'desc_prod': producto.desc_prod or '',
            'stock_prod': producto.stock_prod or 0,
            'estado_prod': producto.estado_prod or 'disponible',
            'categoria_prod': producto.fkcategoria_prod.pkid_cp,
            'categoria_nombre': producto.fkcategoria_prod.desc_cp,
            'img_prod_actual': producto.img_prod.name if producto.img_prod else "",
            'categorias_filtradas': categorias_filtradas
        }
        
        return JsonResponse(datos_producto)
        
    except Productos.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    except Negocios.DoesNotExist:
        return JsonResponse({'error': 'Negocio no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
# ==================== VISTAS VENDEDOR - ELIMINAR PRODUCTO ====================
@login_required(login_url='login')
def eliminar_producto_P(request, producto_id):
    """Vista para eliminar producto - ELIMINACIÓN COMPLETA SIN RESTRICCIONES"""
    if request.method == 'POST':
        try:
            print(f"=== DEBUG ELIMINAR_PRODUCTO: Iniciando eliminación producto {producto_id} ===")
            
            # Obtener el motivo de eliminación del formulario
            motivo_eliminacion = request.POST.get('motivo_eliminacion', 'Sin motivo especificado')
            print(f"DEBUG: Motivo de eliminación: {motivo_eliminacion}")
            
            # Verificar permisos y obtener negocio seleccionado
            perfil = UsuarioPerfil.objects.get(fkuser=request.user)
            
            # USAR EL NEGOCIO SELECCIONADO EN SESIÓN
            negocio_seleccionado_id = request.session.get('negocio_seleccionado_id')
            if not negocio_seleccionado_id:
                messages.error(request, "No tienes un negocio seleccionado.")
                return redirect('Crud_V')
            
            negocio = Negocios.objects.get(
                pkid_neg=negocio_seleccionado_id, 
                fkpropietario_neg=perfil
            )
            
            # Obtener el producto y verificar que pertenezca al negocio seleccionado
            producto = Productos.objects.get(
                pkid_prod=producto_id, 
                fknegocioasociado_prod=negocio
            )
            
            nombre_producto = producto.nom_prod
            stock_eliminado = producto.stock_prod

            with connection.cursor() as cursor:
                print(f"DEBUG: Iniciando eliminación completa para producto {producto_id}")
                
                # 1. OBTENER INFORMACIÓN DE VARIANTES
                cursor.execute("""
                    SELECT id_variante, nombre_variante, stock_variante 
                    FROM variantes_producto 
                    WHERE producto_id = %s
                """, [producto_id])
                variantes_info = cursor.fetchall()
                print(f"DEBUG: Variantes encontradas: {len(variantes_info)}")
                
                # 2. ELIMINAR TODOS LOS MOVIMIENTOS DE STOCK RELACIONADOS CON LAS VARIANTES
                for variante_id, nombre_variante, stock_variante in variantes_info:
                    cursor.execute("""
                        DELETE FROM movimientos_stock 
                        WHERE variante_id = %s
                    """, [variante_id])
                    print(f"✅ DEBUG: Movimientos de variante {variante_id} eliminados: {cursor.rowcount}")
                
                # 3. ELIMINAR LAS VARIANTES
                cursor.execute("""
                    DELETE FROM variantes_producto 
                    WHERE producto_id = %s
                """, [producto_id])
                print(f"✅ DEBUG: Variantes eliminadas: {cursor.rowcount}")
                
                # 4. ELIMINAR TODOS LOS MOVIMIENTOS DE STOCK DEL PRODUCTO PRINCIPAL
                cursor.execute("""
                    DELETE FROM movimientos_stock 
                    WHERE producto_id = %s AND negocio_id = %s
                """, [producto_id, negocio.pkid_neg])
                print(f"✅ DEBUG: Movimientos del producto eliminados: {cursor.rowcount}")
                
                # 5. ELIMINAR PROMOCIONES RELACIONADAS
                cursor.execute("""
                    DELETE FROM promociones 
                    WHERE fkproducto_id = %s AND fknegocio_id = %s
                """, [producto_id, negocio.pkid_neg])
                print(f"✅ DEBUG: Promociones eliminadas: {cursor.rowcount}")
                
                # 6. VERIFICAR SI HAY PEDIDOS RELACIONADOS
                cursor.execute("""
                    SELECT COUNT(*) FROM detalles_pedido 
                    WHERE fkproducto_detalle = %s
                """, [producto_id])
                tiene_pedidos = cursor.fetchone()[0]
                
                if tiene_pedidos > 0:
                    # Si tiene pedidos, no podemos eliminar, mejor desactivar
                    print(f"⚠️ DEBUG: Producto tiene {tiene_pedidos} pedidos relacionados, desactivando en lugar de eliminar")
                    
                    cursor.execute("""
                        UPDATE productos 
                        SET estado_prod = 'no_disponible', stock_prod = 0
                        WHERE pkid_prod = %s
                    """, [producto_id])
                    
                    messages.success(request, f"✅ Producto '{nombre_producto}' ha sido desactivado (tiene pedidos históricos). Motivo: {motivo_eliminacion}")
                    return redirect('Crud_V')
            
            # 7. FINALMENTE: Eliminar el producto (si no tiene pedidos)
            # Usar SQL directo para evitar problemas con Django ORM
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM productos WHERE pkid_prod = %s", [producto_id])
                print(f"✅ DEBUG: Producto {producto_id} eliminado físicamente")
            
            messages.success(request, f"✅ Producto '{nombre_producto}' eliminado exitosamente. Motivo: {motivo_eliminacion}")
            
        except Productos.DoesNotExist:
            messages.error(request, "El producto no existe o no tienes permisos para eliminarlo.")
        except Negocios.DoesNotExist:
            messages.error(request, "El negocio seleccionado no existe o no tienes permisos.")
        except Exception as e:
            print(f"❌ ERROR al eliminar producto: {str(e)}")
            import traceback
            print(f"TRACEBACK COMPLETO: {traceback.format_exc()}")
            
            # Si hay error de constraint, desactivar el producto
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE productos 
                        SET estado_prod = 'no_disponible', stock_prod = 0
                        WHERE pkid_prod = %s
                    """, [producto_id])
                messages.success(request, f"✅ Producto '{nombre_producto}' ha sido desactivado debido a restricciones de base de datos. Motivo: {motivo_eliminacion}")
            except Exception as e2:
                print(f"❌ ERROR al desactivar producto: {str(e2)}")
                messages.error(request, f"Error al eliminar/desactivar producto: {str(e)}")
    
    return redirect('Crud_V')

# ==================== AJUSTAR STOCK DESDE CRUD - FUNCIÓN CORREGIDA ====================
@login_required(login_url='login')
def ajustar_stock_producto(request, producto_id):
    """Vista para ajustar manualmente el stock de un producto DESDE EL CRUD"""
    if request.method == 'POST':
        try:
            print(f"=== DEBUG AJUSTAR STOCK: Producto ID {producto_id} ===")
            
            tipo_ajuste = request.POST.get('tipo_ajuste', 'entrada')
            cantidad_ajuste = int(request.POST.get('cantidad_ajuste', 0))
            motivo = request.POST.get('motivo_ajuste', 'ajuste manual')
            
            print(f"DEBUG: Tipo: {tipo_ajuste}, Cantidad: {cantidad_ajuste}, Motivo: {motivo}")
            
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('principal')
            
            negocio = datos['negocio_activo']
            perfil_id = datos['perfil'].id
            
            print(f"DEBUG: Negocio: {negocio.nom_neg}, Perfil ID: {perfil_id}")
            
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
                print(f"DEBUG: Stock anterior: {stock_anterior}, Producto: {nombre_producto}")
                
                # Calcular nuevo stock según el tipo de ajuste
                if tipo_ajuste == 'entrada':
                    stock_nuevo = stock_anterior + cantidad_ajuste
                    tipo_movimiento = 'entrada'
                    mensaje_tipo = f"+{cantidad_ajuste}"
                elif tipo_ajuste == 'salida':
                    stock_nuevo = stock_anterior - cantidad_ajuste
                    tipo_movimiento = 'salida'
                    mensaje_tipo = f"-{cantidad_ajuste}"
                else:  # ajuste manual
                    stock_nuevo = cantidad_ajuste
                    tipo_movimiento = 'ajuste'
                    mensaje_tipo = f"→ {cantidad_ajuste}"
                
                # Validar que el stock no sea negativo
                if stock_nuevo < 0:
                    messages.error(request, f"❌ No puedes tener stock negativo. Stock actual: {stock_anterior}")
                    return redirect('Crud_V')
                
                print(f"DEBUG: Stock nuevo: {stock_nuevo}, Tipo movimiento: {tipo_movimiento}")
                
                # Actualizar stock en la base de datos
                cursor.execute("""
                    UPDATE productos 
                    SET stock_prod = %s,
                        estado_prod = CASE 
                            WHEN %s <= 0 THEN 'agotado'
                            WHEN %s > 0 AND %s <= 5 THEN 'disponible'
                            ELSE 'disponible'
                        END
                    WHERE pkid_prod = %s AND fknegocioasociado_prod = %s
                """, [stock_nuevo, stock_nuevo, stock_nuevo, stock_nuevo, producto_id, negocio.pkid_neg])
                
                # Verificar que se actualizó correctamente
                cursor.execute("SELECT stock_prod FROM productos WHERE pkid_prod = %s", [producto_id])
                stock_verificado = cursor.fetchone()[0]
                print(f"DEBUG: Stock verificado en BD: {stock_verificado}")
                
                # Registrar movimiento de stock
                try:
                    cursor.execute("""
                        INSERT INTO movimientos_stock 
                        (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                         stock_anterior, stock_nuevo, usuario_id, fecha_movimiento)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        producto_id, negocio.pkid_neg, tipo_movimiento, motivo, 
                        cantidad_ajuste, stock_anterior, stock_nuevo,
                        perfil_id, datetime.now()
                    ])
                    print("DEBUG: Movimiento de stock registrado correctamente")
                except Exception as e:
                    print(f"ERROR registrando movimiento: {e}")
                
                messages.success(request, f"✅ Stock de '{nombre_producto}' actualizado: {stock_anterior} {mensaje_tipo} = {stock_nuevo}")
                print(f"DEBUG: Mensaje de éxito enviado")
                
        except Exception as e:
            print(f"ERROR CRÍTICO al ajustar stock: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback completo: {traceback.format_exc()}")
            messages.error(request, f"Error al ajustar stock: {str(e)}")
    
    # IMPORTANTE: Redirigir al CRUD, no al Stock
    print("DEBUG: Redirigiendo a Crud_V")
    return redirect('Crud_V')

# ==================== Cambiar estado del producto ====================
@login_required(login_url='login')
def cambiar_estado_producto(request, producto_id):
    """Vista para cambiar estado del producto"""
    if request.method == 'POST':
        try:
            nuevo_estado = request.POST.get('nuevo_estado')
            
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('principal')
            
            negocio = datos['negocio_activo']
            
            with connection.cursor() as cursor:
                # Verificar que el producto pertenece al negocio
                cursor.execute("""
                    SELECT nom_prod FROM productos 
                    WHERE pkid_prod = %s AND fknegocioasociado_prod = %s
                """, [producto_id, negocio.pkid_neg])
                
                resultado = cursor.fetchone()
                if not resultado:
                    messages.error(request, "Producto no encontrado")
                    return redirect('Crud_V')
                
                nombre_producto = resultado[0]
                
                # Actualizar estado
                cursor.execute("""
                    UPDATE productos 
                    SET estado_prod = %s
                    WHERE pkid_prod = %s AND fknegocioasociado_prod = %s
                """, [nuevo_estado, producto_id, negocio.pkid_neg])
                
                messages.success(request, f"✅ Estado de '{nombre_producto}' actualizado a: {nuevo_estado}")
                
        except Exception as e:
            print(f"ERROR al cambiar estado: {str(e)}")
            messages.error(request, f"Error al cambiar el estado del producto: {str(e)}")
    
    return redirect('Crud_V')

# ==================== VISTAS VENDEDOR - NEGOCIOS ====================
@login_required(login_url='login')
def Negocios_V(request):
    """Vista SIMPLIFICADA para gestionar múltiples negocios del vendedor - SIN JAVASCRIPT"""
    try:
        # Obtener datos básicos del usuario
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        
        # Obtener negocio activo de la sesión
        negocio_seleccionado_id = request.session.get('negocio_seleccionado_id')
        negocio_activo = None
        
        if negocio_seleccionado_id:
            try:
                negocio_activo = Negocios.objects.get(
                    pkid_neg=negocio_seleccionado_id, 
                    fkpropietario_neg=perfil
                )
            except Negocios.DoesNotExist:
                del request.session['negocio_seleccionado_id']
        
        # Obtener todos los negocios del vendedor
        negocios = Negocios.objects.filter(fkpropietario_neg=perfil)
        tipos_negocio = TipoNegocio.objects.all()
        
        contexto = {
            'nombre': request.user.first_name,
            'perfil': perfil,
            'negocio_activo': negocio_activo,
            'negocios': negocios,
            'tipos_negocio': tipos_negocio,
        }
        
        return render(request, 'Vendedor/Negocios_V.html', contexto)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('principal')

# ==================== CONFIGURACIÓN DE NEGOCIO ====================
@login_required(login_url='login')
def configurar_negocio(request, negocio_id):
    print(f"=== DEBUG configurar_negocio: Negocio ID {negocio_id} ===")
    
    try:
        # Verificar que el negocio pertenece al usuario
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        
        print(f"DEBUG: Usuario: {request.user.username}, Perfil: {perfil.id}")
        
        negocio = get_object_or_404(
            Negocios, 
            pkid_neg=negocio_id, 
            fkpropietario_neg=perfil
        )
        
        print(f"DEBUG: Negocio encontrado: {negocio.nom_neg}")
        
        tipos_negocio = TipoNegocio.objects.all()
        
        if request.method == 'POST':
            print("DEBUG: Procesando POST para actualizar negocio")
            # Procesar actualización del negocio
            nom_neg = request.POST.get('nom_neg')
            nit_neg = request.POST.get('nit_neg')
            direcc_neg = request.POST.get('direcc_neg')
            desc_neg = request.POST.get('desc_neg')
            fktiponeg_neg = request.POST.get('fktiponeg_neg')
            img_neg = request.FILES.get('img_neg')
            
            print(f"DEBUG: Datos recibidos - Nombre: {nom_neg}, NIT: {nit_neg}")
            
            # Validaciones básicas
            if not nom_neg or not nit_neg:
                messages.error(request, "Nombre y NIT son campos obligatorios.")
                return redirect('configurar_negocio', negocio_id=negocio_id)
            
            # Verificar que el NIT no esté en uso por otro negocio
            if Negocios.objects.filter(nit_neg=nit_neg).exclude(pkid_neg=negocio_id).exists():
                messages.error(request, "El NIT ya está registrado por otro negocio.")
                return redirect('configurar_negocio', negocio_id=negocio_id)
            
            # Actualizar el negocio
            negocio.nom_neg = nom_neg
            negocio.nit_neg = nit_neg
            negocio.direcc_neg = direcc_neg
            negocio.desc_neg = desc_neg
            negocio.fktiponeg_neg_id = fktiponeg_neg
            
            if img_neg:
                negocio.img_neg = img_neg
            
            negocio.save()
            
            messages.success(request, f"Negocio '{nom_neg}' actualizado exitosamente.")
            return redirect('Negocios_V')
        
        contexto = {
            'negocio': negocio,
            'tipos_negocio': tipos_negocio,
            'nombre': request.user.first_name,
            'perfil': perfil,
        }
        
        print("DEBUG: Renderizando template de configuración")
        return render(request, 'Vendedor/Conf_ne_V.html', contexto)
        
    except Exception as e:
        print(f"ERROR en configurar_negocio: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        messages.error(request, f"Error al cargar la configuración: {str(e)}")
        return redirect('Negocios_V')

# ==================== RESEÑAS DEL VENDEDOR ====================
@login_required(login_url='login')
def ver_resenas_vendedor(request):
    """Vista para reseñas usando SQL directo - CON INFORMACIÓN DE REPORTES"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('principal')
        
        negocio = datos['negocio_activo']
        
        # CONSULTA ACTUALIZADA CON INFORMACIÓN DE REPORTES
        with connection.cursor() as cursor:
            sql = """
            SELECT 
                r.pkid_resena,
                r.estrellas,
                r.comentario,
                r.fecha_resena,
                u.first_name,
                u.username,
                r.respuesta_vendedor,
                r.fecha_respuesta,
                CASE WHEN rep.pkid_reporte IS NOT NULL THEN 1 ELSE 0 END as reportada
            FROM resenas_negocios r
            JOIN usuario_perfil up ON r.fkusuario_resena = up.id
            JOIN auth_user u ON up.fkuser_id = u.id
            LEFT JOIN reportes rep ON r.pkid_resena = rep.fkresena_reporte 
                AND rep.fknegocio_reportado = %s 
                AND rep.estado_reporte = 'pendiente'
            WHERE r.fknegocio_resena = %s 
            AND r.estado_resena = 'activa'
            ORDER BY r.fecha_resena DESC
            """
            cursor.execute(sql, [negocio.pkid_neg, negocio.pkid_neg])
            resultados = cursor.fetchall()
        
        # Procesar resultados CON RESPUESTAS Y REPORTES
        resenas_completas = []
        resenas_respondidas = 0
        resenas_reportadas = 0
        
        for row in resultados:
            tiene_respuesta = row[6] is not None and row[6].strip() != ''
            reportada = bool(row[8])  # Convertir a booleano
            
            if tiene_respuesta:
                resenas_respondidas += 1
            
            if reportada:
                resenas_reportadas += 1
            
            fecha_respuesta = row[7].strftime('%d %b %Y') if row[7] else ''
            
            resenas_completas.append({
                'id': row[0],
                'calificacion': row[1],
                'comentario': row[2] or 'Sin comentario',
                'fecha': row[3].strftime('%d %b %Y'),
                'cliente': row[4] or row[5] or f"Usuario {row[0]}",
                'respuesta': row[6] or '',
                'tiene_respuesta': tiene_respuesta,
                'fecha_respuesta': fecha_respuesta,
                'reportada': reportada  # Añadido campo reportada
            })
        
        # Calcular estadísticas
        total_resenas = len(resenas_completas)
        if total_resenas > 0:
            suma_estrellas = sum(r['calificacion'] for r in resenas_completas)
            promedio_estrellas = round(suma_estrellas / total_resenas, 1)
        else:
            promedio_estrellas = 0
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': negocio,
            'resenas': resenas_completas,
            'total_resenas': total_resenas,
            'promedio_estrellas': promedio_estrellas,
            'resenas_respondidas': resenas_respondidas,
            'resenas_reportadas': resenas_reportadas,  # Nueva estadística
        }
        
        return render(request, 'Vendedor/ver_resenas.html', contexto)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        messages.error(request, "Error al cargar reseñas")
        return redirect('principal')

@login_required(login_url='login')
def responder_resena(request, resena_id):
    """Vista ACTUALIZADA para guardar respuestas en BD"""
    if request.method == 'POST':
        try:
            respuesta = request.POST.get('respuesta', '').strip()
            if not respuesta:
                messages.error(request, "❌ Escribe una respuesta antes de enviar")
                return redirect('ver_resenas_vendedor')
            
            # Obtener datos del vendedor
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('principal')
            
            # Verificar que la reseña pertenece al negocio del vendedor
            with connection.cursor() as cursor:
                # Verificar propiedad
                cursor.execute(
                    "SELECT pkid_resena FROM resenas_negocios WHERE pkid_resena = %s AND fknegocio_resena = %s",
                    [resena_id, datos['negocio_activo'].pkid_neg]
                )
                if not cursor.fetchone():
                    messages.error(request, "❌ No puedes responder a esta reseña")
                    return redirect('ver_resenas_vendedor')
                
                # ACTUALIZAR LA RESEÑA CON LA RESPUESTA
                cursor.execute(
                    "UPDATE resenas_negocios SET respuesta_vendedor = %s, fecha_respuesta = %s WHERE pkid_resena = %s",
                    [respuesta, datetime.now(), resena_id]
                )
            
            messages.success(request, "✅ Respuesta publicada correctamente")
            
        except Exception as e:
            print(f"ERROR al responder: {str(e)}")
            messages.error(request, "❌ Error al guardar la respuesta")
        
        return redirect('ver_resenas_vendedor')
    
    return redirect('ver_resenas_vendedor')

# ==================== GESTIÓN DE ESTADO DEL NEGOCIO ====================
@login_required(login_url='login')
def cambiar_estado_negocio(request):
    """Vista para activar/desactivar negocio"""
    if request.method == 'POST':
        try:
            negocio_id = request.POST.get('negocio_id')
            
            perfil = UsuarioPerfil.objects.get(fkuser=request.user)
            
            negocio = get_object_or_404(
                Negocios, 
                pkid_neg=negocio_id, 
                fkpropietario_neg=perfil
            )
            
            # Cambiar estado
            if negocio.estado_neg == 'activo':
                negocio.estado_neg = 'inactivo'
                mensaje = f"Negocio '{negocio.nom_neg}' ha sido desactivado. No será visible para los clientes."
            else:
                negocio.estado_neg = 'activo'
                mensaje = f"Negocio '{negocio.nom_neg}' ha sido activado. Ahora es visible para los clientes."
            
            negocio.save()
            messages.success(request, mensaje)
            
        except Exception as e:
            messages.error(request, f"Error al cambiar estado: {str(e)}")
    
    return redirect('Negocios_V')

@login_required(login_url='login')
def cerrar_negocio(request):
    """Vista para cerrar permanentemente un negocio"""
    if request.method == 'POST':
        try:
            negocio_id = request.POST.get('negocio_id')
            
            perfil = UsuarioPerfil.objects.get(fkuser=request.user)
            
            negocio = get_object_or_404(
                Negocios, 
                pkid_neg=negocio_id, 
                fkpropietario_neg=perfil
            )
            
            nombre_negocio = negocio.nom_neg
            
            # Cambiar estado a 'cerrado' en lugar de eliminar
            negocio.estado_neg = 'cerrado'
            negocio.save()
            
            messages.success(request, f"Negocio '{nombre_negocio}' ha sido cerrado permanentemente.")
            
        except Exception as e:
            messages.error(request, f"Error al cerrar negocio: {str(e)}")
    
    return redirect('Negocios_V')

@login_required(login_url='login')
def eliminar_negocio(request):
    """Vista para eliminar permanentemente un negocio"""
    if request.method == 'POST':
        try:
            negocio_id = request.POST.get('negocio_id')
            
            perfil = UsuarioPerfil.objects.get(fkuser=request.user)
            
            negocio = get_object_or_404(
                Negocios, 
                pkid_neg=negocio_id, 
                fkpropietario_neg=perfil
            )
            
            nombre_negocio = negocio.nom_neg
            
            # ELIMINAR PERMANENTEMENTE el negocio
            negocio.delete()
            
            # Si el negocio eliminado era el seleccionado, limpiar la sesión
            if request.session.get('negocio_seleccionado_id') == negocio_id:
                del request.session['negocio_seleccionado_id']
            
            messages.success(request, f"Negocio '{nombre_negocio}' ha sido eliminado permanentemente.")
            
        except Exception as e:
            print(f"ERROR al eliminar negocio: {str(e)}")
            messages.error(request, f"Error al eliminar negocio: {str(e)}")
    
    return redirect('Negocios_V')

# ==================== GESTIÓN DE VENTAS SIMPLIFICADA ====================
@login_required(login_url='login')
def gestionar_ventas(request):
    """Vista para ver ventas con nuevo flujo de estados - COMPLETAMENTE CORREGIDA"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('principal')
        
        negocio = datos['negocio_activo']
        
        # Consulta actualizada con nuevos estados
        with connection.cursor() as cursor:
            sql = """
            SELECT 
                p.pkid_pedido,
                p.estado_pedido,
                p.total_pedido,
                p.fecha_pedido,
                u.first_name,
                u.username,
                u.email,
                up.doc_user,
                COUNT(d.pkid_detalle) as cantidad_productos,
                p.metodo_pago,
                p.metodo_pago_texto,
                p.fecha_actualizacion
            FROM pedidos p
            JOIN usuario_perfil up ON p.fkusuario_pedido = up.id
            JOIN auth_user u ON up.fkuser_id = u.id
            LEFT JOIN detalles_pedido d ON p.pkid_pedido = d.fkpedido_detalle
            WHERE p.fknegocio_pedido = %s
            GROUP BY p.pkid_pedido, p.estado_pedido, p.total_pedido, p.fecha_pedido, 
                     u.first_name, u.username, u.email, up.doc_user, p.metodo_pago, 
                     p.metodo_pago_texto, p.fecha_actualizacion
            ORDER BY p.fecha_pedido DESC
            """
            cursor.execute(sql, [negocio.pkid_neg])
            resultados = cursor.fetchall()
        
        # Procesar resultados CORREGIDO
        pedidos = []
        for row in resultados:
            # Obtener items del pedido para contar productos
            with connection.cursor() as cursor2:
                cursor2.execute("""
                    SELECT COUNT(*) FROM detalles_pedido 
                    WHERE fkpedido_detalle = %s
                """, [row[0]])
                items_count = cursor2.fetchone()[0]
            
            pedidos.append({
                'id': row[0],
                'estado': row[1],
                'total': float(row[2]) if row[2] else 0.0,
                'fecha_creacion': row[3],
                'cliente': {
                    'nombre': row[4] or row[5] or f"Usuario {row[0]}",
                    'email': row[6],
                    'documento': row[7]
                },
                'items': {
                    'count': items_count
                },
                'metodo_pago': row[9] or 'No especificado',
                'metodo_pago_texto': row[10] or 'No especificado',
                'fecha_actualizacion': row[11]
            })
        
        # Calcular estadísticas para el dashboard
        total_pedidos = len(pedidos)
        pedidos_pendientes = len([p for p in pedidos if p['estado'] in ['pendiente', 'confirmado', 'preparando']])
        pedidos_completados = len([p for p in pedidos if p['estado'] == 'entregado'])
        pedidos_cancelados = len([p for p in pedidos if p['estado'] == 'cancelado'])
        
        # Calcular total de ventas y promedio
        total_ventas = sum(p['total'] for p in pedidos if p['estado'] == 'entregado')
        promedio_venta = total_ventas / pedidos_completados if pedidos_completados > 0 else 0
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': negocio,
            'pedidos': pedidos,
            'total_pedidos': total_pedidos,
            'pedidos_pendientes': pedidos_pendientes,
            'pedidos_completados': pedidos_completados,
            'pedidos_cancelados': pedidos_cancelados,
            'total_ventas': f"{total_ventas:,.0f}",
            'promedio_venta': f"{promedio_venta:,.0f}",
        }
        
        return render(request, 'Vendedor/gestion_ventas.html', contexto)
        
    except Exception as e:
        print(f"ERROR al cargar ventas: {str(e)}")
        messages.error(request, "Error al cargar las ventas")
        return redirect('principal')

@login_required(login_url='login')
def ver_recibo_pedido(request, pedido_id):
    """Vista para ver el recibo completo de un pedido"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('principal')
        
        negocio = datos['negocio_activo']
        
        # Obtener información completa del pedido con pago
        with connection.cursor() as cursor:
            # Información del pedido y pago
            cursor.execute("""
                SELECT 
                    p.pkid_pedido,
                    p.estado_pedido,
                    p.total_pedido,
                    p.fecha_pedido,
                    u.first_name,
                    u.username,
                    u.email,
                    up.doc_user,
                    pg.metodo_pago,
                    pg.estado_pago,
                    pg.monto,
                    pg.fecha_pago
                FROM pedidos p
                JOIN usuario_perfil up ON p.fkusuario_pedido = up.id
                JOIN auth_user u ON up.fkuser_id = u.id
                LEFT JOIN pagos_negocios pg ON p.pkid_pedido = pg.fkpedido
                WHERE p.pkid_pedido = %s AND p.fknegocio_pedido = %s
            """, [pedido_id, negocio.pkid_neg])
            
            pedido_info = cursor.fetchone()
            
            if not pedido_info:
                messages.error(request, "Pedido no encontrado")
                return redirect('gestionar_ventas')
            
            # Obtener detalles del pedido (productos)
            cursor.execute("""
                SELECT 
                    d.cantidad_detalle,
                    d.precio_unitario,
                    pr.nom_prod,
                    pr.desc_prod,
                    c.desc_cp as categoria
                FROM detalles_pedido d
                JOIN productos pr ON d.fkproducto_detalle = pr.pkid_prod
                JOIN categoria_productos c ON pr.fkcategoria_prod = c.pkid_cp
                WHERE d.fkpedido_detalle = %s
            """, [pedido_id])
            
            detalles = cursor.fetchall()
        
        # Procesar información del pedido
        pedido = {
            'id': pedido_info[0],
            'estado': pedido_info[1],
            'total': pedido_info[2],
            'fecha': pedido_info[3].strftime('%d/%m/%Y %H:%M'),
            'cliente_nombre': pedido_info[4] or pedido_info[5] or f"Usuario {pedido_info[0]}",
            'cliente_email': pedido_info[6],
            'cliente_documento': pedido_info[7],
            'metodo_pago': pedido_info[8] or 'No especificado',
            'estado_pago': pedido_info[9] or 'pendiente',
            'monto_pago': pedido_info[10] or pedido_info[2],
            'fecha_pago': pedido_info[11].strftime('%d/%m/%Y %H:%M') if pedido_info[11] else 'No procesado'
        }
        
        # Procesar detalles
        productos = []
        for detalle in detalles:
            subtotal = detalle[0] * detalle[1]
            productos.append({
                'cantidad': detalle[0],
                'precio_unitario': detalle[1],
                'nombre': detalle[2],
                'descripcion': detalle[3],
                'categoria': detalle[4],
                'subtotal': subtotal
            })
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': negocio,
            'pedido': pedido,
            'productos': productos,
            'negocio_info': negocio,
        }
        
        return render(request, 'Vendedor/recibo_pedido.html', contexto)
        
    except Exception as e:
        print(f"ERROR al cargar recibo: {str(e)}")
        messages.error(request, "Error al cargar el recibo del pedido")
        return redirect('gestionar_ventas')

@login_required(login_url='login')
def cambiar_estado_pedido(request, pedido_id):
    """Vista para cambiar estado del pedido - SOLO DESCONTAR AL ENTREGAR"""
    if request.method == 'POST':
        try:
            nuevo_estado = request.POST.get('nuevo_estado')
            motivo_cancelacion = request.POST.get('motivo_cancelacion', 'Sin motivo especificado')
            
            print(f"🔄 DEBUG CAMBIAR_ESTADO_PEDIDO: Pedido {pedido_id} a {nuevo_estado}")

            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('principal')
            
            negocio = datos['negocio_activo']
            
            with connection.cursor() as cursor:
                # 1. Obtener el estado actual del pedido
                cursor.execute("""
                    SELECT estado_pedido FROM pedidos 
                    WHERE pkid_pedido = %s AND fknegocio_pedido = %s
                """, [pedido_id, negocio.pkid_neg])
                
                resultado = cursor.fetchone()
                if not resultado:
                    messages.error(request, "Pedido no encontrado")
                    return redirect('gestionar_ventas')
                
                estado_actual = resultado[0]
                print(f"🔄 DEBUG: Estado actual: {estado_actual}, Nuevo estado: {nuevo_estado}")
                
                # 2. Actualizar el estado del pedido
                cursor.execute("""
                    UPDATE pedidos 
                    SET estado_pedido = %s, fecha_actualizacion = %s
                    WHERE pkid_pedido = %s AND fknegocio_pedido = %s
                """, [nuevo_estado, datetime.now(), pedido_id, negocio.pkid_neg])
                
                # 3. ✅ NUEVA LÓGICA: SOLO DESCONTAR STOCK CUANDO SE MARCA COMO "ENTREGADO"
                if nuevo_estado == 'entregado' and estado_actual != 'entregado':
                    print("🔄 DEBUG: Descontando stock por ENTREGA definitiva")
                    
                    # Descontar stock definitivamente
                    stock_descontado = descontar_stock_pedido_al_entregar(pedido_id)
                    
                    if stock_descontado:
                        messages.success(request, f"✅ Pedido marcado como ENTREGADO. Stock descontado definitivamente.")
                    else:
                        messages.warning(request, f"⚠️ Pedido marcado como ENTREGADO, pero hubo problemas al descontar el stock.")
                
                # 4. ✅ CANCELACIÓN: No hacer nada con el stock (nunca se descontó)
                elif nuevo_estado == 'cancelado' and estado_actual != 'cancelado':
                    print("🔄 DEBUG: Cancelando pedido - NO se reabastece stock porque nunca se descontó")
                    messages.success(request, f"✅ Pedido cancelado. Motivo: {motivo_cancelacion}")
                
                else:
                    # Para otros cambios de estado (confirmado, preparando, enviado)
                    messages.success(request, f"✅ Pedido actualizado a: {nuevo_estado}")
                    print(f"🔄 DEBUG: Cambio de estado normal - no se afecta el stock")
                
                # 5. Enviar correo de actualización
                try:
                    print(f"📧 Intentando enviar correo para pedido #{pedido_id}")
                    correo_enviado = enviar_correo_estado_pedido(pedido_id, nuevo_estado)
                    if correo_enviado:
                        print(f"✅ Correo enviado exitosamente")
                except Exception as e:
                    print(f"❌ Error en el proceso de envío de correo: {e}")
                
        except Exception as e:
            print(f"❌ ERROR al cambiar estado: {str(e)}")
            messages.error(request, f"Error al cambiar el estado del pedido: {str(e)}")
    
    return redirect('gestionar_ventas')

@login_required(login_url='login')
def eliminar_pedido(request, pedido_id):
    """Vista para eliminar pedidos - CORREGIDA CON SOPORTE PARA VARIANTES"""
    if request.method == 'POST':
        try:
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('principal')
            
            negocio = datos['negocio_activo']
            
            with connection.cursor() as cursor:
                # Verificar que el pedido pertenece al negocio y obtener su estado
                cursor.execute("""
                    SELECT estado_pedido FROM pedidos 
                    WHERE pkid_pedido = %s AND fknegocio_pedido = %s
                """, [pedido_id, negocio.pkid_neg])
                
                resultado = cursor.fetchone()
                if not resultado:
                    messages.error(request, "Pedido no encontrado o no tienes permisos.")
                    return redirect('gestionar_ventas')
                
                estado_pedido = resultado[0]
                
                # REABASTECER STOCK si el pedido no estaba cancelado - CON SOPORTE PARA VARIANTES
                if estado_pedido in ['pendiente', 'confirmado', 'preparando', 'enviado', 'entregado']:
                    cursor.execute("""
                        SELECT 
                            dp.fkproducto_detalle, 
                            dp.cantidad_detalle, 
                            p.stock_prod, 
                            p.nom_prod,
                            ci.variante_id,
                            vp.nombre_variante,
                            vp.stock_variante
                        FROM detalles_pedido dp
                        JOIN productos p ON dp.fkproducto_detalle = p.pkid_prod
                        LEFT JOIN carrito_item ci ON dp.fkpedido_detalle = ci.fkcarrito
                        LEFT JOIN variantes_producto vp ON ci.variante_id = vp.id_variante
                        WHERE dp.fkpedido_detalle = %s 
                        AND p.fknegocioasociado_prod = %s
                    """, [pedido_id, negocio.pkid_neg])
                    
                    productos_afectados = cursor.fetchall()
                    
                    for (producto_id, cantidad, stock_actual, nombre_producto, 
                         variante_id, nombre_variante, stock_variante) in productos_afectados:
                        
                        if variante_id and stock_variante is not None:
                            # ES UNA VARIANTE - Reabastecer la variante
                            nuevo_stock_variante = stock_variante + cantidad
                            
                            cursor.execute("""
                                UPDATE variantes_producto 
                                SET stock_variante = %s
                                WHERE id_variante = %s
                            """, [nuevo_stock_variante, variante_id])
                            
                            # Registrar movimiento de entrada para la variante
                            try:
                                cursor.execute("""
                                    INSERT INTO movimientos_stock 
                                    (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                                     stock_anterior, stock_nuevo, usuario_id, pedido_id, variante_id, descripcion_variante, fecha_movimiento)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, [
                                    producto_id, negocio.pkid_neg, 'entrada', 'eliminacion_pedido_variante', 
                                    cantidad, stock_variante, nuevo_stock_variante,
                                    datos['perfil'].id, pedido_id, variante_id, nombre_variante, datetime.now()
                                ])
                            except Exception as e:
                                print(f"DEBUG: Error registrando movimiento de variante: {e}")
                        
                        else:
                            # ES PRODUCTO BASE - Reabastecer producto base
                            nuevo_stock = stock_actual + cantidad
                            
                            cursor.execute("""
                                UPDATE productos 
                                SET stock_prod = %s,
                                    estado_prod = CASE 
                                        WHEN %s > 0 THEN 'disponible'
                                        ELSE estado_prod
                                    END
                                WHERE pkid_prod = %s AND fknegocioasociado_prod = %s
                            """, [nuevo_stock, nuevo_stock, producto_id, negocio.pkid_neg])
                            
                            # Registrar movimiento de entrada por eliminación
                            try:
                                cursor.execute("""
                                    INSERT INTO movimientos_stock 
                                    (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                                     stock_anterior, stock_nuevo, usuario_id, pedido_id, fecha_movimiento)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, [
                                    producto_id, negocio.pkid_neg, 'entrada', 'eliminacion_pedido', 
                                    cantidad, stock_actual, nuevo_stock,
                                    datos['perfil'].id, pedido_id, datetime.now()
                                ])
                            except Exception as e:
                                print(f"DEBUG: Error registrando movimiento: {e}")
                
                # **ELIMINAR EN ORDEN CORRECTO PARA EVITAR CONSTRAINTS**
                cursor.execute("DELETE FROM movimientos_stock WHERE pedido_id = %s", [pedido_id])
                cursor.execute("DELETE FROM pagos_negocios WHERE fkpedido = %s", [pedido_id])
                cursor.execute("DELETE FROM detalles_pedido WHERE fkpedido_detalle = %s", [pedido_id])
                cursor.execute("DELETE FROM pedidos WHERE pkid_pedido = %s", [pedido_id])
                
                # Verificar si se eliminó correctamente
                cursor.execute("SELECT COUNT(*) FROM pedidos WHERE pkid_pedido = %s", [pedido_id])
                if cursor.fetchone()[0] == 0:
                    messages.success(request, f"✅ Pedido #{pedido_id} eliminado permanentemente.")
                else:
                    messages.error(request, f"❌ Error: No se pudo eliminar el pedido #{pedido_id}")
                
        except Exception as e:
            print(f"ERROR al eliminar pedido: {str(e)}")
            if "foreign key constraint" in str(e).lower():
                messages.error(request, f"❌ Error: No se puede eliminar el pedido porque tiene movimientos de stock asociados. Intenta cancelarlo en lugar de eliminarlo.")
            else:
                messages.error(request, f"Error al eliminar pedido: {str(e)}")
    
    return redirect('gestionar_ventas')

@login_required(login_url='login')
def corregir_stock_pedido(request, pedido_id):
    """Función especial para corregir problemas de stock en pedidos específicos - CON VARIANTES"""
    if request.method == 'POST':
        try:
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('principal')
            
            negocio = datos['negocio_activo']
            
            with connection.cursor() as cursor:
                # Verificar el pedido
                cursor.execute("""
                    SELECT estado_pedido FROM pedidos 
                    WHERE pkid_pedido = %s AND fknegocio_pedido = %s
                """, [pedido_id, negocio.pkid_neg])
                
                pedido = cursor.fetchone()
                if not pedido:
                    messages.error(request, "Pedido no encontrado")
                    return redirect('gestionar_ventas')
                
                estado_actual = pedido[0]
                
                if estado_actual == 'cancelado':
                    # Reabastecer stock manualmente para pedidos cancelados - CON VARIANTES
                    cursor.execute("""
                        SELECT 
                            dp.fkproducto_detalle, 
                            dp.cantidad_detalle, 
                            p.stock_prod, 
                            p.nom_prod,
                            ci.variante_id,
                            vp.nombre_variante,
                            vp.stock_variante
                        FROM detalles_pedido dp
                        JOIN productos p ON dp.fkproducto_detalle = p.pkid_prod
                        LEFT JOIN carrito_item ci ON dp.fkpedido_detalle = ci.fkcarrito
                        LEFT JOIN variantes_producto vp ON ci.variante_id = vp.id_variante
                        WHERE dp.fkpedido_detalle = %s 
                        AND p.fknegocioasociado_prod = %s
                    """, [pedido_id, negocio.pkid_neg])
                    
                    productos_afectados = cursor.fetchall()
                    
                    productos_corregidos = 0
                    for (producto_id, cantidad, stock_actual, nombre_producto, 
                         variante_id, nombre_variante, stock_variante) in productos_afectados:
                        
                        if variante_id and stock_variante is not None:
                            # ES UNA VARIANTE - Reabastecer la variante
                            nuevo_stock_variante = stock_variante + cantidad
                            
                            cursor.execute("""
                                UPDATE variantes_producto 
                                SET stock_variante = %s
                                WHERE id_variante = %s
                            """, [nuevo_stock_variante, variante_id])
                            
                            # Registrar movimiento de corrección para variante
                            cursor.execute("""
                                INSERT INTO movimientos_stock 
                                (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                                 stock_anterior, stock_nuevo, usuario_id, pedido_id, variante_id, descripcion_variante, fecha_movimiento)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, [
                                producto_id, negocio.pkid_neg, 'entrada', 'correccion_manual_variante', 
                                cantidad, stock_variante, nuevo_stock_variante,
                                datos['perfil'].id, pedido_id, variante_id, nombre_variante, datetime.now()
                            ])
                        
                        else:
                            # ES PRODUCTO BASE - Reabastecer producto base
                            nuevo_stock = stock_actual + cantidad
                            
                            cursor.execute("""
                                UPDATE productos 
                                SET stock_prod = %s,
                                    estado_prod = CASE 
                                        WHEN %s > 0 THEN 'disponible'
                                        ELSE estado_prod
                                    END
                                WHERE pkid_prod = %s AND fknegocioasociado_prod = %s
                            """, [nuevo_stock, nuevo_stock, producto_id, negocio.pkid_neg])
                            
                            # Registrar movimiento de corrección
                            cursor.execute("""
                                INSERT INTO movimientos_stock 
                                (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                                 stock_anterior, stock_nuevo, usuario_id, pedido_id, fecha_movimiento)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, [
                                producto_id, negocio.pkid_neg, 'entrada', 'correccion_manual', 
                                cantidad, stock_actual, nuevo_stock,
                                datos['perfil'].id, pedido_id, datetime.now()
                            ])
                        
                        productos_corregidos += 1
                    
                    messages.success(request, f"✅ Stock del pedido #{pedido_id} corregido manualmente. {productos_corregidos} productos actualizados.")
                else:
                    messages.info(request, "El pedido no está cancelado, no se requiere corrección.")
                
        except Exception as e:
            print(f"ERROR en corrección manual: {str(e)}")
            messages.error(request, f"Error en corrección manual: {str(e)}")
    
    return redirect('gestionar_ventas')

# ==================== FUNCIÓN SIMPLIFICADA PARA ENVIAR CORREOS DE ESTADO ====================
def enviar_correo_estado_pedido(pedido_id, nuevo_estado):
    """Enviar correo electrónico al cliente cuando cambia el estado de un pedido - VERSIÓN SIMPLE"""
    try:
        print(f"📧 Enviando correo para pedido #{pedido_id}, estado: {nuevo_estado}")
        
        with connection.cursor() as cursor:
            # Obtener información básica del pedido
            cursor.execute("""
                SELECT 
                    p.pkid_pedido,
                    p.total_pedido,
                    p.fecha_pedido,
                    u.email,
                    u.first_name,
                    n.nom_neg
                FROM pedidos p
                JOIN usuario_perfil up ON p.fkusuario_pedido = up.id
                JOIN auth_user u ON up.fkuser_id = u.id
                JOIN negocios n ON p.fknegocio_pedido = n.pkid_neg
                WHERE p.pkid_pedido = %s
            """, [pedido_id])
            
            pedido_info = cursor.fetchone()
            
            if not pedido_info:
                print(f"❌ No se encontró el pedido #{pedido_id}")
                return False
            
            # Obtener detalles del pedido
            cursor.execute("""
                SELECT 
                    p.nom_prod,
                    dp.cantidad_detalle,
                    dp.precio_unitario
                FROM detalles_pedido dp
                JOIN productos p ON dp.fkproducto_detalle = p.pkid_prod
                WHERE dp.fkpedido_detalle = %s
            """, [pedido_id])
            
            detalles = cursor.fetchall()

        # Verificar email del cliente
        email_cliente = pedido_info[3]
        if not email_cliente:
            print(f"⚠️ El cliente no tiene email")
            return False

        # Procesar items del pedido
        items_detallados = []
        for detalle in detalles:
            items_detallados.append({
                'nombre': detalle[0],
                'cantidad': detalle[1],
                'precio': float(detalle[2]),
                'subtotal': float(detalle[1]) * float(detalle[2])
            })

        # Textos según el estado
        estados_texto = {
            'confirmado': '✅ Confirmado',
            'preparando': '👨‍🍳 En Preparación', 
            'enviado': '🚚 En Camino',
            'entregado': '🎉 Entregado',
            'cancelado': '❌ Cancelado'
        }

        mensajes_estado = {
            'confirmado': 'El negocio ha confirmado tu pedido.',
            'preparando': 'Tu pedido está siendo preparado.',
            'enviado': '¡Tu pedido está en camino!',
            'entregado': '¡Pedido entregado exitosamente!',
            'cancelado': 'Tu pedido ha sido cancelado.'
        }

        # Formatear fecha
        fecha_pedido = pedido_info[2]
        if hasattr(fecha_pedido, 'strftime'):
            fecha_formateada = fecha_pedido.strftime("%d/%m/%Y a las %I:%M %p").lower()
        else:
            fecha_formateada = "Fecha no disponible"

        # Preparar datos para el template
        context = {
            'numero_pedido': f"VECY-{pedido_id:06d}",
            'estado_display': estados_texto.get(nuevo_estado, nuevo_estado),
            'mensaje_estado': mensajes_estado.get(nuevo_estado, ''),
            'fecha_pedido': fecha_formateada,
            'total_pedido': float(pedido_info[1]),
            'cliente_nombre': pedido_info[4] or "Cliente",
            'negocio_nombre': pedido_info[5],
            'items': items_detallados,
        }

        # Asunto del correo
        asunto = f"Actualización de Pedido - {estados_texto.get(nuevo_estado, 'Estado Actualizado')}"

        # Renderizar y enviar correo
        html_content = render_to_string('emails/estado_pedido.html', context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email='soportevecy@gmail.com',
            to=[email_cliente],
            reply_to=['soportevecy@gmail.com']
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        print(f"✅ Correo enviado a {email_cliente}")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando correo: {e}")
        return False
    
# ==================== FIN DE CÓDIGO PARA GESTIÓN DE VENTAS VENDEDOR ====================

# En la función descargar_plantilla_productos en vendedor_views.py

@login_required(login_url='login')
def descargar_plantilla_productos(request):
    """Vista para descargar plantilla Excel de productos"""
    try:
        # Crear un libro de Excel con pandas
        with pd.ExcelWriter('plantilla_productos.xlsx', engine='openpyxl') as writer:
            
            # Hoja de INSTRUCCIONES MEJORADA
            instrucciones_data = {
                'SECCIÓN': [
                    '📋 PRODUCTOS BASE',
                    '📋 PRODUCTOS BASE', 
                    '📋 PRODUCTOS BASE',
                    '📋 PRODUCTOS BASE',
                    '📋 PRODUCTOS BASE',
                    '📋 PRODUCTOS BASE',
                    '',
                    '🎨 VARIANTES (Opcional)',
                    '🎨 VARIANTES (Opcional)',
                    '🎨 VARIANTES (Opcional)',
                    '🎨 VARIANTES (Opcional)',
                    '🎨 VARIANTES (Opcional)',
                    '',
                    '⚠️ IMPORTANTE',
                    '⚠️ IMPORTANTE',
                    '⚠️ IMPORTANTE',
                    '⚠️ IMPORTANTE'
                ],
                'COLUMNA': [
                    'nombre*',
                    'precio*',
                    'descripcion',
                    'stock_inicial', 
                    'categoria*',
                    'estado',
                    '',
                    'producto_base*',
                    'nombre_variante*',
                    'precio_adicional',
                    'stock',
                    'estado',
                    '',
                    'FORMATO',
                    'OBLIGATORIOS',
                    'CATEGORÍAS',
                    'VINCULACIÓN'
                ],
                'DESCRIPCIÓN': [
                    'Nombre único del producto (Ej: "Helado de Vainilla")',
                    'Precio base del producto (Ej: 4000)',
                    'Descripción opcional del producto',
                    'Stock inicial (Ej: 10). Por defecto: 0',
                    'Nombre de la categoría (Ej: "Helado"). Se crea automáticamente si no existe',
                    'Estado: "disponible", "no_disponible" o "agotado". Por defecto: "disponible"',
                    '',
                    'Nombre EXACTO del producto base (debe existir en la hoja PRODUCTOS_BASE)',
                    'Nombre único de la variante (Ej: "Vaso Grande")',
                    'Precio adicional sobre el precio base (Ej: 1000). Por defecto: 0',
                    'Stock de la variante (Ej: 5). Por defecto: 0',
                    'Estado: "activa" o "inactiva". Por defecto: "activa"',
                    '',
                    'Los campos con * son obligatorios',
                    'Los nombres de productos deben ser únicos',
                    'Las categorías se crearán automáticamente si no existen',
                    'Las variantes se vinculan por nombre EXACTO del producto base'
                ]
            }
            df_instrucciones = pd.DataFrame(instrucciones_data)
            df_instrucciones.to_excel(writer, sheet_name='INSTRUCCIONES', index=False)
            
            # Hoja de PRODUCTOS_BASE VACÍA con solo los encabezados
            productos_data = {
                'nombre*': [],
                'precio*': [], 
                'descripcion': [],
                'stock_inicial': [],
                'categoria*': [],
                'estado': []
            }
            df_productos = pd.DataFrame(productos_data)
            df_productos.to_excel(writer, sheet_name='PRODUCTOS_BASE', index=False)
            
            # Hoja de VARIANTES VACÍA con solo los encabezados
            variantes_data = {
                'producto_base*': [],
                'nombre_variante*': [],
                'precio_adicional': [],
                'stock': [],
                'estado': []
            }
            df_variantes = pd.DataFrame(variantes_data)
            df_variantes.to_excel(writer, sheet_name='VARIANTES', index=False)
        
        # Leer el archivo generado y enviarlo como respuesta
        with open('plantilla_productos.xlsx', 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="plantilla_productos.xlsx"'
        
        # Eliminar el archivo temporal
        os.remove('plantilla_productos.xlsx')
        
        return response
        
    except Exception as e:
        messages.error(request, f'Error al generar plantilla: {str(e)}')
        return redirect('Crud_V')

# En Software/views/vendedor_views.py - función importar_productos_excel

@login_required(login_url='login')
def importar_productos_excel(request):
    """Vista para importar productos desde Excel - ACTUALIZADA CON REGISTRO DE VARIANTES"""
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        try:
            archivo = request.FILES['archivo_excel']
            sobrescribir = request.POST.get('sobrescribir_existentes') == 'on'
            crear_categorias = request.POST.get('crear_categorias') == 'on'
            
            # Validar extensión
            if not archivo.name.endswith(('.xlsx', '.xls')):
                messages.error(request, '❌ Solo se permiten archivos Excel (.xlsx, .xls)')
                return redirect('Crud_V')
            
            # Obtener datos del vendedor
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('Crud_V')
            
            negocio = datos['negocio_activo']
            perfil_id = datos['perfil'].id
            
            # Leer el archivo Excel
            try:
                # Leer todas las hojas
                df_productos = pd.read_excel(archivo, sheet_name='PRODUCTOS_BASE')
                df_variantes = pd.read_excel(archivo, sheet_name='VARIANTES')
            except Exception as e:
                messages.error(request, f'❌ Error al leer el archivo Excel: {str(e)}')
                return redirect('Crud_V')
            
            # Contadores para resultados
            productos_creados = 0
            productos_actualizados = 0
            variantes_creadas = 0
            movimientos_registrados = 0
            errores = []
            
            # ========== PROCESAR PRODUCTOS BASE ==========
            for index, row in df_productos.iterrows():
                try:
                    # Validar campos obligatorios
                    if pd.isna(row['nombre*']) or pd.isna(row['precio*']) or pd.isna(row['categoria*']):
                        errores.append(f"Fila {index+2}: Campos obligatorios faltantes")
                        continue
                    
                    nombre = str(row['nombre*']).strip()
                    precio = float(row['precio*'])
                    descripcion = str(row['descripcion']) if not pd.isna(row['descripcion']) else ""
                    stock = int(row['stock_inicial']) if not pd.isna(row['stock_inicial']) else 0
                    categoria_nombre = str(row['categoria*']).strip()
                    estado = str(row['estado']).lower() if not pd.isna(row['estado']) else 'disponible'
                    
                    # Buscar o crear categoría
                    try:
                        categoria = CategoriaProductos.objects.get(desc_cp__iexact=categoria_nombre)
                    except CategoriaProductos.DoesNotExist:
                        if crear_categorias:
                            categoria = CategoriaProductos.objects.create(desc_cp=categoria_nombre)
                        else:
                            errores.append(f"'{nombre}': Categoría '{categoria_nombre}' no existe")
                            continue
                    
                    # Verificar si el producto ya existe
                    producto_existente = Productos.objects.filter(
                        nom_prod__iexact=nombre,
                        fknegocioasociado_prod=negocio
                    ).first()
                    
                    stock_anterior = 0
                    if producto_existente:
                        stock_anterior = producto_existente.stock_prod
                        
                    if producto_existente and sobrescribir:
                        # Actualizar producto existente
                        producto_existente.precio_prod = precio
                        producto_existente.desc_prod = descripcion
                        producto_existente.stock_prod = stock
                        producto_existente.fkcategoria_prod = categoria
                        producto_existente.estado_prod = estado
                        producto_existente.save()
                        productos_actualizados += 1
                        producto = producto_existente
                    elif producto_existente:
                        errores.append(f"'{nombre}': Ya existe (usar sobrescribir)")
                        producto = producto_existente
                    else:
                        # Crear nuevo producto
                        producto = Productos.objects.create(
                            nom_prod=nombre,
                            precio_prod=precio,
                            desc_prod=descripcion,
                            stock_prod=stock,
                            fkcategoria_prod=categoria,
                            estado_prod=estado,
                            fknegocioasociado_prod=negocio
                        )
                        productos_creados += 1
                    
                    # ✅ REGISTRAR MOVIMIENTO DE STOCK PARA PRODUCTO BASE SI HAY STOCK INICIAL
                    if stock > 0:
                        try:
                            with connection.cursor() as cursor:
                                cursor.execute("""
                                    INSERT INTO movimientos_stock 
                                    (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                                     stock_anterior, stock_nuevo, usuario_id, fecha_movimiento)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, [
                                    producto.pkid_prod,
                                    negocio.pkid_neg,
                                    'entrada',
                                    'importacion_excel_producto',
                                    stock,
                                    stock_anterior,
                                    stock,
                                    perfil_id,
                                    datetime.now()
                                ])
                            movimientos_registrados += 1
                        except Exception as e:
                            print(f"Error registrando movimiento producto {nombre}: {e}")
                    
                except Exception as e:
                    nombre_producto = str(row['nombre*'])[:50] if not pd.isna(row['nombre*']) else f"Fila {index+2}"
                    errores.append(f"'{nombre_producto}': {str(e)}")
                    continue
            
            # ========== PROCESAR VARIANTES ==========
            for index, row in df_variantes.iterrows():
                try:
                    # Validar campos obligatorios
                    if pd.isna(row['producto_base*']) or pd.isna(row['nombre_variante*']):
                        continue  # Saltar variantes incompletas
                    
                    producto_base_nombre = str(row['producto_base*']).strip()
                    nombre_variante = str(row['nombre_variante*']).strip()
                    precio_adicional = float(row['precio_adicional']) if not pd.isna(row['precio_adicional']) else 0
                    stock_variante = int(row['stock']) if not pd.isna(row['stock']) else 0
                    estado_variante = str(row['estado']).lower() if not pd.isna(row['estado']) else 'activa'
                    
                    # Buscar producto base
                    try:
                        producto_base = Productos.objects.get(
                            nom_prod__iexact=producto_base_nombre,
                            fknegocioasociado_prod=negocio
                        )
                    except Productos.DoesNotExist:
                        errores.append(f"Variante '{nombre_variante}': Producto base '{producto_base_nombre}' no encontrado")
                        continue
                    
                    # Verificar si la variante ya existe
                    variante_existente = None
                    stock_anterior_variante = 0
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT id_variante, stock_variante FROM variantes_producto 
                            WHERE producto_id = %s AND nombre_variante = %s
                        """, [producto_base.pkid_prod, nombre_variante])
                        resultado = cursor.fetchone()
                        if resultado:
                            variante_existente = resultado[0]
                            stock_anterior_variante = resultado[1]
                    
                    if variante_existente and sobrescribir:
                        # Actualizar variante existente
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                UPDATE variantes_producto 
                                SET precio_adicional = %s, stock_variante = %s, estado_variante = %s
                                WHERE id_variante = %s
                            """, [precio_adicional, stock_variante, estado_variante, variante_existente])
                    elif not variante_existente:
                        # Crear nueva variante
                        sku_unico = f"VAR-{producto_base.pkid_prod}-{int(timezone.now().timestamp())}"
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO variantes_producto 
                                (producto_id, nombre_variante, precio_adicional, stock_variante, estado_variante, sku_variante, fecha_creacion)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, [
                                producto_base.pkid_prod,
                                nombre_variante,
                                precio_adicional,
                                stock_variante,
                                estado_variante,
                                sku_unico,
                                timezone.now()
                            ])
                            variante_id = cursor.lastrowid
                        variantes_creadas += 1
                        
                        # ✅ REGISTRAR MOVIMIENTO DE STOCK PARA VARIANTE SI HAY STOCK
                        if stock_variante > 0:
                            try:
                                with connection.cursor() as cursor:
                                    cursor.execute("""
                                        INSERT INTO movimientos_stock 
                                        (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                                         stock_anterior, stock_nuevo, usuario_id, variante_id, descripcion_variante, fecha_movimiento)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, [
                                        producto_base.pkid_prod,
                                        negocio.pkid_neg,
                                        'entrada',
                                        'importacion_excel_variante',
                                        stock_variante,
                                        0,  # Stock anterior era 0
                                        stock_variante,
                                        perfil_id,
                                        variante_id,
                                        nombre_variante,
                                        datetime.now()
                                    ])
                                movimientos_registrados += 1
                            except Exception as e:
                                print(f"Error registrando movimiento variante {nombre_variante}: {e}")
                    
                except Exception as e:
                    nombre_var = str(row['nombre_variante*'])[:50] if not pd.isna(row['nombre_variante*']) else f"Variante fila {index+2}"
                    errores.append(f"'{nombre_var}': {str(e)}")
                    continue
            
            # ========== PREPARAR MENSAJE DE RESULTADO ==========
            mensaje = f"✅ Importación completada: "
            if productos_creados > 0:
                mensaje += f"{productos_creados} productos creados, "
            if productos_actualizados > 0:
                mensaje += f"{productos_actualizados} productos actualizados, "
            if variantes_creadas > 0:
                mensaje += f"{variantes_creadas} variantes creadas, "
            if movimientos_registrados > 0:
                mensaje += f"{movimientos_registrados} movimientos registrados."
            
            if errores:
                mensaje += f" ❌ Errores: {len(errores)}"
                # Guardar errores en sesión para mostrarlos
                request.session['importacion_errores'] = errores[:10]  # Máximo 10 errores
            
            messages.success(request, mensaje)
            
        except Exception as e:
            messages.error(request, f'❌ Error en importación: {str(e)}')
    
    return redirect('Crud_V')


# En Software/views/vendedor_views.py - función descontar_stock_pedido_al_entregar

def descontar_stock_pedido_al_entregar(pedido_id):
    """
    DESCONTAR stock solo cuando el vendedor marca el pedido como ENTREGADO
    ACTUALIZADA PARA REGISTRAR MOVIMIENTOS DE VARIANTES
    """
    try:
        print(f"🔄 DEBUG descontar_stock_al_entregar: Descontando stock para pedido ENTREGADO {pedido_id}")
        
        # Obtener datos del pedido
        with connection.cursor() as cursor:
            # Obtener información del pedido y vendedor
            cursor.execute("""
                SELECT 
                    p.pkid_pedido,
                    p.fknegocio_pedido,
                    n.fkpropietario_neg
                FROM pedidos p
                JOIN negocios n ON p.fknegocio_pedido = n.pkid_neg
                WHERE p.pkid_pedido = %s
            """, [pedido_id])
            
            pedido_info = cursor.fetchone()
            if not pedido_info:
                print("❌ ERROR: Pedido no encontrado")
                return False
            
            pedido_id, negocio_id, propietario_id = pedido_info
            
            # ✅ CORRECCIÓN MEJORADA: Obtener items con información de variantes
            cursor.execute("""
                SELECT 
                    dp.fkproducto_detalle,
                    dp.cantidad_detalle,
                    dp.precio_unitario,
                    p.nom_prod,
                    p.stock_prod,
                    ci.variante_id,
                    vp.nombre_variante,
                    vp.stock_variante
                FROM detalles_pedido dp
                JOIN productos p ON dp.fkproducto_detalle = p.pkid_prod
                LEFT JOIN carrito_item ci ON dp.fkpedido_detalle = ci.fkcarrito AND dp.fkproducto_detalle = ci.fkproducto
                LEFT JOIN variantes_producto vp ON ci.variante_id = vp.id_variante
                WHERE dp.fkpedido_detalle = %s
            """, [pedido_id])
            
            items_pedido = cursor.fetchall()
            print(f"🔄 DEBUG: Items encontrados en detalles_pedido: {len(items_pedido)}")
            
            movimientos_registrados = 0
            
            # Procesar productos del pedido
            for (producto_id, cantidad, precio, nombre_producto, stock_actual, 
                 variante_id, nombre_variante, stock_variante) in items_pedido:
                
                print(f"🔄 DEBUG: Procesando - Producto: {producto_id}, Variante: {variante_id}, Cantidad: {cantidad}")
                
                if variante_id and nombre_variante:
                    # ✅ ES UNA VARIANTE - Descontar de la variante
                    print(f"🔄 DEBUG: Procesando VARIANTE {nombre_variante}")
                    
                    nuevo_stock_variante = stock_variante - cantidad
                    
                    print(f"🔄 DEBUG: Variante {nombre_variante} - Stock: {stock_variante} -> {nuevo_stock_variante}")
                    
                    if nuevo_stock_variante < 0:
                        print(f"⚠️ ADVERTENCIA: Stock negativo para variante {nombre_variante}, ajustando a 0")
                        nuevo_stock_variante = 0
                    
                    # Actualizar stock de la variante
                    cursor.execute("""
                        UPDATE variantes_producto 
                        SET stock_variante = %s
                        WHERE id_variante = %s
                    """, [nuevo_stock_variante, variante_id])
                    
                    # Registrar movimiento de salida para la variante
                    try:
                        cursor.execute("""
                            INSERT INTO movimientos_stock 
                            (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                             stock_anterior, stock_nuevo, usuario_id, pedido_id, variante_id, descripcion_variante, fecha_movimiento)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, [
                            producto_id, negocio_id, 'salida', 'pedido_entregado_variante', 
                            cantidad, stock_variante, nuevo_stock_variante,
                            propietario_id, pedido_id, variante_id, nombre_variante, datetime.now()
                        ])
                        movimientos_registrados += 1
                        print(f"✅ Movimiento registrado para variante {nombre_variante}")
                    except Exception as e:
                        print(f"⚠️ Error registrando movimiento de variante: {e}")
                
                else:
                    # ✅ ES PRODUCTO BASE - Descontar del producto base
                    print(f"🔄 DEBUG: Procesando PRODUCTO BASE {nombre_producto}")
                    
                    nuevo_stock = stock_actual - cantidad
                    print(f"🔄 DEBUG: Producto base {nombre_producto} - Stock: {stock_actual} -> {nuevo_stock}")
                    
                    if nuevo_stock < 0:
                        print(f"⚠️ ADVERTENCIA: Stock negativo para {nombre_producto}, ajustando a 0")
                        nuevo_stock = 0
                    
                    # Actualizar stock del producto base
                    cursor.execute("""
                        UPDATE productos 
                        SET stock_prod = %s,
                            estado_prod = CASE 
                                WHEN %s <= 0 THEN 'agotado'
                                ELSE 'disponible'
                            END
                        WHERE pkid_prod = %s
                    """, [nuevo_stock, nuevo_stock, producto_id])
                    
                    # Registrar movimiento de salida para producto base
                    try:
                        cursor.execute("""
                            INSERT INTO movimientos_stock 
                            (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                             stock_anterior, stock_nuevo, usuario_id, pedido_id, fecha_movimiento)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, [
                            producto_id, negocio_id, 'salida', 'pedido_entregado', 
                            cantidad, stock_actual, nuevo_stock,
                            propietario_id, pedido_id, datetime.now()
                        ])
                        movimientos_registrados += 1
                        print(f"✅ Movimiento registrado para producto base {nombre_producto}")
                    except Exception as e:
                        print(f"⚠️ Error registrando movimiento: {e}")
        
        print(f"✅ Stock descontado definitivamente para pedido ENTREGADO. Movimientos registrados: {movimientos_registrados}")
        return True
        
    except Exception as e:
        print(f"❌ ERROR en descontar_stock_al_entregar: {str(e)}")
        import traceback
        print(f"TRACEBACK: {traceback.format_exc()}")
        return False

def reabastecer_stock_por_cancelacion(pedido_id):
    """
    SOLO para uso manual si es necesario reabastecer stock de un pedido cancelado
    Esta función NO se usa en el flujo normal
    """
    try:
        print(f"🔄 DEBUG reabastecer_stock: Reabasteciendo stock para pedido cancelado {pedido_id}")
        
        # Obtener datos del pedido
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    p.fknegocio_pedido,
                    n.fkpropietario_neg
                FROM pedidos p
                JOIN negocios n ON p.fknegocio_pedido = n.pkid_neg
                WHERE p.pkid_pedido = %s
            """, [pedido_id])
            
            pedido_info = cursor.fetchone()
            if not pedido_info:
                return False
            
            negocio_id, propietario_id = pedido_info
            
            # Obtener items del carrito
            cursor.execute("""
                SELECT 
                    ci.fkproducto,
                    ci.cantidad,
                    ci.variante_id,
                    ci.variante_seleccionada
                FROM carrito_item ci
                INNER JOIN carrito c ON ci.fkcarrito = c.pkid_carrito
                INNER JOIN pedidos p ON c.fkusuario_carrito = p.fkusuario_pedido
                WHERE p.pkid_pedido = %s
            """, [pedido_id])
            
            items_carrito = cursor.fetchall()
            
            for (producto_id, cantidad, variante_id, variante_nombre) in items_carrito:
                
                if variante_id:
                    # Reabastecer variante
                    cursor.execute("""
                        SELECT stock_variante, nombre_variante 
                        FROM variantes_producto 
                        WHERE id_variante = %s
                    """, [variante_id])
                    
                    resultado_variante = cursor.fetchone()
                    if resultado_variante:
                        stock_variante, nombre_variante = resultado_variante
                        nuevo_stock_variante = stock_variante + cantidad
                        
                        cursor.execute("""
                            UPDATE variantes_producto 
                            SET stock_variante = %s
                            WHERE id_variante = %s
                        """, [nuevo_stock_variante, variante_id])
                
                else:
                    # Reabastecer producto base
                    cursor.execute("""
                        SELECT stock_prod, nom_prod FROM productos 
                        WHERE pkid_prod = %s
                    """, [producto_id])
                    
                    resultado_producto = cursor.fetchone()
                    if resultado_producto:
                        stock_actual, nombre_producto = resultado_producto
                        nuevo_stock = stock_actual + cantidad
                        
                        cursor.execute("""
                            UPDATE productos 
                            SET stock_prod = %s,
                                estado_prod = CASE 
                                    WHEN %s > 0 THEN 'disponible'
                                    ELSE estado_prod
                                END
                            WHERE pkid_prod = %s
                        """, [nuevo_stock, nuevo_stock, producto_id])
        
        print("✅ Stock reabastecido manualmente")
        return True
        
    except Exception as e:
        print(f"❌ ERROR en reabastecer_stock: {str(e)}")
        return False
    
# ==================== REPORTAR RESEÑAS ====================
@login_required(login_url='login')
def reportar_resena(request, resena_id):
    """Vista para reportar una reseña - CORREGIDA"""
    if request.method == 'POST':
        try:
            # Obtener datos del vendedor
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                return JsonResponse({'success': False, 'error': 'No tienes un negocio activo.'})
            
            negocio = datos['negocio_activo']
            perfil = datos['perfil']
            
            # Verificar que la reseña pertenece al negocio del vendedor
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pkid_resena FROM resenas_negocios WHERE pkid_resena = %s AND fknegocio_resena = %s",
                    [resena_id, negocio.pkid_neg]
                )
                if not cursor.fetchone():
                    return JsonResponse({'success': False, 'error': 'No puedes reportar esta reseña'})
            
            # Verificar si ya existe un reporte pendiente para esta reseña
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pkid_reporte FROM reportes 
                    WHERE fkresena_reporte = %s AND fknegocio_reportado = %s AND estado_reporte = 'pendiente'
                """, [resena_id, negocio.pkid_neg])
                
                if cursor.fetchone():
                    return JsonResponse({'success': False, 'error': 'Ya existe un reporte pendiente para esta reseña'})
            
            # Obtener datos del formulario
            motivo = request.POST.get('motivo', 'otro')
            descripcion = request.POST.get('descripcion', '')
            
            # Validar motivo
            if not motivo:
                return JsonResponse({'success': False, 'error': 'Debes seleccionar un motivo'})
            
            # Insertar el reporte en la base de datos
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO reportes 
                    (fknegocio_reportado, fkresena_reporte, fkusuario_reporta, motivo, descripcion, estado_reporte, fecha_reporte)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [
                    negocio.pkid_neg,
                    resena_id,
                    perfil.id,
                    motivo,
                    descripcion,
                    'pendiente',
                    datetime.now()
                ])
            
            return JsonResponse({'success': True, 'message': 'Reporte enviado correctamente'})
            
        except Exception as e:
            print(f"ERROR al reportar reseña: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Error interno del servidor'})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})
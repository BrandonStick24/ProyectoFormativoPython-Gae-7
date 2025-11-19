# Software/vendedor_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction, connection
from datetime import datetime
import json
import os
from django.conf import settings

# Importar modelos
from Software.models import (
    Negocios, TipoNegocio, UsuarioPerfil, AuthUser, 
    Productos, CategoriaProductos, Pedidos, DetallesPedido,
    ResenasNegocios
)

# Importar función auxiliar de categorías
from .vendedor_categorias_views import obtener_categorias_por_tiponegocio

# ==================== FUNCIONES AUXILIARES VENDEDOR ====================
def obtener_datos_vendedor(request):
    """Función auxiliar para obtener datos del vendedor con negocio seleccionado"""
    try:
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
        
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
            'nombre_usuario': auth_user.first_name,
            'perfil': perfil,
            'negocio_activo': negocio_seleccionado,
        }
    except (AuthUser.DoesNotExist, UsuarioPerfil.DoesNotExist):
        return {}

# ==================== VISTA PARA SELECCIONAR NEGOCIO ====================
@login_required(login_url='login')
def seleccionar_negocio(request, negocio_id):
    """Vista para cambiar el negocio seleccionado en sesión"""
    try:
        # Verificar que el negocio pertenezca al usuario
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
        
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
            
            auth_user = AuthUser.objects.get(username=request.user.username)
            perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
            
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
@login_required(login_url='login')
def vendedor_dash(request):
    try:
        datos = obtener_datos_vendedor(request)
        if not datos:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('inicio')
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': datos['negocio_activo']
        }
        return render(request, 'Vendedor/Dashboard_V.html', contexto)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('inicio')

# ==================== VISTAS VENDEDOR - PRODUCTOS ====================
@login_required(login_url='login')
def Crud_V(request):
    """Vista principal de productos CON VARIANTES"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('inicio')
        
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
        return redirect('inicio')

@login_required(login_url='login')
def gestionar_variantes(request, producto_id):
    """Vista para gestionar variantes de un producto específico"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('inicio')
        
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
            return redirect('inicio')
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': datos['negocio_activo']
        }
        return render(request, 'Vendedor/Chats_V.html', contexto)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('inicio')

# ==================== VISTAS VENDEDOR - STOCK ====================
@login_required(login_url='login')
def Stock_V(request):
    """Vista para dashboard de stock - MEJORADA"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('inicio')
        
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
        return redirect('inicio')

# ==================== VISTAS VENDEDOR - CREAR PRODUCTO ====================
@login_required(login_url='login')
def crear_producto_P(request):
    """Vista para crear nuevo producto usando categorías filtradas por tipo de negocio - CON REGISTRO DE STOCK"""
    if request.method == 'POST':
        try:
            auth_user = AuthUser.objects.get(username=request.user.username)
            perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
            
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
            auth_user = AuthUser.objects.get(username=request.user.username)
            perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
            
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
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
        
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
    """Vista para eliminar producto - CON REGISTRO DE STOCK"""
    if request.method == 'POST':
        try:
            # Verificar permisos y obtener negocio seleccionado
            auth_user = AuthUser.objects.get(username=request.user.username)
            perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
            
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
            
            # REGISTRAR MOVIMIENTO DE STOCK POR ELIMINACIÓN DEL PRODUCTO
            if stock_eliminado > 0:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO movimientos_stock 
                            (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                             stock_anterior, stock_nuevo, usuario_id, fecha_movimiento)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, [
                            producto_id, 
                            negocio.pkid_neg, 
                            'salida', 
                            'eliminacion_producto', 
                            stock_eliminado, 
                            stock_eliminado,  # Stock anterior
                            0,  # Stock nuevo es 0 (producto eliminado)
                            perfil.id, 
                            datetime.now()
                        ])
                except Exception as e:
                    print(f"Error registrando movimiento al eliminar producto (puede ignorarse): {e}")
            
            # Ahora eliminar el producto
            producto.delete()
            
            messages.success(request, f"Producto '{nombre_producto}' eliminado exitosamente.")
            
        except Productos.DoesNotExist:
            messages.error(request, "El producto no existe o no tienes permisos para eliminarlo.")
        except Negocios.DoesNotExist:
            messages.error(request, "El negocio seleccionado no existe o no tienes permisos.")
        except Exception as e:
            messages.error(request, f"Error al eliminar producto: {str(e)}")
    
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
                return redirect('inicio')
            
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
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
        
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
            'nombre': auth_user.first_name,
            'perfil': perfil,
            'negocio_activo': negocio_activo,
            'negocios': negocios,
            'tipos_negocio': tipos_negocio,
        }
        
        return render(request, 'Vendedor/Negocios_V.html', contexto)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('inicio')

# ==================== CONFIGURACIÓN DE NEGOCIO ====================
@login_required(login_url='login')
def configurar_negocio(request, negocio_id):
    print(f"=== DEBUG configurar_negocio: Negocio ID {negocio_id} ===")
    
    try:
        # Verificar que el negocio pertenece al usuario
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
        
        print(f"DEBUG: Usuario: {auth_user.username}, Perfil: {perfil.id}")
        
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
            'nombre': auth_user.first_name,
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
    """Vista para reseñas usando SQL directo - CON NUEVAS COLUMNAS"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('inicio')
        
        negocio = datos['negocio_activo']
        
        # CONSULTA ACTUALIZADA CON LAS NUEVAS COLUMNAS
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
                r.fecha_respuesta
            FROM resenas_negocios r
            JOIN usuario_perfil up ON r.fkusuario_resena = up.id
            JOIN auth_user u ON up.fkuser_id = u.id
            WHERE r.fknegocio_resena = %s 
            AND r.estado_resena = 'activa'
            ORDER BY r.fecha_resena DESC
            """
            cursor.execute(sql, [negocio.pkid_neg])
            resultados = cursor.fetchall()
        
        # Procesar resultados CON RESPUESTAS
        resenas_completas = []
        for row in resultados:
            tiene_respuesta = row[6] is not None and row[6].strip() != ''
            fecha_respuesta = row[7].strftime('%d %b %Y') if row[7] else ''
            
            resenas_completas.append({
                'id': row[0],
                'calificacion': row[1],
                'comentario': row[2] or 'Sin comentario',
                'fecha': row[3].strftime('%d %b %Y'),
                'cliente': row[4] or row[5] or f"Usuario {row[0]}",
                'respuesta': row[6] or '',
                'tiene_respuesta': tiene_respuesta,
                'fecha_respuesta': fecha_respuesta
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
        }
        
        return render(request, 'Vendedor/ver_resenas.html', contexto)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        messages.error(request, "Error al cargar reseñas")
        return redirect('inicio')

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
                return redirect('inicio')
            
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
            
            auth_user = AuthUser.objects.get(username=request.user.username)
            perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
            
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
            
            auth_user = AuthUser.objects.get(username=request.user.username)
            perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
            
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
            
            auth_user = AuthUser.objects.get(username=request.user.username)
            perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
            
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
    """Vista para ver ventas con nuevo flujo de estados"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('inicio')
        
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
                COUNT(d.pkid_detalle) as cantidad_productos,
                pg.metodo_pago,
                pg.estado_pago,
                up.doc_user
            FROM pedidos p
            JOIN usuario_perfil up ON p.fkusuario_pedido = up.id
            JOIN auth_user u ON up.fkuser_id = u.id
            LEFT JOIN detalles_pedido d ON p.pkid_pedido = d.fkpedido_detalle
            LEFT JOIN pagos_negocios pg ON p.pkid_pedido = pg.fkpedido
            WHERE p.fknegocio_pedido = %s
            GROUP BY p.pkid_pedido, p.estado_pedido, p.total_pedido, p.fecha_pedido, 
                     u.first_name, u.username, pg.metodo_pago, pg.estado_pago, up.doc_user
            ORDER BY p.fecha_pedido DESC
            """
            cursor.execute(sql, [negocio.pkid_neg])
            resultados = cursor.fetchall()
        
        # Procesar resultados
        pedidos = []
        for row in resultados:
            pedidos.append({
                'id': row[0],
                'estado': row[1],
                'total': row[2],
                'fecha': row[3].strftime('%d/%m/%Y %H:%M'),
                'cliente': row[4] or row[5] or f"Usuario {row[0]}",
                'documento': row[9],
                'cantidad_productos': row[6],
                'metodo_pago': row[7] or 'No especificado',
                'estado_pago': row[8] or 'pendiente'
            })
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': negocio,
            'pedidos': pedidos,
        }
        
        return render(request, 'Vendedor/gestion_ventas.html', contexto)
        
    except Exception as e:
        print(f"ERROR al cargar ventas: {str(e)}")
        messages.error(request, "Error al cargar las ventas")
        return redirect('inicio')

@login_required(login_url='login')
def ver_recibo_pedido(request, pedido_id):
    """Vista para ver el recibo completo de un pedido"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('inicio')
        
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
    """Vista para cambiar estado del pedido con nuevo flujo de stock"""
    if request.method == 'POST':
        try:
            nuevo_estado = request.POST.get('nuevo_estado')
            motivo_cancelacion = request.POST.get('motivo_cancelacion', 'Sin motivo especificado')
            
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('inicio')
            
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
                
                # 2. Actualizar el estado del pedido
                cursor.execute("""
                    UPDATE pedidos 
                    SET estado_pedido = %s, fecha_actualizacion = %s
                    WHERE pkid_pedido = %s AND fknegocio_pedido = %s
                """, [nuevo_estado, datetime.now(), pedido_id, negocio.pkid_neg])
                
                # 3. MANEJO DE STOCK SEGÚN NUEVO FLUJO
                if nuevo_estado in ['enviado', 'entregado'] and estado_actual not in ['enviado', 'entregado']:
                    # DESCONTAR STOCK solo cuando se envía o entrega por primera vez
                    cursor.execute("""
                        UPDATE productos p
                        JOIN detalles_pedido dp ON p.pkid_prod = dp.fkproducto_detalle
                        SET p.stock_prod = p.stock_prod - dp.cantidad_detalle,
                            p.estado_prod = CASE 
                                WHEN p.stock_prod - dp.cantidad_detalle <= 0 THEN 'agotado'
                                WHEN p.stock_prod - dp.cantidad_detalle > 0 THEN 'disponible'
                                ELSE p.estado_prod
                            END
                        WHERE dp.fkpedido_detalle = %s 
                        AND p.fknegocioasociado_prod = %s
                    """, [pedido_id, negocio.pkid_neg])
                    
                    # Registrar movimiento de salida por envío/entrega
                    cursor.execute("""
                        INSERT INTO movimientos_stock 
                        (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                         stock_anterior, stock_nuevo, usuario_id, pedido_id, fecha_movimiento)
                        SELECT 
                            dp.fkproducto_detalle,
                            %s,
                            'salida',
                            'envio_pedido',
                            dp.cantidad_detalle,
                            p.stock_prod + dp.cantidad_detalle,  -- Stock anterior (antes de descontar)
                            p.stock_prod,  -- Stock nuevo (después de descontar)
                            %s,
                            %s,
                            %s
                        FROM detalles_pedido dp
                        JOIN productos p ON dp.fkproducto_detalle = p.pkid_prod
                        WHERE dp.fkpedido_detalle = %s
                    """, [negocio.pkid_neg, datos['perfil'].id, pedido_id, datetime.now(), pedido_id])
                    
                    messages.success(request, f"✅ Pedido {nuevo_estado}. Stock descontado.")
                
                elif nuevo_estado == 'cancelado' and estado_actual not in ['cancelado']:
                    # REABASTECER STOCK solo si el pedido estaba en un estado donde ya se había descontado stock
                    if estado_actual in ['enviado', 'entregado']:
                        cursor.execute("""
                            UPDATE productos p
                            JOIN detalles_pedido dp ON p.pkid_prod = dp.fkproducto_detalle
                            SET p.stock_prod = p.stock_prod + dp.cantidad_detalle,
                                p.estado_prod = CASE 
                                    WHEN p.stock_prod + dp.cantidad_detalle > 0 THEN 'disponible'
                                    ELSE p.estado_prod
                                END
                            WHERE dp.fkpedido_detalle = %s 
                            AND p.fknegocioasociado_prod = %s
                        """, [pedido_id, negocio.pkid_neg])
                        
                        # Registrar movimiento de entrada por cancelación
                        cursor.execute("""
                            INSERT INTO movimientos_stock 
                            (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                             stock_anterior, stock_nuevo, usuario_id, pedido_id, fecha_movimiento)
                            SELECT 
                                dp.fkproducto_detalle,
                                %s,
                                'entrada',
                                'cancelacion_pedido',
                                dp.cantidad_detalle,
                                p.stock_prod - dp.cantidad_detalle,  -- Stock anterior (antes de reabastecer)
                                p.stock_prod,  -- Stock nuevo (después de reabastecer)
                                %s,
                                %s,
                                %s
                            FROM detalles_pedido dp
                            JOIN productos p ON dp.fkproducto_detalle = p.pkid_prod
                            WHERE dp.fkpedido_detalle = %s
                        """, [negocio.pkid_neg, datos['perfil'].id, pedido_id, datetime.now(), pedido_id])
                        
                        messages.success(request, f"✅ Pedido cancelado. Stock reabastecido. Motivo: {motivo_cancelacion}")
                    else:
                        # Si se cancela un pedido que no tenía stock descontado
                        messages.success(request, f"✅ Pedido cancelado. Motivo: {motivo_cancelacion}")
                
                else:
                    # Para otros cambios de estado (confirmado → preparando, etc.)
                    messages.success(request, f"✅ Pedido actualizado a: {nuevo_estado}")
            
        except Exception as e:
            print(f"ERROR al cambiar estado: {str(e)}")
            messages.error(request, f"Error al cambiar el estado del pedido: {str(e)}")
    
    return redirect('gestionar_ventas')

@login_required(login_url='login')
def eliminar_pedido(request, pedido_id):
    """Vista secreta para eliminar pedidos (solo para pruebas)"""
    if request.method == 'POST':
        try:
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('inicio')
            
            negocio = datos['negocio_activo']
            
            with connection.cursor() as cursor:
                # Verificar que el pedido pertenece al negocio
                cursor.execute("""
                    SELECT COUNT(*) FROM pedidos 
                    WHERE pkid_pedido = %s AND fknegocio_pedido = %s
                """, [pedido_id, negocio.pkid_neg])
                
                if cursor.fetchone()[0] == 0:
                    messages.error(request, "Pedido no encontrado o no tienes permisos.")
                    return redirect('gestionar_ventas')
                
                # Primero eliminar detalles y pagos relacionados
                cursor.execute("DELETE FROM detalles_pedido WHERE fkpedido_detalle = %s", [pedido_id])
                cursor.execute("DELETE FROM pagos_negocios WHERE fkpedido = %s", [pedido_id])
                
                # Luego eliminar el pedido
                cursor.execute("DELETE FROM pedidos WHERE pkid_pedido = %s", [pedido_id])
            
            messages.success(request, f"🚮 Pedido #{pedido_id} eliminado permanentemente (solo pruebas).")
            
        except Exception as e:
            print(f"ERROR al eliminar pedido: {str(e)}")
            messages.error(request, f"Error al eliminar pedido: {str(e)}")
    
    return redirect('gestionar_ventas')

@login_required(login_url='login')
def ajustar_stock_producto(request, producto_id):
    """Vista para ajustar manualmente el stock de un producto - MEJORADA"""
    if request.method == 'POST':
        try:
            tipo_ajuste = request.POST.get('tipo_ajuste', 'entrada')
            cantidad_ajuste = int(request.POST.get('cantidad_ajuste', 0))
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
                
                # Actualizar stock
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
                        datos['perfil'].id, datetime.now()
                    ])
                except Exception as e:
                    print(f"Error registrando movimiento (puede ignorarse): {e}")
                
                messages.success(request, f"✅ Stock de '{nombre_producto}' actualizado: {stock_anterior} {mensaje_tipo} = {stock_nuevo}")
                
        except Exception as e:
            print(f"ERROR al ajustar stock: {str(e)}")
            messages.error(request, f"Error al ajustar stock: {str(e)}")
    
    return redirect('Crud_V')
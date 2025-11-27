# software/views/vendedor_variantes_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import connection
from datetime import datetime
import os
from django.conf import settings

# Importar modelos
from Software.models import Negocios, UsuarioPerfil, Productos
from .vendedor_views import obtener_datos_vendedor  # Usar la misma función auxiliar

# ==================== FUNCIÓN AUXILIAR PARA OBTENER DATOS VENDEDOR ====================
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

@login_required(login_url='login')
def gestionar_variantes(request, producto_id):
    """Vista principal para gestionar variantes de un producto - MEJORADA"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('Crud_V')
        
        negocio = datos['negocio_activo']
        
        # Verificar que el producto pertenece al negocio
        producto = Productos.objects.get(
            pkid_prod=producto_id, 
            fknegocioasociado_prod=negocio
        )
        
        # Obtener variantes del producto
        variantes = []
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    v.id_variante,
                    v.nombre_variante,
                    v.precio_adicional,
                    v.stock_variante,
                    v.estado_variante,
                    v.sku_variante,
                    v.imagen_variante,
                    v.fecha_creacion,
                    (p.precio_prod + COALESCE(v.precio_adicional, 0)) as precio_total
                FROM variantes_producto v
                JOIN productos p ON v.producto_id = p.pkid_prod
                WHERE v.producto_id = %s AND p.fknegocioasociado_prod = %s
                ORDER BY v.nombre_variante
            """, [producto_id, negocio.pkid_neg])
            
            for row in cursor.fetchall():
                variantes.append({
                    'id': row[0],
                    'nombre': row[1],
                    'precio_adicional': float(row[2]) if row[2] else 0.0,
                    'stock': row[3],
                    'estado': row[4],
                    'sku': row[5],
                    'imagen': row[6],
                    'fecha_creacion': row[7].strftime('%d/%m/%Y %H:%M') if row[7] else '',
                    'precio_total': float(row[8]) if row[8] else float(producto.precio_prod)
                })
        
        # Convertir decimales a float para el template
        producto.precio_prod = float(producto.precio_prod)
        
        # Obtener datos para edición si existen en la sesión
        variante_editar = None
        if 'variante_editar_data' in request.session:
            variante_editar = request.session.pop('variante_editar_data', None)
        
        contexto = {
            'nombre': datos.get('nombre_usuario', 'Usuario'),
            'perfil': datos.get('perfil'),
            'negocio_activo': negocio,
            'producto': producto,
            'variantes': variantes,
            'variante_editar': variante_editar,  # Datos para el modal de edición
        }
        
        return render(request, 'Vendedor/gestion_variantes.html', contexto)
        
    except Productos.DoesNotExist:
        messages.error(request, "Producto no encontrado o no tienes permisos.")
        return redirect('Crud_V')
    except Exception as e:
        print(f"ERROR en gestionar_variantes: {str(e)}")
        messages.error(request, f"Error al cargar variantes: {str(e)}")
        return redirect('Crud_V')
    
# En Software/views/vendedor_variantes_views.py - función crear_variante

@login_required(login_url='login')
def crear_variante(request, producto_id):
    """Vista para crear una nueva variante - ACTUALIZADA CON MEJOR REGISTRO"""
    if request.method == 'POST':
        try:
            print(f"=== DEBUG CREAR VARIANTE: Producto ID {producto_id} ===")
            
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('Crud_V')
            
            negocio = datos['negocio_activo']
            perfil_id = datos['perfil'].id
            
            # Verificar que el producto pertenece al negocio
            producto = Productos.objects.get(
                pkid_prod=producto_id, 
                fknegocioasociado_prod=negocio
            )
            
            # Obtener datos del formulario
            nombre_variante = request.POST.get('nombre_variante')
            precio_adicional = request.POST.get('precio_adicional', 0)
            stock_variante = request.POST.get('stock_variante', 0)
            imagen_variante = request.FILES.get('imagen_variante')
            
            print(f"DEBUG: Nombre: {nombre_variante}, Precio: {precio_adicional}, Stock: {stock_variante}")
            
            # Validaciones
            if not nombre_variante:
                messages.error(request, "El nombre de la variante es obligatorio.")
                return redirect('gestionar_variantes', producto_id=producto_id)
            
            # Convertir valores
            try:
                precio_adicional = float(precio_adicional) if precio_adicional else 0.0
                stock_inicial = int(stock_variante) if stock_variante else 0
            except ValueError:
                messages.error(request, "Precio adicional y stock deben ser números válidos.")
                return redirect('gestionar_variantes', producto_id=producto_id)
            
            # Procesar imagen si se subió
            nombre_archivo_imagen = None
            if imagen_variante:
                try:
                    # Generar nombre único para la imagen
                    extension = os.path.splitext(imagen_variante.name)[1]
                    nombre_archivo_imagen = f"variante_{producto_id}_{int(timezone.now().timestamp())}{extension}"
                    
                    # Guardar la imagen en la carpeta media/variantes/
                    media_path = os.path.join(settings.MEDIA_ROOT, 'variantes')
                    os.makedirs(media_path, exist_ok=True)
                    
                    with open(os.path.join(media_path, nombre_archivo_imagen), 'wb+') as destination:
                        for chunk in imagen_variante.chunks():
                            destination.write(chunk)
                    print(f"DEBUG: Imagen guardada: {nombre_archivo_imagen}")
                except Exception as e:
                    print(f"ERROR procesando imagen: {e}")
                    messages.warning(request, "La imagen no pudo ser procesada, pero la variante se creará sin imagen.")
            
            # Generar SKU único automáticamente
            sku_unico = f"VAR-{producto_id}-{int(timezone.now().timestamp())}"
            
            # Crear la variante
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO variantes_producto 
                    (producto_id, nombre_variante, precio_adicional, stock_variante, estado_variante, sku_variante, imagen_variante, fecha_creacion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    producto_id,
                    nombre_variante.strip(),
                    precio_adicional,
                    stock_inicial,
                    'activa',  # Estado por defecto
                    sku_unico,
                    nombre_archivo_imagen,
                    datetime.now()
                ])
                
                # Obtener el ID de la variante recién creada
                variante_id = cursor.lastrowid
                print(f"DEBUG: Variante creada - ID: {variante_id}")
            
            # ✅ REGISTRAR MOVIMIENTO DE STOCK POR CREACIÓN DE VARIANTE - MEJORADO
            if stock_inicial > 0:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO movimientos_stock 
                            (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                             stock_anterior, stock_nuevo, usuario_id, fecha_movimiento, variante_id, descripcion_variante)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, [
                            producto_id,
                            negocio.pkid_neg,
                            'entrada',
                            'creacion_variante',
                            stock_inicial,
                            0,  # Stock anterior era 0
                            stock_inicial,
                            perfil_id,
                            datetime.now(),
                            variante_id,
                            nombre_variante
                        ])
                    print("DEBUG: Movimiento de stock registrado para variante")
                except Exception as e:
                    print(f"ERROR registrando movimiento: {e}")
            
            messages.success(request, f"✅ Variante '{nombre_variante}' creada exitosamente.")
            
        except Productos.DoesNotExist:
            messages.error(request, "Producto no encontrado.")
        except Exception as e:
            print(f"ERROR CRÍTICO al crear variante: {str(e)}")
            messages.error(request, f"Error al crear variante: {str(e)}")
        
        return redirect('gestionar_variantes', producto_id=producto_id)
    
    return redirect('Crud_V')

@login_required(login_url='login')
def editar_variante(request):
    """Vista para editar una variante existente - CORREGIDA"""
    if request.method == 'POST':
        try:
            print("=== DEBUG EDITAR VARIANTE ===")
            
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('Crud_V')
            
            # Obtener datos del formulario
            variante_id = request.POST.get('variante_id')
            nombre_variante = request.POST.get('nombre_variante')
            precio_adicional = request.POST.get('precio_adicional', 0)
            stock_variante = request.POST.get('stock_variante', 0)
            estado_variante = request.POST.get('estado_variante', 'activa')
            imagen_variante = request.FILES.get('imagen_variante')
            
            print(f"DEBUG: Variante ID: {variante_id}, Nombre: {nombre_variante}")
            
            if not variante_id or not nombre_variante:
                messages.error(request, "Datos incompletos para editar la variante.")
                return redirect('Crud_V')
            
            # Convertir valores
            try:
                precio_adicional = float(precio_adicional) if precio_adicional else 0.0
                nuevo_stock = int(stock_variante) if stock_variante else 0
            except ValueError:
                messages.error(request, "Precio adicional y stock deben ser números válidos.")
                return redirect('Crud_V')
            
            # Obtener información actual de la variante
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT producto_id, nombre_variante, stock_variante, imagen_variante 
                    FROM variantes_producto 
                    WHERE id_variante = %s
                """, [variante_id])
                
                resultado = cursor.fetchone()
                if not resultado:
                    messages.error(request, "Variante no encontrada.")
                    return redirect('Crud_V')
                
                producto_id, nombre_anterior, stock_anterior, imagen_actual = resultado
                print(f"DEBUG: Producto ID: {producto_id}, Stock anterior: {stock_anterior}")
            
            # Procesar nueva imagen si se subió
            nombre_archivo_imagen = imagen_actual  # Mantener la imagen actual por defecto
            if imagen_variante:
                try:
                    # Eliminar imagen anterior si existe
                    if imagen_actual:
                        try:
                            imagen_path = os.path.join(settings.MEDIA_ROOT, 'variantes', imagen_actual)
                            if os.path.exists(imagen_path):
                                os.remove(imagen_path)
                        except Exception as e:
                            print(f"Error al eliminar imagen anterior: {e}")
                    
                    # Guardar nueva imagen
                    extension = os.path.splitext(imagen_variante.name)[1]
                    nombre_archivo_imagen = f"variante_{variante_id}_{int(timezone.now().timestamp())}{extension}"
                    
                    media_path = os.path.join(settings.MEDIA_ROOT, 'variantes')
                    os.makedirs(media_path, exist_ok=True)
                    
                    with open(os.path.join(media_path, nombre_archivo_imagen), 'wb+') as destination:
                        for chunk in imagen_variante.chunks():
                            destination.write(chunk)
                    print(f"DEBUG: Nueva imagen guardada: {nombre_archivo_imagen}")
                except Exception as e:
                    print(f"ERROR procesando nueva imagen: {e}")
                    messages.warning(request, "La nueva imagen no pudo ser procesada, se mantendrá la imagen actual.")
                    nombre_archivo_imagen = imagen_actual
            
            # Calcular diferencia de stock para registro
            diferencia_stock = nuevo_stock - stock_anterior
            
            # Actualizar la variante
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE variantes_producto 
                    SET nombre_variante = %s, precio_adicional = %s, 
                        stock_variante = %s, estado_variante = %s, imagen_variante = %s
                    WHERE id_variante = %s
                """, [
                    nombre_variante.strip(),
                    precio_adicional,
                    nuevo_stock,
                    estado_variante,
                    nombre_archivo_imagen,
                    variante_id
                ])
                
                # Verificar que se actualizó
                cursor.execute("SELECT COUNT(*) FROM variantes_producto WHERE id_variante = %s", [variante_id])
                if cursor.fetchone()[0] == 0:
                    messages.error(request, "Error: La variante no se pudo actualizar.")
                    return redirect('gestionar_variantes', producto_id=producto_id)
            
            # REGISTRAR MOVIMIENTO DE STOCK SI HAY CAMBIO
            if diferencia_stock != 0:
                try:
                    tipo_movimiento = 'entrada' if diferencia_stock > 0 else 'salida'
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO movimientos_stock 
                            (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                             stock_anterior, stock_nuevo, usuario_id, fecha_movimiento, variante_id, descripcion_variante)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, [
                            producto_id,
                            datos['negocio_activo'].pkid_neg,
                            tipo_movimiento,
                            'ajuste_stock_variante',
                            abs(diferencia_stock),
                            stock_anterior,
                            nuevo_stock,
                            datos['perfil'].id,
                            datetime.now(),
                            variante_id,
                            nombre_variante
                        ])
                    print(f"DEBUG: Movimiento de stock registrado - Diferencia: {diferencia_stock}")
                except Exception as e:
                    print(f"ERROR registrando movimiento: {e}")
            
            messages.success(request, f"✅ Variante '{nombre_variante}' actualizada exitosamente.")
            
        except Exception as e:
            print(f"ERROR CRÍTICO al actualizar variante: {str(e)}")
            messages.error(request, f"Error al actualizar variante: {str(e)}")
        
        # Redirigir de vuelta a la gestión de variantes
        if 'producto_id' in locals():
            return redirect('gestionar_variantes', producto_id=producto_id)
        return redirect('Crud_V')
    
    return redirect('Crud_V')

@login_required(login_url='login')
def eliminar_variante(request, variante_id):
    """Vista para eliminar una variante - CORREGIDA"""
    if request.method == 'POST':
        try:
            print(f"=== DEBUG ELIMINAR VARIANTE: ID {variante_id} ===")
            
            datos = obtener_datos_vendedor(request)
            if not datos:
                messages.error(request, "No tienes un negocio activo.")
                return redirect('Crud_V')
            
            # Obtener información de la variante antes de eliminar
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT producto_id, nombre_variante, imagen_variante, stock_variante 
                    FROM variantes_producto WHERE id_variante = %s
                """, [variante_id])
                resultado = cursor.fetchone()
                
                if resultado:
                    producto_id, nombre_variante, imagen_variante, stock_eliminado = resultado
                    print(f"DEBUG: Eliminando variante '{nombre_variante}', Stock: {stock_eliminado}")
                    
                    # REGISTRAR MOVIMIENTO DE STOCK POR ELIMINACIÓN
                    if stock_eliminado > 0:
                        try:
                            with connection.cursor() as cursor2:
                                cursor2.execute("""
                                    INSERT INTO movimientos_stock 
                                    (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                                     stock_anterior, stock_nuevo, usuario_id, fecha_movimiento, variante_id, descripcion_variante)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, [
                                    producto_id,
                                    datos['negocio_activo'].pkid_neg,
                                    'salida',
                                    'eliminacion_variante',
                                    stock_eliminado,
                                    stock_eliminado,
                                    0,  # Stock nuevo es 0
                                    datos['perfil'].id,
                                    datetime.now(),
                                    variante_id,
                                    nombre_variante
                                ])
                            print("DEBUG: Movimiento de eliminación registrado")
                        except Exception as e:
                            print(f"ERROR registrando movimiento de eliminación: {e}")
                    
                    # Eliminar la imagen del sistema de archivos si existe
                    if imagen_variante:
                        try:
                            imagen_path = os.path.join(settings.MEDIA_ROOT, 'variantes', imagen_variante)
                            if os.path.exists(imagen_path):
                                os.remove(imagen_path)
                                print(f"DEBUG: Imagen eliminada: {imagen_variante}")
                        except Exception as e:
                            print(f"Error al eliminar imagen: {e}")
                    
                    # Eliminar la variante
                    cursor.execute("DELETE FROM variantes_producto WHERE id_variante = %s", [variante_id])
                    
                    # Verificar que se eliminó
                    cursor.execute("SELECT COUNT(*) FROM variantes_producto WHERE id_variante = %s", [variante_id])
                    if cursor.fetchone()[0] == 0:
                        messages.success(request, f"✅ Variante '{nombre_variante}' eliminada exitosamente.")
                    else:
                        messages.error(request, f"❌ Error: No se pudo eliminar la variante '{nombre_variante}'")
                    
                    return redirect('gestionar_variantes', producto_id=producto_id)
                else:
                    messages.error(request, "Variante no encontrada.")
            
        except Exception as e:
            print(f"ERROR al eliminar variante: {str(e)}")
            messages.error(request, f"Error al eliminar variante: {str(e)}")
        
        return redirect('Crud_V')
    
    return redirect('Crud_V')

@login_required(login_url='login')
def ajustar_stock_variante(request, variante_id):
    """Vista para ajustar stock de una variante específica - SIN AJAX"""
    if request.method == 'POST':
        try:
            print("=== DEBUG AJUSTAR STOCK VARIANTE ===")
            
            # Obtener datos del formulario
            tipo_ajuste = request.POST.get('tipo_ajuste', 'entrada')
            cantidad_ajuste = request.POST.get('cantidad_ajuste', 0)
            motivo = request.POST.get('motivo_ajuste', 'ajuste manual')
            
            print(f"DEBUG: Variante ID: {variante_id}, Tipo: {tipo_ajuste}, Cantidad: {cantidad_ajuste}, Motivo: {motivo}")
            
            # Validar cantidad
            if not cantidad_ajuste or int(cantidad_ajuste) <= 0:
                messages.error(request, "❌ La cantidad debe ser mayor a 0.")
                # Obtener producto_id para redirección
                with connection.cursor() as cursor:
                    cursor.execute("SELECT producto_id FROM variantes_producto WHERE id_variante = %s", [variante_id])
                    resultado = cursor.fetchone()
                    if resultado:
                        return redirect('gestionar_variantes', producto_id=resultado[0])
                return redirect('Crud_V')
            
            cantidad_ajuste = int(cantidad_ajuste)
            
            datos = obtener_datos_vendedor(request)
            if not datos or not datos.get('negocio_activo'):
                messages.error(request, "No tienes un negocio activo.")
                return redirect('Crud_V')
            
            # Obtener información actual de la variante
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT producto_id, nombre_variante, stock_variante 
                    FROM variantes_producto 
                    WHERE id_variante = %s
                """, [variante_id])
                
                resultado = cursor.fetchone()
                if not resultado:
                    messages.error(request, "Variante no encontrada.")
                    return redirect('Crud_V')
                
                producto_id, nombre_variante, stock_anterior = resultado
                print(f"DEBUG: Producto ID: {producto_id}, Stock anterior: {stock_anterior}")
                
                # Calcular nuevo stock
                if tipo_ajuste == 'entrada':
                    stock_nuevo = stock_anterior + cantidad_ajuste
                    mensaje_tipo = f"+{cantidad_ajuste}"
                elif tipo_ajuste == 'salida':
                    stock_nuevo = stock_anterior - cantidad_ajuste
                    # Validar stock negativo
                    if stock_nuevo < 0:
                        messages.error(request, f"❌ No puedes tener stock negativo. Stock actual: {stock_anterior}, Cantidad a restar: {cantidad_ajuste}")
                        return redirect('gestionar_variantes', producto_id=producto_id)
                    mensaje_tipo = f"-{cantidad_ajuste}"
                else:  # ajuste manual
                    stock_nuevo = cantidad_ajuste
                    # Validar stock negativo
                    if stock_nuevo < 0:
                        messages.error(request, f"❌ No puedes tener stock negativo. Stock establecido: {cantidad_ajuste}")
                        return redirect('gestionar_variantes', producto_id=producto_id)
                    mensaje_tipo = f"→ {cantidad_ajuste}"
                
                print(f"DEBUG: Stock nuevo calculado: {stock_nuevo}")
                
                # Actualizar stock de la variante
                cursor.execute("""
                    UPDATE variantes_producto 
                    SET stock_variante = %s
                    WHERE id_variante = %s
                """, [stock_nuevo, variante_id])
                
                # Verificar la actualización
                cursor.execute("SELECT stock_variante FROM variantes_producto WHERE id_variante = %s", [variante_id])
                stock_verificado = cursor.fetchone()[0]
                print(f"DEBUG: Stock verificado en BD: {stock_verificado}")
                
                # REGISTRAR MOVIMIENTO DE STOCK
                try:
                    cursor.execute("""
                        INSERT INTO movimientos_stock 
                        (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                         stock_anterior, stock_nuevo, usuario_id, fecha_movimiento, variante_id, descripcion_variante)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        producto_id,
                        datos['negocio_activo'].pkid_neg,
                        tipo_ajuste,
                        motivo,
                        abs(cantidad_ajuste),
                        stock_anterior,
                        stock_nuevo,
                        datos['perfil'].id,
                        datetime.now(),
                        variante_id,
                        nombre_variante
                    ])
                    print("DEBUG: Movimiento de stock registrado exitosamente")
                except Exception as e:
                    print(f"ERROR registrando movimiento: {e}")
                    # No impedimos la actualización del stock si falla el registro del movimiento
            
            messages.success(request, f"✅ Stock de '{nombre_variante}' actualizado: {stock_anterior} {mensaje_tipo} = {stock_nuevo}")
            
            return redirect('gestionar_variantes', producto_id=producto_id)
            
        except Exception as e:
            print(f"ERROR CRÍTICO al ajustar stock: {str(e)}")
            messages.error(request, f"Error al ajustar stock: {str(e)}")
            # Intentar redirigir al producto si es posible
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT producto_id FROM variantes_producto WHERE id_variante = %s", [variante_id])
                    resultado = cursor.fetchone()
                    if resultado:
                        return redirect('gestionar_variantes', producto_id=resultado[0])
            except:
                pass
            return redirect('Crud_V')
    
    # Si no es POST, redirigir
    return redirect('Crud_V')

@login_required(login_url='login')
def obtener_datos_variante(request, variante_id):
    """Vista para obtener datos de una variante específica - SIN AJAX"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            return redirect('Crud_V')
        
        negocio = datos['negocio_activo']
        
        # Obtener información de la variante
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    v.id_variante,
                    v.nombre_variante,
                    v.precio_adicional,
                    v.stock_variante,
                    v.estado_variante,
                    v.sku_variante,
                    v.imagen_variante,
                    v.producto_id,
                    p.nom_prod,
                    p.precio_prod,
                    (p.precio_prod + COALESCE(v.precio_adicional, 0)) as precio_total
                FROM variantes_producto v
                JOIN productos p ON v.producto_id = p.pkid_prod
                WHERE v.id_variante = %s AND p.fknegocioasociado_prod = %s
            """, [variante_id, negocio.pkid_neg])
            
            resultado = cursor.fetchone()
            
            if resultado:
                variante_data = {
                    'id': resultado[0],
                    'nombre': resultado[1],
                    'precio_adicional': float(resultado[2]) if resultado[2] else 0.0,
                    'stock': resultado[3],
                    'estado': resultado[4],
                    'sku': resultado[5],
                    'imagen': resultado[6],
                    'producto_id': resultado[7],
                    'producto_nombre': resultado[8],
                    'precio_base': float(resultado[9]) if resultado[9] else 0.0,
                    'precio_total': float(resultado[10]) if resultado[10] else 0.0
                }
                
                # Redirigir a la gestión de variantes con los datos en la sesión
                request.session['variante_editar_data'] = variante_data
                messages.info(request, f"Cargando datos de la variante: {variante_data['nombre']}")
                return redirect('gestionar_variantes', producto_id=variante_data['producto_id'])
            else:
                messages.error(request, "Variante no encontrada.")
                return redirect('Crud_V')
                
    except Exception as e:
        print(f"ERROR al obtener datos de variante: {str(e)}")
        messages.error(request, f"Error al cargar datos: {str(e)}")
        return redirect('Crud_V')

@login_required(login_url='login')
def cargar_editar_variante(request, variante_id):
    """Vista para cargar el modal de edición con datos reales"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('Crud_V')
        
        negocio = datos['negocio_activo']
        
        # Obtener información completa de la variante
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    v.id_variante,
                    v.nombre_variante,
                    v.precio_adicional,
                    v.stock_variante,
                    v.estado_variante,
                    v.sku_variante,
                    v.imagen_variante,
                    v.producto_id,
                    p.nom_prod,
                    p.precio_prod,
                    (p.precio_prod + COALESCE(v.precio_adicional, 0)) as precio_total
                FROM variantes_producto v
                JOIN productos p ON v.producto_id = p.pkid_prod
                WHERE v.id_variante = %s AND p.fknegocioasociado_prod = %s
            """, [variante_id, negocio.pkid_neg])
            
            resultado = cursor.fetchone()
            
            if resultado:
                variante_data = {
                    'id': resultado[0],
                    'nombre': resultado[1],
                    'precio_adicional': float(resultado[2]) if resultado[2] else 0.0,
                    'stock': resultado[3],
                    'estado': resultado[4],
                    'sku': resultado[5],
                    'imagen': resultado[6],
                    'producto_id': resultado[7],
                    'producto_nombre': resultado[8],
                    'precio_base': float(resultado[9]) if resultado[9] else 0.0,
                    'precio_total': float(resultado[10]) if resultado[10] else 0.0
                }
                
                # Guardar en sesión y redirigir
                request.session['variante_editar_data'] = variante_data
                messages.info(request, f"Editando variante: {variante_data['nombre']}")
                return redirect('gestionar_variantes', producto_id=variante_data['producto_id'])
            else:
                messages.error(request, "Variante no encontrada.")
                return redirect('Crud_V')
                
    except Exception as e:
        print(f"ERROR al cargar datos de variante: {str(e)}")
        messages.error(request, f"Error al cargar datos: {str(e)}")
        return redirect('Crud_V')
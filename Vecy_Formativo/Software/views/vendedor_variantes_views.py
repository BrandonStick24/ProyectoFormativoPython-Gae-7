# Software/vendedor_variantes_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import connection
from datetime import datetime
import os
from django.conf import settings

# Importar modelos
from Software.models import (
    Negocios, UsuarioPerfil, AuthUser, Productos
)

def obtener_datos_vendedor_variantes(request):
    """Función específica para variantes que valida que exista un negocio activo"""
    try:
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        nombre_usuario = request.user.first_name or request.user.username
        
        negocio_seleccionado_id = request.session.get('negocio_seleccionado_id')
        negocio_seleccionado = None
        
        if negocio_seleccionado_id:
            try:
                negocio_seleccionado = Negocios.objects.get(
                    pkid_neg=negocio_seleccionado_id, 
                    fkpropietario_neg=perfil,
                    estado_neg='activo'
                )
            except Negocios.DoesNotExist:
                del request.session['negocio_seleccionado_id']
                messages.error(request, "El negocio seleccionado no existe o está inactivo.")
                return None
        
        if not negocio_seleccionado:
            negocio_seleccionado = Negocios.objects.filter(
                fkpropietario_neg=perfil, 
                estado_neg='activo'
            ).first()
            
            if negocio_seleccionado:
                request.session['negocio_seleccionado_id'] = negocio_seleccionado.pkid_neg
            else:
                messages.error(request, "No tienes negocios activos. Registra un negocio primero.")
                return None
        
        return {
            'nombre_usuario': nombre_usuario,
            'perfil': perfil,
            'negocio_activo': negocio_seleccionado,
        }
    except (AuthUser.DoesNotExist, UsuarioPerfil.DoesNotExist):
        messages.error(request, "Error al cargar datos del usuario.")
        return None

# Función para registrar movimientos de stock de variantes
def registrar_movimiento_variante(variante_id, negocio_id, usuario_id, tipo_movimiento, motivo, cantidad, stock_anterior, stock_nuevo):
    """Función para registrar movimientos de stock específicos para variantes"""
    try:
        with connection.cursor() as cursor:
            # Obtener información de la variante y producto
            cursor.execute("""
                SELECT producto_id, nombre_variante 
                FROM variantes_producto 
                WHERE id_variante = %s
            """, [variante_id])
            resultado = cursor.fetchone()
            
            if resultado:
                producto_id, nombre_variante = resultado
                
                # Registrar movimiento con variante_id
                cursor.execute("""
                    INSERT INTO movimientos_stock 
                    (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                     stock_anterior, stock_nuevo, usuario_id, fecha_movimiento, variante_id, descripcion_variante)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    producto_id,
                    negocio_id,
                    tipo_movimiento,
                    motivo,
                    cantidad,
                    stock_anterior,
                    stock_nuevo,
                    usuario_id,
                    datetime.now(),
                    variante_id,
                    nombre_variante
                ])
                return True
        return False
    except Exception as e:
        print(f"Error registrando movimiento de variante: {e}")
        return False

@login_required(login_url='login')
def gestionar_variantes(request, producto_id):
    """Vista principal para gestionar variantes de un producto"""
    datos = obtener_datos_vendedor_variantes(request)
    if not datos:
        return redirect('Crud_V')
    
    negocio = datos['negocio_activo']
    
    try:
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
                    (p.precio_prod + v.precio_adicional) as precio_total
                FROM variantes_producto v
                JOIN productos p ON v.producto_id = p.pkid_prod
                WHERE v.producto_id = %s
                ORDER BY v.nombre_variante
            """, [producto_id])
            
            for row in cursor.fetchall():
                variantes.append({
                    'id': row[0],
                    'nombre': row[1],
                    'precio_adicional': float(row[2]),
                    'stock': row[3],
                    'estado': row[4],
                    'sku': row[5],
                    'imagen': row[6],
                    'fecha_creacion': row[7].strftime('%d/%m/%Y %H:%M') if row[7] else '',
                    'precio_total': float(row[8])
                })
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': datos['negocio_activo'],
            'producto': producto,
            'variantes': variantes,
        }
        
        return render(request, 'Vendedor/gestion_variantes.html', contexto)
        
    except Productos.DoesNotExist:
        messages.error(request, "Producto no encontrado o no tienes permisos.")
        return redirect('Crud_V')
    except Exception as e:
        messages.error(request, f"Error al cargar variantes: {str(e)}")
        return redirect('Crud_V')

@login_required(login_url='login')
def crear_variante(request, producto_id):
    """Vista para crear una nueva variante - CON REGISTRO DE MOVIMIENTO DE STOCK"""
    if request.method == 'POST':
        try:
            datos = obtener_datos_vendedor_variantes(request)
            if not datos:
                messages.error(request, "No tienes un negocio activo.")
                return redirect('Crud_V')
            
            negocio = datos['negocio_activo']
            
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
            
            # Validaciones
            if not nombre_variante:
                messages.error(request, "El nombre de la variante es obligatorio.")
                return redirect('gestionar_variantes', producto_id=producto_id)
            
            # Convertir stock a entero
            stock_inicial = int(stock_variante) if stock_variante else 0
            
            # Procesar imagen si se subió
            nombre_archivo_imagen = None
            if imagen_variante:
                # Generar nombre único para la imagen
                extension = imagen_variante.name.split('.')[-1]
                nombre_archivo_imagen = f"variante_{producto_id}_{int(timezone.now().timestamp())}.{extension}"
                
                # Guardar la imagen en la carpeta media/variantes/
                media_path = os.path.join(settings.MEDIA_ROOT, 'variantes')
                os.makedirs(media_path, exist_ok=True)
                
                with open(os.path.join(media_path, nombre_archivo_imagen), 'wb+') as destination:
                    for chunk in imagen_variante.chunks():
                        destination.write(chunk)
            
            # Generar SKU único automáticamente para evitar duplicados
            sku_unico = f"VAR-{producto_id}-{int(timezone.now().timestamp())}"
            
            # Crear la variante
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO variantes_producto 
                    (producto_id, nombre_variante, precio_adicional, stock_variante, sku_variante, imagen_variante)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [
                    producto_id,
                    nombre_variante,
                    precio_adicional,
                    stock_inicial,  # Usar stock convertido
                    sku_unico,
                    nombre_archivo_imagen
                ])
                
                # Obtener el ID de la variante recién creada
                variante_id = cursor.lastrowid
            
            # REGISTRAR MOVIMIENTO DE STOCK POR CREACIÓN DE VARIANTE
            if stock_inicial > 0:
                registrar_movimiento_variante(
                    variante_id=variante_id,
                    negocio_id=negocio.pkid_neg,
                    usuario_id=datos['perfil'].id,
                    tipo_movimiento='entrada',
                    motivo='creacion_variante',
                    cantidad=stock_inicial,
                    stock_anterior=0,  # Stock anterior era 0 (variante nueva)
                    stock_nuevo=stock_inicial
                )
            
            messages.success(request, f"Variante '{nombre_variante}' creada exitosamente.")
            
        except Productos.DoesNotExist:
            messages.error(request, "Producto no encontrado.")
        except Exception as e:
            messages.error(request, f"Error al crear variante: {str(e)}")
        
        return redirect('gestionar_variantes', producto_id=producto_id)
    
    return redirect('Crud_V')

@login_required(login_url='login')
def editar_variante(request, variante_id):
    """Vista para editar una variante existente - CON REGISTRO DE MOVIMIENTOS DE STOCK"""
    if request.method == 'POST':
        try:
            datos = obtener_datos_vendedor_variantes(request)
            if not datos:
                messages.error(request, "No tienes un negocio activo.")
                return redirect('Crud_V')
            
            # Obtener datos del formulario
            nombre_variante = request.POST.get('nombre_variante')
            precio_adicional = request.POST.get('precio_adicional', 0)
            stock_variante = request.POST.get('stock_variante', 0)
            estado_variante = request.POST.get('estado_variante', 'activa')
            imagen_variante = request.FILES.get('imagen_variante')
            
            # Convertir stock a entero
            nuevo_stock = int(stock_variante) if stock_variante else 0
            
            # Obtener stock actual antes de la actualización
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT stock_variante, producto_id 
                    FROM variantes_producto 
                    WHERE id_variante = %s
                """, [variante_id])
                resultado = cursor.fetchone()
                
                if not resultado:
                    messages.error(request, "Variante no encontrada.")
                    return redirect('Crud_V')
                
                stock_anterior, producto_id = resultado
            
            # Calcular diferencia de stock
            diferencia_stock = nuevo_stock - stock_anterior
            
            # Procesar nueva imagen si se subió
            nombre_archivo_imagen = None
            if imagen_variante:
                # Generar nombre único para la imagen
                extension = imagen_variante.name.split('.')[-1]
                nombre_archivo_imagen = f"variante_{variante_id}_{int(timezone.now().timestamp())}.{extension}"
                
                # Guardar la imagen en la carpeta media/variantes/
                media_path = os.path.join(settings.MEDIA_ROOT, 'variantes')
                os.makedirs(media_path, exist_ok=True)
                
                with open(os.path.join(media_path, nombre_archivo_imagen), 'wb+') as destination:
                    for chunk in imagen_variante.chunks():
                        destination.write(chunk)
            
            # Actualizar la variante
            with connection.cursor() as cursor:
                if nombre_archivo_imagen:
                    # Si hay nueva imagen, actualizar también la imagen
                    cursor.execute("""
                        UPDATE variantes_producto 
                        SET nombre_variante = %s, precio_adicional = %s, 
                            stock_variante = %s, estado_variante = %s, imagen_variante = %s
                        WHERE id_variante = %s
                    """, [
                        nombre_variante,
                        precio_adicional,
                        nuevo_stock,
                        estado_variante,
                        nombre_archivo_imagen,
                        variante_id
                    ])
                else:
                    # Si no hay nueva imagen, mantener la imagen existente
                    cursor.execute("""
                        UPDATE variantes_producto 
                        SET nombre_variante = %s, precio_adicional = %s, 
                            stock_variante = %s, estado_variante = %s
                        WHERE id_variante = %s
                    """, [
                        nombre_variante,
                        precio_adicional,
                        nuevo_stock,
                        estado_variante,
                        variante_id
                    ])
            
            # REGISTRAR MOVIMIENTO DE STOCK SI HAY CAMBIO
            if diferencia_stock != 0:
                tipo_movimiento = 'entrada' if diferencia_stock > 0 else 'salida'
                motivo = 'ajuste_stock_variante'
                
                registrar_movimiento_variante(
                    variante_id=variante_id,
                    negocio_id=datos['negocio_activo'].pkid_neg,
                    usuario_id=datos['perfil'].id,
                    tipo_movimiento=tipo_movimiento,
                    motivo=motivo,
                    cantidad=abs(diferencia_stock),
                    stock_anterior=stock_anterior,
                    stock_nuevo=nuevo_stock
                )
            
            messages.success(request, f"Variante '{nombre_variante}' actualizada exitosamente.")
            
        except Exception as e:
            messages.error(request, f"Error al actualizar variante: {str(e)}")
        
        # Redirigir de vuelta a la gestión de variantes
        with connection.cursor() as cursor:
            cursor.execute("SELECT producto_id FROM variantes_producto WHERE id_variante = %s", [variante_id])
            resultado = cursor.fetchone()
            if resultado:
                return redirect('gestionar_variantes', producto_id=resultado[0])
        
        return redirect('Crud_V')
    
    return redirect('Crud_V')

@login_required(login_url='login')
def eliminar_variante(request, variante_id):
    """Vista para eliminar una variante - CON REGISTRO DE MOVIMIENTO DE STOCK"""
    if request.method == 'POST':
        try:
            datos = obtener_datos_vendedor_variantes(request)
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
                    
                    # REGISTRAR MOVIMIENTO DE STOCK POR ELIMINACIÓN DE VARIANTE
                    if stock_eliminado > 0:
                        registrar_movimiento_variante(
                            variante_id=variante_id,
                            negocio_id=datos['negocio_activo'].pkid_neg,
                            usuario_id=datos['perfil'].id,
                            tipo_movimiento='salida',
                            motivo='eliminacion_variante',
                            cantidad=stock_eliminado,
                            stock_anterior=stock_eliminado,
                            stock_nuevo=0
                        )
                    
                    # Eliminar la imagen del sistema de archivos si existe
                    if imagen_variante:
                        try:
                            imagen_path = os.path.join(settings.MEDIA_ROOT, 'variantes', imagen_variante)
                            if os.path.exists(imagen_path):
                                os.remove(imagen_path)
                        except Exception as e:
                            print(f"Error al eliminar imagen: {e}")
                    
                    # Eliminar la variante
                    cursor.execute("DELETE FROM variantes_producto WHERE id_variante = %s", [variante_id])
                    
                    messages.success(request, f"Variante '{nombre_variante}' eliminada exitosamente.")
                    return redirect('gestionar_variantes', producto_id=producto_id)
                else:
                    messages.error(request, "Variante no encontrada.")
            
        except Exception as e:
            messages.error(request, f"Error al eliminar variante: {str(e)}")
        
        return redirect('Crud_V')
    
    return redirect('Crud_V')

@login_required(login_url='login')
def ajustar_stock_variante(request, variante_id):
    """Vista para ajustar stock de una variante específica - CON REGISTRO DE MOVIMIENTO"""
    if request.method == 'POST':
        try:
            tipo_ajuste = request.POST.get('tipo_ajuste', 'entrada')
            cantidad_ajuste = int(request.POST.get('cantidad_ajuste', 0))
            motivo = request.POST.get('motivo_ajuste', 'ajuste manual')
            
            datos = obtener_datos_vendedor_variantes(request)
            if not datos:
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
                
                # Calcular nuevo stock
                if tipo_ajuste == 'entrada':
                    stock_nuevo = stock_anterior + cantidad_ajuste
                elif tipo_ajuste == 'salida':
                    stock_nuevo = stock_anterior - cantidad_ajuste
                else:  # ajuste manual
                    stock_nuevo = cantidad_ajuste
                
                # Validar stock negativo
                if stock_nuevo < 0:
                    messages.error(request, f"❌ No puedes tener stock negativo. Stock actual: {stock_anterior}")
                    return redirect('gestionar_variantes', producto_id=producto_id)
                
                # Actualizar stock de la variante
                cursor.execute("""
                    UPDATE variantes_producto 
                    SET stock_variante = %s
                    WHERE id_variante = %s
                """, [stock_nuevo, variante_id])
                
                # REGISTRAR MOVIMIENTO DE STOCK
                registrar_movimiento_variante(
                    variante_id=variante_id,
                    negocio_id=datos['negocio_activo'].pkid_neg,
                    usuario_id=datos['perfil'].id,
                    tipo_movimiento=tipo_ajuste,
                    motivo=motivo,
                    cantidad=abs(cantidad_ajuste),
                    stock_anterior=stock_anterior,
                    stock_nuevo=stock_nuevo
                )
            
            messages.success(request, f"✅ Stock de '{nombre_variante}' actualizado: {stock_anterior} → {stock_nuevo}")
            
        except Exception as e:
            messages.error(request, f"Error al ajustar stock: {str(e)}")
        
        return redirect('gestionar_variantes', producto_id=producto_id)
    
    return redirect('Crud_V')
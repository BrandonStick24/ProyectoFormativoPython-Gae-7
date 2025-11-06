# Software/vendedor_views.py
from django.shortcuts import render, redirect, get_object_or_404  # <- AÑADE get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .views import obtener_datos_vendedor
from Software.models import Negocios, TipoNegocio, UsuarioPerfil, AuthUser
from django.db import connection
from datetime import datetime
import os
from django.conf import settings

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
                'respuesta': row[6] or '',  # Ahora sí viene de BD
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

# PEDIDOS DEL VENDEDOR

@login_required(login_url='login')
def gestionar_ventas(request):
    """Vista sencilla para gestionar pedidos/ventas del vendedor"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('inicio')
        
        negocio = datos['negocio_activo']
        
        # Consulta simple para obtener los pedidos del negocio
        with connection.cursor() as cursor:
            sql = """
            SELECT 
                p.pkid_pedido,
                p.estado_pedido,
                p.total_pedido,
                p.fecha_pedido,
                u.first_name,
                u.username,
                COUNT(d.pkid_detalle) as cantidad_productos
            FROM pedidos p
            JOIN usuario_perfil up ON p.fkusuario_pedido = up.id
            JOIN auth_user u ON up.fkuser_id = u.id
            LEFT JOIN detalles_pedido d ON p.pkid_pedido = d.fkpedido_detalle
            WHERE p.fknegocio_pedido = %s
            GROUP BY p.pkid_pedido, p.estado_pedido, p.total_pedido, p.fecha_pedido, u.first_name, u.username
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
                'cantidad_productos': row[6]
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
def detalle_pedido(request, pedido_id):
    """Vista para ver detalles de un pedido específico"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos or not datos.get('negocio_activo'):
            messages.error(request, "No tienes un negocio activo.")
            return redirect('inicio')
        
        negocio = datos['negocio_activo']
        
        # Verificar que el pedido pertenece al negocio del vendedor
        with connection.cursor() as cursor:
            # Obtener información básica del pedido
            cursor.execute("""
                SELECT p.estado_pedido, p.total_pedido, p.fecha_pedido,
                       u.first_name, u.username
                FROM pedidos p
                JOIN usuario_perfil up ON p.fkusuario_pedido = up.id
                JOIN auth_user u ON up.fkuser_id = u.id
                WHERE p.pkid_pedido = %s AND p.fknegocio_pedido = %s
            """, [pedido_id, negocio.pkid_neg])
            
            pedido_info = cursor.fetchone()
            
            if not pedido_info:
                messages.error(request, "Pedido no encontrado")
                return redirect('gestionar_ventas')
            
            # Obtener detalles del pedido (productos)
            cursor.execute("""
                SELECT d.cantidad_detalle, d.precio_unitario,
                       pr.nom_prod, pr.desc_prod
                FROM detalles_pedido d
                JOIN productos pr ON d.fkproducto_detalle = pr.pkid_prod
                WHERE d.fkpedido_detalle = %s
            """, [pedido_id])
            
            detalles = cursor.fetchall()
        
        # Procesar información del pedido
        pedido = {
            'id': pedido_id,
            'estado': pedido_info[0],
            'total': pedido_info[1],
            'fecha': pedido_info[2].strftime('%d/%m/%Y %H:%M'),
            'cliente': pedido_info[3] or pedido_info[4] or f"Usuario {pedido_id}",
        }
        
        # Procesar detalles
        productos = []
        for detalle in detalles:
            productos.append({
                'cantidad': detalle[0],
                'precio_unitario': detalle[1],
                'nombre': detalle[2],
                'descripcion': detalle[3],
                'subtotal': detalle[0] * detalle[1]
            })
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': negocio,
            'pedido': pedido,
            'productos': productos,
        }
        
        return render(request, 'Vendedor/detalle_pedido.html', contexto)
        
    except Exception as e:
        print(f"ERROR al cargar detalle: {str(e)}")
        messages.error(request, "Error al cargar el detalle del pedido")
        return redirect('gestionar_ventas')

@login_required(login_url='login')
def cambiar_estado_pedido(request, pedido_id):
    """Vista para cambiar estado del pedido con manejo automático de stock"""
    if request.method == 'POST':
        try:
            nuevo_estado = request.POST.get('nuevo_estado')
            
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
                
                # 3. MANEJO AUTOMÁTICO DE STOCK - DESCONTAR cuando se CONFIRMA
                if nuevo_estado == 'confirmado' and estado_actual != 'confirmado':
                    # Descontar stock cuando se confirma el pedido
                    cursor.execute("""
                        UPDATE productos p
                        JOIN detalles_pedido dp ON p.pkid_prod = dp.fkproducto_detalle
                        SET p.stock_prod = p.stock_prod - dp.cantidad_detalle
                        WHERE dp.fkpedido_detalle = %s 
                        AND p.fknegocioasociado_prod = %s
                    """, [pedido_id, negocio.pkid_neg])
                    
                    # Actualizar estado a "agotado" si stock llega a 0
                    cursor.execute("""
                        UPDATE productos 
                        SET estado_prod = 'agotado' 
                        WHERE fknegocioasociado_prod = %s 
                        AND stock_prod <= 0
                        AND estado_prod != 'agotado'
                    """, [negocio.pkid_neg])
                    
                    messages.success(request, f"✅ Pedido confirmado y stock actualizado")
                
                # 4. DEVOLVER STOCK si se cancela un pedido confirmado
                elif nuevo_estado == 'cancelado' and estado_actual == 'confirmado':
                    cursor.execute("""
                        UPDATE productos p
                        JOIN detalles_pedido dp ON p.pkid_prod = dp.fkproducto_detalle
                        SET p.stock_prod = p.stock_prod + dp.cantidad_detalle,
                            p.estado_prod = 'disponible'
                        WHERE dp.fkpedido_detalle = %s 
                        AND p.fknegocioasociado_prod = %s
                    """, [pedido_id, negocio.pkid_neg])
                    messages.success(request, f"✅ Pedido cancelado y stock reabastecido")
                
                else:
                    messages.success(request, f"✅ Pedido actualizado a: {nuevo_estado}")
            
        except Exception as e:
            print(f"ERROR al cambiar estado: {str(e)}")
            messages.error(request, f"Error al cambiar el estado del pedido: {str(e)}")
    
    return redirect('gestionar_ventas')

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
                
                stock_actual, nombre_producto = resultado
                
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
                
                messages.success(request, f"✅ Stock de '{nombre_producto}' actualizado: {stock_actual} → {nuevo_stock}")
                
        except Exception as e:
            print(f"ERROR al ajustar stock: {str(e)}")
            messages.error(request, f"Error al ajustar stock: {str(e)}")
    
    return redirect('Crud_V')

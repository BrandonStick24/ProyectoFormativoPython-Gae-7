from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import connection
from datetime import datetime
import logging

# Importar modelos
from Software.models import (
    Negocios, UsuarioPerfil, AuthUser, 
    Productos
)

# Configurar logger
logger = logging.getLogger(__name__)

# Función auxiliar para obtener datos del vendedor
def obtener_datos_vendedor_ofertas(request):
    """Función específica para ofertas que valida que exista un negocio activo"""
    try:
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
        
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
            'nombre_usuario': auth_user.first_name,
            'perfil': perfil,
            'negocio_activo': negocio_seleccionado,
        }
    except (AuthUser.DoesNotExist, UsuarioPerfil.DoesNotExist):
        messages.error(request, "Error al cargar datos del usuario.")
        return None

@login_required(login_url='login')
def Ofertas_V(request):
    """Vista principal para gestión de ofertas - SIN DATOS DE PRUEBA"""
    # Primero validamos que tenga un negocio activo
    datos = obtener_datos_vendedor_ofertas(request)
    if not datos:
        return redirect('Negocios_V')  # Redirigir a negocios si no tiene uno activo
    
    negocio = datos['negocio_activo']
    
    # Si es GET, solo mostramos el template con los datos actuales
    if request.method == 'GET':
        try:
            # Obtener productos del negocio usando SQL directo - LISTA VACÍA SI NO HAY
            productos_list = []
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        p.pkid_prod,
                        p.nom_prod,
                        p.precio_prod,
                        p.stock_prod,
                        c.desc_cp as categoria
                    FROM productos p
                    JOIN categoria_productos c ON p.fkcategoria_prod = c.pkid_cp
                    WHERE p.fknegocioasociado_prod = %s 
                    AND p.estado_prod = 'disponible'
                    AND p.stock_prod > 0
                    ORDER BY p.nom_prod
                """, [negocio.pkid_neg])
                productos_db = cursor.fetchall()
            
            # Procesar productos para template - SOLO SI HAY DATOS REALES
            for producto in productos_db:
                productos_list.append({
                    'id': producto[0],
                    'nombre': producto[1],
                    'precio': float(producto[2]),
                    'stock': producto[3],
                    'categoria': producto[4]
                })
            
            # Obtener ofertas activas usando SQL directo - LISTA VACÍA SI NO HAY
            ofertas_list = []
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        pr.pkid_promo,
                        p.nom_prod,
                        pr.porcentaje_descuento,
                        p.precio_prod as precio_original,
                        (p.precio_prod * (1 - pr.porcentaje_descuento / 100)) as precio_oferta,
                        pr.fecha_inicio,
                        pr.fecha_fin,
                        pr.estado_promo,
                        pr.titulo_promo,
                        COALESCE(pr.stock_oferta, 0) as stock_oferta,
                        p.stock_prod
                    FROM promociones pr
                    JOIN productos p ON pr.fkproducto_id = p.pkid_prod
                    WHERE pr.fknegocio_id = %s 
                    AND pr.estado_promo = 'activa'
                    ORDER BY pr.fecha_inicio DESC
                """, [negocio.pkid_neg])
                ofertas_db = cursor.fetchall()
            
            # Procesar ofertas para template - SOLO SI HAY DATOS REALES
            for oferta in ofertas_db:
                ofertas_list.append({
                    'id': oferta[0],
                    'producto_nombre': oferta[1],
                    'descuento': float(oferta[2]),
                    'precio_original': float(oferta[3]),
                    'precio_oferta': float(oferta[4]),
                    'fecha_inicio': oferta[5].strftime('%d/%m/%Y') if oferta[5] else '',
                    'fecha_fin': oferta[6].strftime('%d/%m/%Y') if oferta[6] else '',
                    'estado': oferta[7],
                    'titulo': oferta[8],
                    'stock_oferta': oferta[9],
                    'stock_disponible': oferta[10]
                })
            
            # Calcular fechas para el template
            today = timezone.now().date()
            tomorrow = today + timezone.timedelta(days=1)
            
            contexto = {
                'nombre': datos['nombre_usuario'],
                'perfil': datos['perfil'],
                'negocio_activo': datos['negocio_activo'],
                'productos': productos_list,  # Lista vacía si no hay productos
                'ofertas_activas': ofertas_list,  # Lista vacía si no hay ofertas
                'today': today.strftime('%Y-%m-%d'),
                'tomorrow': tomorrow.strftime('%Y-%m-%d')
            }
            
            return render(request, 'Vendedor/Ofertas_V.html', contexto)
            
        except Exception as e:
            # EN CASO DE ERROR, MOSTRAR LISTAS VACÍAS - SIN DATOS DE PRUEBA
            logger.error(f"Error en GET Ofertas_V: {str(e)}")
            today = timezone.now().date()
            tomorrow = today + timezone.timedelta(days=1)
            
            contexto = {
                'nombre': datos['nombre_usuario'],
                'perfil': datos['perfil'],
                'negocio_activo': datos['negocio_activo'],
                'productos': [],  # LISTA VACÍA EN CASO DE ERROR
                'ofertas_activas': [],  # LISTA VACÍA EN CASO DE ERROR
                'today': today.strftime('%Y-%m-%d'),
                'tomorrow': tomorrow.strftime('%Y-%m-%d')
            }
            return render(request, 'Vendedor/Ofertas_V.html', contexto)
    
    # Si es POST, procesamos el formulario
    elif request.method == 'POST':
        logger.info("Formulario de oferta recibido")
        
        producto_id = request.POST.get('producto_id')
        porcentaje_descuento = request.POST.get('porcentaje_descuento')
        stock_oferta = request.POST.get('stock_oferta')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        
        # Validaciones básicas
        if not producto_id or not porcentaje_descuento or not stock_oferta or not fecha_fin:
            messages.error(request, 'Todos los campos obligatorios deben ser llenados.')
            return redirect('Ofertas_V')
        
        try:
            producto_id = int(producto_id)
            porcentaje_descuento = float(porcentaje_descuento)
            stock_oferta = int(stock_oferta)
            
            if porcentaje_descuento <= 0 or porcentaje_descuento > 100:
                messages.error(request, 'El descuento debe estar entre 1% y 100%.')
                return redirect('Ofertas_V')
            
            if stock_oferta <= 0:
                messages.error(request, 'El stock de oferta debe ser mayor a 0.')
                return redirect('Ofertas_V')
            
            # Validar que el producto pertenezca al negocio usando SQL
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pkid_prod, nom_prod, precio_prod, stock_prod 
                    FROM productos 
                    WHERE pkid_prod = %s AND fknegocioasociado_prod = %s
                """, [producto_id, negocio.pkid_neg])
                producto_db = cursor.fetchone()
            
            if not producto_db:
                messages.error(request, 'Producto no encontrado o no pertenece a tu negocio.')
                return redirect('Ofertas_V')
            
            producto_nombre = producto_db[1]
            stock_disponible = producto_db[3]
            
            # Validar stock
            if stock_oferta > stock_disponible:
                messages.error(request, f'Stock insuficiente para {producto_nombre}. Disponible: {stock_disponible}')
                return redirect('Ofertas_V')
            
            # Verificar si ya existe una oferta activa para este producto
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM promociones 
                    WHERE fkproducto_id = %s AND estado_promo = 'activa'
                """, [producto_id])
                oferta_existente = cursor.fetchone()[0] > 0
            
            if oferta_existente:
                messages.error(request, f'Ya existe una oferta activa para {producto_nombre}.')
                return redirect('Ofertas_V')
            
            # Procesar fechas
            today = timezone.now().date()
            fecha_inicio_obj = today  # Por defecto hoy
            if fecha_inicio:
                try:
                    fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                    if fecha_inicio_obj < today:
                        messages.error(request, 'La fecha de inicio no puede ser en el pasado.')
                        return redirect('Ofertas_V')
                except ValueError:
                    messages.error(request, 'Formato de fecha inicio incorrecto.')
                    return redirect('Ofertas_V')
            
            try:
                fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                if fecha_fin_obj <= fecha_inicio_obj:
                    messages.error(request, 'La fecha de fin debe ser posterior a la fecha de inicio.')
                    return redirect('Ofertas_V')
            except ValueError:
                messages.error(request, 'Formato de fecha fin incorrecto.')
                return redirect('Ofertas_V')
            
            # Calcular precio con oferta
            precio_original = float(producto_db[2])
            precio_oferta = precio_original * (1 - porcentaje_descuento / 100)
            
            # Crear título automático
            titulo = f"Oferta {producto_nombre} - {porcentaje_descuento:.0f}% OFF"
            descripcion = f"Oferta especial de {producto_nombre}. Precio regular: ${precio_original:.0f}"
            
            # Crear la oferta usando SQL directo
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO promociones 
                    (fknegocio_id, fkproducto_id, titulo_promo, descripcion_promo, 
                     porcentaje_descuento, fecha_inicio, fecha_fin, estado_promo, stock_oferta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    negocio.pkid_neg,
                    producto_id,
                    titulo,
                    descripcion,
                    porcentaje_descuento,
                    fecha_inicio_obj,
                    fecha_fin_obj,
                    'activa',
                    stock_oferta
                ])
            
            messages.success(request, f'✅ Oferta creada exitosamente para {producto_nombre}')
            logger.info(f"Oferta creada para {producto_nombre}")
            return redirect('Ofertas_V')
            
        except ValueError as e:
            messages.error(request, f'Error en los datos numéricos: {str(e)}')
            logger.error(f"Error de valor: {str(e)}")
        except Exception as e:
            messages.error(request, f'Error al crear oferta: {str(e)}')
            logger.error(f"Error general: {str(e)}")
        
        return redirect('Ofertas_V')

@login_required(login_url='login')
def eliminar_oferta(request, oferta_id):
    """ELIMINAR una oferta usando SQL directo"""
    try:
        datos = obtener_datos_vendedor_ofertas(request)
        if not datos:
            messages.error(request, "No tienes un negocio activo.")
            return redirect('Ofertas_V')
        
        negocio = datos['negocio_activo']
        
        # Validar que la oferta pertenezca al negocio usando SQL
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM promociones 
                WHERE pkid_promo = %s AND fknegocio_id = %s
            """, [oferta_id, negocio.pkid_neg])
            oferta_valida = cursor.fetchone()[0] > 0
        
        if not oferta_valida:
            messages.error(request, 'Oferta no encontrada')
            return redirect('Ofertas_V')
        
        # ELIMINAR la oferta completamente de la base de datos
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM promociones 
                WHERE pkid_promo = %s
            """, [oferta_id])
        
        messages.success(request, '✅ Oferta eliminada exitosamente')
        
    except Exception as e:
        messages.error(request, f'Error al eliminar oferta: {str(e)}')
        logger.error(f"Error al eliminar oferta: {str(e)}")
    
    return redirect('Ofertas_V')
#software/views/vendedor_ofertas_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import connection
from datetime import datetime, date, time
import logging

# Importar modelos necesarios
from Software.models import (
    Negocios, UsuarioPerfil, 
    Productos, CategoriaProductos
)

# Configurar logger
logger = logging.getLogger(__name__)

# Función auxiliar para obtener datos del vendedor
def obtener_datos_vendedor_ofertas(request):
    """Función específica para ofertas que valida que exista un negocio activo"""
    try:
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        
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
            'nombre_usuario': request.user.first_name,
            'perfil': perfil,
            'negocio_activo': negocio_seleccionado,
        }
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, "Error al cargar datos del usuario.")
        return None

def actualizar_estado_ofertas_automatico(negocio_id):
    """Función MEJORADA para actualizar automáticamente el estado de las ofertas con manejo de horas"""
    try:
        with connection.cursor() as cursor:
            ahora = timezone.now()
            hoy = date.today()

            # 1. ✅ IDENTIFICAR OFERTAS QUE EXPIRARON Y REINTEGRAR STOCK
            cursor.execute("""
                SELECT pkid_promo, fkproducto_id, variante_id, stock_actual_oferta, tipo_oferta
                FROM promociones 
                WHERE fknegocio_id = %s 
                AND estado_promo = 'activa'
                AND tipo_oferta = 'stock'
                AND stock_actual_oferta > 0
                AND fecha_fin < %s
            """, [negocio_id, ahora])
            
            ofertas_expiradas = cursor.fetchall()
            
            for oferta in ofertas_expiradas:
                oferta_id, producto_id, variante_id, stock_restante, tipo_oferta = oferta
                
                # REINTEGRAR STOCK SOBRANTE
                if stock_restante > 0:
                    if variante_id:
                        cursor.execute("""
                            UPDATE variantes_producto 
                            SET stock_variante = stock_variante + %s
                            WHERE id_variante = %s
                        """, [stock_restante, variante_id])
                    else:
                        cursor.execute("""
                            UPDATE productos 
                            SET stock_prod = stock_prod + %s
                            WHERE pkid_prod = %s
                        """, [stock_restante, producto_id])
                    
                    # Registrar movimiento de reintegración
                    registrar_movimiento_oferta(
                        producto_id, negocio_id, None, stock_restante,
                        'devolucion_automatica_oferta',
                        f"Devolución automática oferta expirada ID: {oferta_id}",
                        variante_id
                    )
            
            # 2. ACTUALIZAR ESTADO DE OFERTAS EXPIRADAS
            cursor.execute("""
                UPDATE promociones 
                SET estado_promo = 'finalizada',
                    activa_por_stock = 0,
                    stock_actual_oferta = 0  # ✅ LIMPIAR STOCK RESTANTE
                WHERE fknegocio_id = %s 
                AND estado_promo = 'activa'
                AND fecha_fin < %s
            """, [negocio_id, ahora])
            
            # 1. Actualizar ofertas por tiempo que han expirado (considerando hora)
            cursor.execute("""
                UPDATE promociones 
                SET estado_promo = 'finalizada',
                    activa_por_stock = 0
                WHERE fknegocio_id = %s 
                AND estado_promo = 'activa'
                AND tipo_oferta = 'tiempo'
                AND fecha_fin < %s
            """, [negocio_id, ahora])
            
            # 2. Actualizar ofertas por stock que se han agotado
            cursor.execute("""
                UPDATE promociones 
                SET estado_promo = 'finalizada',
                    activa_por_stock = 0
                WHERE fknegocio_id = %s 
                AND estado_promo = 'activa'
                AND tipo_oferta = 'stock'
                AND stock_actual_oferta <= 0
            """, [negocio_id])
            
            # 3. Reactivar ofertas por stock que tienen stock
            cursor.execute("""
                UPDATE promociones 
                SET estado_promo = 'activa',
                    activa_por_stock = 1
                WHERE fknegocio_id = %s 
                AND estado_promo = 'finalizada'
                AND tipo_oferta = 'stock'
                AND stock_actual_oferta > 0
                AND (fecha_fin IS NULL OR fecha_fin >= %s)
            """, [negocio_id, ahora])
            
            # 4. Para ofertas por tiempo, verificar que estén en fecha y hora
            cursor.execute("""
                UPDATE promociones 
                SET estado_promo = 'activa'
                WHERE fknegocio_id = %s 
                AND estado_promo = 'finalizada'
                AND tipo_oferta = 'tiempo'
                AND fecha_fin >= %s
                AND fecha_inicio <= %s
            """, [negocio_id, ahora, ahora])
            
    except Exception as e:
        logger.error(f"Error actualizando estado de ofertas: {str(e)}")

def registrar_movimiento_oferta(producto_id, negocio_id, usuario_id, cantidad, motivo, descripcion, variante_id=None):
    """Registrar movimiento de stock para ofertas - MEJORADO CON VARIANTES"""
    try:
        with connection.cursor() as cursor:
            # ✅ OBTENER STOCK ACTUAL CONSIDERANDO VARIANTES
            if variante_id:
                cursor.execute("""
                    SELECT v.stock_variante, p.nom_prod, v.nombre_variante
                    FROM variantes_producto v
                    JOIN productos p ON v.producto_id = p.pkid_prod
                    WHERE v.id_variante = %s
                """, [variante_id])
            else:
                cursor.execute("""
                    SELECT stock_prod, nom_prod FROM productos 
                    WHERE pkid_prod = %s
                """, [producto_id])
            
            resultado = cursor.fetchone()
            stock_actual = resultado[0] if resultado else 0
            
            # ✅ CALCULAR STOCK NUEVO
            if 'creacion' in motivo:
                stock_nuevo = stock_actual - cantidad  # Descontar
            elif 'eliminacion' in motivo or 'finalizacion' in motivo:
                stock_nuevo = stock_actual + cantidad  # Reintegrar
            else:
                stock_nuevo = stock_actual
            
            # ✅ REGISTRAR MOVIMIENTO CON VARIANTE_ID
            cursor.execute("""
                INSERT INTO movimientos_stock 
                (producto_id, negocio_id, tipo_movimiento, motivo, cantidad, 
                 stock_anterior, stock_nuevo, usuario_id, fecha_movimiento, descripcion, variante_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                producto_id, 
                negocio_id, 
                'reserva_oferta', 
                motivo, 
                cantidad, 
                stock_actual, 
                stock_nuevo,  # ✅ STOCK REAL CALCULADO
                usuario_id, 
                timezone.now(),
                descripcion,
                variante_id  # ✅ SIEMPRE INCLUIR VARIANTE_ID (puede ser NULL)
            ])
    except Exception as e:
        logger.error(f"Error registrando movimiento de oferta: {str(e)}")

@login_required(login_url='login')
def Ofertas_V(request):
    """Vista principal para gestión de ofertas - CORREGIDA PARA MOSTRAR TODOS LOS PRODUCTOS CON VARIANTES"""
    datos = obtener_datos_vendedor_ofertas(request)
    if not datos:
        return redirect('Negocios_V')
    
    negocio = datos['negocio_activo']
    
    # ACTUALIZAR ESTADO DE OFERTAS AUTOMÁTICAMENTE AL CARGAR
    actualizar_estado_ofertas_automatico(negocio.pkid_neg)
    
    if request.method == 'GET':
        try:
            # Obtener TODOS los productos del negocio con sus variantes - SIN FILTRO DE ESTADO
            productos_list = []
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT
                        p.pkid_prod,
                        p.nom_prod,
                        p.precio_prod,
                        p.stock_prod,
                        c.desc_cp as categoria,
                        p.estado_prod,
                        p.desc_prod
                    FROM productos p
                    JOIN categoria_productos c ON p.fkcategoria_prod = c.pkid_cp
                    WHERE p.fknegocioasociado_prod = %s 
                    ORDER BY p.nom_prod
                """, [negocio.pkid_neg])
                productos_base = cursor.fetchall()
            
            print(f"DEBUG: Productos base encontrados: {len(productos_base)}")
            
            # Procesar cada producto para obtener sus variantes y calcular stocks
            for producto_base in productos_base:
                producto_id = producto_base[0]
                
                # Obtener variantes activas de este producto
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            id_variante,
                            nombre_variante,
                            precio_adicional,
                            stock_variante,
                            estado_variante,
                            sku_variante
                        FROM variantes_producto 
                        WHERE producto_id = %s AND estado_variante = 'activa'
                        ORDER BY nombre_variante
                    """, [producto_id])
                    variantes_db = cursor.fetchall()
                
                # Calcular stock total del producto (principal + variantes)
                stock_principal = producto_base[3]
                stock_variantes_total = sum(v[3] for v in variantes_db)
                stock_total = stock_principal + stock_variantes_total
                
                # Preparar lista de variantes para el template
                variantes_list = []
                for variante in variantes_db:
                    precio_total = float(producto_base[2]) + float(variante[2])
                    variantes_list.append({
                        'id': variante[0],
                        'nombre': variante[1],
                        'precio_adicional': float(variante[2]),
                        'stock': variante[3],
                        'estado': variante[4],
                        'sku': variante[5],
                        'precio_total': precio_total,
                        'nombre_completo': f"{producto_base[1]} - {variante[1]}"
                    })
                
                # INCLUIR EL PRODUCTO SI:
                # 1. Tiene stock principal > 0, O
                # 2. Tiene variantes activas (aunque el stock principal sea 0)
                # 3. El producto está disponible o agotado (pero no eliminado)
                tiene_variantes_activas = len(variantes_list) > 0
                estado_valido = producto_base[5] in ['disponible', 'agotado', 'no_disponible']
                
                if estado_valido and (stock_principal > 0 or tiene_variantes_activas):
                    producto_data = {
                        'id': producto_id,
                        'nombre': producto_base[1],
                        'precio': float(producto_base[2]),
                        'stock': stock_total,  # Stock total (principal + variantes)
                        'stock_principal': stock_principal,  # Stock solo del producto principal
                        'categoria': producto_base[4],
                        'estado': producto_base[5],
                        'descripcion': producto_base[6],
                        'variantes': variantes_list,
                        'tiene_variantes_activas': tiene_variantes_activas,
                        'stock_variantes_total': stock_variantes_total,
                        'total_variantes': len(variantes_list)
                    }
                    
                    productos_list.append(producto_data)
                    
                    print(f"DEBUG: Producto incluido: {producto_base[1]}")
                    print(f"DEBUG:   - Estado: {producto_base[5]}")
                    print(f"DEBUG:   - Stock principal: {stock_principal}")
                    print(f"DEBUG:   - Stock variantes: {stock_variantes_total}")
                    print(f"DEBUG:   - Stock total: {stock_total}")
                    print(f"DEBUG:   - Tiene variantes: {tiene_variantes_activas}")
                    print(f"DEBUG:   - Variantes activas: {len(variantes_list)}")
                else:
                    print(f"DEBUG: Producto excluido: {producto_base[1]} - Estado: {producto_base[5]}, Stock principal: {stock_principal}, Tiene variantes: {tiene_variantes_activas}")
            
            print(f"DEBUG: Productos finales en lista: {len(productos_list)}")
            
            # Obtener ofertas activas con información completa
            ofertas_list = []
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        pr.pkid_promo,
                        p.nom_prod,
                        COALESCE(v.nombre_variante, '') as nombre_variante,
                        pr.porcentaje_descuento,
                        p.precio_prod as precio_original,
                        COALESCE(v.precio_adicional, 0) as precio_adicional,
                        (COALESCE((p.precio_prod + COALESCE(v.precio_adicional, 0)) * (1 - pr.porcentaje_descuento / 100), 
                         p.precio_prod * (1 - pr.porcentaje_descuento / 100))) as precio_oferta,
                        pr.fecha_inicio,
                        pr.fecha_fin,
                        pr.estado_promo,
                        pr.titulo_promo,
                        COALESCE(pr.stock_oferta, 0) as stock_oferta,
                        COALESCE(v.stock_variante, p.stock_prod) as stock_disponible,
                        pr.tipo_oferta,
                        COALESCE(pr.stock_actual_oferta, 0) as stock_actual_oferta,
                        pr.activa_por_stock,
                        pr.variante_id,
                        pr.fecha_creacion
                    FROM promociones pr
                    JOIN productos p ON pr.fkproducto_id = p.pkid_prod
                    LEFT JOIN variantes_producto v ON pr.variante_id = v.id_variante
                    WHERE pr.fknegocio_id = %s 
                    ORDER BY pr.estado_promo, pr.fecha_inicio DESC
                """, [negocio.pkid_neg])
                ofertas_db = cursor.fetchall()
            
            # Procesar ofertas para template
            for oferta in ofertas_db:
                # Determinar si la oferta está realmente activa
                hoy = date.today()
                fecha_fin = oferta[8] if oferta[8] else hoy
                esta_activa = oferta[9] == 'activa'
                
                # Para ofertas por tiempo, verificar fechas
                if oferta[12] == 'tiempo' and esta_activa:
                    if hoy > fecha_fin:
                        esta_activa = False
                
                # Para ofertas por stock, verificar stock
                if oferta[12] == 'stock' and esta_activa:
                    if oferta[14] == 0 or oferta[13] <= 0:
                        esta_activa = False
                
                # Determinar nombre completo del producto
                nombre_producto = oferta[1]
                if oferta[2]:  # Tiene variante
                    nombre_producto = f"{oferta[1]} - {oferta[2]}"
                
                ofertas_list.append({
                    'id': oferta[0],
                    'producto_nombre': nombre_producto,
                    'nombre_base': oferta[1],
                    'nombre_variante': oferta[2],
                    'descuento': float(oferta[3]),
                    'precio_original': float(oferta[4]),
                    'precio_adicional': float(oferta[5]),
                    'precio_oferta': float(oferta[6]),
                    'fecha_inicio': oferta[7].strftime('%d/%m/%Y') if oferta[7] else '',
                    'fecha_fin': oferta[8].strftime('%d/%m/%Y') if oferta[8] else '',
                    'estado': oferta[9],
                    'esta_activa_real': esta_activa,
                    'titulo': oferta[10],
                    'stock_oferta': oferta[11],
                    'stock_disponible': oferta[12],
                    'tipo_oferta': oferta[13],
                    'stock_actual_oferta': oferta[14],
                    'activa_por_stock': oferta[15],
                    'variante_id': oferta[16],
                    'fecha_creacion': oferta[17].strftime('%d/%m/%Y %H:%M') if oferta[17] else ''
                })
            
            # Calcular fechas para el template
            today = timezone.now().date()
            tomorrow = today + timezone.timedelta(days=1)
            
            contexto = {
                'nombre': datos['nombre_usuario'],
                'perfil': datos['perfil'],
                'negocio_activo': datos['negocio_activo'],
                'productos': productos_list,
                'ofertas_activas': ofertas_list,
                'today': today.strftime('%Y-%m-%d'),
                'tomorrow': tomorrow.strftime('%Y-%m-%d')
            }
            
            return render(request, 'Vendedor/Ofertas_V.html', contexto)
            
        except Exception as e:
            logger.error(f"Error en GET Ofertas_V: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            messages.error(request, f"Error al cargar ofertas: {str(e)}")
            return redirect('dash_vendedor')
    
    # Si es POST, procesamos la creación de oferta
    elif request.method == 'POST':
        return crear_oferta(request)

@login_required(login_url='login')
def crear_oferta(request):
    """Vista MEJORADA para crear ofertas - CON VALIDACIÓN DE STOCK POR VARIANTES"""
    try:
        datos = obtener_datos_vendedor_ofertas(request)
        if not datos:
            messages.error(request, "No tienes un negocio activo.")
            return redirect('Ofertas_V')
        
        negocio = datos['negocio_activo']
        
        # Obtener datos del formulario
        producto_id = request.POST.get('producto_id')
        variante_id = request.POST.get('variante_id')
        porcentaje_descuento = request.POST.get('porcentaje_descuento')
        stock_oferta = request.POST.get('stock_oferta')
        fecha_inicio = request.POST.get('fecha_inicio')
        hora_inicio = request.POST.get('hora_inicio', '00:00')
        fecha_fin = request.POST.get('fecha_fin')
        hora_fin = request.POST.get('hora_fin', '23:59')
        tipo_oferta = request.POST.get('tipo_oferta', 'tiempo')
        
        # Validaciones básicas
        if not producto_id or not porcentaje_descuento or not stock_oferta:
            messages.error(request, 'Todos los campos obligatorios deben ser llenados.')
            return redirect('Ofertas_V')
        
        # PARA AMBOS TIPOS DE OFERTA: fecha fin es obligatoria
        if not fecha_fin:
            messages.error(request, 'La fecha fin es obligatoria para ambos tipos de oferta.')
            return redirect('Ofertas_V')
        
        try:
            producto_id = int(producto_id)
            porcentaje_descuento = float(porcentaje_descuento)
            stock_oferta = int(stock_oferta)
            variante_id = int(variante_id) if variante_id else None
            
            if porcentaje_descuento <= 0 or porcentaje_descuento > 100:
                messages.error(request, 'El descuento debe estar entre 1% y 100%.')
                return redirect('Ofertas_V')
            
            if stock_oferta <= 0:
                messages.error(request, 'El stock de oferta debe ser mayor a 0.')
                return redirect('Ofertas_V')
            
            # Validar que el producto/variante pertenezca al negocio - CONSULTA CORREGIDA
            with connection.cursor() as cursor:
                if variante_id:
                    # Validar variante específica
                    cursor.execute("""
                        SELECT p.pkid_prod, p.nom_prod, p.precio_prod, 
                               v.nombre_variante, v.precio_adicional, v.stock_variante,
                               p.stock_prod, v.estado_variante
                        FROM productos p
                        JOIN variantes_producto v ON p.pkid_prod = v.producto_id
                        WHERE p.pkid_prod = %s AND p.fknegocioasociado_prod = %s 
                        AND v.id_variante = %s AND v.estado_variante = 'activa'
                    """, [producto_id, negocio.pkid_neg, variante_id])
                else:
                    # Validar producto principal - CORREGIDO: verificar stock total incluyendo variantes
                    cursor.execute("""
                        SELECT 
                            p.pkid_prod, 
                            p.nom_prod, 
                            p.precio_prod, 
                            p.stock_prod,
                            -- Calcular stock total incluyendo variantes activas
                            p.stock_prod + COALESCE(
                                (SELECT SUM(stock_variante) 
                                 FROM variantes_producto v2 
                                 WHERE v2.producto_id = p.pkid_prod 
                                 AND v2.estado_variante = 'activa'), 0
                            ) as stock_total
                        FROM productos p 
                        WHERE p.pkid_prod = %s AND p.fknegocioasociado_prod = %s
                    """, [producto_id, negocio.pkid_neg])
                
                producto_db = cursor.fetchone()
            
            if not producto_db:
                messages.error(request, 'Producto/Variante no encontrado o no pertenece a tu negocio.')
                return redirect('Ofertas_V')
            
            # Obtener información del producto/variante - LÓGICA CORREGIDA
            if variante_id:
                # Verificar que la variante esté activa
                if producto_db[7] != 'activa':
                    messages.error(request, 'La variante seleccionada no está activa.')
                    return redirect('Ofertas_V')
                    
                producto_nombre = f"{producto_db[1]} - {producto_db[3]}"
                precio_original = float(producto_db[2]) + float(producto_db[4])
                stock_disponible = producto_db[5]  # Stock de la variante específica
            else:
                producto_nombre = producto_db[1]
                precio_original = float(producto_db[2])
                stock_disponible = producto_db[4]  # Usar stock_total en lugar de stock_prod
            
            print(f"DEBUG: Creando oferta para {producto_nombre} - Stock disponible: {stock_disponible}")
            
            # Validar stock disponible - CORREGIDO PARA VARIANTES
            stock_total_ofertas_activas = 0
            with connection.cursor() as cursor:
                if variante_id:
                    cursor.execute("""
                        SELECT COALESCE(SUM(stock_oferta), 0) 
                        FROM promociones 
                        WHERE fkproducto_id = %s AND variante_id = %s 
                        AND estado_promo = 'activa'
                        AND tipo_oferta = 'stock'
                    """, [producto_id, variante_id])
                else:
                    cursor.execute("""
                        SELECT COALESCE(SUM(stock_oferta), 0) 
                        FROM promociones 
                        WHERE fkproducto_id = %s 
                        AND estado_promo = 'activa'
                        AND tipo_oferta = 'stock'
                    """, [producto_id])
                
                stock_total_ofertas_activas = cursor.fetchone()[0]
            
            if tipo_oferta == 'stock':
                with connection.cursor() as cursor:
                    if variante_id:
                        # Descontar de la variante
                        cursor.execute("""
                            UPDATE variantes_producto 
                            SET stock_variante = stock_variante - %s
                            WHERE id_variante = %s
                        """, [stock_oferta, variante_id])
                        
                        # Obtener stock actualizado para registro
                        cursor.execute("SELECT stock_variante FROM variantes_producto WHERE id_variante = %s", [variante_id])
                        stock_nuevo_variante = cursor.fetchone()[0]
                        
                    else:
                        # Descontar del producto principal
                        cursor.execute("""
                            UPDATE productos 
                            SET stock_prod = stock_prod - %s
                            WHERE pkid_prod = %s
                        """, [stock_oferta, producto_id])
                        
                        # Obtener stock actualizado para registro
                        cursor.execute("SELECT stock_prod FROM productos WHERE pkid_prod = %s", [producto_id])
                        stock_nuevo_producto = cursor.fetchone()[0]
            
            # PROCESAR FECHAS Y HORAS - AMBOS TIPOS REQUIEREN FECHA FIN
            now = timezone.now()
            today_local = now.date()
            
            # Fecha y hora de inicio
            if fecha_inicio:
                try:
                    # Parsear fecha y hora
                    fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                    hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
                    
                    # Crear datetime naive (sin zona horaria)
                    fecha_hora_inicio_naive = datetime.combine(fecha_inicio_obj, hora_inicio_obj)
                    
                    # Validar que la fecha no sea en el pasado
                    if fecha_inicio_obj < today_local:
                        messages.error(request, 'La fecha de inicio no puede ser en el pasado.')
                        return redirect('Ofertas_V')
                        
                    # Convertir a datetime aware para la base de datos
                    fecha_hora_inicio_obj = timezone.make_aware(fecha_hora_inicio_naive)
                        
                except ValueError:
                    messages.error(request, 'Formato de fecha u hora incorrecto.')
                    return redirect('Ofertas_V')
            else:
                # Si no se especifica fecha inicio, usar ahora
                fecha_hora_inicio_obj = now

            # Fecha y hora de fin - OBLIGATORIA PARA AMBOS TIPOS
            try:
                fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                hora_fin_obj = datetime.strptime(hora_fin, '%H:%M').time()
                
                # Crear datetime naive primero
                fecha_hora_fin_naive = datetime.combine(fecha_fin_obj, hora_fin_obj)
                
                # Validar que la fecha fin sea después de la fecha inicio
                fecha_inicio_naive = datetime.combine(
                    fecha_inicio_obj if fecha_inicio else today_local, 
                    hora_inicio_obj if fecha_inicio else now.time()
                )
                
                if fecha_hora_fin_naive <= fecha_inicio_naive:
                    messages.error(request, 'La fecha y hora de fin deben ser posteriores al inicio.')
                    return redirect('Ofertas_V')
                
                # Convertir a datetime aware para la base de datos
                fecha_hora_fin_obj = timezone.make_aware(fecha_hora_fin_naive)
                
            except ValueError:
                messages.error(request, 'Formato de fecha u hora incorrecto.')
                return redirect('Ofertas_V')
            
            # Calcular precio con oferta
            precio_oferta = precio_original * (1 - porcentaje_descuento / 100)
            
            # Crear título automático
            tipo_texto = "por tiempo" if tipo_oferta == 'tiempo' else "hasta agotar stock"
            titulo = f"Oferta {producto_nombre} - {porcentaje_descuento:.0f}% OFF ({tipo_texto})"
            descripcion = f"Oferta especial de {producto_nombre}. Precio regular: ${precio_original:.0f}"
            
            # Crear la oferta - AMBOS TIPOS TIENEN FECHA_FIN
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO promociones 
                    (fknegocio_id, fkproducto_id, titulo_promo, descripcion_promo, 
                     porcentaje_descuento, fecha_inicio, fecha_fin, estado_promo, 
                     stock_oferta, tipo_oferta, stock_inicial_oferta, stock_actual_oferta,
                     activa_por_stock, variante_id, fecha_creacion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    negocio.pkid_neg,
                    producto_id,
                    titulo,
                    descripcion,
                    porcentaje_descuento,
                    fecha_hora_inicio_obj,
                    fecha_hora_fin_obj,  # Siempre tiene valor para ambos tipos
                    'activa',
                    stock_oferta,
                    tipo_oferta,
                    stock_oferta,
                    stock_oferta,
                    1 if tipo_oferta == 'stock' else 0,
                    variante_id,
                    timezone.now()
                ])
            
            # Registrar movimiento de stock para la oferta
            if tipo_oferta == 'stock':
                registrar_movimiento_oferta(
                    producto_id, 
                    negocio.pkid_neg, 
                    datos['perfil'].id,
                    stock_oferta,
                    'creacion_oferta',
                    f"Oferta creada: {titulo}",
                    variante_id
                )
            
            messages.success(request, 
                f'✅ Oferta creada exitosamente para {producto_nombre} '
                f'({tipo_texto}) - Stock asignado: {stock_oferta}'
            )
            return redirect('Ofertas_V')
            
        except ValueError as e:
            messages.error(request, f'Error en los datos numéricos: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al crear oferta: {str(e)}')
            import traceback
            logger.error(f"Error al crear oferta: {traceback.format_exc()}")
        
        return redirect('Ofertas_V')
    except Exception as e:
        messages.error(request, f'Error al procesar la solicitud: {str(e)}')
        return redirect('Ofertas_V')

@login_required(login_url='login')
def eliminar_oferta(request, oferta_id):
    """ELIMINAR una oferta y liberar stock"""
    try:
        datos = obtener_datos_vendedor_ofertas(request)
        if not datos:
            messages.error(request, "No tienes un negocio activo.")
            return redirect('Ofertas_V')
        
        negocio = datos['negocio_activo']
        
        # Obtener información de la oferta antes de eliminar
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT fkproducto_id, stock_oferta, titulo_promo, variante_id, tipo_oferta
                FROM promociones 
                WHERE pkid_promo = %s AND fknegocio_id = %s
            """, [oferta_id, negocio.pkid_neg])
            oferta_info = cursor.fetchone()
        
        if not oferta_info:
            messages.error(request, 'Oferta no encontrada')
            return redirect('Ofertas_V')
        
        producto_id, stock_oferta, titulo, variante_id, tipo_oferta = oferta_info
        
        # ELIMINAR la oferta
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM promociones WHERE pkid_promo = %s", [oferta_id])
        
        # Registrar movimiento de liberación de stock solo para ofertas por stock
        if tipo_oferta == 'stock' and stock_oferta > 0:
            with connection.cursor() as cursor:
                if variante_id:
                    # Reintegrar a la variante
                    cursor.execute("""
                        UPDATE variantes_producto 
                        SET stock_variante = stock_variante + %s
                        WHERE id_variante = %s
                    """, [stock_oferta, variante_id])
                else:
                    # Reintegrar al producto principal
                    cursor.execute("""
                        UPDATE productos 
                        SET stock_prod = stock_prod + %s
                        WHERE pkid_prod = %s
                    """, [stock_oferta, producto_id])
        
        messages.success(request, f'✅ Oferta eliminada exitosamente.')
        
    except Exception as e:
        messages.error(request, f'Error al eliminar oferta: {str(e)}')
        logger.error(f"Error al eliminar oferta: {str(e)}")
    
    return redirect('Ofertas_V')

@login_required(login_url='login')
def finalizar_oferta_manual(request, oferta_id):
    """Finalizar una oferta manualmente y liberar stock sobrante"""
    if request.method == 'POST':
        try:
            datos = obtener_datos_vendedor_ofertas(request)
            if not datos:
                messages.error(request, "No tienes un negocio activo.")
                return redirect('Ofertas_V')
            
            negocio = datos['negocio_activo']
            
            with connection.cursor() as cursor:
                # Obtener información de la oferta
                cursor.execute("""
                    SELECT fkproducto_id, stock_actual_oferta, titulo_promo, variante_id, tipo_oferta
                    FROM promociones 
                    WHERE pkid_promo = %s AND fknegocio_id = %s AND estado_promo = 'activa'
                """, [oferta_id, negocio.pkid_neg])
                oferta_info = cursor.fetchone()
            
            if not oferta_info:
                messages.error(request, 'Oferta no encontrada o no está activa')
                return redirect('Ofertas_V')
            
            producto_id, stock_actual, titulo, variante_id, tipo_oferta = oferta_info
            
            # Finalizar la oferta
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE promociones 
                    SET estado_promo = 'finalizada',
                        activa_por_stock = 0
                    WHERE pkid_promo = %s
                """, [oferta_id])
            
            # Registrar movimiento si hay stock sobrante y es oferta por stock
            if stock_actual > 0 and tipo_oferta == 'stock':
                registrar_movimiento_oferta(
                    producto_id, 
                    negocio.pkid_neg, 
                    datos['perfil'].id,
                    stock_actual,
                    'finalizacion_oferta',
                    f"Oferta finalizada manualmente: {titulo} - Stock sobrante liberado: {stock_actual}",
                    variante_id
                )
            
            messages.success(request, 
                f'✅ Oferta finalizada manualmente. '
                f'Stock sobrante liberado: {stock_actual}' if stock_actual > 0 and tipo_oferta == 'stock' else 
                f'✅ Oferta finalizada manualmente.'
            )
            
        except Exception as e:
            messages.error(request, f'Error al finalizar oferta: {str(e)}')
            logger.error(f"Error al finalizar oferta: {str(e)}")
    
    return redirect('Ofertas_V')

@login_required(login_url='login')
def verificar_estado_ofertas(request):
    """Vista para verificar y actualizar estado de ofertas manualmente"""
    try:
        datos = obtener_datos_vendedor_ofertas(request)
        if not datos:
            messages.error(request, "No tienes un negocio activo.")
            return redirect('Ofertas_V')
        
        negocio = datos['negocio_activo']
        
        # Actualizar estado de ofertas
        actualizar_estado_ofertas_automatico(negocio.pkid_neg)
        
        # Contar ofertas actualizadas
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM promociones 
                WHERE fknegocio_id = %s AND estado_promo = 'finalizada'
                AND DATE(fecha_creacion) = DATE(%s)
            """, [negocio.pkid_neg, timezone.now()])
            ofertas_finalizadas = cursor.fetchone()[0]
        
        if ofertas_finalizadas > 0:
            messages.success(request, f"Estado de ofertas actualizado. {ofertas_finalizadas} oferta(s) finalizada(s).")
        else:
            messages.info(request, "Estado de ofertas actualizado. No hay ofertas que finalizar.")
        
        return redirect('Ofertas_V')
        
    except Exception as e:
        logger.error(f"Error en verificar_estado_ofertas: {str(e)}")
        messages.error(request, f"Error al actualizar estado de ofertas: {str(e)}")
        return redirect('Ofertas_V')
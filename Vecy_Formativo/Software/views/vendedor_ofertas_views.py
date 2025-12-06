from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import connection
from datetime import datetime, date, time
import json
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
    """Función MEJORADA para actualizar automáticamente el estado de las ofertas"""
    try:
        print(f"🔄 DEBUG actualizar_estado_ofertas: Iniciando para negocio {negocio_id}")
        
        with connection.cursor() as cursor:
            ahora = timezone.now()

            # ✅ CORRECCIÓN: Actualizar ofertas por tiempo que han expirado
            cursor.execute("""
                UPDATE promociones 
                SET estado_promo = 'finalizada',
                    activa_por_stock = 0,
                    stock_actual_oferta = 0
                WHERE fknegocio_id = %s 
                AND estado_promo = 'activa'
                AND tipo_oferta = 'tiempo'
                AND fecha_fin < %s
            """, [negocio_id, ahora])
            filas_afectadas = cursor.rowcount
            print(f"🔄 DEBUG: Ofertas por tiempo finalizadas: {filas_afectadas}")
            
            # ✅ CORRECCIÓN: Actualizar ofertas por stock que se han agotado
            cursor.execute("""
                UPDATE promociones 
                SET estado_promo = 'finalizada',
                    activa_por_stock = 0
                WHERE fknegocio_id = %s 
                AND estado_promo = 'activa'
                AND tipo_oferta = 'stock'
                AND stock_actual_oferta <= 0
            """, [negocio_id])
            filas_afectadas = cursor.rowcount
            print(f"🔄 DEBUG: Ofertas por stock agotadas: {filas_afectadas}")
            
            # ✅ CORRECCIÓN: Reactivar ofertas por stock que tienen stock y no han expirado
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
            filas_afectadas = cursor.rowcount
            print(f"🔄 DEBUG: Ofertas por stock reactivadas: {filas_afectadas}")
            
            # ✅ CORRECCIÓN: Para ofertas por tiempo, verificar que estén en fecha
            cursor.execute("""
                UPDATE promociones 
                SET estado_promo = 'activa'
                WHERE fknegocio_id = %s 
                AND estado_promo = 'finalizada'
                AND tipo_oferta = 'tiempo'
                AND fecha_fin >= %s
                AND fecha_inicio <= %s
            """, [negocio_id, ahora, ahora])
            filas_afectadas = cursor.rowcount
            print(f"🔄 DEBUG: Ofertas por tiempo reactivadas: {filas_afectadas}")
            
            # ✅ Actualizar estado de combos
            cursor.execute("""
                UPDATE combos 
                SET estado_combo = 'inactivo'
                WHERE fknegocio_id = %s 
                AND estado_combo = 'activo'
                AND fecha_fin < %s
            """, [negocio_id, ahora.date()])
            filas_afectadas = cursor.rowcount
            print(f"🔄 DEBUG: Combos finalizados: {filas_afectadas}")
            
            # ✅ Actualizar estado de promociones 2x1
            cursor.execute("""
                UPDATE promociones_2x1 
                SET estado = 'finalizada'
                WHERE fknegocio_id = %s 
                AND estado = 'activa'
                AND fecha_fin < %s
            """, [negocio_id, ahora.date()])
            filas_afectadas = cursor.rowcount
            print(f"🔄 DEBUG: Promociones 2x1 finalizadas: {filas_afectadas}")
            
    except Exception as e:
        print(f"❌ ERROR actualizando estado de ofertas: {str(e)}")
        import traceback
        print(f"❌ TRACEBACK: {traceback.format_exc()}")

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
    """Vista principal para gestión de ofertas - AHORA CON COMBOS Y 2X1"""
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
            
            # Obtener combos activos del negocio
            combos_list = []
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        c.pkid_combo,
                        c.nombre_combo,
                        c.descripcion_combo,
                        c.precio_combo,
                        c.precio_regular,
                        c.descuento_porcentaje,
                        c.imagen_combo,
                        c.estado_combo,
                        c.stock_combo,
                        c.fecha_creacion,
                        c.fecha_inicio,
                        c.fecha_fin,
                        COUNT(ci.pkid_combo_item) as total_items
                    FROM combos c
                    LEFT JOIN combo_items ci ON c.pkid_combo = ci.fkcombo_id
                    WHERE c.fknegocio_id = %s
                    GROUP BY c.pkid_combo
                    ORDER BY c.estado_combo, c.fecha_creacion DESC
                """, [negocio.pkid_neg])
                combos_db = cursor.fetchall()
            
            # Procesar combos para template
            for combo in combos_db:
                # Obtener items del combo
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            p.nom_prod,
                            COALESCE(v.nombre_variante, '') as nombre_variante,
                            ci.cantidad,
                            p.precio_prod,
                            COALESCE(v.precio_adicional, 0) as precio_adicional,
                            p.nom_prod || COALESCE(' - ' || v.nombre_variante, '') as nombre_completo
                        FROM combo_items ci
                        JOIN productos p ON ci.fkproducto_id = p.pkid_prod
                        LEFT JOIN variantes_producto v ON ci.variante_id = v.id_variante
                        WHERE ci.fkcombo_id = %s
                    """, [combo[0]])
                    items_db = cursor.fetchall()
                
                items_list = []
                for item in items_db:
                    precio_total_item = float(item[3]) + float(item[4])
                    items_list.append({
                        'nombre_producto': item[0],
                        'nombre_variante': item[1],
                        'cantidad': item[2],
                        'precio_unitario': precio_total_item,
                        'precio_total': precio_total_item * item[2],
                        'nombre_completo': item[5]
                    })
                
                # Calcular ahorro si hay precio regular
                precio_combo = float(combo[3])
                precio_regular = float(combo[4]) if combo[4] else 0
                ahorro = precio_regular - precio_combo if precio_regular > 0 else 0
                
                combos_list.append({
                    'id': combo[0],
                    'nombre': combo[1],
                    'descripcion': combo[2],
                    'precio': precio_combo,
                    'precio_regular': precio_regular,
                    'descuento_porcentaje': float(combo[5]) if combo[5] else 0,
                    'imagen': combo[6],
                    'estado': combo[7],
                    'stock': combo[8],
                    'fecha_creacion': combo[9].strftime('%d/%m/%Y %H:%M') if combo[9] else '',
                    'fecha_inicio': combo[10].strftime('%d/%m/%Y') if combo[10] else '',
                    'fecha_fin': combo[11].strftime('%d/%m/%Y') if combo[11] else '',
                    'total_items': combo[12],
                    'items': items_list,
                    'ahorro': ahorro,
                    'tiene_ahorro': ahorro > 0
                })
            
            # Obtener promociones 2x1 activas
            promociones_2x1_list = []
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        p2.pkid_promo_2x1,
                        p.nom_prod,
                        COALESCE(v.nombre_variante, '') as nombre_variante,
                        p2.fecha_inicio,
                        p2.fecha_fin,
                        p2.estado,
                        p2.aplica_variantes,
                        p2.fecha_creacion
                    FROM promociones_2x1 p2
                    JOIN productos p ON p2.fkproducto_id = p.pkid_prod
                    LEFT JOIN variantes_producto v ON p2.variante_id = v.id_variante
                    WHERE p2.fknegocio_id = %s
                    ORDER BY p2.estado, p2.fecha_inicio DESC
                """, [negocio.pkid_neg])
                promos_2x1_db = cursor.fetchall()
            
            for promo in promos_2x1_db:
                nombre_producto = promo[1]
                if promo[2]:  # Tiene variante
                    nombre_producto = f"{promo[1]} - {promo[2]}"
                
                promociones_2x1_list.append({
                    'id': promo[0],
                    'producto_nombre': nombre_producto,
                    'fecha_inicio': promo[3].strftime('%d/%m/%Y') if promo[3] else '',
                    'fecha_fin': promo[4].strftime('%d/%m/%Y') if promo[4] else '',
                    'estado': promo[5],
                    'aplica_variantes': promo[6],
                    'fecha_creacion': promo[7].strftime('%d/%m/%Y %H:%M') if promo[7] else '',
                    'esta_activa': promo[5] == 'activa' and date.today() <= (promo[4] if promo[4] else date.today())
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
                'combos_activos': combos_list,
                'promociones_2x1': promociones_2x1_list,
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
        # Verificar si es creación de combo o 2x1
        if 'crear_combo' in request.POST:
            return crear_combo(request)
        elif 'crear_2x1' in request.POST:
            return crear_promocion_2x1(request)
        else:
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
            if tipo_oferta == 'stock':
                with connection.cursor() as cursor:
                    if variante_id:
                        # Descontar de la variante
                        cursor.execute("""
                            UPDATE variantes_producto 
                            SET stock_variante = stock_variante - %s
                            WHERE id_variante = %s
                        """, [stock_oferta, variante_id])
                    else:
                        # Descontar del producto principal
                        cursor.execute("""
                            UPDATE productos 
                            SET stock_prod = stock_prod - %s
                            WHERE pkid_prod = %s
                        """, [stock_oferta, producto_id])
            
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
def crear_combo(request):
    """Crear un combo/paquete de productos"""
    try:
        datos = obtener_datos_vendedor_ofertas(request)
        if not datos:
            messages.error(request, "No tienes un negocio activo.")
            return redirect('Ofertas_V')
        
        negocio = datos['negocio_activo']
        
        # Obtener datos del formulario
        nombre_combo = request.POST.get('nombre_combo')
        descripcion_combo = request.POST.get('descripcion_combo')
        precio_combo = request.POST.get('precio_combo')
        descuento_porcentaje = request.POST.get('descuento_porcentaje', 0)
        stock_combo = request.POST.get('stock_combo', 0)
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        productos_combo = request.POST.getlist('productos_combo[]')
        cantidades = request.POST.getlist('cantidades[]')
        variantes = request.POST.getlist('variantes[]')
        
        # Validaciones básicas
        if not nombre_combo or not precio_combo:
            messages.error(request, 'Nombre y precio del combo son obligatorios.')
            return redirect('Ofertas_V')
        
        if not productos_combo or len(productos_combo) == 0:
            messages.error(request, 'Debes seleccionar al menos un producto para el combo.')
            return redirect('Ofertas_V')
        
        try:
            precio_combo = float(precio_combo)
            descuento_porcentaje = float(descuento_porcentaje) if descuento_porcentaje else 0
            stock_combo = int(stock_combo) if stock_combo else 0
            
            if precio_combo <= 0:
                messages.error(request, 'El precio del combo debe ser mayor a 0.')
                return redirect('Ofertas_V')
            
            if descuento_porcentaje < 0 or descuento_porcentaje > 100:
                messages.error(request, 'El descuento debe estar entre 0% y 100%.')
                return redirect('Ofertas_V')
            
            # Calcular precio regular (suma de productos individuales)
            precio_regular_total = 0
            items_validos = []
            
            for i, (producto_id_str, cantidad_str, variante_id_str) in enumerate(zip(productos_combo, cantidades, variantes)):
                try:
                    producto_id = int(producto_id_str)
                    cantidad = int(cantidad_str)
                    variante_id = int(variante_id_str) if variante_id_str and variante_id_str != 'null' else None
                    
                    if cantidad <= 0:
                        continue
                    
                    # Validar producto/variante
                    with connection.cursor() as cursor:
                        if variante_id:
                            cursor.execute("""
                                SELECT p.pkid_prod, p.nom_prod, p.precio_prod, 
                                       v.nombre_variante, v.precio_adicional, v.stock_variante
                                FROM productos p
                                JOIN variantes_producto v ON p.pkid_prod = v.producto_id
                                WHERE p.pkid_prod = %s AND p.fknegocioasociado_prod = %s 
                                AND v.id_variante = %s AND v.estado_variante = 'activa'
                            """, [producto_id, negocio.pkid_neg, variante_id])
                        else:
                            cursor.execute("""
                                SELECT pkid_prod, nom_prod, precio_prod, stock_prod
                                FROM productos 
                                WHERE pkid_prod = %s AND fknegocioasociado_prod = %s
                            """, [producto_id, negocio.pkid_neg])
                        
                        producto_db = cursor.fetchone()
                    
                    if not producto_db:
                        continue
                    
                    # Calcular precio unitario
                    if variante_id:
                        precio_unitario = float(producto_db[2]) + float(producto_db[4])
                        nombre_completo = f"{producto_db[1]} - {producto_db[3]}"
                        stock_disponible = producto_db[5]
                    else:
                        precio_unitario = float(producto_db[2])
                        nombre_completo = producto_db[1]
                        stock_disponible = producto_db[3]
                    
                    # Validar stock disponible
                    if stock_combo > 0 and cantidad * stock_combo > stock_disponible:
                        messages.error(request, f'Stock insuficiente para {nombre_completo}. Disponible: {stock_disponible}, Necesario: {cantidad * stock_combo}')
                        return redirect('Ofertas_V')
                    
                    precio_regular_total += precio_unitario * cantidad
                    
                    items_validos.append({
                        'producto_id': producto_id,
                        'variante_id': variante_id,
                        'cantidad': cantidad,
                        'precio_unitario': precio_unitario,
                        'nombre': nombre_completo
                    })
                    
                except (ValueError, IndexError) as e:
                    logger.error(f"Error procesando item de combo: {e}")
                    continue
            
            if not items_validos:
                messages.error(request, 'No se encontraron productos válidos para el combo.')
                return redirect('Ofertas_V')
            
            # Si no se proporcionó precio regular, usar el calculado
            precio_regular = request.POST.get('precio_regular')
            if not precio_regular or precio_regular == '0':
                precio_regular = precio_regular_total
            else:
                precio_regular = float(precio_regular)
            
            # Calcular descuento automático si no se proporcionó
            if descuento_porcentaje == 0 and precio_regular > precio_combo:
                descuento_porcentaje = ((precio_regular - precio_combo) / precio_regular) * 100
            
            # Procesar fechas
            fecha_inicio_obj = None
            fecha_fin_obj = None
            
            if fecha_inicio:
                fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            if fecha_fin:
                fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            # Crear el combo
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO combos 
                    (fknegocio_id, nombre_combo, descripcion_combo, precio_combo, 
                     precio_regular, descuento_porcentaje, stock_combo, estado_combo,
                     fecha_inicio, fecha_fin, fecha_creacion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    negocio.pkid_neg,
                    nombre_combo,
                    descripcion_combo,
                    precio_combo,
                    precio_regular,
                    descuento_porcentaje,
                    stock_combo,
                    'activo',
                    fecha_inicio_obj,
                    fecha_fin_obj,
                    timezone.now()
                ])
                
                combo_id = cursor.lastrowid
                
                # Crear items del combo
                for item in items_validos:
                    cursor.execute("""
                        INSERT INTO combo_items 
                        (fkcombo_id, fkproducto_id, variante_id, cantidad)
                        VALUES (%s, %s, %s, %s)
                    """, [
                        combo_id,
                        item['producto_id'],
                        item['variante_id'],
                        item['cantidad']
                    ])
                
                # Reservar stock si el combo tiene stock definido
                if stock_combo > 0:
                    for item in items_validos:
                        cantidad_total_reservar = item['cantidad'] * stock_combo
                        
                        if item['variante_id']:
                            # Descontar de variante
                            cursor.execute("""
                                UPDATE variantes_producto 
                                SET stock_variante = stock_variante - %s
                                WHERE id_variante = %s
                            """, [cantidad_total_reservar, item['variante_id']])
                            
                            registrar_movimiento_oferta(
                                item['producto_id'],
                                negocio.pkid_neg,
                                datos['perfil'].id,
                                cantidad_total_reservar,
                                'creacion_combo',
                                f"Reserva para combo: {nombre_combo}",
                                item['variante_id']
                            )
                        else:
                            # Descontar del producto principal
                            cursor.execute("""
                                UPDATE productos 
                                SET stock_prod = stock_prod - %s
                                WHERE pkid_prod = %s
                            """, [cantidad_total_reservar, item['producto_id']])
                            
                            registrar_movimiento_oferta(
                                item['producto_id'],
                                negocio.pkid_neg,
                                datos['perfil'].id,
                                cantidad_total_reservar,
                                'creacion_combo',
                                f"Reserva para combo: {nombre_combo}"
                            )
            
            ahorro_msg = ""
            if precio_regular > precio_combo:
                ahorro = precio_regular - precio_combo
                ahorro_msg = f" Los clientes ahorran ${ahorro:.0f} ({descuento_porcentaje:.1f}%)"
            
            messages.success(request, 
                f'✅ Combo "{nombre_combo}" creado exitosamente.{ahorro_msg}'
            )
            return redirect('Ofertas_V')
            
        except ValueError as e:
            messages.error(request, f'Error en los datos numéricos: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al crear combo: {str(e)}')
            import traceback
            logger.error(f"Error al crear combo: {traceback.format_exc()}")
        
        return redirect('Ofertas_V')
    except Exception as e:
        messages.error(request, f'Error al procesar la solicitud: {str(e)}')
        return redirect('Ofertas_V')

@login_required(login_url='login')
def crear_promocion_2x1(request):
    """Crear una promoción 2x1"""
    try:
        datos = obtener_datos_vendedor_ofertas(request)
        if not datos:
            messages.error(request, "No tienes un negocio activo.")
            return redirect('Ofertas_V')
        
        negocio = datos['negocio_activo']
        
        # Obtener datos del formulario
        producto_id = request.POST.get('producto_id_2x1')
        variante_id = request.POST.get('variante_id_2x1')
        fecha_inicio = request.POST.get('fecha_inicio_2x1')
        fecha_fin = request.POST.get('fecha_fin_2x1')
        aplica_variantes = request.POST.get('aplica_variantes', '0')
        
        # Validaciones básicas
        if not producto_id:
            messages.error(request, 'Debes seleccionar un producto para la promoción 2x1.')
            return redirect('Ofertas_V')
        
        if not fecha_inicio or not fecha_fin:
            messages.error(request, 'Las fechas de inicio y fin son obligatorias.')
            return redirect('Ofertas_V')
        
        try:
            producto_id = int(producto_id)
            variante_id = int(variante_id) if variante_id else None
            aplica_variantes = aplica_variantes == '1'
            
            # Validar que el producto pertenezca al negocio
            with connection.cursor() as cursor:
                if variante_id:
                    cursor.execute("""
                        SELECT p.pkid_prod, p.nom_prod, v.nombre_variante
                        FROM productos p
                        JOIN variantes_producto v ON p.pkid_prod = v.producto_id
                        WHERE p.pkid_prod = %s AND p.fknegocioasociado_prod = %s 
                        AND v.id_variante = %s AND v.estado_variante = 'activa'
                    """, [producto_id, negocio.pkid_neg, variante_id])
                else:
                    cursor.execute("""
                        SELECT pkid_prod, nom_prod FROM productos 
                        WHERE pkid_prod = %s AND fknegocioasociado_prod = %s
                    """, [producto_id, negocio.pkid_neg])
                
                producto_db = cursor.fetchone()
            
            if not producto_db:
                messages.error(request, 'Producto/Variante no encontrado o no pertenece a tu negocio.')
                return redirect('Ofertas_V')
            
            # Determinar nombre del producto
            if variante_id:
                producto_nombre = f"{producto_db[1]} - {producto_db[2]}"
            else:
                producto_nombre = producto_db[1]
            
            # Procesar fechas
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            # Validar fechas
            if fecha_fin_obj < fecha_inicio_obj:
                messages.error(request, 'La fecha de fin no puede ser anterior a la fecha de inicio.')
                return redirect('Ofertas_V')
            
            # Crear la promoción 2x1
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO promociones_2x1 
                    (fknegocio_id, fkproducto_id, variante_id, fecha_inicio, 
                     fecha_fin, estado, aplica_variantes, fecha_creacion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    negocio.pkid_neg,
                    producto_id,
                    variante_id,
                    fecha_inicio_obj,
                    fecha_fin_obj,
                    'activa',
                    aplica_variantes,
                    timezone.now()
                ])
            
            messages.success(request, 
                f'✅ Promoción 2x1 creada exitosamente para {producto_nombre}'
            )
            return redirect('Ofertas_V')
            
        except ValueError as e:
            messages.error(request, f'Error en los datos: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al crear promoción 2x1: {str(e)}')
            logger.error(f"Error al crear promoción 2x1: {str(e)}")
        
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
def eliminar_combo(request, combo_id):
    """Eliminar un combo y liberar stock reservado"""
    try:
        datos = obtener_datos_vendedor_ofertas(request)
        if not datos:
            messages.error(request, "No tienes un negocio activo.")
            return redirect('Ofertas_V')
        
        negocio = datos['negocio_activo']
        
        # Obtener información del combo antes de eliminar
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.nombre_combo, c.stock_combo
                FROM combos c
                WHERE c.pkid_combo = %s AND c.fknegocio_id = %s
            """, [combo_id, negocio.pkid_neg])
            combo_info = cursor.fetchone()
        
        if not combo_info:
            messages.error(request, 'Combo no encontrado')
            return redirect('Ofertas_V')
        
        nombre_combo, stock_combo = combo_info
        
        # Obtener items del combo para liberar stock
        if stock_combo > 0:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT ci.fkproducto_id, ci.variante_id, ci.cantidad
                    FROM combo_items ci
                    WHERE ci.fkcombo_id = %s
                """, [combo_id])
                items = cursor.fetchall()
            
            # Liberar stock de cada item
            for item in items:
                producto_id, variante_id, cantidad = item
                cantidad_total_liberar = cantidad * stock_combo
                
                if variante_id:
                    cursor.execute("""
                        UPDATE variantes_producto 
                        SET stock_variante = stock_variante + %s
                        WHERE id_variante = %s
                    """, [cantidad_total_liberar, variante_id])
                else:
                    cursor.execute("""
                        UPDATE productos 
                        SET stock_prod = stock_prod + %s
                        WHERE pkid_prod = %s
                    """, [cantidad_total_liberar, producto_id])
        
        # Eliminar el combo
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM combos WHERE pkid_combo = %s", [combo_id])
        
        messages.success(request, f'✅ Combo "{nombre_combo}" eliminado exitosamente.')
        
    except Exception as e:
        messages.error(request, f'Error al eliminar combo: {str(e)}')
        logger.error(f"Error al eliminar combo: {str(e)}")
    
    return redirect('Ofertas_V')

@login_required(login_url='login')
def eliminar_promocion_2x1(request, promocion_id):
    """Eliminar una promoción 2x1"""
    try:
        datos = obtener_datos_vendedor_ofertas(request)
        if not datos:
            messages.error(request, "No tienes un negocio activo.")
            return redirect('Ofertas_V')
        
        negocio = datos['negocio_activo']
        
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM promociones_2x1 
                WHERE pkid_promo_2x1 = %s AND fknegocio_id = %s
            """, [promocion_id, negocio.pkid_neg])
        
        messages.success(request, f'✅ Promoción 2x1 eliminada exitosamente.')
        
    except Exception as e:
        messages.error(request, f'Error al eliminar promoción 2x1: {str(e)}')
        logger.error(f"Error al eliminar promoción 2x1: {str(e)}")
    
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
def finalizar_combo_manual(request, combo_id):
    """Finalizar un combo manualmente"""
    if request.method == 'POST':
        try:
            datos = obtener_datos_vendedor_ofertas(request)
            if not datos:
                messages.error(request, "No tienes un negocio activo.")
                return redirect('Ofertas_V')
            
            negocio = datos['negocio_activo']
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE combos 
                    SET estado_combo = 'inactivo'
                    WHERE pkid_combo = %s AND fknegocio_id = %s
                """, [combo_id, negocio.pkid_neg])
            
            messages.success(request, '✅ Combo finalizado manualmente.')
            
        except Exception as e:
            messages.error(request, f'Error al finalizar combo: {str(e)}')
            logger.error(f"Error al finalizar combo: {str(e)}")
    
    return redirect('Ofertas_V')

@login_required(login_url='login')
def finalizar_promocion_2x1_manual(request, promocion_id):
    """Finalizar una promoción 2x1 manualmente"""
    if request.method == 'POST':
        try:
            datos = obtener_datos_vendedor_ofertas(request)
            if not datos:
                messages.error(request, "No tienes un negocio activo.")
                return redirect('Ofertas_V')
            
            negocio = datos['negocio_activo']
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE promociones_2x1 
                    SET estado = 'finalizada'
                    WHERE pkid_promo_2x1 = %s AND fknegocio_id = %s
                """, [promocion_id, negocio.pkid_neg])
            
            messages.success(request, '✅ Promoción 2x1 finalizada manualmente.')
            
        except Exception as e:
            messages.error(request, f'Error al finalizar promoción 2x1: {str(e)}')
            logger.error(f"Error al finalizar promoción 2x1: {str(e)}")
    
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
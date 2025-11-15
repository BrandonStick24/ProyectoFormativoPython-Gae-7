# Software/vendedor_categorias_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import connection

# Importar modelos
from Software.models import (
    Negocios, UsuarioPerfil, AuthUser, Productos, CategoriaProductos, TipoNegocio
)

# Función auxiliar para obtener datos del vendedor
def obtener_datos_vendedor_categorias(request):
    """Función específica para categorías que valida que exista un negocio activo"""
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

def obtener_categorias_por_tiponegocio(tiponegocio_id):
    """Obtener categorías filtradas por tipo de negocio"""
    categorias_filtradas = []
    
    try:
        # Primero intentar obtener de la tabla categorias_tiponegocio
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT cp.pkid_cp, cp.desc_cp 
                FROM categoria_productos cp
                JOIN categorias_tiponegocio ctn ON cp.pkid_cp = ctn.categoria_id
                WHERE ctn.tiponegocio_id = %s AND ctn.es_activa = 1
                ORDER BY cp.desc_cp
            """, [tiponegocio_id])
            
            for row in cursor.fetchall():
                categorias_filtradas.append({
                    'id': row[0],
                    'descripcion': row[1]
                })
        
        # Si no hay categorías específicas, usar categorías generales
        if not categorias_filtradas:
            categorias_generales = CategoriaProductos.objects.all().order_by('desc_cp')
            for categoria in categorias_generales:
                categorias_filtradas.append({
                    'id': categoria.pkid_cp,
                    'descripcion': categoria.desc_cp
                })
                
    except Exception as e:
        # Fallback: usar todas las categorías
        print(f"Error obteniendo categorías por tipo negocio: {e}")
        categorias_generales = CategoriaProductos.objects.all().order_by('desc_cp')
        for categoria in categorias_generales:
            categorias_filtradas.append({
                'id': categoria.pkid_cp,
                'descripcion': categoria.desc_cp
            })
    
    return categorias_filtradas

def obtener_tipos_negocio():
    """Obtener todos los tipos de negocio"""
    tipos_negocio = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM tipo_negocio")
            for row in cursor.fetchall():
                # Asumiendo que la estructura es: [id, descripcion, ...]
                tipos_negocio.append({
                    'id': row[0],
                    'descripcion': row[1] if len(row) > 1 else f"Tipo {row[0]}"
                })
    except Exception as e:
        print(f"Error obteniendo tipos de negocio: {e}")
    
    return tipos_negocio

@login_required(login_url='login')
def gestionar_categorias_tiponegocio(request):
    """Vista para gestionar categorías por tipo de negocio (solo para administración)"""
    datos = obtener_datos_vendedor_categorias(request)
    if not datos:
        return redirect('dash_vendedor')
    
    # Solo permitir si el usuario es administrador o moderador
    # Aquí puedes agregar validación de permisos si es necesario
    
    try:
        tipos_negocio = obtener_tipos_negocio()
        todas_categorias = CategoriaProductos.objects.all().order_by('desc_cp')
        
        # Obtener asignaciones actuales
        asignaciones = []
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ctn.id, ctn.tiponegocio_id, ctn.categoria_id, 
                       tn.desc_tn, cp.desc_cp, ctn.es_activa
                FROM categorias_tiponegocio ctn
                JOIN tipo_negocio tn ON ctn.tiponegocio_id = tn.pkid_tn
                JOIN categoria_productos cp ON ctn.categoria_id = cp.pkid_cp
                ORDER BY tn.desc_tn, cp.desc_cp
            """)
            
            for row in cursor.fetchall():
                asignaciones.append({
                    'id': row[0],
                    'tiponegocio_id': row[1],
                    'categoria_id': row[2],
                    'tipo_negocio_nombre': row[3],
                    'categoria_nombre': row[4],
                    'activa': row[5]
                })
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': datos['negocio_activo'],
            'tipos_negocio': tipos_negocio,
            'todas_categorias': todas_categorias,
            'asignaciones': asignaciones,
        }
        
        return render(request, 'Vendedor/gestion_categorias.html', contexto)
        
    except Exception as e:
        messages.error(request, f"Error al cargar gestión de categorías: {str(e)}")
        return redirect('dash_vendedor')

@login_required(login_url='login')
def asignar_categoria_tiponegocio(request):
    """Vista para asignar categoría a tipo de negocio"""
    if request.method == 'POST':
        datos = obtener_datos_vendedor_categorias(request)
        if not datos:
            return redirect('dash_vendedor')
        
        try:
            tiponegocio_id = request.POST.get('tiponegocio_id')
            categoria_id = request.POST.get('categoria_id')
            
            if not tiponegocio_id or not categoria_id:
                messages.error(request, "Tipo de negocio y categoría son obligatorios.")
                return redirect('gestionar_categorias_tiponegocio')
            
            # Verificar si ya existe la asignación
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM categorias_tiponegocio 
                    WHERE tiponegocio_id = %s AND categoria_id = %s
                """, [tiponegocio_id, categoria_id])
                
                if cursor.fetchone():
                    messages.warning(request, "Esta categoría ya está asignada a este tipo de negocio.")
                    return redirect('gestionar_categorias_tiponegocio')
                
                # Crear la asignación
                cursor.execute("""
                    INSERT INTO categorias_tiponegocio (tiponegocio_id, categoria_id, es_activa)
                    VALUES (%s, %s, 1)
                """, [tiponegocio_id, categoria_id])
            
            messages.success(request, "Categoría asignada exitosamente al tipo de negocio.")
            
        except Exception as e:
            messages.error(request, f"Error al asignar categoría: {str(e)}")
        
        return redirect('gestionar_categorias_tiponegocio')
    
    return redirect('gestionar_categorias_tiponegocio')

@login_required(login_url='login')
def cambiar_estado_asignacion(request, asignacion_id):
    """Vista para activar/desactivar asignación de categoría"""
    if request.method == 'POST':
        datos = obtener_datos_vendedor_categorias(request)
        if not datos:
            return redirect('dash_vendedor')
        
        try:
            nuevo_estado = request.POST.get('nuevo_estado', 0)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE categorias_tiponegocio 
                    SET es_activa = %s 
                    WHERE id = %s
                """, [nuevo_estado, asignacion_id])
            
            estado_texto = "activada" if nuevo_estado == "1" else "desactivada"
            messages.success(request, f"Asignación {estado_texto} exitosamente.")
            
        except Exception as e:
            messages.error(request, f"Error al cambiar estado: {str(e)}")
        
        return redirect('gestionar_categorias_tiponegocio')
    
    return redirect('gestionar_categorias_tiponegocio')

@login_required(login_url='login')
def eliminar_asignacion(request, asignacion_id):
    """Vista para eliminar asignación de categoría"""
    if request.method == 'POST':
        datos = obtener_datos_vendedor_categorias(request)
        if not datos:
            return redirect('dash_vendedor')
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM categorias_tiponegocio WHERE id = %s", [asignacion_id])
            
            messages.success(request, "Asignación eliminada exitosamente.")
            
        except Exception as e:
            messages.error(request, f"Error al eliminar asignación: {str(e)}")
        
        return redirect('gestionar_categorias_tiponegocio')
    
    return redirect('gestionar_categorias_tiponegocio')
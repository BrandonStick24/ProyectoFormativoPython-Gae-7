from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import date
from django.contrib.auth.decorators import login_required
from Software.models import Pedidos, DetallesPedido, ResenasNegocios, AuthUser, UsuarioPerfil, Roles, TipoDocumento, UsuariosRoles, Negocios, TipoNegocio, Productos, CategoriaProductos
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
import json
from django.db import transaction


# ==================== VISTAS PÚBLICAS ====================
def inicio(request):
    return render(request, 'Cliente/Index.html')


from django.db.models import Avg
from .models import Negocios, CategoriaProductos, ResenasNegocios

def principal(request):
    negocios = Negocios.objects.all()
    categorias = CategoriaProductos.objects.all()[:20]
    categoria_principal = CategoriaProductos.objects.filter(desc_cp="Celulares y accesorios").first()
    otras_categorias = CategoriaProductos.objects.exclude(desc_cp="Celulares y accesorios")[:11]
    t_negocios = TipoNegocio.objects.all()
    if categoria_principal:
        categorias_interes = [categoria_principal] + list(otras_categorias)
    else:
        categorias_interes = list(otras_categorias)

    # Negocios mejor calificados (promedio de estrellas de 4 a 5)
    negocios_mejor_calificados = (
        Negocios.objects
        .annotate(promedio=Avg('resenasnegocios__estrellas'))
        .filter(promedio__gte=4)
        .order_by('-promedio')[:10]  # Puedes ajustar la cantidad que se muestra
    )

    contexto = {
        'negocios': negocios,
        'categorias': categorias,
        'categorias_interes': categorias_interes,
        'negocios_mejor_calificados': negocios_mejor_calificados,
        't_negocios': t_negocios
    }

    return render(request, 'Cliente/Principal.html', contexto)


def iniciar_sesion(request):
    # LIMPIAR MENSAJES ANTIGUOS AL CARGAR LA PÁGINA DE LOGIN
    storage = messages.get_messages(request)
    for message in storage:
        pass
    
    if request.method == "POST":
        correo = request.POST.get("correo")
        password = request.POST.get("contrasena")

        try:
            user_obj = AuthUser.objects.get(email=correo)
        except AuthUser.DoesNotExist:
            messages.error(request, "Correo incorrecto.", extra_tags='correo')
            return render(request, "Login_Registro/login.html")

        user = authenticate(request, username=user_obj.username, password=password)
        if not user:
            messages.error(request, "Contraseña incorrecta.", extra_tags='contrasena')
            return render(request, "Login_Registro/login.html")

        try:
            perfil = UsuarioPerfil.objects.get(fkuser=user_obj)
        except UsuarioPerfil.DoesNotExist:
            messages.error(request, "Perfil de usuario no encontrado.", extra_tags='general')
            return render(request, "Login_Registro/login.html")

        rol_usuario = UsuariosRoles.objects.filter(fkperfil=perfil).first()
        if not rol_usuario:
            messages.error(request, "Rol de usuario no definido.", extra_tags='general')
            return render(request, "Login_Registro/login.html")

        rol_desc = rol_usuario.fkrol.desc_rol.upper()

        if rol_desc == 'VENDEDOR':
            negocio = Negocios.objects.filter(fkpropietario_neg=perfil, estado_neg='activo').first()
            if not negocio:
                messages.error(request, "No tienes un negocio activo registrado.", extra_tags='negocio')
                return render(request, "Login_Registro/login.html")
            
            login(request, user)
            messages.success(request, "¡Bienvenido, Vendedor!", extra_tags='general')
            return redirect('dash_vendedor')

        elif rol_desc == 'CLIENTE':
            login(request, user)
            messages.success(request, "¡Bienvenido, Cliente!", extra_tags='general')
            return redirect('cliente_dash')
        
        elif rol_desc == 'MODERADOR':
            login(request, user)
            messages.success(request, "¡Bienvenido, Moderador!", extra_tags='general')
            return render(request, 'Moderador/moderador_dash.html')


        else:
            messages.error(request, "Rol no permitido.", extra_tags='general')
            return render(request, "Login_Registro/login.html")

    return render(request, "Login_Registro/login.html")


def registro_user(request):
    roles = Roles.objects.exclude(desc_rol='MODERADOR')
    tipo_documentos = TipoDocumento.objects.all()

    if request.method == 'POST':
        tipo_doc_id = request.POST.get("tipo_doc")
        doc_user = request.POST.get("documento")
        nombre = request.POST.get("nombre")
        correo = request.POST.get("correo")
        fecha_nac = request.POST.get("fechan")
        contrasena = request.POST.get("contrasena")
        confirmar_contrasena = request.POST.get("confirmar_contrasena")
        rol_id = request.POST.get("rol")
        
        errores = False

        try:
            fecha_nac_date = date.fromisoformat(fecha_nac)
            hoy = date.today()
            fecha_limite = hoy.replace(year=hoy.year - 18)

            if fecha_nac_date > fecha_limite:
                messages.error(request, "Debes ser mayor de 18 años para registrarte.", extra_tags='fechan')
                errores = True
        except:
            messages.error(request, "Fecha de nacimiento inválida.", extra_tags='fechan')
            errores = True

        if contrasena != confirmar_contrasena:
            messages.error(request, "Las contraseñas no coinciden.", extra_tags='confirmar_contrasena')
            errores = True

        if len(contrasena) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.", extra_tags='contrasena')
            errores = True

        if UsuarioPerfil.objects.filter(doc_user=doc_user).exists():
            messages.error(request, "El número de documento ya está registrado.", extra_tags='documento')
            errores = True

        if User.objects.filter(email=correo).exists():
            messages.error(request, "El correo electrónico ya está registrado.", extra_tags='correo')
            errores = True

        if errores:
            return render(request, 'Login_Registro/registro.html', {
                'roles': roles,
                'tipo_documentos': tipo_documentos
            })

        auth_user = AuthUser.objects.create(
            username=correo, 
            first_name=nombre,
            last_name='',
            email=correo,
            password=make_password(contrasena),
            is_active=1,
            is_staff=0,
            is_superuser=0,
            date_joined=timezone.now()
        )

        perfil = UsuarioPerfil.objects.create(
            fkuser=auth_user,
            fktipodoc_user_id=tipo_doc_id,
            doc_user=doc_user,
            fechanac_user=fecha_nac,
            estado_user='activo',
            fecha_creacion=timezone.now()
        )

        rol = Roles.objects.get(pk=rol_id)
        UsuariosRoles.objects.create(
            fkperfil=perfil,
            fkrol=rol
        )
        
        if rol.desc_rol.upper() == 'VENDEDOR':
            request.session['perfil_registro_negocio'] = perfil.pk
            return redirect('registro_negocios')

        messages.success(request, "Usuario registrado exitosamente.")
        return redirect('inicio')

    return render(request, 'Login_Registro/registro.html', {
        'roles': roles,
        'tipo_documentos': tipo_documentos
    })


def registro_negocio(request):
    tipo_negocios = TipoNegocio.objects.all()

    perfil_id = request.session.get('perfil_registro_negocio')

    if not perfil_id:
        messages.error(request, "Primero debes registrarte.")
        return redirect('registro')

    propietario = UsuarioPerfil.objects.get(pk=perfil_id)

    if request.method == 'POST':
        nit = request.POST.get('nit')
        nombre = request.POST.get('nom_neg')
        direccion = request.POST.get('direcc_neg')
        descripcion = request.POST.get('desc_neg')
        tipo_neg = request.POST.get('fktiponeg_neg')
        imagen = request.FILES.get('img_neg')

        Negocios.objects.create(
            nit_neg=nit,
            nom_neg=nombre,
            direcc_neg=direccion,
            desc_neg=descripcion,
            fktiponeg_neg_id=tipo_neg,
            fkpropietario_neg=propietario,
            estado_neg='activo',
            fechacreacion_neg=timezone.now(),
            img_neg=imagen
        )

        del request.session['perfil_registro_negocio']  # Limpia la sesión después de usarla

        messages.success(request, "Negocio registrado exitosamente. Ahora inicia sesión.")
        return redirect('login')

    return render(request, 'Login_Registro/registroNegocio.html', {
        'tipo_negocios': tipo_negocios
    })

#=====================================================================================================
# ========================================== VISTAS CLIENTE ==========================================
#=====================================================================================================

@login_required(login_url='login')
def cliente_dash(request):
    negocios = Negocios.objects.all()
    categorias = CategoriaProductos.objects.all()[:20]
    categoria_principal = CategoriaProductos.objects.filter(desc_cp="Celulares y accesorios").first()
    otras_categorias = CategoriaProductos.objects.exclude(desc_cp="Celulares y accesorios")[:11]
    t_negocios = TipoNegocio.objects.all()
    negocios_mejor_calificados = (
        Negocios.objects
        .annotate(promedio=Avg('resenasnegocios__estrellas'))
        .filter(promedio__gte=4)
        .order_by('-promedio')[:10]
    )
    if categoria_principal:
        categorias_interes = [categoria_principal] + list(otras_categorias)
    else:
        categorias_interes = list(otras_categorias)

    try:
        perfil = UsuarioPerfil.objects.get(fkuser__username=request.user.username)
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, "Perfil de usuario no encontrado.")
        return redirect('inicio')
    
    contexto = {
        'nombre' : request.user.first_name,
        'perfil' : perfil,
        'negocios': negocios,
        't_negocios': t_negocios,
        'categorias': categorias,
        'categorias_interes': categorias_interes,
        'negocios_mejor_calificados': negocios_mejor_calificados
    }
    return render(request, 'Cliente/Cliente.html', contexto)

#==================== PEDIDOS =====================
from django.shortcuts import redirect, get_object_or_404
from .models import Carrito, CarritoItem, Productos, UsuarioPerfil
from django.utils import timezone

@login_required(login_url='login')
def agregar_al_carrito(request, producto_id):
    if not request.user.is_authenticated:
        return redirect('login')
    auth_user = get_object_or_404(AuthUser, username=request.user.username)
    usuario_perfil = get_object_or_404(UsuarioPerfil, fkuser=auth_user)
    
    producto = get_object_or_404(Productos, pkid_prod=producto_id)

    # Obtener o crear carrito del usuario
    carrito, created = Carrito.objects.get_or_create(
        fkusuario_carrito=usuario_perfil
    )

    # Verificar si el producto ya está en el carrito
    item, created = CarritoItem.objects.get_or_create(
        fkcarrito=carrito,
        fkproducto=producto,
        fknegocio=producto.fknegocioasociado_prod,
        defaults={'cantidad': 1, 'precio_unitario': producto.precio_prod}
    )

    if not created:
        item.cantidad += 1
        item.save()

    return redirect('ver_carrito')

@login_required(login_url='login')
def agregar_carrito_ajax(request):
    import json
    from django.http import JsonResponse

    if request.method == "POST":
        data = json.loads(request.body)
        prod_id = data.get('prod_id')
        cantidad = data.get('cantidad', 1)

        # Usamos directamente request.user
        try:
            auth_user = AuthUser.objects.get(username=request.user.username)
            usuario_perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
        except UsuarioPerfil.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Perfil no encontrado'})

        producto = get_object_or_404(Productos, pkid_prod=prod_id)

        carrito, created = Carrito.objects.get_or_create(fkusuario_carrito=usuario_perfil)

        item, created = CarritoItem.objects.get_or_create(
            fkcarrito=carrito,
            fkproducto=producto,
            fknegocio=producto.fknegocioasociado_prod,
            defaults={'cantidad': cantidad, 'precio_unitario': producto.precio_prod}
        )

        if not created:
            item.cantidad += cantidad
            item.save()

        return JsonResponse({'success': True})

from django.utils import timezone
from decimal import Decimal
from collections import defaultdict
from django.shortcuts import redirect
from .models import Pedidos, DetallesPedido, PagosNegocios, CarritoItem

from django.shortcuts import redirect
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import CarritoItem, Pedidos, DetallesPedido, PagosNegocios, UsuarioPerfil

from django.db import transaction

@login_required(login_url='login')
def procesar_pago(request):
    auth_user = AuthUser.objects.get(username=request.user.username)
    usuario_perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
    carrito_items = CarritoItem.objects.filter(fkcarrito__fkusuario_carrito=usuario_perfil)

    if not carrito_items.exists():
        return redirect('carrito')

    negocios_items = {}
    for item in carrito_items:
        negocio = item.fknegocio
        if negocio not in negocios_items:
            negocios_items[negocio] = []
        negocios_items[negocio].append(item)

    try:
        with transaction.atomic():  # <-- Inicio de transacción
            for negocio, items in negocios_items.items():
                total_pedido = sum(item.cantidad * item.precio_unitario for item in items)
                pedido = Pedidos.objects.create(
                    fkusuario_pedido=usuario_perfil,
                    fknegocio_pedido=negocio,
                    estado_pedido='pendiente',  # inicial
                    total_pedido=total_pedido,
                    fecha_pedido=timezone.now(),
                    fecha_actualizacion=timezone.now()
                )

                pago = PagosNegocios.objects.create(
                    fkpedido=pedido,
                    fknegocio=negocio,
                    monto=total_pedido,
                    estado_pago='pendiente'  # inicial
                )

                # --- ACTUALIZAR ESTADOS A CONFIRMADO ---
                pedido.estado_pedido = 'confirmado'
                pedido.save()
                pago.estado_pago = 'pagado'
                pago.save()

                for item in items:
                    producto = item.fkproducto
                    if producto.stock_prod < item.cantidad:
                        raise ValueError(f"No hay suficiente stock de {producto.nom_prod}.")

                    DetallesPedido.objects.create(
                        fkpedido_detalle=pedido,
                        fkproducto_detalle=producto,
                        cantidad_detalle=item.cantidad,
                        precio_unitario=item.precio_unitario
                    )

                    producto.stock_prod -= item.cantidad
                    producto.save()

            carrito_items.delete()

    except Exception as e:
        messages.error(request, f"Error al procesar el pago: {str(e)}")
        return redirect('carrito')

    return redirect('pago_exitoso')


@login_required(login_url='login')
def pago_exitoso(request):
    return render(request, 'Cliente/pago_exitoso.html')

@login_required(login_url='login')
def ver_carrito(request):
    # Obtener el AuthUser correspondiente al request.user
    auth_user = get_object_or_404(AuthUser, username=request.user.username)
    
    # Obtener perfil de usuario
    usuario_perfil = get_object_or_404(UsuarioPerfil, fkuser=auth_user)
    
    # Obtener carrito del usuario
    carrito = get_object_or_404(Carrito, fkusuario_carrito=usuario_perfil)
    carrito_items = CarritoItem.objects.filter(fkcarrito=carrito)

    # Calculamos subtotales
    for item in carrito_items:
        item.subtotal = item.cantidad * item.precio_unitario

    return render(request, 'Cliente/ver_carrito.html', {'carrito_items': carrito_items})



@login_required(login_url='login')
def detalle_negocio(request, id):
    # Obtener negocio y propietario
    negocio = get_object_or_404(Negocios, pkid_neg=id)
    propietario = negocio.fkpropietario_neg
    tipo_negocio = negocio.fktiponeg_neg

    # Productos del negocio
    productos = Productos.objects.filter(fknegocioasociado_prod=negocio).select_related('fkcategoria_prod')

    # Perfil del cliente logueado
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser__username=request.user.username)
    except UsuarioPerfil.DoesNotExist:
        perfil_cliente = None

    # Reseñas del negocio directamente desde la BD
    resenas = ResenasNegocios.objects.filter(fknegocio_resena=negocio).select_related('fkusuario_resena__fkuser')

    contexto = {
        'negocio': negocio,
        'propietario': propietario,
        'productos': productos,
        'tipo_negocio': tipo_negocio,
        'perfil_cliente': perfil_cliente,
        'resenas': resenas,   # directamente el queryset
        'nombre': request.user.first_name,
    }

    return render(request, 'Cliente/detalle_neg.html', contexto)

@login_required
def guardar_resena(request):
    if request.method == 'POST':
        estrellas = int(request.POST.get('estrellas', 5))
        comentario = request.POST.get('comentario', '')
        negocio_id = request.POST.get('fknegocio_resena')

        # Obtener instancia de AuthUser
        auth_user = get_object_or_404(AuthUser, username=request.user.username)

        # Obtener perfil del usuario logueado
        usuario = get_object_or_404(UsuarioPerfil, fkuser=auth_user)

        # Obtener negocio
        negocio = get_object_or_404(Negocios, pkid_neg=negocio_id)

        # Crear y guardar la reseña
        resena = ResenasNegocios(
        fkusuario_resena=usuario,
        fknegocio_resena=negocio,
        estrellas=int(estrellas),  # directamente entero
        comentario=comentario,
        fecha_resena=timezone.now(),
        estado_resena='activa'
        )
        resena.save()

        return redirect('detalle_negocio', id=negocio_id)
#=================================================================================



# ==================== FUNCIONES AUXILIARES VENDEDOR ACTUALIZADAS ====================
def obtener_datos_vendedor(request):
    """Función auxiliar para obtener datos del vendedor con negocio seleccionado"""
    try:
        from Software.models import AuthUser
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
            'negocio_activo': negocio_seleccionado,  # Cambiamos nombre por compatibilidad
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
            nit = request.POST.get('nit_neg')  # ← CORREGIDO: era 'nit' pero debería ser 'nit_neg'
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
        productos = []
        try:
            from Software.models import Productos
            productos = Productos.objects.filter(fknegocioasociado_prod=negocio)
        except ImportError:
            messages.info(request, "El sistema de productos está siendo configurado.")
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': negocio,
            'productos': productos,
        }
        return render(request, 'Vendedor/Crud_V.html', contexto)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('inicio')


# ==================== VISTAS VENDEDOR - OFERTAS ====================
@login_required(login_url='login')
def Ofertas_V(request):
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
        return render(request, 'Vendedor/Ofertas_V.html', contexto)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('inicio')


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
        return render(request, 'Vendedor/Stock_V.html', contexto)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('inicio')


# ==================== VISTAS VENDEDOR - CREAR PRODUCTO ====================
@login_required(login_url='login')
def crear_producto_P(request):
    """Vista para crear nuevo producto con categorías de texto libre"""
    if request.method == 'POST':
        try:
            auth_user = AuthUser.objects.get(username=request.user.username)
            perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
            
            # USAR EL NEGOCIO SELECCIONADO EN SESIÓN en lugar de cualquier negocio activo
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
            categoria_texto = request.POST.get('categoria_prod', '').strip()
            estado_prod = request.POST.get('estado_prod', 'disponible')
            
            # Validar campos obligatorios
            if not nom_prod or not precio_prod or not categoria_texto:
                messages.error(request, "Nombre, precio y categoría son obligatorios.")
                return redirect('Crud_V')
            
            # BUSCAR O CREAR CATEGORÍA
            from Software.models import CategoriaProductos
            categoria, created = CategoriaProductos.objects.get_or_create(
                desc_cp=categoria_texto,
                defaults={
                    'desc_cp': categoria_texto,
                    'fecha_creacion': timezone.now()
                }
            )
            
            # Crear el producto sin imagen primero
            from Software.models import Productos
            producto = Productos.objects.create(
                nom_prod=nom_prod,
                precio_prod=precio_prod,
                desc_prod=desc_prod or "",
                fkcategoria_prod=categoria,
                stock_prod=int(stock_prod) if stock_prod else 0,
                stock_minimo=5,
                fknegocioasociado_prod=negocio,
                estado_prod=estado_prod,
                fecha_creacion=timezone.now()
            )
            
            # Si hay imagen, guardarla manualmente
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
    """Vista para editar producto existente"""
    if request.method == 'POST':
        try:
            from Software.models import Productos, CategoriaProductos, AuthUser
            from Software.models import UsuarioPerfil, Negocios
            
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
            
            # Obtener datos del formulario
            nom_prod = request.POST.get('nom_prod')
            precio_prod = request.POST.get('precio_prod')
            desc_prod = request.POST.get('desc_prod')
            stock_prod = request.POST.get('stock_prod')
            img_prod = request.FILES.get('img_prod')
            categoria_texto = request.POST.get('categoria_prod', '').strip()
            estado_prod = request.POST.get('estado_prod', 'disponible')
            
            # Validar campos obligatorios
            if not nom_prod or not precio_prod or not categoria_texto:
                messages.error(request, "Nombre, precio y categoría son obligatorios.")
                return redirect('Crud_V')
            
            # BUSCAR O CREAR CATEGORÍA
            categoria, created = CategoriaProductos.objects.get_or_create(
                desc_cp=categoria_texto,
                defaults={
                    'desc_cp': categoria_texto,
                    'fecha_creacion': timezone.now()
                }
            )
            
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
                
                # Crear carpeta productos si no existe
                productos_dir = 'media/productos'
                if not os.path.exists(productos_dir):
                    os.makedirs(productos_dir)
                
                # Generar nombre único
                ext = os.path.splitext(img_prod.name)[1]
                filename = f"producto_{uuid4()}{ext}"
                filepath = os.path.join(productos_dir, filename)
                
                # Guardar archivo
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
    """Vista para obtener datos del producto en formato JSON (para el modal de editar)"""
    try:
        from Software.models import Productos, AuthUser, UsuarioPerfil, Negocios
        
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
        
        # 🔥 **CORRECCIÓN PRINCIPAL**: Convertir imagen a string para JSON
        img_prod_actual = ""
        if producto.img_prod:
            # Si es un ImageFieldFile, obtener el nombre del archivo
            if hasattr(producto.img_prod, 'name'):
                img_prod_actual = producto.img_prod.name
            else:
                # Si ya es un string, usarlo directamente
                img_prod_actual = str(producto.img_prod)
        
        # Preparar datos para JSON
        datos_producto = {
            'pkid_prod': producto.pkid_prod,
            'nom_prod': producto.nom_prod,
            'precio_prod': str(producto.precio_prod),
            'desc_prod': producto.desc_prod or '',
            'stock_prod': producto.stock_prod or 0,
            'estado_prod': producto.estado_prod or 'disponible',
            'categoria_prod': producto.fkcategoria_prod.desc_cp,
            'img_prod_actual': img_prod_actual  # 🔥 Ahora es string, no objeto
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
    """Vista para eliminar producto"""
    if request.method == 'POST':
        try:
            from Software.models import Productos, AuthUser, UsuarioPerfil, Negocios
            
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
            producto.delete()
            
            messages.success(request, f"Producto '{nombre_producto}' eliminado exitosamente.")
            
        except Productos.DoesNotExist:
            messages.error(request, "El producto no existe o no tienes permisos para eliminarlo.")
        except Negocios.DoesNotExist:
            messages.error(request, "El negocio seleccionado no existe o no tienes permisos.")
        except Exception as e:
            messages.error(request, f"Error al eliminar producto: {str(e)}")
    
    return redirect('Crud_V')

# ==================== VISTAS VENDEDOR - NEGOCIOS ====================
@login_required(login_url='login')
def Negocios_V(request):
    """Vista para gestionar múltiples negocios del vendedor"""
    try:
        datos = obtener_datos_vendedor(request)
        if not datos:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('inicio')
        
        # Obtener todos los negocios del vendedor
        negocios = Negocios.objects.filter(fkpropietario_neg=datos['perfil'])
        tipos_negocio = TipoNegocio.objects.all()  # ← AÑADIR ESTA LÍNEA
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': datos['negocio_activo'],
            'negocios': negocios,
            'tipos_negocio': tipos_negocio,  # ← AÑADIR ESTA LÍNEA
        }
        return render(request, 'Vendedor/Negocios_V.html', contexto)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('inicio')

# ==================== CERRAR SESION ====================
@login_required(login_url='login')
def cerrar_sesion(request):
    logout(request)
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("principal")
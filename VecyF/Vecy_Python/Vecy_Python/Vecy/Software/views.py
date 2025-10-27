from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import date
from django.contrib.auth.decorators import login_required
from Software.models import AuthUser, UsuarioPerfil, Roles, TipoDocumento, UsuariosRoles, Negocios, TipoNegocio
from django.http import JsonResponse


# ==================== VISTAS PÚBLICAS ====================
def inicio(request):
    return render(request, 'Cliente/Index.html')


def principal(request):
    negocios = Negocios.objects.all()
    return render(request, 'Cliente/Principal.html', {'negocios': negocios})


def iniciar_sesion(request):
    if request.method == "POST":
        correo = request.POST.get("correo")
        password = request.POST.get("contrasena")

        # Intentamos obtener el usuario AuthUser
        try:
            user_obj = AuthUser.objects.get(email=correo)
        except AuthUser.DoesNotExist:
            messages.error(request, "Correo o contraseña incorrectos.")
            return render(request, "Login_Registro/login.html")

        # Validamos la contraseña
        user = authenticate(request, username=user_obj.username, password=password)
        if not user:
            messages.error(request, "Correo o contraseña incorrectos.")
            return render(request, "Login_Registro/login.html")

        # Obtenemos el perfil asociado
        try:
            perfil = UsuarioPerfil.objects.get(fkuser=user_obj)
        except UsuarioPerfil.DoesNotExist:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('inicio')

        # Obtenemos el rol del usuario
        rol_usuario = UsuariosRoles.objects.filter(fkperfil=perfil).first()
        if not rol_usuario:
            messages.error(request, "Rol de usuario no definido.")
            return redirect('inicio')

        rol_desc = rol_usuario.fkrol.desc_rol.upper()

        # Validación según rol
        if rol_desc == 'VENDEDOR':
            # Revisamos que tenga un negocio activo
            negocio = Negocios.objects.filter(fkpropietario_neg=perfil, estado_neg='activo').first()
            if not negocio:
                messages.error(request, "No tienes un negocio activo registrado.")
                return redirect('registro_negocio')
            
            login(request, user)  # Iniciamos sesión solo si todo está OK
            messages.success(request, "¡Bienvenido, Vendedor!")
            return redirect('dash_vendedor')

        elif rol_desc == 'CLIENTE':
            login(request, user)  # Solo iniciamos sesión si es cliente
            messages.success(request, "¡Bienvenido, Cliente!")
            return redirect('cliente_dash')

        else:
            messages.error(request, "Rol no permitido.")
            return redirect('inicio')

    # GET
    return render(request, "Login_Registro/login.html")


def registro_user(request):
    roles = Roles.objects.exclude(desc_rol='Moderador')
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


# ==================== FUNCIONES AUXILIARES VENDEDOR ====================
def obtener_datos_vendedor(request):
    """Función auxiliar para obtener datos del vendedor"""
    try:
        from Software.models import AuthUser
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
        negocio = Negocios.objects.filter(fkpropietario_neg=perfil, estado_neg='activo').first()
        
        return {
            'nombre_usuario': auth_user.first_name,
            'perfil': perfil,
            'negocio_activo': negocio,
        }
    except (AuthUser.DoesNotExist, UsuarioPerfil.DoesNotExist):
        return {}


# ==================== VISTAS CLIENTE ====================
@login_required(login_url='login')
def cliente_dash(request):
    negocios = Negocios.objects.all()
    t_negocios = TipoNegocio.objects.all()
    try:
        perfil = UsuarioPerfil.objects.get(fkuser__username=request.user.username)
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, "Perfil de usuario no encontrado.")
        return redirect('inicio')
    
    contexto = {
        'nombre' : request.user.first_name,
        'perfil' : perfil,
        'negocios': negocios,
        't_negocios': t_negocios
    }
    negocios = Negocios.objects.all()
    return render(request, 'Cliente/Cliente.html', contexto)


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
            # CORRECCIÓN: Obtener el AuthUser correcto
            from Software.models import AuthUser
            auth_user = AuthUser.objects.get(username=request.user.username)
            perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
            
            negocio = Negocios.objects.get(fkpropietario_neg=perfil, estado_neg='activo')
            
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
            
            # Manejar la imagen - GUARDAR SOLO EL NOMBRE
            img_prod_name = None
            if img_prod:
                # Solo guardamos el nombre del archivo en la BD
                img_prod_name = img_prod.name
            
            # Crear el producto
            from Software.models import Productos
            producto = Productos.objects.create(
                nom_prod=nom_prod,
                precio_prod=precio_prod,
                desc_prod=desc_prod or "",
                fkcategoria_prod=categoria,
                stock_prod=int(stock_prod) if stock_prod else 0,
                stock_minimo=5,
                fknegocioasociado_prod=negocio,
                img_prod=img_prod_name,  # Solo el nombre, no el path completo
                estado_prod=estado_prod,
                fecha_creacion=timezone.now()
            )
            
            # Si hay imagen, guardarla manualmente
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
                
                # Actualizar el producto con el nombre del archivo guardado
                producto.img_prod = f"productos/{filename}"
                producto.save()
            
            messages.success(request, f"Producto '{nom_prod}' creado exitosamente.")
            return redirect('Crud_V')
            
        except Exception as e:
            # Debug detallado
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
            
            # Obtener el producto
            producto = Productos.objects.get(pkid_prod=producto_id)
            
            # Verificar que el producto pertenezca al negocio del usuario
            auth_user = AuthUser.objects.get(username=request.user.username)
            perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
            negocio = Negocios.objects.get(fkpropietario_neg=perfil, estado_neg='activo')
            
            if producto.fknegocioasociado_prod != negocio:
                messages.error(request, "No tienes permisos para editar este producto.")
                return redirect('Crud_V')
            
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
            messages.error(request, "El producto no existe.")
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
        negocio = Negocios.objects.get(fkpropietario_neg=perfil, estado_neg='activo')
        
        producto = Productos.objects.get(
            pkid_prod=producto_id, 
            fknegocioasociado_prod=negocio
        )
        
        # Preparar datos para JSON
        datos_producto = {
            'pkid_prod': producto.pkid_prod,
            'nom_prod': producto.nom_prod,
            'precio_prod': str(producto.precio_prod),
            'desc_prod': producto.desc_prod or '',
            'stock_prod': producto.stock_prod or 0,
            'estado_prod': producto.estado_prod or 'disponible',
            'categoria_prod': producto.fkcategoria_prod.desc_cp,
            'img_prod_actual': producto.img_prod or ''
        }
        
        return JsonResponse(datos_producto)
        
    except Productos.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==================== VISTAS VENDEDOR - ELIMINAR PRODUCTO ====================
@login_required(login_url='login')
def eliminar_producto_P(request, producto_id):
    """Vista para eliminar producto"""
    if request.method == 'POST':
        try:
            from Software.models import Productos, AuthUser, UsuarioPerfil, Negocios
            
            # Verificar permisos
            auth_user = AuthUser.objects.get(username=request.user.username)
            perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
            negocio = Negocios.objects.get(fkpropietario_neg=perfil, estado_neg='activo')
            
            # Obtener el producto y verificar que pertenezca al negocio del usuario
            producto = Productos.objects.get(
                pkid_prod=producto_id, 
                fknegocioasociado_prod=negocio
            )
            
            nombre_producto = producto.nom_prod
            producto.delete()
            
            messages.success(request, f"Producto '{nombre_producto}' eliminado exitosamente.")
            
        except Productos.DoesNotExist:
            messages.error(request, "El producto no existe o no tienes permisos para eliminarlo.")
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
        tipos_negocio = TipoNegocio.objects.all()
        
        contexto = {
            'nombre': datos['nombre_usuario'],
            'perfil': datos['perfil'],
            'negocio_activo': datos['negocio_activo'],
            'negocios': negocios,
            'tipos_negocio': tipos_negocio,
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
    return redirect("inicio")
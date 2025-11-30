from google import genai
import json
import os
from pathlib import Path
from django.apps import apps
from django.db.models import Count, Q

class GeminiAssistant:
    def __init__(self):
        self._cargar_variables_entorno()
        self.api_key = os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY no encontrada")
        
        self.client = genai.Client(api_key=self.api_key)
        print("Asistente Gemini iniciado")
        
        self.conversacion_historial = []
    
    def _cargar_variables_entorno(self):
        try:
            ruta_env = Path(__file__).parent.parent.parent / '.env'
            if ruta_env.exists():
                with open(ruta_env, 'r', encoding='utf-8') as f:
                    for linea in f:
                        linea = linea.strip()
                        if linea and not linea.startswith('#') and '=' in linea:
                            key, value = linea.split('=', 1)
                            os.environ[key.strip()] = value.strip()
        except Exception as e:
            print(f"Error .env: {e}")
    
    def _convertir_markdown_a_html(self, texto):
        if not texto:
            return texto
        
        texto = texto.replace('**', '<strong>')
        strong_count = texto.count('<strong>')
        for i in range(strong_count):
            texto = texto.replace('<strong>', '</strong>', 1)
            texto = texto.replace('</strong>', '<strong>', 1)
        
        texto = texto.replace('*', '<em>')
        em_count = texto.count('<em>')
        for i in range(em_count):
            texto = texto.replace('<em>', '</em>', 1)
            texto = texto.replace('</em>', '<em>', 1)
        
        texto = texto.replace('`', '<code>')
        code_count = texto.count('<code>')
        for i in range(code_count):
            texto = texto.replace('<code>', '</code>', 1)
            texto = texto.replace('</code>', '<code>', 1)
        
        texto = texto.replace('\n', '<br>')
        
        return texto
    
    def _buscar_productos_inteligente(self, consulta, productos):
        consulta_lower = consulta.lower()
        productos_encontrados = []
        
        palabras_clave = {
            'audifonos': ['audífonos', 'audifonos', 'headphones', 'auriculares', 'sonido', 'audio'],
            'helados': ['helado', 'heladería', 'postre', 'crema'],
            'electronica': ['electrónica', 'tecnología', 'tecnologia', 'gadgets'],
            'ropa': ['vestuario', 'moda', 'camisa', 'pantalon'],
            'comida': ['alimento', 'comestible', 'restaurante', 'cocina']
        }
        
        for producto in productos:
            nombre_lower = producto['nombre'].lower()
            descripcion_lower = (producto['descripcion'] or '').lower()
            categoria_lower = producto['categoria'].lower()
            negocio_lower = producto['negocio'].lower()
            
            encontrado = False
            
            if consulta_lower in nombre_lower or consulta_lower in descripcion_lower:
                encontrado = True
            
            for palabra_principal, sinonimos in palabras_clave.items():
                if (consulta_lower in palabra_principal or 
                    any(sinonimo in consulta_lower for sinonimo in sinonimos)):
                    
                    if (palabra_principal in nombre_lower or 
                        any(sinonimo in nombre_lower for sinonimo in sinonimos) or
                        palabra_principal in categoria_lower or
                        any(sinonimo in categoria_lower for sinonimo in sinonimos)):
                        encontrado = True
            
            if consulta_lower in negocio_lower:
                encontrado = True
            
            if encontrado:
                productos_encontrados.append(producto)
        
        return productos_encontrados
    
    def _obtener_datos_reales_bd(self, user_id=None):
        try:
            Productos = apps.get_model('Software', 'Productos')
            CategoriaProductos = apps.get_model('Software', 'CategoriaProductos')
            Negocios = apps.get_model('Software', 'Negocios')
            Carrito = apps.get_model('Software', 'Carrito')
            CarritoItem = apps.get_model('Software', 'CarritoItem')
            Pedidos = apps.get_model('Software', 'Pedidos')
            Promociones = apps.get_model('Software', 'Promociones')
            Favoritos = apps.get_model('Software', 'Favoritos')
            VariantesProducto = apps.get_model('Software', 'VariantesProducto')
            
            datos_reales = {
                "productos": [],
                "categorias": [],
                "negocios": [],
                "ofertas_activas": [],
                "carrito_usuario": {},
                "pedidos_recientes": [],
                "favoritos_usuario": [],
                "variantes_productos": {}
            }
            
            productos = Productos.objects.select_related(
                'fkcategoria_prod', 'fknegocioasociado_prod'
            ).filter(estado_prod='disponible')
            
            for p in productos:
                producto_data = {
                    "id": p.pkid_prod,
                    "nombre": p.nom_prod,
                    "precio": float(p.precio_prod),
                    "categoria": p.fkcategoria_prod.desc_cp if p.fkcategoria_prod else "Sin categoría",
                    "categoria_id": p.fkcategoria_prod.pkid_cp if p.fkcategoria_prod else None,
                    "negocio": p.fknegocioasociado_prod.nom_neg if p.fknegocioasociado_prod else "Sin negocio",
                    "negocio_id": p.fknegocioasociado_prod.pkid_neg if p.fknegocioasociado_prod else None,
                    "descripcion": p.desc_prod or "",
                    "stock": p.stock_prod or 0,
                    "imagen": p.img_prod.url if p.img_prod else None,
                    "estado": p.estado_prod,
                    "tiene_variantes": False
                }
                
                variantes = VariantesProducto.objects.filter(
                    producto_id=p.pkid_prod, 
                    estado_variante='activa'
                )
                
                if variantes.exists():
                    producto_data["tiene_variantes"] = True
                    variantes_data = []
                    for v in variantes:
                        variante_info = {
                            "id": v.id_variante,
                            "nombre": v.nombre_variante,
                            "precio_adicional": float(v.precio_adicional),
                            "precio_total": float(p.precio_prod) + float(v.precio_adicional),
                            "stock": v.stock_variante,
                            "sku": v.sku_variante,
                            "imagen": v.imagen_variante.url if v.imagen_variante else None
                        }
                        variantes_data.append(variante_info)
                    
                    datos_reales["variantes_productos"][str(p.pkid_prod)] = variantes_data
                
                datos_reales["productos"].append(producto_data)
            
            categorias = CategoriaProductos.objects.all()
            for c in categorias:
                datos_reales["categorias"].append({
                    "id": c.pkid_cp,
                    "nombre": c.desc_cp
                })
            
            negocios = Negocios.objects.filter(estado_neg='activo')
            for n in negocios:
                datos_reales["negocios"].append({
                    "id": n.pkid_neg,
                    "nombre": n.nom_neg,
                    "categoria": n.fktiponeg_neg.desc_tiponeg if n.fktiponeg_neg else "Sin categoría",
                    "direccion": n.direcc_neg,
                    "imagen": n.img_neg.url if n.img_neg else None
                })
            
            from django.utils import timezone
            hoy = timezone.now().date()
            ofertas = Promociones.objects.filter(
                estado_promo='activa',
                fecha_inicio__lte=hoy,
                fecha_fin__gte=hoy
            ).select_related('fkproducto')
            
            for o in ofertas:
                if o.fkproducto:
                    datos_reales["ofertas_activas"].append({
                        "producto": o.fkproducto.nom_prod,
                        "titulo": o.titulo_promo,
                        "descuento": float(o.porcentaje_descuento) if o.porcentaje_descuento else 0,
                        "precio_original": float(o.fkproducto.precio_prod),
                        "precio_final": float(o.fkproducto.precio_prod) * (1 - (float(o.porcentaje_descuento) / 100)) if o.porcentaje_descuento else float(o.fkproducto.precio_prod)
                    })
            
            if user_id:
                try:
                    carrito = Carrito.objects.filter(fkusuario_carrito_id=user_id).first()
                    if carrito:
                        items_carrito = CarritoItem.objects.filter(fkcarrito=carrito).select_related('fkproducto')
                        total_items = 0
                        total_precio = 0
                        items_detalle = []
                        
                        for item in items_carrito:
                            total_items += item.cantidad
                            total_precio += float(item.precio_unitario) * item.cantidad
                            items_detalle.append({
                                "producto": item.fkproducto.nom_prod,
                                "cantidad": item.cantidad,
                                "precio_unitario": float(item.precio_unitario),
                                "subtotal": float(item.precio_unitario) * item.cantidad,
                                "variante_seleccionada": item.variante_seleccionada,
                                "variante_id": item.variante_id
                            })
                        
                        datos_reales["carrito_usuario"] = {
                            "total_items": total_items,
                            "total_precio": total_precio,
                            "items": items_detalle
                        }
                except Exception as e:
                    print(f"Error obteniendo carrito: {e}")
            
            if user_id:
                try:
                    pedidos = Pedidos.objects.filter(
                        fkusuario_pedido_id=user_id
                    ).order_by('-fecha_pedido')
                    
                    for ped in pedidos:
                        datos_reales["pedidos_recientes"].append({
                            "id": ped.pkid_pedido,
                            "estado": ped.estado_pedido,
                            "total": float(ped.total_pedido),
                            "fecha": ped.fecha_pedido.strftime("%d/%m/%Y"),
                            "negocio": ped.fknegocio_pedido.nom_neg if ped.fknegocio_pedido else "Sin negocio"
                        })
                except Exception as e:
                    print(f"Error obteniendo pedidos: {e}")
            
            if user_id:
                try:
                    favoritos = Favoritos.objects.filter(
                        fkusuario_id=user_id
                    ).select_related('fkproducto')
                    
                    for fav in favoritos:
                        datos_reales["favoritos_usuario"].append({
                            "producto_id": fav.fkproducto.pkid_prod,
                            "nombre": fav.fkproducto.nom_prod,
                            "precio": float(fav.fkproducto.precio_prod),
                            "fecha_agregado": fav.fecha_agregado.strftime("%d/%m/%Y")
                        })
                except Exception as e:
                    print(f"Error obteniendo favoritos: {e}")
            
            print(f"Datos BD: {len(datos_reales['productos'])} productos, {len(datos_reales['favoritos_usuario'])} favoritos")
            return datos_reales
            
        except Exception as e:
            print(f"Error obteniendo datos BD: {e}")
            return {"productos": [], "categorias": [], "negocios": [], "ofertas_activas": [], "favoritos_usuario": [], "variantes_productos": {}}
    
    def obtener_respuesta_interactiva(self, consulta_usuario, user_id=None):
        try:
            print(f"Procesando: {consulta_usuario}")
            
            datos_reales = self._obtener_datos_reales_bd(user_id)
            
            productos_encontrados = self._buscar_productos_inteligente(consulta_usuario, datos_reales["productos"])
            
            datos_reales["productos_encontrados"] = productos_encontrados
            
            self.conversacion_historial.append(f"Usuario: {consulta_usuario}")
            if len(self.conversacion_historial) > 8:
                self.conversacion_historial = self.conversacion_historial[-8:]
            
            historial_contexto = "\n".join(self.conversacion_historial[-4:])
            
            prompt = f"""
            Eres VECY_ASISTENTE, un asistente VIRTUAL para la plataforma de compras Vecy.
            Tienes acceso a DATOS REALES EN TIEMPO REAL de la base de datos.
            
            DATOS REALES ACTUALES:
            {json.dumps(datos_reales, indent=2, ensure_ascii=False)}
            
            CONTEXTO:
            - Usuario: {"LOGEADO" if user_id else "No logueado"}
            - Conversación reciente: {historial_contexto}
            - Productos encontrados para "{consulta_usuario}": {len(productos_encontrados)} productos
            
            INSTRUCCIONES CRÍTICAS:
            - SI hay productos en "productos_encontrados", MENCIONALOS específicamente en tu respuesta
            - Usa los NOMBRES REALES de los productos encontrados
            - Menciona los PRECIOS REALES de los productos encontrados
            - Si hay productos del negocio "El Rincón", destácalos específicamente
            - NO digas "no tenemos productos" si hay productos en "productos_encontrados"
            
            INSTRUCCIONES DE FORMATEO:
            - Usa **negritas SOLO para lo MÁS importante**: precios finales, totales, números clave
            - Usa *cursivas* para énfasis suave y tono amigable
            - MÁXIMO 2-3 negritas por mensaje - no abuses
            - Prioriza negritas en: precios, totales, números, acciones principales
            - Evita negritas en: saludos, preguntas, textos descriptivos normales
            - Usa emojis estratégicamente para hacerlo más amigable
            - Sé natural y conversacional
            
            RESPUESTA EN JSON:
            {{
                "respuesta_chat": "Texto conversacional con negritas MEDIDAS y estratégicas",
                "tipo_respuesta": "productos|carrito|pedidos|ofertas|favoritos|variantes|navegacion|conversacional",
                "datos_interactivos": {{
                    "mostrar_productos": true/false,
                    "productos_destacados": [lista de IDs de productos_encontrados],
                    "mostrar_categorias": true/false,
                    "categorias_sugeridas": [lista de IDs],
                    "mostrar_ofertas": true/false,
                    "mostrar_favoritos": true/false,
                    "mostrar_variantes": true/false,
                    "producto_con_variantes": id_producto,
                    "accion_recomendada": "buscar|filtrar|agregar_carrito|ver_pedidos|ver_ofertas|ver_favoritos|elegir_variante",
                    "filtros_sugeridos": ["categoria:X", "precio_min:Y", "precio_max:Z", "negocio:W"]
                }},
                "sugerencia_navegacion": {{
                    "pagina_recomendada": "productos_filtrados|carrito|mis_pedidos|dashboard|favoritos",
                    "url_destino": "/productos-filtrados/|/carrito/|/mis-pedidos-data/|/dashboard/|/favoritos/",
                    "confianza": 1-10,
                    "razon": "Texto corto y natural para el botón - MÁXIMO 5 palabras"
                }}
            }}
            
            INSTRUCCIÓN IMPORTANTE: 
            - En "razon" escribe SOLO el texto que aparecerá en el botón
            - NO expliques tu razonamiento lógico
            - NO pongas "El usuario solicitó" o "siguiente paso lógico"
            - Usa textos cortos como: "Explorar categorías", "Ver productos", "Ir al carrito", "Ver favoritos"
            
            EJEMPLOS DE RESPUESTAS CUANDO HAY PRODUCTOS ENCONTRADOS:
            
            CON PRODUCTOS:
            "¡Perfecto! Encontré {len(productos_encontrados)} productos relacionados con '{consulta_usuario}'. Te recomiendo ver *Audífonos Gamer Pro* de **El Rincón** por **$85,000** 🎧. ¿Te gustaría que te muestre más detalles?"
            
            SIN PRODUCTOS:
            "No encontré productos exactos para '{consulta_usuario}', pero te sugiero explorar la categoría de electrónica en *El Rincón* donde suelen tener productos similares. ¿Quieres ver todos los productos disponibles?"
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            texto_limpio = response.text.replace('```json', '').replace('```', '').strip()
            resultado = json.loads(texto_limpio)
            
            resultado["respuesta_chat"] = self._convertir_markdown_a_html(resultado["respuesta_chat"])
            
            self.conversacion_historial.append(f"Asistente: {resultado['respuesta_chat']}")
            
            print(f"Respuesta interactiva: {resultado['tipo_respuesta']}, Productos encontrados: {len(productos_encontrados)}")
            return resultado
            
        except Exception as e:
            print(f"Error: {e}")
            return self._respuesta_emergencia(consulta_usuario)
    
    def _respuesta_emergencia(self, consulta):
        return {
            "respuesta_chat": "¡Hola! 👋 Estoy teniendo problemas técnicos momentáneos. Mientras tanto, puedes explorar nuestras secciones principales.",
            "tipo_respuesta": "conversacional",
            "datos_interactivos": {
                "mostrar_productos": False,
                "accion_recomendada": "navegar"
            },
            "sugerencia_navegacion": {
                "pagina_recomendada": "dashboard",
                "url_destino": "/dashboard/",
                "confianza": 5,
                "razon": "Página principal"
            }
        }

asistente_gemini = GeminiAssistant()
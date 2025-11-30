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
            raise ValueError("❌ GEMINI_API_KEY no encontrada")
        
        self.client = genai.Client(api_key=self.api_key)
        print("🎯 ASISTENTE INTERACTIVO CON BD REAL INICIADO")
        
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
            print(f"❌ Error .env: {e}")
    
    def _convertir_markdown_a_html(self, texto):
        """Convertir markdown simple a HTML para mejor visualización"""
        if not texto:
            return texto
        
        # Convertir **texto** a <strong>texto</strong>
        texto = texto.replace('**', '<strong>')
        # Cerrar las etiquetas strong correctamente
        strong_count = texto.count('<strong>')
        for i in range(strong_count):
            texto = texto.replace('<strong>', '</strong>', 1)
            texto = texto.replace('</strong>', '<strong>', 1)
        
        # Convertir *texto* a <em>texto</em> (cursiva)
        texto = texto.replace('*', '<em>')
        # Cerrar las etiquetas em correctamente
        em_count = texto.count('<em>')
        for i in range(em_count):
            texto = texto.replace('<em>', '</em>', 1)
            texto = texto.replace('</em>', '<em>', 1)
        
        # Convertir `texto` a <code>texto</code>
        texto = texto.replace('`', '<code>')
        # Cerrar las etiquetas code correctamente
        code_count = texto.count('<code>')
        for i in range(code_count):
            texto = texto.replace('<code>', '</code>', 1)
            texto = texto.replace('</code>', '<code>', 1)
        
        # Convertir saltos de línea
        texto = texto.replace('\n', '<br>')
        
        return texto
    
    def _obtener_datos_reales_bd(self, user_id=None):
        """Obtener datos REALES de tu base de datos"""
        try:
            # Obtener modelos REALES de tu BD
            Productos = apps.get_model('Software', 'Productos')
            CategoriaProductos = apps.get_model('Software', 'CategoriaProductos')
            Negocios = apps.get_model('Software', 'Negocios')
            Carrito = apps.get_model('Software', 'Carrito')
            CarritoItem = apps.get_model('Software', 'CarritoItem')
            Pedidos = apps.get_model('Software', 'Pedidos')
            Promociones = apps.get_model('Software', 'Promociones')
            
            datos_reales = {
                "productos": [],
                "categorias": [],
                "negocios": [],
                "ofertas_activas": [],
                "carrito_usuario": {},
                "pedidos_recientes": []
            }
            
            # Obtener PRODUCTOS REALES con sus categorías y negocios
            productos = Productos.objects.select_related(
                'fkcategoria_prod', 'fknegocioasociado_prod'
            ).filter(estado_prod='activo')[:15]  # Últimos 15 productos activos
            
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
                    "estado": p.estado_prod
                }
                datos_reales["productos"].append(producto_data)
            
            # Obtener CATEGORÍAS REALES
            categorias = CategoriaProductos.objects.all()[:10]
            for c in categorias:
                datos_reales["categorias"].append({
                    "id": c.pkid_cp,
                    "nombre": c.desc_cp
                })
            
            # Obtener NEGOCIOS ACTIVOS
            negocios = Negocios.objects.filter(estado_neg='activo')[:10]
            for n in negocios:
                datos_reales["negocios"].append({
                    "id": n.pkid_neg,
                    "nombre": n.nom_neg,
                    "categoria": n.fktiponeg_neg.desc_tiponeg if n.fktiponeg_neg else "Sin categoría",
                    "direccion": n.direcc_neg,
                    "imagen": n.img_neg.url if n.img_neg else None
                })
            
            # Obtener OFERTAS ACTIVAS
            from django.utils import timezone
            hoy = timezone.now().date()
            ofertas = Promociones.objects.filter(
                estado_promo='activa',
                fecha_inicio__lte=hoy,
                fecha_fin__gte=hoy
            ).select_related('fkproducto')[:5]
            
            for o in ofertas:
                if o.fkproducto:
                    datos_reales["ofertas_activas"].append({
                        "producto": o.fkproducto.nom_prod,
                        "titulo": o.titulo_promo,
                        "descuento": float(o.porcentaje_descuento) if o.porcentaje_descuento else 0,
                        "precio_original": float(o.fkproducto.precio_prod),
                        "precio_final": float(o.fkproducto.precio_prod) * (1 - (float(o.porcentaje_descuento) / 100)) if o.porcentaje_descuento else float(o.fkproducto.precio_prod)
                    })
            
            # Obtener CARRITO del usuario (si está logueado)
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
                                "subtotal": float(item.precio_unitario) * item.cantidad
                            })
                        
                        datos_reales["carrito_usuario"] = {
                            "total_items": total_items,
                            "total_precio": total_precio,
                            "items": items_detalle
                        }
                except Exception as e:
                    print(f"⚠️ Error obteniendo carrito: {e}")
            
            # Obtener PEDIDOS RECIENTES del usuario
            if user_id:
                try:
                    pedidos = Pedidos.objects.filter(
                        fkusuario_pedido_id=user_id
                    ).order_by('-fecha_pedido')[:5]
                    
                    for ped in pedidos:
                        datos_reales["pedidos_recientes"].append({
                            "id": ped.pkid_pedido,
                            "estado": ped.estado_pedido,
                            "total": float(ped.total_pedido),
                            "fecha": ped.fecha_pedido.strftime("%d/%m/%Y"),
                            "negocio": ped.fknegocio_pedido.nom_neg if ped.fknegocio_pedido else "Sin negocio"
                        })
                except Exception as e:
                    print(f"⚠️ Error obteniendo pedidos: {e}")
            
            print(f"✅ Datos BD: {len(datos_reales['productos'])} productos, {len(datos_reales['categorias'])} categorías")
            return datos_reales
            
        except Exception as e:
            print(f"❌ Error obteniendo datos BD: {e}")
            return {"productos": [], "categorias": [], "negocios": [], "ofertas_activas": []}
    
    def obtener_respuesta_interactiva(self, consulta_usuario, user_id=None):
        """Respuesta SUPER INTERACTIVA con negritas equilibradas"""
        try:
            print(f"🚀 Procesando: {consulta_usuario}")
            
            # OBTENER DATOS REALES DE LA BD
            datos_reales = self._obtener_datos_reales_bd(user_id)
            
            # Agregar al historial
            self.conversacion_historial.append(f"Usuario: {consulta_usuario}")
            if len(self.conversacion_historial) > 8:
                self.conversacion_historial = self.conversacion_historial[-8:]
            
            historial_contexto = "\n".join(self.conversacion_historial[-4:])
            
            prompt = f"""
            Eres VECY_ASISTENTE, un asistente VIRTUAL SUPER INTERACTIVO para la plataforma de compras Vecy.
            Tienes acceso a DATOS REALES EN TIEMPO REAL de la base de datos.
            
            DATOS REALES ACTUALES:
            {json.dumps(datos_reales, indent=2, ensure_ascii=False)}
            
            CONTEXTO:
            - Usuario: {"✅ LOGEADO" if user_id else "🚫 No logueado"}
            - Conversación reciente: {historial_contexto}
            
            🎯 **INSTRUCCIONES DE FORMATEO - NEGRITAS EQUILIBRADAS:**
            - Usa **negritas SOLO para lo MÁS importante**: precios finales, totales, números clave
            - Usa *cursivas* para énfasis suave y tono amigable
            - **MÁXIMO 2-3 negritas por mensaje** - no abuses
            - Prioriza negritas en: precios, totales, números, acciones principales
            - Evita negritas en: saludos, preguntas, textos descriptivos normales
            - Usa emojis estratégicamente para hacerlo más amigable 🎯
            - Sé natural y conversacional
            
            RESPUESTA EN JSON:
            {{
                "respuesta_chat": "Texto conversacional con negritas MEDIDAS y estratégicas",
                "tipo_respuesta": "productos|carrito|pedidos|ofertas|navegacion|conversacional",
                "datos_interactivos": {{
                    "mostrar_productos": true/false,
                    "productos_destacados": [lista de IDs],
                    "mostrar_categorias": true/false,
                    "categorias_sugeridas": [lista de IDs],
                    "mostrar_ofertas": true/false,
                    "accion_recomendada": "buscar|filtrar|agregar_carrito|ver_pedidos|ver_ofertas",
                    "filtros_sugeridos": ["categoria:X", "precio_min:Y", "precio_max:Z", "negocio:W"]
                }},
                "sugerencia_navegacion": {{
                    "pagina_recomendada": "productos_filtrados|carrito|mis_pedidos|dashboard",
                    "url_destino": "/productos-filtrados/|/carrito/|/mis-pedidos-data/|/dashboard/",
                    "confianza": 1-10,
                    "razon": "Texto corto y natural para el botón - MÁXIMO 5 palabras"
                }}
            }}
            
            🚫 **INSTRUCCIÓN IMPORTANTE:** 
            - En "razon" escribe SOLO el texto que aparecerá en el botón
            - NO expliques tu razonamiento lógico
            - NO pongas "El usuario solicitó" o "siguiente paso lógico"
            - Usa textos cortos como: "Explorar categorías", "Ver productos", "Ir al carrito"
            
            📝 **EJEMPLOS DE RESPUESTAS CON NEGRITAS EQUILIBRADAS:**
            
            ✅ BIEN (negritas estratégicas):
            - "Encontré 3 helados por debajo de **$10,000**. *¡Perfectos para tu presupuesto!* 🍦"
            - "Tu carrito tiene 2 productos por un total de **$25,500**. ¿Quieres proceder al pago? 💳"
            - "📦 Pedido *#456* está *en camino*. Llegará estimadamente mañana. 🚚"
            - "¡Oferta especial! *Hoy solamente*: Helado de Vainilla por **$8,500** (antes $10,000) 🎉"
            
            ❌ MAL (demasiadas negritas):
            - "**Encontré** **3 helados** por debajo de **$10,000**. **¡Perfectos** para tu **presupuesto!** 🍦"
            - "**Tu carrito** tiene **2 productos** por un **total** de **$25,500**. **¿Quieres** proceder al **pago?** 💳"
            
            🎯 **CUÁNDO USAR NEGRITAS:**
            - PRECIOS: **$10,000** (solo el precio, no "por debajo de")
            - TOTALES: **$25,500** (solo el total, no "por un total de")  
            - NÚMEROS CLAVE: **3 helados**, **Pedido #456**
            - ACCIONES: **proceder al pago** (solo si es muy importante)
            
            INSTRUCCIONES INTERACTIVAS:
            
            1. PRODUCTOS:
            - "helados" → mostrar productos de categoría helados
            - "productos baratos" → filtrar por precio < 10000
            - Mencionar precios REALES con **negritas estratégicas**
            
            2. CARRITO:
            - Si usuario tiene carrito → mencionar total con **negrita**
            - "mi carrito" → mostrar resumen del carrito real
            
            3. OFERTAS:
            - "ofertas" → mostrar promociones activas REALES
            - Destacar precio final con **negrita**
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            texto_limpio = response.text.replace('```json', '').replace('```', '').strip()
            resultado = json.loads(texto_limpio)
            
            # ✅ CONVERTIR MARKDOWN A HTML
            resultado["respuesta_chat"] = self._convertir_markdown_a_html(resultado["respuesta_chat"])
            
            # Agregar respuesta al historial
            self.conversacion_historial.append(f"Asistente: {resultado['respuesta_chat']}")
            
            print(f"✅ Respuesta interactiva: {resultado['tipo_respuesta']}")
            return resultado
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return self._respuesta_emergencia(consulta_usuario)
    
    def _respuesta_emergencia(self, consulta):
        """Respuesta de emergencia"""
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

# Instancia global
asistente_gemini = GeminiAssistant()
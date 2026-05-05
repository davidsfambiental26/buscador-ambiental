# app.py - BUSCADOR COMPLETO (UE, ESPAÑA, CANARIAS)
import streamlit as st
import pandas as pd
import requests
import time
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json

# Configuración
st.set_page_config(page_title="Buscador Legislativo Ambiental", page_icon="🌍", layout="wide")

st.title("🔍 Buscador de Legislación Ambiental")
st.markdown("**Unión Europea | España | Canarias**")
st.markdown("*Agua | Suelo | Aire | Ruido | Residuos | Radiactividad | Emisiones*")

# ============================================
# PALABRAS CLAVE COMPLETAS (español)
# ============================================
CATEGORIAS = {
    "Agua": ["agua", "hidrológico", "vertido", "depuración", "acuífero", "desalación", "trasvase", "embalse", "cuenca", "regadío"],
    "Residuos": ["residuo", "basura", "reciclaje", "vertedero", "economía circular", "envases", "plástico", "orgánico", "peligroso"],
    "Aire": ["aire", "atmósfera", "emisión", "calidad del aire", "ozono", "partículas", "CO2", "contaminación atmosférica"],
    "Suelo": ["suelo", "contaminación del suelo", "restauración", "sedimento", "erosión", "deslizamiento"],
    "Ruido": ["ruido", "acústica", "vibración", "sonométrico", "decibelios"],
    "Radiactividad": ["radiactivo", "nuclear", "radiación", "Euratom", "central nuclear", "residuo radiactivo"]
}

# ============================================
# FUNCIÓN 1: BUSCADOR DEL BOE (API REAL)
# ============================================
def buscar_boe(palabra, fecha_inicio, fecha_fin, max_resultados=20):
    """Busca en el Boletín Oficial del Estado (API oficial)"""
    resultados = []
    url = "https://www.boe.es/buscar/api.php"
    
    fecha_inicio_str = fecha_inicio.strftime("%Y%m%d")
    fecha_fin_str = fecha_fin.strftime("%Y%m%d")
    
    params = {
        'q': palabra,
        'fecha_desde': fecha_inicio_str,
        'fecha_hasta': fecha_fin_str,
        'coleccion': 'boe',
        'page': 1,
        'pageSize': max_resultados
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            
            for item in data.get('resultados', []):
                titulo = item.get('titulo', 'Sin título')
                fecha = item.get('fecha', '')
                url_pdf = item.get('url_pdf', '')
                texto = item.get('texto', '')[:500]
                
                # Detectar si está derogada
                estado = "✅ Vigente"
                if re.search(r'derogad[ao]|sin vigencia|dejado sin efecto', titulo.lower() + " " + texto.lower()):
                    estado = "❌ DEROGADA"
                elif re.search(r'modificad[ao]|texto refundido|versión consolidada', titulo.lower()):
                    estado = "📝 Modificada/Refundida"
                
                resultados.append({
                    "Título": titulo[:200],
                    "Fuente": "BOE",
                    "Fecha": fecha,
                    "Estado": estado,
                    "Enlace": f"https://www.boe.es{url_pdf}" if url_pdf else "",
                    "Tipo": "Disposición legal"
                })
    except Exception as e:
        st.warning(f"⚠️ BOE: {str(e)[:80]}")
    
    return resultados

# ============================================
# FUNCIÓN 2: BUSCADOR DEL BOC (SCRAPING XML)
# ============================================
def buscar_boc(palabra, fecha_inicio, fecha_fin):
    """Busca en el Boletín Oficial de Canarias (scraping de sumarios)"""
    resultados = []
    
    # Determinar años a buscar
    año_inicio = fecha_inicio.year
    año_fin = fecha_fin.year
    
    for año in range(año_inicio, año_fin + 1):
        for mes in range(1, 13):
            # Construir URL del sumario mensual
            url_sumario = f"https://www.gobiernodecanarias.org/boc/sumarios/{año}/{str(mes).zfill(2)}/"
            
            try:
                response = requests.get(url_sumario, timeout=8)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    texto_completo = soup.get_text().lower()
                    
                    # Verificar si aparece la palabra clave
                    if palabra.lower() in texto_completo:
                        # Intentar extraer los títulos de los anuncios
                        titulos = soup.find_all('h3')
                        for titulo in titulos[:5]:  # Limitar a 5 por mes
                            titulo_texto = titulo.get_text().strip()
                            if palabra.lower() in titulo_texto.lower():
                                resultados.append({
                                    "Título": titulo_texto[:150],
                                    "Fuente": "BOC",
                                    "Fecha": f"{año}-{str(mes).zfill(2)}-01",
                                    "Estado": "✅ Consultar vigencia",
                                    "Enlace": url_sumario,
                                    "Tipo": "Disposición autonómica"
                                })
                        
                        # Si no se encontraron títulos específicos, añadir entrada genérica
                        if not any(palabra.lower() in r["Título"].lower() for r in resultados if r["Fuente"] == "BOC" and r["Fecha"].startswith(f"{año}-{str(mes).zfill(2)}")):
                            resultados.append({
                                "Título": f"Contenido relacionado con '{palabra}' en el BOC ({año}/{mes})",
                                "Fuente": "BOC",
                                "Fecha": f"{año}-{str(mes).zfill(2)}-01",
                                "Estado": "✅ Pendiente revisión",
                                "Enlace": url_sumario,
                                "Tipo": "Anuncio oficial"
                            })
                
                time.sleep(0.3)  # Cortesía con el servidor
                
            except Exception as e:
                continue
    
    return resultados

# ============================================
# FUNCIÓN 3: BUSCADOR EUR-LEX (REST API)
# ============================================
def buscar_eurlex(palabra, fecha_inicio, fecha_fin):
    """
    Búsqueda en EUR-Lex usando el servicio de búsqueda REST
    Alternativa al SPARQL que es más estable
    """
    resultados = []
    
    # Traducción simple al inglés para EUR-Lex
    traducciones = {
        "agua": "water", "residuos": "waste", "aire": "air",
        "suelo": "soil", "ruido": "noise", "radiactividad": "radioactivity",
        "vertido": "discharge", "depuración": "treatment", "reciclaje": "recycling",
        "emisión": "emission", "contaminación": "pollution"
    }
    
    term_en = traducciones.get(palabra.lower(), palabra.lower())
    
    # URL de búsqueda de EUR-Lex (formato JSON)
    url = "https://eur-lex.europa.eu/search.html"
    
    params = {
        'q': term_en,
        'type': 'advanced',
        'lang': 'es',
        'page': 1,
        'pageSize': 15,
        'date-ds': fecha_inicio.strftime("%Y-%m-%d"),
        'date-de': fecha_fin.strftime("%Y-%m-%d"),
        'format': 'json'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            # Intentar parsear JSON
            try:
                data = response.json()
                results = data.get('results', {}).get('result', [])
                
                for item in results:
                    titulo = item.get('title', 'Sin título')
                    celex = item.get('celex', '')
                    fecha = item.get('date_document', '')[:10]
                    tipo = item.get('resource_type', 'Acto legal')
                    
                    if celex:
                        enlace = f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{celex}"
                    else:
                        enlace = item.get('url', '')
                    
                    resultados.append({
                        "Título": titulo[:200],
                        "Fuente": "EUR-Lex",
                        "Fecha": fecha,
                        "Estado": "✅ Consultar en EUR-Lex",
                        "Enlace": enlace,
                        "Tipo": tipo
                    })
            except json.JSONDecodeError:
                # Si no devuelve JSON, mostrar advertencia
                st.warning("EUR-Lex no devolvió JSON, puede estar sobrecargado")
        else:
            st.warning(f"EUR-Lex respondió con código {response.status_code}")
            
    except Exception as e:
        st.warning(f"EUR-Lex: {str(e)[:80]}")
    
    return resultados

# ============================================
# INTERFAZ DE USUARIO
# ============================================
st.sidebar.header("🔍 Configuración de búsqueda")

# Selector de categoría
categoria = st.sidebar.selectbox("Categoría ambiental", list(CATEGORIAS.keys()))

# Palabras clave específicas
palabras_disponibles = CATEGORIAS[categoria]
palabra_seleccionada = st.sidebar.selectbox("Palabra clave específica", palabras_disponibles + ["🔎 Personalizar"])

if palabra_seleccionada == "🔎 Personalizar":
    keyword = st.sidebar.text_input("Escribe tu palabra clave", placeholder="Ej: atmósfera, vertido, acústica...")
else:
    keyword = palabra_seleccionada

st.sidebar.markdown("---")
st.sidebar.markdown("### 🌍 Niveles a consultar")
buscar_ue = st.sidebar.checkbox("🇪🇺 Unión Europea (EUR-Lex)", value=True)
buscar_es = st.sidebar.checkbox("🇪🇸 España (BOE)", value=True)
buscar_can = st.sidebar.checkbox("🇮🇨 Canarias (BOC)", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Rango temporal")
col1, col2 = st.sidebar.columns(2)
with col1:
    fecha_desde = st.date_input("Desde", datetime(1990, 1, 1))
with col2:
    fecha_hasta = st.date_input("Hasta", datetime.now())

st.sidebar.markdown("---")
boton_buscar = st.sidebar.button("🔍 BUSCAR LEGISLACIÓN", type="primary", use_container_width=True)

# ============================================
# EJECUCIÓN DE LA BÚSQUEDA
# ============================================
if boton_buscar and keyword:
    st.header(f"📋 Resultados para: '{keyword}'")
    st.caption(f"Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}")
    
    resultados_totales = []
    
    # Barra de progreso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Búsqueda en EUR-Lex
    if buscar_ue:
        status_text.text("🇪🇺 Buscando en EUR-Lex...")
        resultados_ue = buscar_eurlex(keyword, fecha_desde, fecha_hasta)
        resultados_totales.extend(resultados_ue)
        progress_bar.progress(33)
    
    # Búsqueda en BOE
    if buscar_es:
        status_text.text("🇪🇸 Buscando en BOE...")
        resultados_es = buscar_boe(keyword, fecha_desde, fecha_hasta)
        resultados_totales.extend(resultados_es)
        progress_bar.progress(66)
    
    # Búsqueda en BOC
    if buscar_can:
        status_text.text("🇮🇨 Buscando en BOC...")
        resultados_can = buscar_boc(keyword, fecha_desde, fecha_hasta)
        resultados_totales.extend(resultados_can)
        progress_bar.progress(100)
    
    status_text.empty()
    progress_bar.empty()
    
    # MOSTRAR RESULTADOS
    if resultados_totales:
        st.success(f"✅ {len(resultados_totales)} resultados encontrados")
        
        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📄 Total", len(resultados_totales))
        col2.metric("🇪🇺 UE", len([r for r in resultados_totales if r["Fuente"] == "EUR-Lex"]))
        col3.metric("🇪🇸 BOE", len([r for r in resultados_totales if r["Fuente"] == "BOE"]))
        col4.metric("🇮🇨 BOC", len([r for r in resultados_totales if r["Fuente"] == "BOC"]))
        
        # Convertir a DataFrame
        df = pd.DataFrame(resultados_totales)
        
        # Mostrar tabla
        st.dataframe(
            df[["Título", "Fuente", "Fecha", "Estado"]],
            use_container_width=True,
            column_config={
                "Título": st.column_config.TextColumn("Título de la norma", width="large"),
                "Fuente": st.column_config.TextColumn("Origen", width="small"),
                "Fecha": st.column_config.TextColumn("Fecha publicación", width="small"),
                "Estado": st.column_config.TextColumn("Estado", width="small")
            }
        )
        
        # Expandir con enlaces
        with st.expander("🔗 Ver enlaces directos a las normas"):
            for i, row in df.iterrows():
                st.markdown(f"**{row['Título'][:100]}** ({row['Fuente']})")
                st.markdown(f"📅 {row['Fecha']} | {row['Estado']}")
                st.markdown(f"[🔗 Abrir norma]({row['Enlace']})")
                if 'Tipo' in row and row['Tipo']:
                    st.caption(f"Tipo: {row['Tipo']}")
                st.markdown("---")
        
        # Botón de descarga CSV
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 DESCARGAR RESULTADOS (CSV)",
            data=csv,
            file_name=f"legislacion_ambiental_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    else:
        st.warning(f"⚠️ No se encontraron resultados para '{keyword}' en el período seleccionado.")
        st.info("💡 **Sugerencias:** Prueba con otra palabra clave, amplía el rango de fechas o selecciona más niveles.")

elif boton_buscar and not keyword:
    st.warning("⚠️ Por favor, selecciona o escribe una palabra clave para buscar.")

else:
    # Pantalla de bienvenida
    st.info("👈 **Configura tu búsqueda en la barra lateral y haz clic en 'BUSCAR LEGISLACIÓN'**")
    
    # Información sobre el buscador
    with st.expander("ℹ️ Cómo funciona este buscador"):
        st.markdown("""
        ### 🔍 Fuentes de datos en tiempo real
        
        | Nivel | Fuente | Método | Cobertura |
        |-------|--------|--------|-----------|
        | 🇪🇺 **Unión Europea** | EUR-Lex | API REST | 1990 - actualidad |
        | 🇪🇸 **España** | BOE | API oficial | 1990 - actualidad |
        | 🇮🇨 **Canarias** | BOC | Scraping XML | 2000 - actualidad |
        
        ### 📌 Palabras clave por categoría
        
        - **Agua:** agua, vertido, depuración, acuífero, desalación, trasvase
        - **Residuos:** residuo, reciclaje, vertedero, economía circular, envases
        - **Aire:** aire, emisión, calidad del aire, ozono, CO2
        - **Suelo:** suelo, contaminación del suelo, restauración
        - **Ruido:** ruido, acústica, vibración
        - **Radiactividad:** radiactivo, nuclear, radiación
        
        ### 📊 Estado de las normas
        
        | Color | Significado |
        |-------|-------------|
        | ✅ Vigente | Norma activa y en vigor |
        | 📝 Modificada/Refundida | Existe versión posterior |
        | ❌ Derogada | Norma sin vigencia |
        """)

st.markdown("---")
st.caption(f"🔍 Búsqueda en tiempo real - Última carga: {datetime.now().strftime('%H:%M:%S')}")

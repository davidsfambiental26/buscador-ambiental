# app.py - BÚSQUEDA REAL CON SPARQL (EUR-Lex) + APIs BOE/BOC
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
st.markdown("**Búsqueda en tiempo real: EUR-Lex (SPARQL) | BOE | BOC**")
st.markdown("*Rango temporal: 1 enero 1990 - Actualidad*")

# Palabras clave por categoría
CATEGORIAS = {
    "Agua": ["agua", "hidrológico", "vertido", "depuración", "acuífero", "desalación", "trasvase", "water", "hydrological"],
    "Residuos": ["residuo", "basura", "reciclaje", "vertedero", "economía circular", "envases", "waste", "recycling"],
    "Aire": ["aire", "atmósfera", "emisión", "calidad del aire", "ozono", "partículas", "air", "emissions"],
    "Suelo": ["suelo", "contaminación del suelo", "restauración", "sedimento", "soil", "land"],
    "Ruido": ["ruido", "acústica", "vibración", "sonométrico", "noise"],
    "Radiactividad": ["radiactivo", "nuclear", "radiación", "Euratom", "radioactive", "nuclear"]
}

# Traducción de términos al inglés para SPARQL
def traducir_termino(palabra):
    """Traduce términos ambientales al inglés para consultas SPARQL"""
    traducciones = {
        "agua": ["water", "hydrological"],
        "residuos": ["waste", "recycling", "circular economy"],
        "aire": ["air", "emissions", "atmospheric"],
        "suelo": ["soil", "land", "contaminated land"],
        "ruido": ["noise", "acoustic"],
        "radiactividad": ["radioactive", "nuclear", "radiation"],
        "vertido": ["discharge", "dumping"],
        "depuración": ["treatment", "purification"]
    }
    
    palabra_lower = palabra.lower()
    if palabra_lower in traducciones:
        return traducciones[palabra_lower]
    return [palabra_lower]

# Función para construir consulta SPARQL
def construir_consulta_sparql(keyword, fecha_inicio, fecha_fin, tipo_documento=None):
    """
    Construye una consulta SPARQL para EUR-Lex
    Basado en la documentación oficial de Cellar [citation:4][citation:5]
    """
    terminos = traducir_termino(keyword)
    termino_busqueda = " || ".join([f'"{t}"' for t in terminos])
    
    # Format fechas para SPARQL (YYYY-MM-DD)
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")
    
    # Filtro por tipo de documento (opcional)
    filtro_tipo = ""
    if tipo_documento and tipo_documento != "any":
        tipos_map = {
            "Reglamento": "http://publications.europa.eu/resource/authority/resource-type/REGULATION",
            "Directiva": "http://publications.europa.eu/resource/authority/resource-type/DIRECTIVE",
            "Decisión": "http://publications.europa.eu/resource/authority/resource-type/DECISION",
            "Recomendación": "http://publications.europa.eu/resource/authority/resource-type/RECOMMENDATION"
        }
        if tipo_documento in tipos_map:
            filtro_tipo = f'FILTER(?resource_type = <{tipos_map[tipo_documento]}>)'
    
    # Consulta SPARQL completa [citation:1][citation:6]
    query = f"""
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX eurovoc: <http://eurovoc.europa.eu/>
    
    SELECT DISTINCT ?work ?title ?celex ?date_document ?resource_type ?in_force
    WHERE {{
        ?work a cdm:work.
        ?work cdm:work_id_document ?doc_id.
        ?work dc:title ?title.
        ?work cdm:work_has_resource-type ?resource_type_uri.
        ?resource_type_uri skos:prefLabel ?resource_type.
        
        OPTIONAL {{ ?work cdm:work_date_document ?date_document. }}
        OPTIONAL {{ ?work cdm:work_celex ?celex. }}
        OPTIONAL {{ 
            ?expression cdm:expression_belongs_to_work ?work.
            ?expression cdm:expression_has_validity ?validity.
            ?validity cdm:validity_is_in_force ?in_force.
        }}
        
        FILTER( lang(?title) = "es" || lang(?title) = "en" )
        FILTER( regex(?title, "{termino_busqueda}", "i") )
        FILTER( ?date_document >= "{fecha_inicio_str}"^^xsd:date && ?date_document <= "{fecha_fin_str}"^^xsd:date )
        {filtro_tipo}
    }}
    ORDER BY DESC(?date_document)
    LIMIT 50
    """
    return query

# Función para ejecutar consulta SPARQL en EUR-Lex
def buscar_eurlex_sparql(keyword, fecha_inicio, fecha_fin):
    """
    Ejecuta consulta SPARQL real en el endpoint de la UE
    Endpoint: https://publications.europa.eu/webapi/rdf/sparql [citation:2][citation:4]
    """
    resultados = []
    endpoint = "https://publications.europa.eu/webapi/rdf/sparql"
    
    # Intentar con términos en español primero, luego en inglés
    query = construir_consulta_sparql(keyword, fecha_inicio, fecha_fin)
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "BuscadorAmbiental/1.0 (https://buscador-ambiental.streamlit.app)"
    }
    
    try:
        response = requests.post(
            endpoint,
            data={"query": query, "format": "json"},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])
            
            for binding in bindings:
                titulo = binding.get("title", {}).get("value", "Sin título")
                celex = binding.get("celex", {}).get("value", "")
                fecha = binding.get("date_document", {}).get("value", "")[:10]
                tipo = binding.get("resource_type", {}).get("value", "Acto legal")
                en_vigor = binding.get("in_force", {}).get("value", "true")
                
                # Determinar estado
                estado = "✅ Vigente" if en_vigor == "true" else "❌ Derogada/Expirada"
                
                # Construir URL a partir de CELEX
                if celex:
                    url = f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{celex}"
                else:
                    url = binding.get("work", {}).get("value", "")
                
                resultados.append({
                    "Título": titulo[:200],
                    "Nivel": "🇪🇺 Unión Europea (EUR-Lex)",
                    "Fecha": fecha,
                    "Estado": estado,
                    "Enlace": url,
                    "CELEX": celex,
                    "Tipo": tipo
                })
                
            # Mostrar información de depuración
            st.info(f"📡 EUR-Lex SPARQL: {len(resultados)} resultados encontrados")
            
        else:
            st.warning(f"⚠️ EUR-Lex SPARQL respondió con código {response.status_code}")
            
    except requests.exceptions.Timeout:
        st.warning("⏰ EUR-Lex SPARQL: Timeout (30s). La consulta puede ser muy amplia.")
    except Exception as e:
        st.warning(f"⚠️ EUR-Lex SPARQL: {str(e)[:100]}")
    
    return resultados

# Función para buscar en BOE (API real)
def buscar_boe(palabra, fecha_inicio, fecha_fin):
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
        'pageSize': 15
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for item in data.get('resultados', []):
                titulo = item.get('titulo', 'Sin título')
                estado = "✅ Vigente"
                if re.search(r'derogad[ao]|sin vigencia', titulo.lower()):
                    estado = "❌ DEROGADA"
                elif re.search(r'modificaci[oó]n|texto refundido', titulo.lower()):
                    estado = "📝 Modificada/Refundida"
                
                resultados.append({
                    "Título": titulo[:200],
                    "Nivel": "🇪🇸 España (BOE)",
                    "Fecha": item.get('fecha', ''),
                    "Estado": estado,
                    "Enlace": f"https://www.boe.es{item.get('url_pdf', '')}",
                    "CELEX": "",
                    "Tipo": "Disposición legal"
                })
    except Exception as e:
        st.warning(f"⚠️ BOE: {str(e)[:50]}")
    
    time.sleep(0.5)
    return resultados

# Función para buscar en BOC
def buscar_boc(palabra, fecha_inicio, fecha_fin):
    resultados = []
    
    años = range(max(fecha_inicio.year, 1990), fecha_fin.year + 1)
    
    for año in años:
        for mes in range(1, 13):
            url_sumario = f"https://www.gobiernodecanarias.org/boc/sumarios/{año}/{str(mes).zfill(2)}/"
            try:
                response = requests.get(url_sumario, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    texto = soup.get_text().lower()
                    
                    if palabra.lower() in texto:
                        resultados.append({
                            "Título": f"Contenido relacionado con '{palabra}' en BOC {año}-{mes}",
                            "Nivel": "🇮🇨 Canarias (BOC)",
                            "Fecha": f"{año}-{str(mes).zfill(2)}-01",
                            "Estado": "✅ Pendiente revisión",
                            "Enlace": url_sumario,
                            "CELEX": "",
                            "Tipo": "Anuncio/Disposición autonómica"
                        })
            except:
                pass
            time.sleep(0.2)
    
    return resultados

# Interfaz de usuario
st.sidebar.header("🔍 Configuración")

categoria = st.sidebar.selectbox("Categoría ambiental", list(CATEGORIAS.keys()) + ["📝 Búsqueda personalizada"])

if categoria == "📝 Búsqueda personalizada":
    keyword = st.sidebar.text_input("Palabra clave", placeholder="Ej: vertido, atmósfera, circular economy...")
else:
    keyword = st.sidebar.selectbox("Palabra clave específica", CATEGORIAS[categoria])

st.sidebar.markdown("---")
st.sidebar.markdown("### 🌍 Niveles")
buscar_ue = st.sidebar.checkbox("🇪🇺 Unión Europea (SPARQL)", True)
buscar_es = st.sidebar.checkbox("🇪🇸 España (BOE)", True)
buscar_can = st.sidebar.checkbox("🇮🇨 Canarias (BOC)", False)  # Desactivado por defecto por lentitud

st.sidebar.markdown("### 📅 Rango temporal")
st.sidebar.caption("Desde 1 enero 1990 hasta actualidad")

fecha_desde = st.sidebar.date_input("Desde", datetime(1990, 1, 1))
fecha_hasta = st.sidebar.date_input("Hasta", datetime.now())

st.sidebar.markdown("---")
st.sidebar.markdown("### 📄 Tipo de documento (UE)")
tipo_ue = st.sidebar.selectbox("Filtrar por tipo", ["any", "Reglamento", "Directiva", "Decisión", "Recomendación"])

buscar = st.sidebar.button("🔍 BUSCAR EN TIEMPO REAL", type="primary", use_container_width=True)

if buscar and keyword:
    st.header(f"📋 Resultados para: '{keyword}'")
    st.caption(f"Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}")
    
    resultados = []
    
    # Barra de progreso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Búsqueda en EUR-Lex con SPARQL
    if buscar_ue:
        status_text.text("🇪🇺 Consultando EUR-Lex vía SPARQL...")
        resultados_ue = buscar_eurlex_sparql(keyword, fecha_desde, fecha_hasta)
        resultados.extend(resultados_ue)
        progress_bar.progress(33)
    
    # Búsqueda en BOE
    if buscar_es:
        status_text.text("🇪🇸 Consultando BOE...")
        resultados_es = buscar_boe(keyword, fecha_desde, fecha_hasta)
        resultados.extend(resultados_es)
        progress_bar.progress(66)
    
    # Búsqueda en Canarias
    if buscar_can:
        status_text.text("🇮🇨 Consultando BOC...")
        resultados_can = buscar_boc(keyword, fecha_desde, fecha_hasta)
        resultados.extend(resultados_can)
        progress_bar.progress(100)
    
    status_text.empty()
    progress_bar.empty()
    
    # Mostrar resultados
    if resultados:
        st.success(f"🔍 {len(resultados)} resultados encontrados")
        
        df = pd.DataFrame(resultados)
        
        # Métricas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🇪🇺 UE", len([r for r in resultados if "EUR-Lex" in r["Nivel"]]))
        with col2:
            st.metric("🇪🇸 España", len([r for r in resultados if "BOE" in r["Nivel"]]))
        with col3:
            st.metric("🇮🇨 Canarias", len([r for r in resultados if "BOC" in r["Nivel"]]))
        
        # Mostrar tabla
        st.dataframe(df[["Título", "Nivel", "Fecha", "Estado", "Tipo"]], use_container_width=True)
        
        # Expandir con enlaces
        with st.expander("🔗 Ver enlaces directos a las normas"):
            for idx, row in df.iterrows():
                st.markdown(f"**{row['Título'][:80]}** - {row['Nivel']}")
                st.markdown(f"[🔗 Acceder a la norma completa]({row['Enlace']})")
                if row.get('CELEX'):
                    st.caption(f"CELEX: {row['CELEX']}")
                st.markdown("---")
        
        # Botón descarga CSV
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 DESCARGAR CSV",
            data=csv,
            file_name=f"legislacion_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("No se encontraron resultados. Prueba otra palabra clave o rango de fechas.")

elif buscar and not keyword:
    st.warning("Por favor, ingresa una palabra clave para buscar.")

else:
    st.info("👈 **Configura tu búsqueda en la barra lateral y haz clic en 'BUSCAR EN TIEMPO REAL'**")
    
    with st.expander("ℹ️ Sobre la búsqueda SPARQL en EUR-Lex"):
        st.markdown("""
        **¿Qué es SPARQL?** Es el lenguaje de consulta oficial de la UE para acceder a su repositorio Cellar [citation:4].
        
        **Ventajas:**
        - ✅ Método oficial y permitido (no scraping)
        - ✅ Acceso a metadatos completos (fechas, estado, CELEX)
        - ✅ Consultas estructuradas y eficientes
        
        **Rango temporal:** Desde 1 de enero de 1990
        """)

st.caption(f"🕐 Última consulta: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

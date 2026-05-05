# app_v2_corregida.py - BUSCADOR BOE + BOC (ESTABLE CON DEBUG)
import streamlit as st
import pandas as pd
import requests
import time
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Configuración
st.set_page_config(page_title="Buscador Legislativo Ambiental", page_icon="🌍", layout="wide")

st.title("🔍 Buscador de Legislación Ambiental")
st.markdown("**España (BOE) | Canarias (BOC)**")
st.markdown("*Rango: 1 enero 1990 - Actualidad*")

# ============================================
# PALABRAS CLAVE COMPLETAS
# ============================================
CATEGORIAS = {
    "Agua": ["agua", "hidrológico", "vertido", "depuración", "acuífero", "desalación", "trasvase", "embalse", "cuenca", "regadío"],
    "Residuos": ["residuo", "basura", "reciclaje", "vertedero", "economía circular", "envases", "plástico", "orgánico", "peligroso"],
    "Aire": ["aire", "atmósfera", "emisión", "calidad del aire", "ozono", "partículas", "CO2", "contaminación atmosférica"],
    "Suelo": ["suelo", "contaminación del suelo", "restauración", "sedimento", "erosión"],
    "Ruido": ["ruido", "acústica", "vibración", "sonométrico", "decibelios"],
    "Radiactividad": ["radiactivo", "nuclear", "radiación", "central nuclear"]
}

# ============================================
# DATOS DE EJEMPLO (FALLBACK SI APIS FALLAN)
# ============================================
DATOS_EJEMPLO = {
    "agua": [
        {"titulo": "Real Decreto Legislativo 1/2001, de 20 de julio, por el que se aprueba el texto refundido de la Ley de Aguas", "fecha": "2001-07-20", "enlace": "https://www.boe.es/buscar/act.php?id=BOE-A-2001-14276"},
        {"titulo": "Real Decreto 849/1986, de 11 de abril, por el que se aprueba el Reglamento del Dominio Público Hidráulico", "fecha": "1986-04-11", "enlace": "https://www.boe.es/buscar/act.php?id=BOE-A-1986-10067"},
        {"titulo": "Directiva 2000/60/CE del Parlamento Europeo y del Consejo, de 23 de octubre de 2000, por la que se establece un marco comunitario de actuación en el ámbito de la política de aguas", "fecha": "2000-10-23", "enlace": "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32000L0060"},
        {"titulo": "Ley 12/2019, de 25 de abril, de Cambio Climático y Transición Energética de Canarias (incluye gestión del agua)", "fecha": "2019-04-25", "enlace": "https://www.gobiernodecanarias.org/boc/2019/086/001.html"}
    ],
    "residuos": [
        {"titulo": "Ley 7/2022, de 8 de abril, de residuos y suelos contaminados para una economía circular", "fecha": "2022-04-08", "enlace": "https://www.boe.es/eli/es/l/2022/04/08/7"},
        {"titulo": "Real Decreto 105/2008, de 1 de febrero, por el que se regula la producción y gestión de los residuos de construcción y demolición", "fecha": "2008-02-01", "enlace": "https://www.boe.es/buscar/act.php?id=BOE-A-2008-2486"},
        {"titulo": "Directiva 2008/98/CE del Parlamento Europeo y del Consejo, de 19 de noviembre de 2008, sobre residuos", "fecha": "2008-11-19", "enlace": "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32008L0098"},
        {"titulo": "Decreto 81/2022, de 26 de mayo, por el que se aprueba el Plan Director de Residuos de Canarias", "fecha": "2022-05-26", "enlace": "https://www.gobiernodecanarias.org/boc/2022/111/001.html"}
    ],
    "aire": [
        {"titulo": "Ley 34/2007, de 15 de noviembre, de calidad del aire y protección de la atmósfera", "fecha": "2007-11-15", "enlace": "https://www.boe.es/buscar/act.php?id=BOE-A-2007-21044"},
        {"titulo": "Directiva 2008/50/CE del Parlamento Europeo y del Consejo, de 21 de mayo de 2008, relativa a la calidad del aire ambiente", "fecha": "2008-05-21", "enlace": "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32008L0050"},
        {"titulo": "Ley 12/2019, de 25 de abril, de Cambio Climático y Transición Energética de Canarias", "fecha": "2019-04-25", "enlace": "https://www.gobiernodecanarias.org/boc/2019/086/001.html"}
    ]
}

# ============================================
# FUNCIÓN BOE (API REAL CON TIMEOUT)
# ============================================
def buscar_boe(palabra, fecha_inicio, fecha_fin):
    """Busca en el BOE usando su API oficial"""
    resultados = []
    url = "https://www.boe.es/buscar/api.php"
    
    params = {
        'q': palabra,
        'fecha_desde': fecha_inicio.strftime("%Y%m%d"),
        'fecha_hasta': fecha_fin.strftime("%Y%m%d"),
        'coleccion': 'boe',
        'pageSize': 15
    }
    
    try:
        response = requests.get(url, params=params, timeout=8)
        
        if response.status_code == 200:
            data = response.json()
            
            for item in data.get('resultados', []):
                titulo = item.get('titulo', 'Sin título')
                
                # Detectar estado
                estado = "✅ Vigente"
                if re.search(r'derogad[ao]|sin vigencia', titulo.lower()):
                    estado = "❌ DEROGADA"
                elif re.search(r'modificad[ao]|texto refundido', titulo.lower()):
                    estado = "📝 Modificada"
                
                resultados.append({
                    "Título": titulo[:200],
                    "Fuente": "🇪🇸 BOE",
                    "Fecha": item.get('fecha', ''),
                    "Estado": estado,
                    "Enlace": f"https://www.boe.es{item.get('url_pdf', '')}"
                })
        else:
            st.warning(f"BOE respondió con código {response.status_code}")
            
    except requests.exceptions.Timeout:
        st.warning("⏰ BOE: Tiempo de espera agotado")
    except Exception as e:
        st.warning(f"⚠️ BOE: {str(e)[:50]}")
    
    return resultados

# ============================================
# FUNCIÓN BOC (SOLO ÚLTIMOS 2 AÑOS PARA NO BLOQUEAR)
# ============================================
def buscar_boc(palabra):
    """
    Busca en BOC solo los últimos 2 años para evitar timeouts
    """
    resultados = []
    año_actual = datetime.now().year
    mes_actual = datetime.now().month
    
    # Solo buscar en año actual y anterior
    años_buscar = [año_actual, año_actual - 1]
    
    for año in años_buscar:
        meses_a_buscar = range(1, mes_actual + 1) if año == año_actual else range(1, 13)
        
        for mes in meses_a_buscar:
            url_sumario = f"https://www.gobiernodecanarias.org/boc/sumarios/{año}/{str(mes).zfill(2)}/"
            
            try:
                response = requests.get(url_sumario, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    texto = soup.get_text().lower()
                    
                    if palabra.lower() in texto:
                        # Buscar título específico
                        titulo_encontrado = None
                        for link in soup.find_all('a'):
                            if palabra.lower() in link.get_text().lower():
                                titulo_encontrado = link.get_text()[:150]
                                break
                        
                        resultados.append({
                            "Título": titulo_encontrado or f"Contenido en BOC ({año}/{mes}) sobre '{palabra}'",
                            "Fuente": "🇮🇨 BOC",
                            "Fecha": f"{año}-{str(mes).zfill(2)}",
                            "Estado": "✅ Verificar",
                            "Enlace": url_sumario
                        })
                time.sleep(0.3)
            except Exception:
                pass
    
    return resultados

# ============================================
# FUNCIÓN FALLBACK (DATOS DE EJEMPLO)
# ============================================
def obtener_datos_ejemplo(palabra):
    """Devuelve datos de ejemplo si las APIs fallan"""
    palabra_lower = palabra.lower()
    
    for categoria, leyes in DATOS_EJEMPLO.items():
        if palabra_lower in categoria or any(palabra_lower in ley["titulo"].lower() for ley in leyes):
            return [{
                "Título": ley["titulo"],
                "Fuente": "📋 Ejemplo",
                "Fecha": ley["fecha"],
                "Estado": "✅ Verificar",
                "Enlace": ley["enlace"]
            } for ley in leyes]
    return []

# ============================================
# INTERFAZ
# ============================================
st.sidebar.header("🔍 Configuración")

categoria = st.sidebar.selectbox("Categoría ambiental", list(CATEGORIAS.keys()))
palabra = st.sidebar.selectbox("Palabra clave", CATEGORIAS[categoria])

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Rango temporal (BOE)")
st.sidebar.caption("BOE: Desde 1990 hasta actualidad")
st.sidebar.caption("BOC: Últimos 2 años (por estabilidad)")

fecha_desde = st.sidebar.date_input("Desde", datetime(1990, 1, 1))
fecha_hasta = st.sidebar.date_input("Hasta", datetime.now())

st.sidebar.markdown("---")
st.sidebar.info("💡 Si la búsqueda no devuelve resultados, se mostrarán ejemplos")

boton_buscar = st.sidebar.button("🔍 BUSCAR", type="primary", use_container_width=True)

# ============================================
# EJECUCIÓN
# ============================================
if boton_buscar:
    st.header(f"📋 Resultados para: '{palabra}'")
    st.caption(f"BOE: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}")
    st.caption(f"BOC: Últimos 2 años")
    
    resultados = []
    boe_exitoso = False
    boc_exitoso = False
    
    # Barra de progreso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Búsqueda BOE
    status_text.text("🇪🇸 Buscando en BOE...")
    resultados_es = buscar_boe(palabra, fecha_desde, fecha_hasta)
    resultados.extend(resultados_es)
    if resultados_es:
        boe_exitoso = True
    progress_bar.progress(50)
    
    # Búsqueda BOC
    status_text.text("🇮🇨 Buscando en BOC...")
    resultados_can = buscar_boc(palabra)
    resultados.extend(resultados_can)
    if resultados_can:
        boc_exitoso = True
    progress_bar.progress(100)
    
    status_text.empty()
    progress_bar.empty()
    
    # Si no hay resultados, usar fallback
    if not resultados:
        st.warning("No se encontraron resultados en las APIs. Mostrando legislación de ejemplo.")
        resultados_ejemplo = obtener_datos_ejemplo(palabra)
        resultados.extend(resultados_ejemplo)
    
    # Mostrar resultados
    if resultados:
        st.success(f"✅ {len(resultados)} resultados encontrados")
        
        # Métricas
        col1, col2, col3 = st.columns(3)
        col1.metric("📄 Total", len(resultados))
        col2.metric("🇪🇸 BOE", len([r for r in resultados if "BOE" in r["Fuente"]]))
        col3.metric("🇮🇨 BOC", len([r for r in resultados if "BOC" in r["Fuente"]]))
        
        df = pd.DataFrame(resultados)
        
        # Mostrar tabla
        st.dataframe(
            df[["Título", "Fuente", "Fecha", "Estado"]],
            use_container_width=True,
            column_config={
                "Título": st.column_config.TextColumn("Norma", width="large"),
                "Fuente": st.column_config.TextColumn("Origen", width="small"),
                "Fecha": st.column_config.TextColumn("Fecha", width="small"),
                "Estado": st.column_config.TextColumn("Estado", width="small")
            }
        )
        
        # Enlaces
        with st.expander("🔗 Ver enlaces directos"):
            for _, row in df.iterrows():
                st.markdown(f"**{row['Título'][:100]}**")
                st.markdown(f"[🔗 Acceder al documento]({row['Enlace']})")
                st.markdown("---")
        
        # CSV
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f"legislacion_{palabra}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.error("No se encontraron resultados. Verifica tu conexión o intenta con otra palabra clave.")
        
        # Mostrar ejemplo de búsqueda
        with st.expander("🔍 Ejemplo de búsqueda"):
            st.code("""
            Prueba con:
            - 'agua' para normativa hídrica
            - 'residuos' para gestión de residuos
            - 'aire' para calidad atmosférica
            """)

else:
    st.info("👈 **Selecciona una categoría y palabra clave, luego haz clic en BUSCAR**")
    
    with st.expander("📋 Normativa incluida en los datos de ejemplo"):
        for cat, leyes in DATOS_EJEMPLO.items():
            st.markdown(f"**{cat.upper()}**")
            for ley in leyes:
                st.markdown(f"- {ley['titulo'][:80]}... ({ley['fecha']})")
            st.markdown("---")
    
    st.caption("""
    **Fuentes:**
    - 🇪🇸 BOE: API oficial (desde 1990)
    - 🇮🇨 BOC: Boletín Oficial de Canarias (últimos 2 años)
    """)

st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

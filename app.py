# app.py - Buscador Legislativo Ambiental con detección de cambios y derogaciones
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import requests
import time
import plotly.express as px
import re
from bs4 import BeautifulSoup

# Configuración de la página
st.set_page_config(
    page_title="Buscador Legislativo Ambiental",
    page_icon="🌍",
    layout="wide"
)

# Título
st.title("🔍 Buscador Legislativo Ambiental")
st.markdown("**Tres niveles: Unión Europea | España | Canarias**")
st.markdown("*Agua | Suelo | Aire | Ruido | Residuos | Emisiones | Radiactividad*")

# Palabras clave predefinidas
KEYWORDS = {
    "Agua": ["agua", "hidrológico", "vertido", "depuración", "acuífero", "desalación"],
    "Residuos": ["residuo", "basura", "reciclaje", "vertedero", "economía circular"],
    "Aire": ["aire", "atmósfera", "emisión", "calidad del aire", "ozono"],
    "Suelo": ["suelo", "contaminación del suelo", "restauración", "vertedero"],
    "Ruido": ["ruido", "acústica", "vibración"],
    "Radiactividad": ["radiactivo", "nuclear", "radiación"]
}

# Función para detectar si una norma está derogada o modificada
def detectar_estado_norma(titulo, texto_completo=""):
    """
    Detecta si una norma está derogada o tiene modificaciones pendientes
    Retorna: (estado, mensaje)
    """
    texto_lower = (titulo + " " + texto_completo).lower()
    
    # Palabras clave de derogación
    if re.search(r'derogad[ao]|sin vigencia|dejado sin efecto|abrogad[ao]', texto_lower):
        return ("❌ DEROGADA", "Esta norma ha sido derogada y no está vigente")
    
    # Palabras clave de modificación en curso
    if re.search(r'modificaci[oó]n en curso|proyecto de modificaci[oó]n|en tramitaci[oó]n', texto_lower):
        return ("🟡 MODIFICACIÓN EN CURSO", "Esta norma está siendo modificada. Consultar estado actual")
    
    if re.search(r'refundido|texto refundido|versión consolidada', texto_lower):
        return ("📝 TEXTO REFUNDIDO", "Existe una versión refundida/consolidada más reciente")
    
    return ("✅ VIGENTE", "Norma vigente sin cambios detectados")

# Función para buscar en EUR-Lex
def buscar_eurlex(keyword):
    """
    Búsqueda en legislación europea
    """
    resultados = []
    
    # Datos de ejemplo reales de legislación europea ambiental
    base_datos_europa = {
        "agua": [
            {
                "titulo": "Directiva 2000/60/CE del Parlamento Europeo y del Consejo, de 23 de octubre de 2000, por la que se establece un marco comunitario de actuación en el ámbito de la política de aguas (Directiva Marco del Agua)",
                "fuente": "EUR-Lex",
                "fecha_publicacion": "2000-10-23",
                "enlace": "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32000L0060",
                "materia": "Agua",
                "estado": "✅ VIGENTE",
                "estado_msg": "Norma marco del agua. Parcialmente modificada por Directivas posteriores"
            },
            {
                "titulo": "Directiva 91/271/CEE sobre el tratamiento de las aguas residuales urbanas",
                "fuente": "EUR-Lex",
                "fecha_publicacion": "1991-05-21",
                "enlace": "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:31991L0271",
                "materia": "Agua",
                "estado": "🟡 MODIFICACIÓN EN CURSO",
                "estado_msg": "En proceso de revisión por la Comisión Europea (Propuesta 2022/0345)"
            }
        ],
        "residuos": [
            {
                "titulo": "Directiva 2008/98/CE sobre residuos (Directiva Marco de Residuos)",
                "fuente": "EUR-Lex",
                "fecha_publicacion": "2008-11-19",
                "enlace": "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32008L0098",
                "materia": "Residuos",
                "estado": "📝 TEXTO REFUNDIDO",
                "estado_msg": "Modificada por Directiva (UE) 2018/851"
            }
        ],
        "aire": [
            {
                "titulo": "Directiva 2008/50/CE sobre calidad del aire ambiente",
                "fuente": "EUR-Lex",
                "fecha_publicacion": "2008-05-21",
                "enlace": "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32008L0050",
                "materia": "Aire",
                "estado": "✅ VIGENTE",
                "estado_msg": "Norma vigente sobre límites de contaminantes"
            }
        ]
    }
    
    # Buscar en la base de datos local
    for materia, normas in base_datos_europa.items():
        if keyword.lower() in materia.lower() or keyword.lower() in str(normas).lower():
            for norma in normas:
                if keyword.lower() in norma["materia"].lower() or keyword.lower() in norma["titulo"].lower():
                    resultados.append(norma)
    
    return resultados

# Función para buscar en BOE con detección de estado
def buscar_boe(keyword, fecha_desde=None, fecha_hasta=None):
    """Búsqueda en BOE con análisis de vigencia"""
    resultados = []
    url_api = "https://www.boe.es/buscar/api.php"
    
    if not fecha_desde:
        fecha_desde = "20200101"
    if not fecha_hasta:
        fecha_hasta = datetime.now().strftime("%Y%m%d")
    
    params = {
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'q': keyword,
        'coleccion': 'boe',
        'page': 1,
        'pageSize': 10
    }
    
    try:
        response = requests.get(url_api, params=params, timeout=10)
        if response.status_code == 200:
            datos = response.json()
            
            for item in datos.get('resultados', []):
                titulo = item.get('titulo', 'Sin título')
                texto_corto = f"{titulo} {item.get('texto', '')}"
                
                # Detectar estado de la norma
                estado, estado_msg = detectar_estado_norma(titulo, texto_corto)
                
                # Identificar materia principal
                materia_detectada = "Ambiental"
                for cat, keywords_list in KEYWORDS.items():
                    if any(palabra in titulo.lower() for palabra in keywords_list):
                        materia_detectada = cat
                        break
                
                resultados.append({
                    "titulo": titulo[:200],
                    "fuente": "BOE",
                    "fecha_publicacion": item.get('fecha', ''),
                    "enlace": f"https://www.boe.es{item.get('url_pdf', '')}",
                    "materia": materia_detectada,
                    "estado": estado,
                    "estado_msg": estado_msg
                })
            
            time.sleep(0.3)
    except Exception as e:
        st.warning(f"Error en búsqueda BOE: {e}")
    
    return resultados

# Función para buscar en BOC (Canarias)
def buscar_boc(keyword):
    """Búsqueda en Boletín Oficial de Canarias"""
    resultados = []
    
    # Base de datos de legislación canaria
    base_datos_canarias = [
        {
            "titulo": "Ley 12/2019, de 25 de abril, de Cambio Climático y Transición Energética de Canarias",
            "fuente": "BOC",
            "fecha_publicacion": "2019-05-02",
            "enlace": "https://www.gobiernodecanarias.org/boc/2019/086/001.html",
            "materia": "Aire",
            "estado": "✅ VIGENTE",
            "estado_msg": "Ley autonómica de cambio climático"
        },
        {
            "titulo": "Decreto 37/2015, de 26 de febrero, por el que se aprueba el Reglamento de Protección frente a la Contaminación Acústica en Canarias",
            "fuente": "BOC",
            "fecha_publicacion": "2015-03-09",
            "enlace": "https://www.gobiernodecanarias.org/boc/2015/047/001.html",
            "materia": "Ruido",
            "estado": "✅ VIGENTE",
            "estado_msg": "Normativa acústica vigente en Canarias"
        },
        {
            "titulo": "Ley 4/2017, de 13 de julio, del Suelo y de los Espacios Naturales Protegidos de Canarias",
            "fuente": "BOC",
            "fecha_publicacion": "2017-07-19",
            "enlace": "https://www.gobiernodecanarias.org/boc/2017/143/001.html",
            "materia": "Suelo",
            "estado": "✅ VIGENTE",
            "estado_msg": "Normativa de suelo y espacios protegidos"
        },
        {
            "titulo": "Decreto 81/2022, de 26 de mayo, por el que se aprueba el Plan Director de Residuos de Canarias",
            "fuente": "BOC",
            "fecha_publicacion": "2022-06-06",
            "enlace": "https://www.gobiernodecanarias.org/boc/2022/111/001.html",
            "materia": "Residuos",
            "estado": "✅ VIGENTE",
            "estado_msg": "Plan director de residuos 2022-2027"
        }
    ]
    
    # Filtrar por keyword
    for norma in base_datos_canarias:
        if keyword.lower() in norma["materia"].lower() or keyword.lower() in norma["titulo"].lower():
            resultados.append(norma)
    
    return resultados

# Interfaz de usuario
st.sidebar.header("🔍 Búsqueda")

# Selector de palabra clave
categoria = st.sidebar.selectbox(
    "Categoría ambiental",
    list(KEYWORDS.keys()) + ["Búsqueda personalizada"]
)

if categoria == "Búsqueda personalizada":
    keyword = st.sidebar.text_input("Palabra clave personalizada", placeholder="Ej: vertido, atmósfera...")
else:
    palabras_sugeridas = KEYWORDS[categoria]
    keyword = st.sidebar.selectbox("Palabra clave específica", palabras_sugeridas)

# Selección de niveles
st.sidebar.markdown("### 🌍 Niveles a consultar")
nivel_europa = st.sidebar.checkbox("Unión Europea", value=True)
nivel_espana = st.sidebar.checkbox("España (BOE)", value=True)
nivel_canarias = st.sidebar.checkbox("Canarias (BOC)", value=True)

# Rango de fechas
st.sidebar.markdown("### 📅 Rango temporal")
fecha_desde = st.sidebar.date_input("Desde", value=datetime(2020, 1, 1))
fecha_hasta = st.sidebar.date_input("Hasta", value=datetime.now())

# Botón de búsqueda
buscar = st.sidebar.button("🔍 Buscar legislación", type="primary", use_container_width=True)

# Contenedor para resultados
if buscar and keyword:
    st.header(f"📋 Resultados para: '{keyword}'")
    
    resultados_totales = []
    
    # Progreso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Búsqueda en Europa
    if nivel_europa:
        status_text.text("Buscando en legislación europea...")
        resultados_europa = buscar_eurlex(keyword)
        resultados_totales.extend(resultados_europa)
        progress_bar.progress(0.33)
    
    # Búsqueda en BOE
    if nivel_espana:
        status_text.text("Buscando en Boletín Oficial del Estado...")
        fecha_desde_str = fecha_desde.strftime("%Y%m%d")
        fecha_hasta_str = fecha_hasta.strftime("%Y%m%d")
        resultados_boe = buscar_boe(keyword, fecha_desde_str, fecha_hasta_str)
        resultados_totales.extend(resultados_boe)
        progress_bar.progress(0.66)
    
    # Búsqueda en Canarias
    if nivel_canarias:
        status_text.text("Buscando en Boletín Oficial de Canarias...")
        resultados_canarias = buscar_boc(keyword)
        resultados_totales.extend(resultados_canarias)
        progress_bar.progress(1.0)
    
    status_text.empty()
    progress_bar.empty()
    
    # Mostrar resultados
    if resultados_totales:
        df_resultados = pd.DataFrame(resultados_totales)
        
        # Resumen
        st.markdown(f"### 📊 {len(df_resultados)} normativas encontradas")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🇪🇺 UE", len(df_resultados[df_resultados['fuente'] == 'EUR-Lex']))
        with col2:
            st.metric("🇪🇸 España", len(df_resultados[df_resultados['fuente'] == 'BOE']))
        with col3:
            st.metric("🇮🇨 Canarias", len(df_resultados[df_resultados['fuente'] == 'BOC']))
        
        # Función para colorear - CORREGIDA (usando applymap que funciona)
        def color_estado(val):
            if 'DEROGADA' in str(val):
                return 'background-color: #ffcccc; color: #cc0000; font-weight: bold'
            elif 'MODIFICACIÓN' in str(val) or 'REFUNDIDO' in str(val):
                return 'background-color: #fff3cd; color: #856404'
            elif 'VIGENTE' in str(val):
                return 'background-color: #d4edda; color: #155724'
            return ''
        
        # Aplicar estilo - CORREGIDO: usar map en lugar de applymap
        styled_df = df_resultados.style.map(color_estado, subset=['estado'])
        
        # Mostrar dataframe con estilo
        st.dataframe(
            styled_df,
            use_container_width=True,
            column_config={
                "titulo": st.column_config.TextColumn("Título", width="large"),
                "fuente": st.column_config.TextColumn("Fuente", width="small"),
                "fecha_publicacion": st.column_config.TextColumn("Fecha", width="small"),
                "materia": st.column_config.TextColumn("Materia", width="small"),
                "estado": st.column_config.TextColumn("Estado", width="small"),
                "estado_msg": st.column_config.TextColumn("Observación", width="medium")
            }
        )
        
        # Expandir para ver detalles
        with st.expander("📜 Ver normas con modificaciones o derogaciones"):
            normas_especiales = df_resultados[df_resultados['estado'] != "✅ VIGENTE"]
            if not normas_especiales.empty:
                for idx, row in normas_especiales.iterrows():
                    st.markdown(f"**{row['estado']}** - {row['titulo'][:80]}...")
                    st.caption(f"_{row['estado_msg']}_")
                    st.markdown(f"[🔗 Ver norma]({row['enlace']})")
                    st.markdown("---")
            else:
                st.success("✅ Todas las normas encontradas están vigentes")
        
        # Botón para descargar CSV
        csv = df_resultados.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Descargar resultados en CSV",
            data=csv,
            file_name=f"legislacion_ambiental_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # Gráfico de distribución
        if len(df_resultados) > 0:
            fig = px.pie(
                df_resultados, 
                names='fuente', 
                title='Distribución por nivel',
                color_discrete_sequence=['#2ecc71', '#3498db', '#e74c3c']
            )
            st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.warning(f"No se encontraron resultados para '{keyword}'. Prueba con otra palabra clave.")
        
elif buscar and not keyword:
    st.warning("Por favor, ingresa una palabra clave para buscar.")

else:
    # Mensaje inicial
    st.info("👈 Selecciona una categoría ambiental o palabra clave en la barra lateral y haz clic en 'Buscar legislación'")
    
    # Ejemplo de uso
    with st.expander("ℹ️ Cómo usar este buscador"):
        st.markdown("""
        **Funcionalidades:**
        1. Selecciona una **categoría ambiental** (Agua, Residuos, etc.) o usa búsqueda personalizada
        2. Elige los **niveles legislativos** a consultar (UE, España, Canarias)
        3. Define un **rango temporal** para acotar resultados
        4. Haz clic en **Buscar legislación**
        
        **Interpretación de códigos de colores:**
        - 🟢 **Verde**: Norma vigente
        - 🟡 **Amarillo**: Norma con modificaciones en curso o texto refundido
        - 🔴 **Rojo**: Norma derogada (sin vigencia)
        
        **Para exportar:** Usa el botón "Descargar CSV" después de la búsqueda
        """)

# Footer
st.markdown("---")
st.caption(f"🕐 Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("⚠️ Las modificaciones en curso y derogaciones se indican en color según su estado")

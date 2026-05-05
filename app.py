# app_v2_sin_ue.py - BUSCADOR BOE + BOC (RÁPIDO Y ESTABLE)
import streamlit as st
import pandas as pd
import requests
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup

# Configuración
st.set_page_config(page_title="Buscador Legislativo Ambiental", page_icon="🌍", layout="wide")

st.title("🔍 Buscador de Legislación Ambiental")
st.markdown("**España (BOE) | Canarias (BOC)**")
st.markdown("*Agua | Suelo | Aire | Ruido | Residuos | Radiactividad*")

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
# FUNCIÓN BOE (API REAL)
# ============================================
def buscar_boe(palabra, fecha_inicio, fecha_fin):
    resultados = []
    url = "https://www.boe.es/buscar/api.php"
    
    params = {
        'q': palabra,
        'fecha_desde': fecha_inicio.strftime("%Y%m%d"),
        'fecha_hasta': fecha_fin.strftime("%Y%m%d"),
        'coleccion': 'boe',
        'pageSize': 20
    }
    
    try:
        response = requests.get(url, params=params, timeout=12)
        if response.status_code == 200:
            data = response.json()
            for item in data.get('resultados', []):
                titulo = item.get('titulo', 'Sin título')
                estado = "✅ Vigente"
                if re.search(r'derogad[ao]|sin vigencia', titulo.lower()):
                    estado = "❌ DEROGADA"
                
                resultados.append({
                    "Título": titulo[:200],
                    "Fuente": "BOE (España)",
                    "Fecha": item.get('fecha', ''),
                    "Estado": estado,
                    "Enlace": f"https://www.boe.es{item.get('url_pdf', '')}"
                })
    except Exception as e:
        st.warning(f"⚠️ BOE: {str(e)[:80]}")
    
    return resultados

# ============================================
# FUNCIÓN BOC (SCRAPING OPTIMIZADO)
# ============================================
def buscar_boc(palabra, fecha_inicio, fecha_fin):
    resultados = []
    
    año_inicio = max(fecha_inicio.year, 2010)
    año_fin = fecha_fin.year
    
    for año in range(año_inicio, año_fin + 1):
        meses_a_buscar = range(1, 13) if año < año_fin else range(1, datetime.now().month + 1)
        
        for mes in meses_a_buscar:
            url_sumario = f"https://www.gobiernodecanarias.org/boc/sumarios/{año}/{str(mes).zfill(2)}/"
            
            try:
                response = requests.get(url_sumario, timeout=6)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    texto = soup.get_text().lower()
                    
                    if palabra.lower() in texto:
                        # Intentar extraer títulos relevantes
                        enlaces = soup.find_all('a')
                        for enlace in enlaces:
                            texto_enlace = enlace.get_text().lower()
                            if palabra.lower() in texto_enlace:
                                href = enlace.get('href', '')
                                url_completa = f"https://www.gobiernodecanarias.org{href}" if href.startswith('/') else href
                                resultados.append({
                                    "Título": enlace.get_text()[:150],
                                    "Fuente": "BOC (Canarias)",
                                    "Fecha": f"{año}-{str(mes).zfill(2)}-01",
                                    "Estado": "✅ Verificar",
                                    "Enlace": url_completa if url_completa else url_sumario
                                })
                                break
                        else:
                            resultados.append({
                                "Título": f"Contenido en BOC ({año}/{mes}) sobre '{palabra}'",
                                "Fuente": "BOC (Canarias)",
                                "Fecha": f"{año}-{str(mes).zfill(2)}-01",
                                "Estado": "✅ Verificar",
                                "Enlace": url_sumario
                            })
                time.sleep(0.3)
            except Exception:
                pass
    
    return resultados

# ============================================
# INTERFAZ
# ============================================
st.sidebar.header("🔍 Configuración")

categoria = st.sidebar.selectbox("Categoría ambiental", list(CATEGORIAS.keys()))
palabra = st.sidebar.selectbox("Palabra clave", CATEGORIAS[categoria])

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Rango temporal")
fecha_desde = st.sidebar.date_input("Desde", datetime(2010, 1, 1))
fecha_hasta = st.sidebar.date_input("Hasta", datetime.now())

st.sidebar.markdown("---")
boton_buscar = st.sidebar.button("🔍 BUSCAR LEGISLACIÓN", type="primary", use_container_width=True)

# ============================================
# RESULTADOS
# ============================================
if boton_buscar:
    st.header(f"📋 Resultados para: '{palabra}'")
    
    resultados = []
    
    # Barra de progreso
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    progress_text.text("🇪🇸 Buscando en BOE...")
    resultados_es = buscar_boe(palabra, fecha_desde, fecha_hasta)
    resultados.extend(resultados_es)
    progress_bar.progress(50)
    
    progress_text.text("🇮🇨 Buscando en BOC...")
    resultados_can = buscar_boc(palabra, fecha_desde, fecha_hasta)
    resultados.extend(resultados_can)
    progress_bar.progress(100)
    
    progress_text.empty()
    progress_bar.empty()
    
    if resultados:
        st.success(f"✅ Total: {len(resultados)} resultados")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📄 Total", len(resultados))
        col2.metric("🇪🇸 BOE", len([r for r in resultados if "BOE" in r["Fuente"]]))
        col3.metric("🇮🇨 BOC", len([r for r in resultados if "BOC" in r["Fuente"]]))
        
        df = pd.DataFrame(resultados)
        st.dataframe(df[["Título", "Fuente", "Fecha", "Estado"]], use_container_width=True)
        
        with st.expander("🔗 Enlaces directos"):
            for _, row in df.iterrows():
                st.markdown(f"**{row['Título'][:100]}** ({row['Fuente']}) - {row['Fecha']}")
                st.markdown(f"[🔗 Ver documento]({row['Enlace']})")
                st.markdown("---")
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar CSV", csv, f"legislacion_{palabra}.csv", "text/csv")
    else:
        st.warning("No se encontraron resultados")

else:
    st.info("👈 Selecciona categoría y palabra clave, luego haz clic en BUSCAR")
    
    with st.expander("ℹ️ Fuentes de datos"):
        st.markdown("""
        - **BOE:** API oficial del Boletín Oficial del Estado (tiempo real)
        - **BOC:** Scraping de sumarios del Boletín Oficial de Canarias
        - **Rango:** Desde 2010 hasta actualidad
        """)

st.caption(f"Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

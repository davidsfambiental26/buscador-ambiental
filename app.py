import streamlit as st
import pandas as pd
import requests
from datetime import date
from bs4 import BeautifulSoup

# Configuración de la página
st.set_page_config(page_title="Monitor Ambiental Legal", layout="wide")

# --- LISTADO DESPLEGABLE (MANTENIDO INTACTO) ---
MATERIAS_SGA = {
    "Residuos": "residuos",
    "Emisiones Atmosféricas": "emisiones atmósfera",
    "Vertidos y Aguas": "vertidos aguas",
    "Suelos Contaminados": "suelos contaminados",
    "Evaluación de Impacto Ambiental": "impacto ambiental",
    "Cambio Climático y Energía": "cambio climático",
    "Ruidos y Vibraciones": "ruido",
    "Sustancias Químicas (REACH/CLP)": "sustancias químicas",
    "Responsabilidad Medioambiental": "responsabilidad medioambiental",
    "Envases y Embalajes": "envases",
    "Eficiencia Energética": "eficiencia energética",
    "Biodiversidad y Espacios Protegidos": "biodiversidad"
}

# --- FUNCIÓN DE CONSULTA EUROPA (SPARQL) ---
def buscar_eurlex(termino, f_inicio, f_fin):
    endpoint = "https://publications.europa.eu/webapi/rdf/sparql"
    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    SELECT DISTINCT ?celex ?title ?date WHERE {{
      ?work cdm:resource_legal_id_celex ?celex .
      ?work cdm:work_date_document ?date .
      ?work cdm:work_has_title ?title_res .
      ?title_res cdm:title_has_content ?title .
      FILTER(lang(?title) = "es")
      FILTER(CONTAINS(LCASE(?title), "{termino.lower()}"))
      FILTER(?date >= "{f_inicio}"^^<http://www.w3.org/2001/XMLSchema#date>)
      FILTER(?date <= "{f_fin}"^^<http://www.w3.org/2001/XMLSchema#date>)
    }} ORDER BY DESC(?date) LIMIT 50
    """
    try:
        r = requests.get(
            endpoint,
            params={'query': query},
            headers={'Accept': 'application/sparql-results+json'},
            timeout=20
        )
        if r.status_code == 200:
            res = r.json()['results']['bindings']
            return [
                {
                    "Fecha": b['date']['value'],
                    "Normativa": b['title']['value'],
                    "Enlace": f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{b['celex']['value']}"
                }
                for b in res
            ]
    except Exception as e:
        st.error(f"Error consultando EUR-Lex: {e}")
        return []
    return []

# --- FUNCIÓN DE CONSULTA BOE (SCRAPING) ---
def buscar_boe(termino, f_inicio, f_fin):
    # BOE sólo permite filtrar por año en este buscador sencillo
    url = (
        "https://www.boe.es/buscar/boe.php"
        f"?campo=tit&dato={termino}&operador=AND&punto_leg=on"
        f"&fmin={f_inicio.year}&fmax={f_fin.year}"
    )
    resultados = []
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return resultados

        soup = BeautifulSoup(r.text, "html.parser")

        # Cada resultado suele ir en elementos con clase 'resultado-busqueda'
        bloques = soup.select(".resultado-busqueda")
        for b in bloques:
            # Título
            a = b.select_one("a")
            if not a:
                continue
            titulo = a.get_text(strip=True)
            enlace = "https://www.boe.es" + a.get("href", "")

            # Fecha (suele aparecer en un <span> o <p> con clase 'fecha')
            fecha_el = b.select_one(".fecha")
            fecha = fecha_el.get_text(strip=True) if fecha_el else ""

            resultados.append(
                {
                    "Fecha": fecha,
                    "Normativa": titulo,
                    "Enlace": enlace
                }
            )
    except Exception as e:
        st.error(f"Error consultando BOE: {e}")
        return []

    return resultados

# --- FUNCIÓN DE CONSULTA BOC (SCRAPING) ---
def buscar_boc(termino, f_inicio, f_fin):
    # El buscador del BOC no filtra tan fino por fecha en la URL,
    # pero podemos usar el término y luego filtrar por fecha en el texto si aparece.
    url = (
        "https://www.gobiernodecanarias.org/juridico/boc/buscar.jsp"
        f"?busqueda={termino}"
    )
    resultados = []
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return resultados

        soup = BeautifulSoup(r.text, "html.parser")

        # La estructura puede variar; aquí se asume que cada resultado está en un <tr> o <div> con clase 'resultado'
        filas = soup.select("tr, div.resultado")
        for fila in filas:
            a = fila.select_one("a")
            if not a:
                continue
            titulo = a.get_text(strip=True)
            enlace = a.get("href", "")
            if enlace.startswith("/"):
                enlace = "https://www.gobiernodecanarias.org" + enlace

            # Intento de extracción de fecha si aparece en alguna celda o span
            texto_fila = fila.get_text(" ", strip=True)
            # No hay un patrón único; se podría mejorar con regex.
            fecha = ""
            # Aquí podrías añadir lógica de regex para detectar dd/mm/aaaa

            resultados.append(
                {
                    "Fecha": fecha,
                    "Normativa": titulo,
                    "Enlace": enlace
                }
            )
    except Exception as e:
        st.error(f"Error consultando BOC: {e}")
        return []

    return resultados

# --- INTERFAZ ---
st.title("⚖️ Buscador Legislativo de Materias Ambientales")

with st.sidebar:
    st.header("Filtros temporales")
    f_ini = st.date_input(
        "Fecha inicial:",
        value=date(1990, 1, 1),
        min_value=date(1990, 1, 1)
    )
    f_fin = st.date_input(
        "Fecha final:",
        value=date.today()
    )

    st.divider()
    seleccion = st.selectbox("Aspecto ambiental:", list(MATERIAS_SGA.keys()))
    termino = MATERIAS_SGA[seleccion]

    ejecutar = st.button("🔍 Obtener listados")

if ejecutar:
    # 1. NIVEL EUROPEO
    st.subheader(f"🇪🇺 Directivas y Reglamentos Europeos ({seleccion})")
    with st.spinner("Consultando EUR-Lex..."):
        listado_eu = buscar_eurlex(termino, f_ini.isoformat(), f_fin.isoformat())
        if listado_eu:
            df_eu = pd.DataFrame(listado_eu)
            st.dataframe(
                df_eu,
                column_config={"Enlace": st.column_config.LinkColumn("Abrir norma")},
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning("EUR-Lex no devolvió resultados para este término en el rango elegido.")

    # 2. NIVEL ESTATAL (BOE)
    st.subheader(f"🇪🇸 Normativa estatal (BOE) sobre {seleccion}")
    with st.spinner("Consultando BOE..."):
        listado_boe = buscar_boe(termino, f_ini, f_fin)
        if listado_boe:
            df_boe = pd.DataFrame(listado_boe)
            st.dataframe(
                df_boe,
                column_config={"Enlace": st.column_config.LinkColumn("Abrir norma")},
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No se han encontrado resultados en el BOE con los filtros actuales.")

    # 3. NIVEL AUTONÓMICO CANARIO (BOC)
    st.subheader(f"🏝️ Normativa autonómica canaria (BOC) sobre {seleccion}")
    with st.spinner("Consultando BOC..."):
        listado_boc = buscar_boc(termino, f_ini, f_fin)
        if listado_boc:
            df_boc = pd.DataFrame(listado_boc)
            st.dataframe(
                df_boc,
                column_config={"Enlace": st.column_config.LinkColumn("Abrir norma")},
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No se han encontrado resultados en el BOC con los filtros actuales.")

st.divider()
st.caption(
    "Nota profesional: este panel está pensado como apoyo al SGA; "
    "verifique siempre la vigencia de la norma en el diario oficial."
)

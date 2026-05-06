import streamlit as st
import pandas as pd
import requests
from datetime import date

# ---------------------------------------------------------
# CONFIGURACIÓN BÁSICA
# ---------------------------------------------------------
st.set_page_config(page_title="Monitor Ambiental Legal (SGA)", layout="wide")

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

# ---------------------------------------------------------
# FUNCIÓN EUR-LEX (SPARQL)
# ---------------------------------------------------------
def buscar_eurlex(termino: str, f_inicio: date, f_fin: date):
    """
    Consulta básica a EUR-Lex vía SPARQL.
    Devuelve lista de dicts con Fecha, Normativa, Enlace.
    """
    endpoint = "https://publications.europa.eu/webapi/rdf/sparql"

    # Fechas en formato ISO (yyyy-mm-dd)
    f_ini_str = f_inicio.isoformat()
    f_fin_str = f_fin.isoformat()

    # Relajamos un poco el filtro: quitamos lang="es" para no vaciar resultados
    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    SELECT DISTINCT ?celex ?title ?date WHERE {{
      ?work cdm:resource_legal_id_celex ?celex .
      ?work cdm:work_date_document ?date .
      ?work cdm:work_has_title ?title_res .
      ?title_res cdm:title_has_content ?title .
      FILTER(CONTAINS(LCASE(?title), "{termino.lower()}"))
      FILTER(?date >= "{f_ini_str}"^^<http://www.w3.org/2001/XMLSchema#date>)
      FILTER(?date <= "{f_fin_str}"^^<http://www.w3.org/2001/XMLSchema#date>)
    }} ORDER BY DESC(?date) LIMIT 50
    """

    try:
        r = requests.get(
            endpoint,
            params={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=20,
        )
        if r.status_code != 200:
            return []

        data = r.json()
        bindings = data.get("results", {}).get("bindings", [])

        resultados = []
        for b in bindings:
            fecha = b.get("date", {}).get("value", "")
            titulo = b.get("title", {}).get("value", "")
            celex = b.get("celex", {}).get("value", "")
            enlace = f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{celex}"

            resultados.append(
                {
                    "Fecha": fecha,
                    "Normativa": titulo,
                    "Enlace": enlace,
                }
            )

        return resultados

    except Exception:
        # En producción podrías loguear el error
        return []

# ---------------------------------------------------------
# INTERFAZ STREAMLIT
# ---------------------------------------------------------
st.title("⚖️ Buscador Legislativo Ambiental para SGA")

with st.sidebar:
    st.header("Filtros temporales")
    f_ini = st.date_input(
        "Fecha inicial",
        value=date(1990, 1, 1),
        min_value=date(1990, 1, 1),
    )
    f_fin = st.date_input(
        "Fecha final",
        value=date.today(),
    )

    st.divider()
    seleccion = st.selectbox("Aspecto ambiental", list(MATERIAS_SGA.keys()))
    termino = MATERIAS_SGA[seleccion]

    ejecutar = st.button("🔍 Buscar legislación")

if ejecutar:
    # ---------------- EUR-LEX ----------------
    st.subheader(f"🇪🇺 Legislación europea (EUR-Lex) sobre {seleccion}")
    with st.spinner("Consultando EUR-Lex..."):
        eu = buscar_eurlex(termino, f_ini, f_fin)

    if eu:
        df_eu = pd.DataFrame(eu)
        st.dataframe(
            df_eu,
            column_config={"Enlace": st.column_config.LinkColumn("Abrir norma")},
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.warning("EUR-Lex no devolvió resultados para este término en el rango elegido.")

    # ---------------- BOE (ENLACES DIRECTOS) ----------------
    st.subheader(f"🇪🇸 Legislación estatal (BOE) sobre {seleccion}")
    st.info(
        "Por estabilidad y cambios frecuentes en el HTML del BOE, "
        "se muestran enlaces directos al buscador oficial."
    )

    url_boe = (
        "https://www.boe.es/buscar/boe.php?"
        f"campo=tit&dato={termino}&operador=AND&punto_leg=on"
        f"&fmin={f_ini.year}&fmax={f_fin.year}"
    )

    df_boe = pd.DataFrame(
        [
            {
                "Nivel": "ESTATAL (BOE)",
                "Descripción": f"Leyes y Reales Decretos sobre {seleccion}",
                "Acceso": url_boe,
            }
        ]
    )

    st.dataframe(
        df_boe,
        column_config={"Acceso": st.column_config

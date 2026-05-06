import streamlit as st
import pandas as pd
import requests
from datetime import date
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Monitor Ambiental Legal", layout="wide")

MATERIAS_SGA = {
    "Residuos": "residuos",
    "Emisiones Atmosféricas": "emisiones",
    "Vertidos y Aguas": "vertidos",
    "Suelos Contaminados": "suelos",
    "Evaluación de Impacto Ambiental": "impacto ambiental",
    "Cambio Climático y Energía": "cambio climático",
    "Ruidos y Vibraciones": "ruido",
    "Sustancias Químicas (REACH/CLP)": "químicas",
    "Responsabilidad Medioambiental": "responsabilidad",
    "Envases y Embalajes": "envases",
    "Eficiencia Energética": "eficiencia energética",
    "Biodiversidad y Espacios Protegidos": "biodiversidad"
}

# ---------------- EUR-LEX API ----------------
def buscar_eurlex(termino, f_ini, f_fin):
    url = (
        "https://eur-lex.europa.eu/api/search?"
        f"lang=es&query=title={termino}&page=1&pageSize=50"
        f"&dateFrom={f_ini}&dateTo={f_fin}"
    )

    try:
        r = requests.get(url, timeout=20)
        data = r.json()

        resultados = []
        for item in data.get("results", []):
            resultados.append({
                "Fecha": item.get("date", ""),
                "Normativa": item.get("title", ""),
                "Enlace": item.get("url", "")
            })

        return resultados

    except:
        return []

# ---------------- BOE API XML ----------------
def buscar_boe(termino):
    url = f"https://www.boe.es/buscar/legislacion.php?campo=tit&texto={termino}&format=xml"
    r = requests.get(url, timeout=20)

    resultados = []
    root = ET.fromstring(r.text)

    for item in root.findall(".//item"):
        titulo = item.findtext("titulo", "")
        fecha = item.findtext("fecha_disposicion", "")
        enlace = item.findtext("url_pdf", "")

        resultados.append({
            "Fecha": fecha,
            "Normativa": titulo,
            "Enlace": enlace
        })

    return resultados

# ---------------- BOC API XML ----------------
def buscar_boc(termino):
    url = f"https://www.gobiernodecanarias.org/boc/buscar.jsp?tipo=1&texto={termino}&format=xml"
    r = requests.get(url, timeout=20)

    resultados = []
    root = ET.fromstring(r.text)

    for item in root.findall(".//item"):
        titulo = item.findtext("titulo", "")
        fecha = item.findtext("fecha", "")
        enlace = item.findtext("url", "")

        resultados.append({
            "Fecha": fecha,
            "Normativa": titulo,
            "Enlace": enlace
        })

    return resultados

# ---------------- INTERFAZ ----------------
st.title("⚖️ Buscador Legislativo Ambiental (SGA)")

with st.sidebar:
    f_ini = st.date_input("Fecha inicial", value=date(1990,1,1))
    f_fin = st.date_input("Fecha final", value=date.today())
    seleccion = st.selectbox("Aspecto ambiental", list(MATERIAS_SGA.keys()))
    termino = MATERIAS_SGA[seleccion]
    ejecutar = st.button("Buscar legislación")

if ejecutar:

    # EUR-Lex
    st.subheader("🇪🇺 Legislación Europea")
    eu = buscar_eurlex(termino, f_ini.isoformat(), f_fin.isoformat())
    st.dataframe(pd.DataFrame(eu)) if eu else st.warning("Sin resultados")

    # BOE
    st.subheader("🇪🇸 Legislación Estatal (BOE)")
    boe = buscar_boe(termino)
    st.dataframe(pd.DataFrame(boe)) if boe else st.warning("Sin resultados")

    # BOC
    st.subheader("🏝️ Legislación Canaria (BOC)")
    boc = buscar_boc(termino)
    st.dataframe(pd.DataFrame(boc)) if boc else st.warning("Sin resultados")

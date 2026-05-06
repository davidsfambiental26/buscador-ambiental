import streamlit as st
import pandas as pd
import requests
from datetime import date
from bs4 import BeautifulSoup

st.set_page_config(page_title="Monitor Ambiental Legal", layout="wide")

MATERIAS_SGA = {
    "Residuos": "waste",
    "Emisiones Atmosféricas": "air",
    "Vertidos y Aguas": "water",
    "Suelos Contaminados": "soil",
    "Evaluación de Impacto Ambiental": "impact",
    "Cambio Climático y Energía": "climate",
    "Ruidos y Vibraciones": "noise",
    "Sustancias Químicas (REACH/CLP)": "chemical",
    "Responsabilidad Medioambiental": "liability",
    "Envases y Embalajes": "packaging",
    "Eficiencia Energética": "energy",
    "Biodiversidad y Espacios Protegidos": "biodiversity"
}

# ---------------- EUR-LEX (REST API) ----------------
def buscar_eurlex(termino, f_ini, f_fin):
    url = "https://eur-lex.europa.eu/EURLexWebService"
    params = {
        "WS": "search",
        "lang": "es",
        "type": "legislation",
        "keyword": termino,
        "dateFrom": f_ini,
        "dateTo": f_fin,
        "page": 1
    }

    try:
        r = requests.get(url, params=params, timeout=20)
        data = r.json()

        resultados = []
        for item in data.get("results", []):
            resultados.append({
                "Fecha": item.get("date", ""),
                "Normativa": item.get("title", ""),
                "Enlace": item.get("url", "")
            })

        return resultados

    except Exception as e:
        st.error(f"Error EUR-Lex: {e}")
        return []

# ---------------- BOE ----------------
def buscar_boe(termino, f_ini, f_fin):
    url = f"https://www.boe.es/buscar/boe.php?campo=tit&dato={termino}&fmin={f_ini.year}&fmax={f_fin.year}"

    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=20)

    soup = BeautifulSoup(r.text, "html.parser")
    bloques = soup.select("div.resultado")

    resultados = []
    for b in bloques:
        a = b.find("a")
        if not a:
            continue

        titulo = a.text.strip()
        enlace = "https://www.boe.es" + a["href"]

        fecha = ""
        f = b.find("span", class_="fecha")
        if f:
            fecha = f.text.strip()

        resultados.append({
            "Fecha": fecha,
            "Normativa": titulo,
            "Enlace": enlace
        })

    return resultados

# ---------------- BOC ----------------
def buscar_boc(termino):
    url = f"https://www.gobiernodecanarias.org/boc/buscar.jsp?tipo=1&texto={termino}"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    resultados = []
    filas = soup.select("div.resultado-busqueda")

    for fila in filas:
        a = fila.find("a")
        if not a:
            continue

        titulo = a.text.strip()
        enlace = a["href"]
        if enlace.startswith("/"):
            enlace = "https://www.gobiernodecanarias.org" + enlace

        resultados.append({
            "Fecha": "",
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
    boe = buscar_boe(termino, f_ini, f_fin)
    st.dataframe(pd.DataFrame(boe)) if boe else st.warning("Sin resultados")

    # BOC
    st.subheader("🏝️ Legislación Canaria (BOC)")
    boc = buscar_boc(termino)
    st.dataframe(pd.DataFrame(boc)) if boc else st.warning("Sin resultados")

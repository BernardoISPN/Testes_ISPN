import streamlit as st
import pandas as pd
import geopandas as gpd
import geobr
import pydeck as pdk
import time
import numpy as np

st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded"
)


st.write("")
st.write("")
st.write("")

# ==============================
# PROTEÇÃO POR SENHA
# ==============================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    
    container_logo = st.container(horizontal_alignment="center")

    container_logo.image("https://fundoecos.org.br/wp-content/uploads/2025/05/Logo-Fundo-Ecos-PNG-sem-fundo-sem-margem.png", width=300)

    # Colunas para centralizar
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)

        st.subheader("Mapa CGN - Edital 45")

        st.write("")

        senha_digitada = st.text_input(
            "Digite a senha",
            type="password",
        )

        st.write("")

        if st.button("Entrar"):
            if senha_digitada == st.secrets["senha"]["app_password"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Senha incorreta")

    st.stop()

st.logo("https://fundoecos.org.br/wp-content/uploads/2025/05/Logo-Fundo-Ecos-PNG-sem-fundo-sem-margem.png", size="large")

st.sidebar.markdown("## Filtros")
st.sidebar.write("")

tipo_visualizacao = st.sidebar.radio(
    "Selecione a origem dos votos:",
    ["CT", "CGN"],
    horizontal=True,
    key="tipo_visualizacao"
)

# Detecta mudança CT/CGN
if "tipo_visualizacao_anterior" not in st.session_state:
    st.session_state.tipo_visualizacao_anterior = tipo_visualizacao

if tipo_visualizacao != st.session_state.tipo_visualizacao_anterior:

    # limpa checkboxes dos projetos
    for k in list(st.session_state.keys()):
        if k.startswith("peq_") or k.startswith("cons_"):
            del st.session_state[k]

    # reset filtros principais
    st.session_state["ver_estados"] = False
    st.session_state["mostrar_pequenos"] = True
    st.session_state["mostrar_consolidacao"] = True

    st.session_state.tipo_visualizacao_anterior = tipo_visualizacao
    st.rerun()
    
if tipo_visualizacao == "CT":
    st.subheader(f"Projetos que receberam votos da CT - Edital 45")
else:
    st.subheader(f"Projetos que receberam votos do CGN - Edital 45")

st.write("")
st.write("")
st.write("")


# ==============================
# CONFIGURAÇÕES
# ==============================
sheet_id = st.secrets["google"]["sheet_id"]
if tipo_visualizacao == "CT":
    gid_pequenos = st.secrets["google"]["gid_pequenos_ct"]
    gid_consolidacao = st.secrets["google"]["gid_consolidacao_ct"]

else:  # CGN
    gid_pequenos = st.secrets["google"]["gid_pequenos_cgn"]
    gid_consolidacao = st.secrets["google"]["gid_consolidacao_cgn"]

url_pequenos = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_pequenos}"
url_consolidacao = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_consolidacao}"

# ==============================
# CARREGAR PLANILHAS
# ==============================
@st.cache_data
def carregar_dados(url_pequenos, url_consolidacao):
    df_peq = pd.read_csv(url_pequenos)
    df_cons = pd.read_csv(url_consolidacao)

    df_peq["tipo"] = "Pequeno"
    df_cons["tipo"] = "Consolidação"

    df = pd.concat([df_peq, df_cons], ignore_index=True)
    df["Município Principal"] = pd.to_numeric(
        df["Município Principal"],
        errors="coerce"
    )

    df = df.dropna(subset=["Município Principal"])
    df["Município Principal"] = df["Município Principal"].astype(int)
    df["ranking_str"] = df["Ranking por votos"].astype(str)
    
    df["ranking_num"] = (
        df["ranking_str"]
        .str.split(",")
        .str[0]
        .astype(int)
    )

    return df

df = carregar_dados(url_pequenos, url_consolidacao)


# ==============================
# FILTROS NA SIDEBAR (COM FORM)
# ==============================

# Criar label completa antes do form
df["label_projeto"] = (
    df["Ranking por votos"].astype(str)
    + " - "
    + "**" + df["Número projeto"].astype(str) + "**"
    + " - "
    + df["Nome da organização"].astype(str)
)

df = df.sort_values(["ranking_num", "tipo"])

with st.sidebar.form("filtros_form", border=False):
    
    st.divider()
    
    ver_estados = st.checkbox(
        "Ver estados (pode aumentar o tempo de carregamento da página)",
        value=False,
        key="ver_estados"
    )
    
    st.divider()

    # ======================
    # CHECKBOX GERAL POR TIPO
    # ======================
    
    col1, col2 = st.columns(2)
    mostrar_pequenos = col1.checkbox(
        "Projetos Pequenos",
        value=True,
        key="mostrar_pequenos"
    )
    
    mostrar_consolidacao = col2.checkbox(
        "Projetos Consolidação",
        value=True,
        key="mostrar_consolidacao"
    )

    st.divider()

    projetos_selecionados = []

    # ======================
    # COLUNAS LADO A LADO
    # ======================

    col1, col2 = st.columns(2)

    # COLUNA PEQUENOS
    with col1:
        if mostrar_pequenos:
            st.markdown("### 🔵 Pequenos")

            df_peq = df[df["tipo"] == "Pequeno"]

            for _, row in df_peq.iterrows():
                checked = st.checkbox(
                    row["label_projeto"],
                    value=True,
                    key=f"peq_{row['Número projeto']}"
                )
                if checked:
                    projetos_selecionados.append(row["label_projeto"])

    # COLUNA CONSOLIDAÇÃO
    with col2:
        if mostrar_consolidacao:
            st.markdown("### 🔴 Consolidação")

            df_cons = df[df["tipo"] == "Consolidação"]

            for _, row in df_cons.iterrows():
                checked = st.checkbox(
                    row["label_projeto"],
                    value=True,
                    key=f"cons_{row['Número projeto']}"
                )
                if checked:
                    projetos_selecionados.append(row["label_projeto"])
                    
    st.write("")

    aplicar_filtros = st.form_submit_button("Aplicar filtros")

# Só filtra depois que clicar no botão
if aplicar_filtros:

    tipos = []
    if mostrar_pequenos:
        tipos.append("Pequeno")
    if mostrar_consolidacao:
        tipos.append("Consolidação")

    df = df[df["tipo"].isin(tipos)]
    df = df[df["label_projeto"].isin(projetos_selecionados)]

# ==============================
# GEO
# ==============================
@st.cache_resource
def carregar_geo():

    municipios = geobr.read_municipality(
        year=2020,
        simplified=True
    )

    estados_desejados = [
        "GO","TO","MA","CE","PI","BA","PE","RN","PB",
        "AL","SE","MG","MT","MS","DF"
    ]

    municipios = municipios[
        municipios["abbrev_state"].isin(estados_desejados)
    ]

    biomas = geobr.read_biomes(year=2019)
    biomas = biomas[biomas["name_biome"].isin(["Cerrado", "Caatinga"])]
    biomas = biomas.to_crs(epsg=4326)

    cerrado = biomas[biomas["name_biome"] == "Cerrado"]
    caatinga = biomas[biomas["name_biome"] == "Caatinga"]

    return municipios, cerrado, caatinga

municipios, cerrado, caatinga = carregar_geo()

@st.cache_resource
def carregar_estados():
    estados = geobr.read_state(year=2020, simplified=True)

    estados_desejados = [
        "Mato Grosso","Mato Grosso Do Sul","Distrito Federal",
        "Goiás","Tocantins","Maranhão","Ceará","Piauí","Bahia",
        "Pernambuco","Rio Grande Do Norte","Paraíba","Alagoas",
        "Sergipe","Minas Gerais"
    ]

    estados = estados[estados["name_state"].isin(estados_desejados)]
    estados = estados.to_crs(epsg=4326)

    return estados

@st.cache_data(show_spinner=False)
def preparar_mapa(df_filtrado):

    codigos_municipios = df_filtrado["Município Principal"].unique()

    municipios_filtrados = municipios[
        municipios["code_muni"].isin(codigos_municipios)
    ]

    df_geo = municipios_filtrados.merge(
        df_filtrado,
        left_on="code_muni",
        right_on="Município Principal",
        how="inner"
    )

    df_geo_proj = df_geo.to_crs(epsg=5880)
    df_geo_proj["geometry"] = df_geo_proj.geometry.centroid
    df_geo = df_geo_proj.to_crs(epsg=4326)

    df_geo["lon"] = df_geo.geometry.x
    df_geo["lat"] = df_geo.geometry.y
    df_geo = df_geo.drop(columns="geometry")

    df_pontos, df_linhas = criar_spiderfy(df_geo)

    df_pontos["color"] = df_pontos["tipo"].map({
        "Pequeno": [52, 152, 219],
        "Consolidação": [231, 76, 60]
    })

    df_pontos["ranking_num"] = (
        df_pontos["ranking_str"]
        .str.split(",")
        .str[0]
        .astype(int)
    )

    df_pontos["radius"] = 30 - (df_pontos["ranking_num"] * 1.2)
    df_pontos["radius"] = df_pontos["radius"].clip(lower=10)

    return (
        df_pontos.to_dict("records"),
        df_linhas.to_dict("records")
    )

# ==============================
# SPIDERFY
# ==============================
@st.cache_data
def criar_spiderfy(df, raio_km=10):
    df = df.copy()
    pontos = []
    linhas = []

    for muni, group in df.groupby("Município Principal"):
        centro_lat = group.iloc[0]["lat"]
        centro_lon = group.iloc[0]["lon"]
        n = len(group)

        raio = raio_km / 111
        angles = np.linspace(0, 2*np.pi, n, endpoint=False)

        for i, (_, row) in enumerate(group.iterrows()):
            if n == 1:
                lat = centro_lat
                lon = centro_lon
            else:
                lat = centro_lat + raio * np.sin(angles[i])
                lon = centro_lon + raio * np.cos(angles[i])

            linhas.append({
                "source": [centro_lon, centro_lat],
                "target": [lon, lat]
            })

            novo = row.copy()
            novo["lat_plot"] = lat
            novo["lon_plot"] = lon
            pontos.append(novo)

    return pd.DataFrame(pontos), pd.DataFrame(linhas)

df_pontos, df_linhas = preparar_mapa(df)

# ==============================
# CAMADAS 
# ==============================

cerrado_layer = pdk.Layer(
    "GeoJsonLayer",
    data=cerrado.__geo_interface__,
    opacity=0.01,  
    stroked=True,
    filled=True,
    get_fill_color=[46, 204, 113],
    get_line_color=[0, 0, 0],
)

caatinga_layer = pdk.Layer(
    "GeoJsonLayer",
    data=caatinga.__geo_interface__,
    opacity=0.01,  
    stroked=True,
    filled=True,
    get_fill_color=[241, 196, 15],
    get_line_color=[0, 0, 0],
)

estados_layer = None

if ver_estados:
    estados = carregar_estados()

    estados_layer = pdk.Layer(
        "GeoJsonLayer",
        data=estados.__geo_interface__,
        stroked=True,
        filled=False,
        get_line_color=[0, 0, 0],
        get_line_width=0.5,
        line_width_min_pixels=0.5,
    )

linhas_layer = pdk.Layer(
    "LineLayer",
    data=df_linhas,  
    get_source_position="source",
    get_target_position="target",
    get_width=2,
    get_color=[120, 120, 120],
)

pontos_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_pontos, 
    get_position='[lon_plot, lat_plot]',
    get_fill_color='color',
    pickable=True,
    radiusUnits="pixels",
    get_radius=1,           
    radiusMinPixels=15,       
    radiusMaxPixels=22,      
)

texto_layer = pdk.Layer(
    "TextLayer",
    data=df_pontos,
    get_position='[lon_plot, lat_plot]',
    get_text="ranking_str",
    get_size=12,
    get_color=[0, 0, 0],
)

# ==============================
# VIEW
# ==============================
view = pdk.ViewState(
    latitude=-14,
    longitude=-52,
    zoom=4,
)

# ==============================
# MAPA
# ==============================
layers = [
    cerrado_layer,
    caatinga_layer,
    pontos_layer,
    texto_layer,
    linhas_layer,
]

if estados_layer:
    layers.insert(2, estados_layer)  # insere abaixo dos biomas

deck = pdk.Deck(
    layers=layers,
    initial_view_state=view,
    map_style="light",
    tooltip={
        "html": """
        <b>Código do projeto:</b> {Número projeto}<br/>
        <b>Município:</b> {name_muni} - {abbrev_state}<br/>
        <b>Organização:</b> {Nome da organização}<br/>
        <b>Nome do projeto:</b> {Nome do projeto}<br/>
        <b>Número de famílias beneficiadas:</b> {Número de famílias beneficiadas}<br/>
        """,
        "style": {
            "backgroundColor": "white",
            "color": "black",
            "fontSize": "13px",
            "border": "1px solid #ccc",
            "borderRadius": "6px",
            "padding": "8px"
        }
    }
)

st.pydeck_chart(deck, width="stretch", height=950)
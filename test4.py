import streamlit as st
import geopandas as gpd
import folium
from folium import Choropleth, LayerControl
from streamlit_folium import st_folium
import plotly.express as px
import ZipFile
import os

# Pré-cálculo das estatísticas de risco médio e arredondado
# Carregar dados
malha_viaria = gpd.read_file('Risco.geojson')
hexagonos_h3 = gpd.read_file('H3.geojson')

# Calcular risco médio por hexágono e salvar os resultados
if 'risk_mean_rounded' not in hexagonos_h3.columns:
    for index, row in hexagonos_h3.iterrows():
        segmentos_no_hex = malha_viaria[malha_viaria.intersects(row.geometry)]
        if not segmentos_no_hex.empty:
            hexagonos_h3.loc[index, 'risk_mean'] = segmentos_no_hex['KmP'].mean()
            hexagonos_h3.loc[index, 'risk_mean_rounded'] = segmentos_no_hex['KmP'].mean().round()
        else:
            hexagonos_h3.loc[index, 'risk_mean'] = 0
            hexagonos_h3.loc[index, 'risk_mean_rounded'] = 0

    # Salvar o GeoDataFrame com estatísticas pré-calculadas
    hexagonos_h3.to_file('hexagonos_h3_com_risco.geojson', driver='GeoJSON')

#Verificar e descompactar o arquivo
if not os.path.exists("MUN_SP.geojson"):
    with ZipFile("MUN_SP.zip","r") as zip_ref:
        zip_ref.extractall(".")

# Carregar dados processados
hexagonos_h3 = gpd.read_file('hexagonos_h3_com_risco.geojson')
areas_urbanas = gpd.read_file('AU.geojson')
municipios = gpd.read_file('MUN_SP.geojson')

# Configuração do Streamlit
st.set_page_config(page_title="Dashboard Interativo - Risco de Atropelamento", layout="wide")

st.title("Dashboard Interativo: Risco de Atropelamento no Estado de São Paulo")

# Layout da página
st.sidebar.header("Configurações")
selected_municipio = st.sidebar.selectbox("Selecione um município:", municipios['NM_MUN'].unique())
show_areas_urbanas = st.sidebar.button("Mostrar/Esconder Áreas Urbanas")

# Filtrar município selecionado
municipio_selecionado = municipios[municipios['NM_MUN'] == selected_municipio]

# Criar mapa
m = folium.Map(location=[-23.55, -46.63], zoom_start=7, tiles="OpenStreetMap")

# Adicionar camada de hexágonos com risco médio
Choropleth(
    geo_data=hexagonos_h3,
    data=hexagonos_h3,
    columns=["index", "risk_mean_rounded"],
    key_on="feature.properties.index",
    fill_color="RdYlGn_r",  # Escala de cores de verde (baixo) a vermelho (alto)
    fill_opacity=0.4,  # Maior transparência
    line_opacity=0.2,
    legend_name="Risco Médio"
).add_to(m)

# Adicionar camada de áreas urbanas (opcional)
if show_areas_urbanas:
    folium.GeoJson(areas_urbanas, name="Áreas Urbanas", style_function=lambda x: {'color': 'gray', 'weight': 0.5, 'fillOpacity': 0.3}).add_to(m)

# Adicionar camada do município selecionado
folium.GeoJson(municipio_selecionado, name="Município", style_function=lambda x: {'color': 'blue', 'weight': 2}).add_to(m)

# Adicionar controle de camadas
LayerControl().add_to(m)

# Exibir mapa no Streamlit
st_folium(m, width=800, height=500)

# Seção de gráfico
st.sidebar.header("Distribuição de Risco por Categoria")

# Verificar se as geometrias são válidas antes de unir
municipio_selecionado = municipio_selecionado[municipio_selecionado.is_valid]

# Filtrar hexágonos que intersectam o município selecionado
hex_no_municipio = hexagonos_h3[hexagonos_h3.intersects(municipio_selecionado.unary_union)]

# Calcular % de risco por categoria
risco_percentual = hex_no_municipio['risk_mean_rounded'].value_counts(normalize=True).reset_index()
risco_percentual.columns = ["Categoria de Risco", "%"]
risco_percentual["%"] *= 100

# Criar gráfico de anel
fig = px.pie(risco_percentual, values="%", names="Categoria de Risco", 
             title=f"Distribuição de Risco no Município: {selected_municipio}", 
             color="Categoria de Risco",
             color_discrete_map={
                 0: "#00FF00",  # Verde
                 1: "#80FF00",
                 2: "#FFFF00",
                 3: "#FFBF00",
                 4: "#FF8000",
                 5: "#FF4000",
                 6: "#FF0000"   # Vermelho
             },
             hole=0.4)  # Gráfico em anel

# Exibir gráfico no Streamlit
st.sidebar.plotly_chart(fig)

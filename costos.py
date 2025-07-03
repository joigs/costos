
import streamlit as st
import requests
from datetime import date

st.set_page_config(page_title="UF por Ascensor", layout="centered")
st.title("📊 Cálculo de UF por Ascensor (Santiago / Zona Norte)")

# Obtener valor de la UF automáticamente desde mindicador.cl
@st.cache_data
def obtener_valor_uf(fecha: str):
    try:
        response = requests.get(f"https://mindicador.cl/api/uf/{fecha}")
        data = response.json()
        return data["serie"][0]["valor"]
    except Exception:
        return None

# Zona
zona = st.selectbox("Zona", ["Santiago/Sur", "Zona Norte"])

# Fecha para valor UF
st.subheader("📅 Fecha para la UF")
hoy = date.today()
fecha_seleccionada = st.date_input("Fecha UF", min_value=hoy, value=hoy)
valor_uf = obtener_valor_uf(fecha_seleccionada.strftime("%d-%m-%Y"))

if valor_uf is None:
    st.error("No se pudo obtener el valor de la UF para esta fecha.")
    st.stop()

# Costos en CLP (como números enteros)
st.subheader("💸 Costos en pesos chilenos")
comida = st.number_input("Costo de comida", min_value=0, value=0, step=1000, format="%d")
viaje = st.number_input("Costo pasaje avión", min_value=0, value=0, step=10000, format="%d")
vehiculo = st.number_input("Costo de vehículo", min_value=0, value=0, step=1000, format="%d")
hotel = st.number_input("Costo de hotel por noche", min_value=0, value=0, step=1000, format="%d")
movilizacion = st.number_input("Costo de movilización", min_value=0, value=0, step=1000, format="%d")

# Parámetros de cálculo
st.subheader("🔢 Parámetros específicos")
ascensores = st.number_input("Cantidad de ascensores", min_value=1, max_value=100, value=5, step=1)
noches = st.number_input("Cantidad de noches", min_value=0, max_value=10, value=2, step=1)
uf_ascensor = st.number_input("UF adicional por ascensor", min_value=1.0, max_value=10.0, value=3.5, step=0.1)

# Función de cálculo
def calcular_costo(noches):
    if zona == "Santiago/Sur":
        if noches == 0:
            return comida + vehiculo
        else:
            return (noches * hotel) + ((noches + 1) * comida) + vehiculo
    elif zona == "Zona Norte":
        if noches == 0:
            return comida + viaje + movilizacion
        else:
            return (noches * hotel) + ((noches + 1) * comida) + viaje + movilizacion

# Cálculo total en UF
costo_total_clp = calcular_costo(noches)
uf_total = (costo_total_clp / valor_uf) + (ascensores * uf_ascensor)

# Resultado
st.subheader("📈 Resultado del cálculo")
st.markdown(f"**Zona:** {zona}  \n"
            f"**Fecha UF:** {fecha_seleccionada.strftime('%d-%m-%Y')}  \n"
            f"**Valor UF:** ${valor_uf:,.0f} CLP")

st.success(f"✅ Para **{ascensores} ascensores** y **{noches} noche(s)**, el valor total es: **{uf_total:.2f} UF**")


import streamlit as st
import requests
import calendar
import html
import hashlib
import bcrypt
from datetime import date
from sqlalchemy import text

st.set_page_config(page_title="UF por Ascensor", layout="wide")

if "calendario_mes" not in st.session_state:
    st.session_state.calendario_mes = date.today().month
if "calendario_anio" not in st.session_state:
    st.session_state.calendario_anio = date.today().year
if "calendario_dia" not in st.session_state:
    st.session_state.calendario_dia = date.today().day
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None
if "editor_fecha" not in st.session_state:
    st.session_state.editor_fecha = ""
if "editor_texto" not in st.session_state:
    st.session_state.editor_texto = ""

vista_actual = st.query_params.get("vista", "calendario")
if vista_actual != "costos":
    vista_actual = "calendario"

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0e1117;
    }
    div[data-testid="stButton"] {
        margin-bottom: 0rem;
    }
    div.element-container:has(div[data-testid="stButton"]) {
        margin-bottom: -0.55rem !important;
    }
    div.element-container:has(.calendar-weekday) {
        margin-bottom: 1.55rem !important;
    }
    .login-box {
        background: #111827;
        border: 1px solid #374151;
        border-radius: 16px;
        padding: 22px;
        margin-top: 90px;
    }
    .session-pill {
        display: inline-block;
        background: #111827;
        border: 1px solid #374151;
        border-radius: 999px;
        padding: 7px 12px;
        color: #f3f4f6;
        font-size: 0.9rem;
        margin-top: 4px;
    }
    .calendar-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #f9fafb;
        text-align: center;
        margin: 0;
        padding-top: 6px;
    }
    .calendar-weekday {
        text-align: center;
        font-weight: 700;
        color: #d1d5db;
        padding: 8px 0 8px 0;
        font-size: 0.95rem;
    }
    .calendar-day-box {
        background: #111827;
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 8px;
        min-height: 170px;
        margin-top: 0px;
        margin-bottom: 18px;
    }
    .calendar-day-box.selected {
        border: 2px solid #22c55e;
        box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.20);
    }
    .calendar-event {
        margin-top: 4px;
        padding: 8px 10px;
        border-radius: 10px;
        color: #f3f4f6;
        font-size: 0.84rem;
        line-height: 1.25rem;
        word-break: break-word;
        white-space: pre-wrap;
    }
    .calendar-event-author {
        font-weight: 700;
        margin-bottom: 2px;
    }
    .calendar-event-meta {
        font-size: 0.74rem;
        opacity: 0.85;
        margin-bottom: 4px;
    }
    .calendar-event-body {
        white-space: pre-wrap;
    }
    .calendar-empty {
        margin-top: 4px;
        min-height: 110px;
        border-radius: 10px;
        background: rgba(255,255,255,0.02);
    }
    .calendar-editor {
        background: #111827;
        border: 1px solid #374151;
        border-radius: 14px;
        padding: 12px;
        margin-top: 10px;
        margin-bottom: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True
)
# Obtener valor de la UF automáticamente desde mindicador.cl
@st.cache_data
def obtener_valor_uf(fecha: str):
    try:
        response = requests.get(f"https://mindicador.cl/api/uf/{fecha}", timeout=10)
        data = response.json()
        return data["serie"][0]["valor"]
    except Exception:
        return None

def obtener_conexion():
    return st.connection("mysql", type="sql")

def valor_limpio(valor):
    if valor is None:
        return ""
    texto = str(valor)
    if texto.lower() == "nan":
        return ""
    return texto

def ir_a_costos():
    st.query_params["vista"] = "costos"

def ir_a_calendario():
    st.query_params.clear()

def cerrar_sesion():
    st.session_state.usuario_actual = None
    st.session_state.editor_fecha = ""
    st.session_state.editor_texto = ""
    st.query_params.clear()

def color_usuario(real_name):
    base = real_name.strip().lower() or "usuario"
    digest = hashlib.md5(base.encode("utf-8")).hexdigest()
    r = 80 + int(digest[0:2], 16) // 2
    g = 80 + int(digest[2:4], 16) // 2
    b = 80 + int(digest[4:6], 16) // 2
    return {
        "hex": f"#{r:02x}{g:02x}{b:02x}",
        "bg": f"rgba({r}, {g}, {b}, 0.22)"
    }

def fecha_a_clave(valor):
    if hasattr(valor, "strftime"):
        return valor.strftime("%Y-%m-%d")
    texto = str(valor)
    if " " in texto:
        texto = texto.split(" ")[0]
    return texto[:10]

def hora_corta(valor):
    if valor is None:
        return ""
    if hasattr(valor, "strftime"):
        return valor.strftime("%H:%M")
    texto = str(valor)
    if len(texto) >= 16:
        return texto[11:16]
    return texto

def obtener_usuario_por_username(username):
    conn = obtener_conexion()
    df = conn.query(
        """
        SELECT id, username, password_digest, real_name
        FROM users
        WHERE username = :username
          AND deleted_at IS NULL
        LIMIT 1
        """,
        params={"username": username},
        ttl=0
    )
    if df is None or df.empty:
        return None
    row = df.iloc[0]
    real_name = valor_limpio(row["real_name"]).strip() or valor_limpio(row["username"]).strip()
    return {
        "id": int(row["id"]),
        "username": valor_limpio(row["username"]).strip(),
        "password_digest": valor_limpio(row["password_digest"]),
        "real_name": real_name
    }

def autenticar_usuario(username, password):
    usuario = obtener_usuario_por_username(username)
    if usuario is None:
        return None
    try:
        if not bcrypt.checkpw(password.encode("utf-8"), usuario["password_digest"].encode("utf-8")):
            return None
    except Exception:
        return None
    return {
        "id": usuario["id"],
        "username": usuario["username"],
        "real_name": usuario["real_name"]
    }

def obtener_entradas_mes(anio, mes):
    fecha_inicio = date(anio, mes, 1)
    if mes == 12:
        fecha_fin = date(anio + 1, 1, 1)
    else:
        fecha_fin = date(anio, mes + 1, 1)

    conn = obtener_conexion()
    df = conn.query(
        """
        SELECT
            ce.id,
            ce.user_id,
            ce.entry_date,
            ce.content,
            ce.created_at,
            ce.updated_at,
            u.username,
            u.real_name
        FROM calendar_entries ce
        INNER JOIN users u ON u.id = ce.user_id
        WHERE ce.entry_date >= :fecha_inicio
          AND ce.entry_date < :fecha_fin
          AND u.deleted_at IS NULL
        ORDER BY ce.entry_date ASC, ce.created_at ASC, ce.id ASC
        """,
        params={"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin},
        ttl=0
    )

    entradas = {}
    if df is None or df.empty:
        return entradas

    for _, row in df.iterrows():
        real_name = valor_limpio(row["real_name"]).strip() or valor_limpio(row["username"]).strip()
        color = color_usuario(real_name)
        fecha_clave = fecha_a_clave(row["entry_date"])
        entradas.setdefault(fecha_clave, []).append(
            {
                "id": int(row["id"]),
                "user_id": int(row["user_id"]),
                "real_name": real_name,
                "username": valor_limpio(row["username"]).strip(),
                "content": valor_limpio(row["content"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "color_hex": color["hex"],
                "color_bg": color["bg"]
            }
        )
    return entradas

def guardar_entrada(user_id, fecha_clave, contenido):
    conn = obtener_conexion()
    with conn.session as s:
        s.execute(
            text(
                """
                INSERT INTO calendar_entries (user_id, entry_date, content, created_at, updated_at)
                VALUES (:user_id, :entry_date, :content, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    content = :content_update,
                    updated_at = NOW()
                """
            ),
            params={
                "user_id": user_id,
                "entry_date": fecha_clave,
                "content": contenido,
                "content_update": contenido
            }
        )
        s.commit()

def eliminar_entrada(user_id, fecha_clave):
    conn = obtener_conexion()
    with conn.session as s:
        s.execute(
            text(
                """
                DELETE FROM calendar_entries
                WHERE user_id = :user_id
                  AND entry_date = :entry_date
                """
            ),
            params={"user_id": user_id, "entry_date": fecha_clave}
        )
        s.commit()

def sincronizar_editor(fecha_clave, texto_actual):
    if st.session_state.editor_fecha != fecha_clave:
        st.session_state.editor_fecha = fecha_clave
        st.session_state.editor_texto = texto_actual

def mostrar_login():
    col_izq, col_centro, col_der = st.columns([1, 1.1, 1])
    with col_centro:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.title("Iniciar sesión")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            enviado = st.form_submit_button("Ingresar", use_container_width=True)
        if enviado:
            usuario = autenticar_usuario(username.strip(), password)
            if usuario is None:
                st.error("Credenciales inválidas.")
            else:
                st.session_state.usuario_actual = usuario
                st.session_state.editor_fecha = ""
                st.session_state.editor_texto = ""
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def mostrar_calendario():
    usuario_actual = st.session_state.usuario_actual
    meses = {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre"
    }

    anio_actual = date.today().year
    anio_minimo = min(anio_actual, 2025)
    anio_maximo = max(anio_actual, 2025)
    anios_disponibles = list(range(anio_minimo, anio_maximo + 1))

    if st.session_state.calendario_anio not in anios_disponibles:
        st.session_state.calendario_anio = anios_disponibles[-1]

    cab_izq, cab_der = st.columns([5, 1])
    with cab_izq:
        st.markdown(f"<div class='session-pill'>Sesión: {html.escape(usuario_actual['real_name'])}</div>", unsafe_allow_html=True)
    with cab_der:
        if st.button("Cerrar sesión", use_container_width=True, key="cerrar_sesion_calendario"):
            cerrar_sesion()
            st.rerun()

    col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 1])
    with col_a:
        if st.button("Costos", use_container_width=True):
            ir_a_costos()
            st.rerun()
    with col_b:
        st.markdown(f"<div class='calendar-title'>{meses[st.session_state.calendario_mes]} {st.session_state.calendario_anio}</div>", unsafe_allow_html=True)
    with col_c:
        st.selectbox(
            "Mes",
            options=list(meses.keys()),
            index=st.session_state.calendario_mes - 1,
            format_func=lambda x: meses[x],
            key="calendario_mes"
        )
    with col_d:
        st.selectbox(
            "Año",
            options=anios_disponibles,
            index=anios_disponibles.index(st.session_state.calendario_anio),
            key="calendario_anio"
        )

    dias_en_mes = calendar.monthrange(st.session_state.calendario_anio, st.session_state.calendario_mes)[1]
    if st.session_state.calendario_dia > dias_en_mes:
        st.session_state.calendario_dia = dias_en_mes

    entradas_mes = obtener_entradas_mes(st.session_state.calendario_anio, st.session_state.calendario_mes)

    fecha_clave = f"{st.session_state.calendario_anio:04d}-{st.session_state.calendario_mes:02d}-{st.session_state.calendario_dia:02d}"
    fecha_mostrada = f"{st.session_state.calendario_dia:02d}/{st.session_state.calendario_mes:02d}/{st.session_state.calendario_anio}"
    entradas_dia = entradas_mes.get(fecha_clave, [])
    entrada_propia = next((entrada for entrada in entradas_dia if entrada["user_id"] == usuario_actual["id"]), None)
    texto_actual = entrada_propia["content"] if entrada_propia is not None else ""

    sincronizar_editor(fecha_clave, texto_actual)

    st.markdown("<div class='calendar-editor'>", unsafe_allow_html=True)
    st.subheader(f"{fecha_mostrada}")
    st.caption(f"Escribiendo como {usuario_actual['real_name']}")
    st.text_area("Texto", height=90, key="editor_texto")
    col_guardar, col_borrar = st.columns(2)
    with col_guardar:
        if st.button("Guardar", use_container_width=True):
            contenido = st.session_state.editor_texto.strip()
            if not contenido:
                st.error("Debes escribir un texto.")
            else:
                guardar_entrada(usuario_actual["id"], fecha_clave, contenido)
                st.session_state.editor_fecha = fecha_clave
                st.session_state.editor_texto = contenido
                st.rerun()
    with col_borrar:
        if st.button("Eliminar", use_container_width=True, disabled=entrada_propia is None):
            eliminar_entrada(usuario_actual["id"], fecha_clave)
            st.session_state.editor_fecha = fecha_clave
            st.session_state.editor_texto = ""
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    encabezados = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    cols_encabezado = st.columns(7)
    for i, nombre in enumerate(encabezados):
        with cols_encabezado[i]:
            st.markdown(f"<div class='calendar-weekday'>{nombre}</div>", unsafe_allow_html=True)

    semanas = calendar.monthcalendar(st.session_state.calendario_anio, st.session_state.calendario_mes)

    for semana in semanas:
        cols = st.columns(7)
        for i, dia in enumerate(semana):
            with cols[i]:
                if dia == 0:
                    st.markdown("<div style='height: 170px;'></div>", unsafe_allow_html=True)
                else:
                    fecha_celda = f"{st.session_state.calendario_anio:04d}-{st.session_state.calendario_mes:02d}-{dia:02d}"
                    seleccionado = dia == st.session_state.calendario_dia
                    clase_seleccion = "calendar-day-box selected" if seleccionado else "calendar-day-box"

                    if st.button(f"{dia:02d}", key=f"dia_{fecha_celda}", use_container_width=True):
                        st.session_state.calendario_dia = dia
                        st.rerun()

                    entradas_celda = entradas_mes.get(fecha_celda, [])
                    if entradas_celda:
                        bloques = []
                        for entrada in entradas_celda:
                            autor = html.escape(entrada["real_name"])
                            hora = html.escape(hora_corta(entrada["updated_at"]))
                            contenido = html.escape(entrada["content"])
                            bloques.append(
                                f"<div class='calendar-event' style='background:{entrada['color_bg']}; border-left:4px solid {entrada['color_hex']};'>"
                                f"<div class='calendar-event-author'>{autor}</div>"
                                f"<div class='calendar-event-meta'>{hora}</div>"
                                f"<div class='calendar-event-body'>{contenido}</div>"
                                f"</div>"
                            )
                        st.markdown(
                            f"<div class='{clase_seleccion}'>" + "".join(bloques) + "</div>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f"<div class='{clase_seleccion}'><div class='calendar-empty'></div></div>",
                            unsafe_allow_html=True
                        )
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

if st.session_state.usuario_actual is None:
    mostrar_login()
else:
    if vista_actual == "costos":
        usuario_actual = st.session_state.usuario_actual

        cab_izq, cab_der = st.columns([5, 1])
        with cab_izq:
            st.markdown(f"<div class='session-pill'>Sesión: {html.escape(usuario_actual['real_name'])}</div>", unsafe_allow_html=True)
        with cab_der:
            if st.button("Cerrar sesión", use_container_width=True, key="cerrar_sesion_costos"):
                cerrar_sesion()
                st.rerun()

        st.title("📊 Cálculo de UF por Ascensor (Santiago / Zona Norte)")

        if st.button("Ir al calendario", use_container_width=True):
            ir_a_calendario()
            st.rerun()

        # Zona
        zona = st.selectbox("Zona", ["Santiago/Sur", "Zona Norte"])

        # Fecha para valor UF
        st.subheader("📅 Fecha para la UF")
        hoy = date.today()
        fecha_seleccionada = st.date_input("Fecha UF", max_value=hoy, value=hoy)
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
                    f"**Fecha UF:** {fecha_seleccionada.strftime('%d/%m/%Y')}  \n"
                    f"**Valor UF:** ${valor_uf:,.0f} CLP")

        st.success(f"✅ Para **{ascensores} ascensores** y **{noches} noche(s)**, el valor total es: **{uf_total:.2f} UF**")
    else:
        mostrar_calendario()

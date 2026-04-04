import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from datetime import datetime

# =========================
# 🔥 FIREBASE
# =========================
if not firebase_admin._apps:
    firebase_dict = json.loads(os.environ["FIREBASE_KEY"])
    cred = credentials.Certificate(firebase_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Sistema Producción", layout="centered")
st.title("🧵 Sistema Producción Confección")

# =========================
# SESSION
# =========================
if "usuario" not in st.session_state:
    st.session_state.usuario = None

# =========================
# LOGIN
# =========================
if st.session_state.usuario is None:

    st.subheader("🔐 Ingreso al sistema")
    codigo = st.text_input("Ingrese su código")

    if st.button("Ingresar"):

        usuarios = db.collection("usuarios").stream()

        for user in usuarios:
            data = user.to_dict()
            if data.get("codigo") == codigo:
                st.session_state.usuario = data
                st.rerun()

        st.error("❌ Código no encontrado")

# =========================
# SISTEMA
# =========================
else:
    usuario = st.session_state.usuario
    rol = usuario.get("rol")

    st.success(f"Bienvenido {usuario.get('nombre')}")
    st.write(f"Rol: {rol}")

    # =========================================================
    # 🔧 OPERARIO
    # =========================================================
    if rol == "operario":

        st.header("🔧 Módulo Operario")

        satelite = usuario.get("satelite")

        lotes_ref = db.collection("lotes") \
            .where("satelite", "==", satelite) \
            .where("estado", "==", "en_produccion") \
            .stream()

        lotes = list(lotes_ref)

        if not lotes:
            st.warning("No hay lotes en producción para tu satélite")
        else:
            lote_dict = {l.to_dict()["lote_id"]: l for l in lotes}

            lote_id = st.selectbox("📦 Lote", list(lote_dict.keys()))
            lote_doc = lote_dict[lote_id]
            lote_data = lote_doc.to_dict()

            talla = st.selectbox("👕 Talla", list(lote_data["tallas"].keys()))
            disponible = lote_data["tallas"][talla]

            st.info(f"Disponible: {disponible}")

            operaciones = [op.to_dict()["nombre"] for op in db.collection("operaciones").stream()]
            operacion = st.selectbox("🧵 Operación", operaciones)

            cantidad = st.number_input("Cantidad", min_value=0)

            if st.button("Guardar producción"):

                lote_ref = db.collection("lotes").document(lote_doc.id)
                transaction = db.transaction()

                @firestore.transactional
                def actualizar(transaction):
                    snap = lote_ref.get(transaction=transaction)
                    data = snap.to_dict()

                    actual = data["tallas"][talla]

                    if cantidad > actual:
                        raise Exception(f"Stock insuficiente: {actual}")

                    transaction.update(lote_ref, {
                        f"tallas.{talla}": actual - cantidad
                    })

                try:
                    actualizar(transaction)

                    db.collection("produccion").add({
                        "lote_id": lote_id,
                        "operario": usuario["nombre"],
                        "codigo": usuario["codigo"],
                        "operacion": operacion,
                        "cantidad": cantidad,
                        "talla": talla,
                        "timestamp": firestore.SERVER_TIMESTAMP
                    })

                    st.success("Producción registrada")
                    st.rerun()

                except Exception as e:
                    st.error(str(e))

    # =========================================================
    # 👷 SUPERVISOR
    # =========================================================
    elif rol == "supervisor":

        st.header("👷 Módulo Supervisor")

        lotes = list(db.collection("lotes").stream())

        if lotes:
            lote_dict = {l.to_dict()["lote_id"]: l for l in lotes}

            lote_id = st.selectbox("Lote", list(lote_dict.keys()))
            lote_doc = lote_dict[lote_id]

            satelite = st.selectbox("Enviar a:", ["Satelite Norte", "Satelite Sur"])

            if st.button("Enviar a producción"):

                db.collection("lotes").document(lote_doc.id).update({
                    "estado": "en_produccion",
                    "satelite": satelite
                })

                db.collection("movimientos_lote").add({
                    "lote_id": lote_id,
                    "estado": "en_produccion",
                    "ubicacion": satelite,
                    "usuario": usuario["nombre"],
                    "fecha": firestore.SERVER_TIMESTAMP
                })

                st.success("Lote enviado")

    # =========================================================
    # 🏭 COORDINADOR
    # =========================================================
    elif rol == "coordinador":

        st.header("🏭 Coordinador")

        satelite = usuario.get("satelite")

        lotes = db.collection("lotes") \
            .where("satelite", "==", satelite) \
            .stream()

        for l in lotes:
            data = l.to_dict()
            st.write(f"Lote: {data['lote_id']} | Estado: {data['estado']}")

            if st.button(f"Finalizar {data['lote_id']}"):
                db.collection("lotes").document(l.id).update({
                    "estado": "tintoreria"
                })

                st.success("Enviado a tintorería")

    # =========================================================
    # 👑 GERENTE
    # =========================================================
    elif rol == "gerente":

        st.header("📊 Dashboard Gerente")

        lotes = list(db.collection("lotes").stream())
        produccion = list(db.collection("produccion").stream())

        st.subheader("📦 Lotes activos")
        for l in lotes:
            d = l.to_dict()
            st.write(f"{d['lote_id']} - {d['estado']} - {d.get('satelite','')}")

        st.subheader("📈 Producción total")
        total = sum(p.to_dict()["cantidad"] for p in produccion)
        st.metric("Total producido", total)

        st.subheader("🏭 Producción por operario")
        resumen = {}
        for p in produccion:
            d = p.to_dict()
            nombre = d["operario"]
            resumen[nombre] = resumen.get(nombre, 0) + d["cantidad"]

        st.write(resumen)
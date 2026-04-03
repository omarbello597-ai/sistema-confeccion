import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

# 🔥 Firebase desde entorno (Render)
if not firebase_admin._apps:
    firebase_dict = json.loads(os.environ["FIREBASE_KEY"])
    cred = credentials.Certificate(firebase_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(page_title="Sistema Producción", layout="centered")

st.title("🧵 Sistema Producción Confección")

# ---------------- LOGIN ----------------
st.subheader("🔐 Ingreso al sistema")

codigo = st.text_input("Ingrese su código")

if st.button("Ingresar"):
    usuarios = db.collection("usuarios").stream()
    usuario_encontrado = None

    for user in usuarios:
        data = user.to_dict()
        if data.get("codigo") == codigo:
            usuario_encontrado = data
            break

    if usuario_encontrado:

        nombre = usuario_encontrado.get("nombre")
        rol = usuario_encontrado.get("rol")
        satelite = usuario_encontrado.get("satelite")

        st.success(f"Bienvenido {nombre}")
        st.write(f"Rol: {rol}")

        # =========================
        # 🔧 MÓDULO OPERARIO
        # =========================
        if rol == "operario":

            st.header("🔧 Módulo Operario")

            # 🔹 Traer lotes del satélite
            lotes_ref = db.collection("lotes").where("satelite", "==", satelite).stream()

            lotes = []
            lotes_dict = {}

            for lote in lotes_ref:
                data = lote.to_dict()
                lote_id = data.get("lote_id")

                if lote_id:
                    lotes.append(lote_id)
                    lotes_dict[lote_id] = data

            if not lotes:
                st.warning("No hay lotes disponibles para tu satélite")
            else:
                # 🔽 Seleccionar lote
                lote_seleccionado = st.selectbox("📦 Seleccione lote", lotes)

                if lote_seleccionado:

                    lote_data = lotes_dict[lote_seleccionado]

                    # 🔽 Tallas
                    tallas = list(lote_data.get("tallas", {}).keys())
                    talla = st.selectbox("👕 Seleccione talla", tallas)

                    # 🔽 Mostrar disponible
                    cantidad_disponible = lote_data.get("tallas", {}).get(talla, 0)

                    st.info(f"Disponible en talla {talla}: {cantidad_disponible}")

                    if cantidad_disponible <= 0:
                        st.error("❌ No hay unidades disponibles en esta talla")
                    else:

                        # 🔽 Operaciones
                        operaciones_ref = db.collection("operaciones").stream()
                        operaciones = []

                        for op in operaciones_ref:
                            data_op = op.to_dict()
                            nombre_op = data_op.get("nombre")
                            if nombre_op:
                                operaciones.append(nombre_op)

                        operacion = st.selectbox("🧵 Seleccione operación", operaciones)

                        cantidad = st.number_input(
                            "🔢 Cantidad realizada",
                            min_value=1,
                            max_value=cantidad_disponible,
                            step=1
                        )

                        if st.button("Guardar producción"):

                            # 🔥 Guardar producción
                            db.collection("produccion").add({
                                "operario": nombre,
                                "codigo": codigo,
                                "lote_id": lote_seleccionado,
                                "talla": talla,
                                "operacion": operacion,
                                "cantidad": int(cantidad),
                                "timestamp": firestore.SERVER_TIMESTAMP
                            })

                            # 🔥 Descontar del lote
                            lotes_query = db.collection("lotes").where("lote_id", "==", lote_seleccionado).stream()

                            for lote_doc in lotes_query:
                                lote_ref = db.collection("lotes").document(lote_doc.id)
                                lote_data_actual = lote_doc.to_dict()

                                tallas_actuales = lote_data_actual.get("tallas", {})
                                cantidad_actual = tallas_actuales.get(talla, 0)

                                nueva_cantidad = cantidad_actual - int(cantidad)

                                lote_ref.update({
                                    f"tallas.{talla}": nueva_cantidad
                                })

                            st.success("✅ Producción registrada y lote actualizado")

        # =========================
        # 📊 SUPERVISOR
        # =========================
        elif rol == "supervisor":
            st.header("📊 Módulo Supervisor")
            st.write("Aquí podrás ver operarios y producción")

        # =========================
        # 📈 GERENTE
        # =========================
        elif rol == "gerente":
            st.header("📈 Módulo Gerente")
            st.write("Vista general del sistema")

    else:
        st.error("❌ Código no encontrado")
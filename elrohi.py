import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

# 🔥 Firebase
if not firebase_admin._apps:
    firebase_dict = json.loads(os.environ["FIREBASE_KEY"])
    cred = credentials.Certificate(firebase_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(page_title="Sistema Producción", layout="centered")

st.title("🧵 Sistema Producción Confección")

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
        st.success(f"Bienvenido {usuario_encontrado.get('nombre')}")
        rol = usuario_encontrado.get("rol")

        # =========================
        # 🔧 OPERARIO
        # =========================
        if rol == "operario":

            st.header("🔧 Módulo Operario")

            satelite = usuario_encontrado.get("satelite")

            lotes_ref = db.collection("lotes") \
                .where("satelite", "==", satelite) \
                .where("estado", "==", "en_produccion") \
                .stream()

            lotes = list(lotes_ref)

            if len(lotes) == 0:
                st.warning("No hay lotes en producción para tu satélite")
            else:
                lote_dict = {lote.to_dict().get("lote_id"): lote for lote in lotes}

                lote_seleccionado = st.selectbox("📦 Seleccione lote", list(lote_dict.keys()))
                lote_doc = lote_dict[lote_seleccionado]
                lote_data = lote_doc.to_dict()

                tallas = lote_data.get("tallas", {})

                talla = st.selectbox("👕 Seleccione talla", list(tallas.keys()))
                disponible = tallas.get(talla, 0)

                st.info(f"Disponible en talla {talla}: {disponible}")

                operaciones_ref = db.collection("operaciones").stream()
                operaciones = [op.to_dict().get("nombre") for op in operaciones_ref]

                operacion = st.selectbox("🧵 Seleccione operación", operaciones)

                cantidad = int(st.number_input("🔢 Cantidad realizada", min_value=0, step=1))

                if st.button("Guardar producción"):

                    lote_ref = db.collection("lotes").document(lote_doc.id)
                    transaction = db.transaction()

                    @firestore.transactional
                    def proceso(transaction):

                        snapshot = lote_ref.get(transaction=transaction)
                        data = snapshot.to_dict()

                        disponible_actual = data.get("tallas", {}).get(talla, 0)

                        if cantidad <= 0:
                            raise Exception("Cantidad inválida")

                        if cantidad > disponible_actual:
                            raise Exception(f"STOCK:{disponible_actual}")

                        nuevo_valor = disponible_actual - cantidad

                        transaction.update(lote_ref, {
                            f"tallas.{talla}": nuevo_valor
                        })

                        return disponible_actual

                    try:
                        disponible_antes = proceso(transaction)

                        db.collection("produccion").add({
                            "codigo": codigo,
                            "operario": usuario_encontrado.get("nombre"),
                            "lote_id": lote_seleccionado,
                            "operacion": operacion,
                            "cantidad": cantidad,
                            "talla": talla,
                            "timestamp": firestore.SERVER_TIMESTAMP
                        })

                        st.success(f"✅ OK | Antes: {disponible_antes} → Ahora: {disponible_antes - cantidad}")
                        st.rerun()

                    except Exception as e:
                        msg = str(e)

                        if "STOCK" in msg:
                            disponible_actual = msg.split(":")[1]
                            st.error(f"❌ Solo hay {disponible_actual} disponibles")
                        else:
                            st.error(msg)

        # =========================
        # 👷 SUPERVISOR
        # =========================
        elif rol == "supervisor":

            st.header("👷 Módulo Supervisor")

            lotes_ref = db.collection("lotes").stream()
            lotes = list(lotes_ref)

            if len(lotes) == 0:
                st.warning("No hay lotes creados")
            else:
                lote_dict = {lote.to_dict().get("lote_id"): lote for lote in lotes}

                lote_seleccionado = st.selectbox("📦 Seleccione lote", list(lote_dict.keys()))
                lote_doc = lote_dict[lote_seleccionado]

                st.write(f"📦 Lote seleccionado: {lote_seleccionado}")

                # 🔥 Lista de satélites (puedes luego mover esto a Firebase)
                satelites = [
                    "Satelite Norte",
                    "Satelite Sur",
                    "Satelite Centro"
                ]

                satelite_asignado = st.selectbox("🏭 Enviar a producción a:", satelites)

                if st.button("🚀 Enviar a producción"):

                    db.collection("lotes").document(lote_doc.id).update({
                        "estado": "en_produccion",
                        "satelite": satelite_asignado
                    })

                    st.success(f"✅ Lote enviado a {satelite_asignado}")
                    st.rerun()

        # =========================
        # 📈 GERENTE
        # =========================
        elif rol == "gerente":
            st.header("📈 Módulo Gerente")

    else:
        st.error("❌ Código no encontrado")
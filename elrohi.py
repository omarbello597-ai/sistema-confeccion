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

        if rol == "operario":
            st.header("🔧 Módulo Operario")

        elif rol == "supervisor":
            st.header("📊 Módulo Supervisor")

        elif rol == "gerente":
            st.header("📈 Módulo Gerente")

    else:
        st.error("❌ Código no encontrado")
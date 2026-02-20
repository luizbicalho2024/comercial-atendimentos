import streamlit as st
import os
from database import users_col, hash_pw, init_admin
from colaborador import render_colaborador
from gestor import render_gestor

# Garante o administrador inicial
init_admin()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo.png"): st.image("logo.png")
        else: st.title("🏦 Rovema Comercial")
        
        email = st.text_input("Email")
        pw = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            user = users_col.find_one({"email": email, "ativo": True})
            if user and user['senha'] == hash_pw(pw):
                st.session_state.logged_in = True
                st.session_state.user_role = user['role']
                st.session_state.user_name = user['nome']
                st.session_state.user_email = user['email']
                st.rerun()
            else:
                st.error("Credenciais inválidas.")

if not st.session_state.logged_in:
    login_screen()
else:
    with st.sidebar:
        st.write(f"Logado: **{st.session_state.user_name}**")
        if st.button("Sair"):
            st.session_state.clear()
            st.rerun()
    
    if st.session_state.user_role == 'admin':
        render_gestor()
    else:
        render_colaborador()

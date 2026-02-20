import streamlit as st
import os

# CONFIGURAÇÃO DE PÁGINA - DEVE SER A PRIMEIRA CHAMADA
st.set_page_config(
    page_title="Rovema Comercial PRO", 
    page_icon="🏦", 
    layout="wide", # Fixa o modo Wide
    initial_sidebar_state="expanded"
)

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
        # Tenta carregar a logo, se não houver, usa texto
        if os.path.exists("logo.png"): 
            st.image("logo.png", use_column_width=True)
        else: 
            st.markdown("<h1 style='text-align: center; color: #0052cc;'>🏦 Rovema Comercial</h1>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("### Login do Sistema")
            email = st.text_input("E-mail corporativo")
            pw = st.text_input("Senha", type="password")
            
            if st.button("Acessar Sistema", type="primary", use_container_width=True):
                user = users_col.find_one({"email": email, "ativo": True})
                if user and user['senha'] == hash_pw(pw):
                    st.session_state.logged_in = True
                    st.session_state.user_role = user['role']
                    st.session_state.user_name = user['nome']
                    st.session_state.user_email = user['email']
                    st.rerun()
                else:
                    st.error("E-mail ou senha inválidos.")

if not st.session_state.logged_in:
    login_screen()
else:
    # Barra Lateral (Sidebar)
    with st.sidebar:
        st.markdown(f"### Bem-vindo(a),\n**{st.session_state.user_name}**")
        st.caption(f"Perfil: {st.session_state.user_role.capitalize()}")
        st.divider()
        if st.button("Sair / Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    # Roteamento de Perfil
    if st.session_state.user_role == 'admin':
        render_gestor()
    else:
        render_colaborador()

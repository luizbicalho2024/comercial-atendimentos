import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime, timedelta
import hashlib
from streamlit_geolocation import streamlit_geolocation
import os

# Configuração da página (deve ser a primeira chamada do Streamlit)
st.set_page_config(page_title="Sistema Comercial", page_icon="📊", layout="wide")

# ==========================================
# CONFIGURAÇÃO DE BANCO DE DADOS E FUNÇÕES
# ==========================================

@st.cache_resource
def init_connection():
    try:
        # Puxa a string de conexão dos Secrets do Streamlit Cloud
        uri = st.secrets["MONGO_URI"]
        client = pymongo.MongoClient(uri)
        return client
    except Exception as e:
        st.error(f"Erro ao conectar ao MongoDB. Verifique os Secrets. Erro: {e}")
        st.stop()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

client = init_connection()
db = client['sistema_comercial']
users_col = db['usuarios']
visits_col = db['atendimentos']

# Criação automática do usuário administrador inicial
def init_admin():
    admin_email = "luiz.bicalho@rovemabank.com.br"
    if not users_col.find_one({"email": admin_email}):
        users_col.insert_one({
            "nome": "Luiz Bicalho",
            "email": admin_email,
            "senha": hash_password("123456"),
            "role": "admin",
            "ativo": True
        })

init_admin()

# ==========================================
# CONTROLE DE SESSÃO (LOGIN/LOGOUT)
# ==========================================

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

def login(email, password):
    user = users_col.find_one({"email": email, "ativo": True})
    if user and user['senha'] == hash_password(password):
        st.session_state.logged_in = True
        st.session_state.user_role = user['role']
        st.session_state.user_name = user['nome']
        st.session_state.user_email = user['email']
        st.rerun()
    else:
        st.error("E-mail ou senha incorretos, ou usuário inativo.")

def logout():
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_name = None
    st.session_state.user_email = None
    st.rerun()

# ==========================================
# TELAS DO SISTEMA
# ==========================================

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Tenta carregar a logo, se não existir, mostra um título
        if os.path.exists("logo.png"):
            st.image("logo.png", use_column_width=True)
        else:
            st.markdown("<h2 style='text-align: center; color: #0052cc;'>Sistema Comercial</h2>", unsafe_allow_html=True)
        
        st.markdown("### Acesso ao Sistema")
        email = st.text_input("E-mail")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            if email and password:
                login(email, password)
            else:
                st.warning("Preencha e-mail e senha.")

def collaborator_page():
    st.title(f"Bem-vindo, {st.session_state.user_name}")
    st.write("Registre seu atendimento atual abaixo.")
    
    with st.container(border=True):
        cliente_nome = st.text_input("Nome do Cliente")
        observacoes = st.text_area("Observações do Atendimento")
        
        st.markdown("**Capturar Localização (GPS)**")
        st.info("Clique no botão abaixo e permita o acesso à localização no seu navegador/smartphone.")
        location = streamlit_geolocation()
        
        if st.button("Registrar Atendimento", type="primary"):
            if not cliente_nome:
                st.error("O nome do cliente é obrigatório.")
            elif not location or 'latitude' not in location or location['latitude'] is None:
                st.error("É obrigatório capturar a localização do GPS antes de registrar.")
            else:
                novo_atendimento = {
                    "colaborador_email": st.session_state.user_email,
                    "colaborador_nome": st.session_state.user_name,
                    "cliente_nome": cliente_nome,
                    "observacoes": observacoes,
                    "latitude": location['latitude'],
                    "longitude": location['longitude'],
                    "data_hora": datetime.now()
                }
                visits_col.insert_one(novo_atendimento)
                st.success("Atendimento registrado com sucesso!")
                st.balloons()

def admin_page():
    st.title("Painel do Gestor")
    
    tab1, tab2 = st.tabs(["📊 Visualizar Atendimentos", "👥 Gerenciar Equipe"])
    
    with tab1:
        st.header("Histórico de Atendimentos")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_tempo = st.selectbox("Período", ["Hoje", "Esta Semana", "Este Mês", "Todos"])
        with col2:
            usuarios_ativos = list(users_col.find({"role": "colaborador"}, {"nome": 1, "email": 1}))
            lista_nomes = ["Todos"] + [u['nome'] for u in usuarios_ativos]
            filtro_colaborador = st.selectbox("Colaborador", lista_nomes)
            
        # Busca no banco
        query = {}
        if filtro_colaborador != "Todos":
            query["colaborador_nome"] = filtro_colaborador
            
        hoje = datetime.now()
        if filtro_tempo == "Hoje":
            inicio = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
            query["data_hora"] = {"$gte": inicio}
        elif filtro_tempo == "Esta Semana":
            inicio = (hoje - timedelta(days=hoje.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            query["data_hora"] = {"$gte": inicio}
        elif filtro_tempo == "Este Mês":
            inicio = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query["data_hora"] = {"$gte": inicio}

        atendimentos = list(visits_col.find(query).sort("data_hora", -1))
        
        if atendimentos:
            df = pd.DataFrame(atendimentos)
            df['Data'] = df['data_hora'].dt.strftime('%d/%m/%Y %H:%M')
            df = df[['Data', 'colaborador_nome', 'cliente_nome', 'observacoes', 'latitude', 'longitude']]
            df.columns = ['Data/Hora', 'Colaborador', 'Cliente', 'Observações', 'Latitude', 'Longitude']
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum atendimento encontrado para os filtros selecionados.")

    with tab2:
        st.header("Gestão de Colaboradores")
        
        with st.expander("➕ Cadastrar Novo Colaborador", expanded=False):
            with st.form("form_novo_usuario"):
                novo_nome = st.text_input("Nome Completo")
                novo_email = st.text_input("E-mail")
                nova_senha = st.text_input("Senha", type="password")
                novo_role = st.selectbox("Nível de Acesso", ["colaborador", "admin"])
                submit_novo = st.form_submit_button("Cadastrar")
                
                if submit_novo:
                    if not novo_nome or not novo_email or not nova_senha:
                        st.error("Preencha todos os campos!")
                    elif users_col.find_one({"email": novo_email}):
                        st.error("Este e-mail já está cadastrado.")
                    else:
                        users_col.insert_one({
                            "nome": novo_nome,
                            "email": novo_email,
                            "senha": hash_password(nova_senha),
                            "role": novo_role,
                            "ativo": True
                        })
                        st.success(f"Usuário {novo_nome} cadastrado com sucesso!")
                        st.rerun()
        
        st.subheader("Colaboradores Cadastrados")
        todos_usuarios = list(users_col.find())
        if todos_usuarios:
            for u in todos_usuarios:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                    c1.write(f"**{u['nome']}**")
                    c2.write(u['email'])
                    c3.write(f"Nível: {u['role'].capitalize()}")
                    
                    status = "Ativo" if u['ativo'] else "Inativo"
                    c4.write(f"Status: **{status}**")
                    
                    # Evita que o admin principal se desative acidentalmente
                    if u['email'] != "luiz.bicalho@rovemabank.com.br":
                        acao = "Desativar" if u['ativo'] else "Ativar"
                        if st.button(f"{acao} usuário", key=f"btn_{u['_id']}"):
                            users_col.update_one({"_id": u['_id']}, {"$set": {"ativo": not u['ativo']}})
                            st.rerun()

# ==========================================
# ROTEAMENTO PRINCIPAL
# ==========================================

# Adiciona botão de logout na barra lateral se estiver logado
if st.session_state.logged_in:
    with st.sidebar:
        st.write(f"Logado como: **{st.session_state.user_name}**")
        if st.button("Sair", use_container_width=True):
            logout()

# Gerencia qual tela exibir
if not st.session_state.logged_in:
    login_page()
else:
    if st.session_state.user_role == 'admin':
        admin_page()
    else:
        collaborator_page()

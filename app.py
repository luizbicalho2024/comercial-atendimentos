import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime, timedelta
import hashlib
from streamlit_geolocation import streamlit_geolocation
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# Configuração da página (deve ser a primeira chamada)
st.set_page_config(page_title="Sistema Comercial", page_icon="📊", layout="wide")

# ==========================================
# CUSTOM CSS PARA MELHORAR O DESIGN DO GPS E TEMA
# ==========================================
st.markdown("""
    <style>
    /* Estilo do Card Moderno do GPS */
    .gps-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #e6f0ff 0%, #ffffff 100%);
        border: 2px dashed #0052cc;
        border-radius: 12px;
        padding: 30px 20px 40px 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0, 82, 204, 0.08);
        transition: all 0.3s ease;
    }
    .gps-container:hover {
        border-color: #003d99;
        box-shadow: 0 6px 20px rgba(0, 82, 204, 0.15);
    }
    .gps-title {
        color: #0052cc;
        font-weight: 800;
        font-size: 20px;
        margin-bottom: 10px;
        text-align: center;
    }
    .gps-desc {
        font-size: 15px;
        color: #555;
        margin-bottom: 25px;
        text-align: center;
        max-width: 80%;
    }
    /* Aumenta o tamanho do botão do plugin para facilitar o toque no celular */
    iframe[title="streamlit_geolocation.streamlit_geolocation"] {
        transform: scale(1.4);
        transform-origin: top center;
        height: 45px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# CONFIGURAÇÃO DE BANCO DE DADOS E FUNÇÕES
# ==========================================

@st.cache_resource
def init_connection():
    try:
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

@st.cache_data(ttl=3600)
def get_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="sistema_comercial_app")
        location = geolocator.reverse((lat, lon), exactly_one=True, timeout=10)
        return location.address if location else "Endereço não localizado automaticamente"
    except GeocoderTimedOut:
        return "Tempo limite excedido ao buscar endereço"
    except Exception:
        return "Erro ao buscar endereço"

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
    for key in ['logged_in', 'user_role', 'user_name', 'user_email']:
        st.session_state[key] = None
    st.session_state.logged_in = False
    st.rerun()

# ==========================================
# TELAS DO SISTEMA
# ==========================================

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
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
    
    tab1, tab2 = st.tabs(["📝 Registrar Atendimento", "🕰️ Meu Histórico"])
    
    with tab1:
        st.markdown("### Novo Atendimento")
        with st.container(border=True):
            cliente_nome = st.text_input("Nome do Cliente *", placeholder="Ex: Mercado Silva")
            observacoes = st.text_area("Observações do Atendimento *", placeholder="Detalhes da visita...")
            
            st.divider()
            
            # Painel Centralizado e Super Estilizado para o GPS
            st.markdown("""
                <div class="gps-container">
                    <div class="gps-title">📍 Captura de Localização GPS</div>
                    <div class="gps-desc">Toque no ícone abaixo para confirmar sua localização exata no momento deste atendimento.</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Ajuste das colunas para centralizar perfeitamente o iframe com o zoom aplicado
            col_space1, col_btn, col_space2 = st.columns([3, 1, 3])
            with col_btn:
                # Movemos o iframe ligeiramente para cima via CSS embutido para casar com o design
                st.markdown('<div style="margin-top: -65px; margin-bottom: 20px; text-align: center;">', unsafe_allow_html=True)
                location = streamlit_geolocation()
                st.markdown('</div>', unsafe_allow_html=True)
            
            endereco_atual = ""
            lat, lon = None, None
            
            if location and 'latitude' in location and location['latitude'] is not None:
                lat = location['latitude']
                lon = location['longitude']
                endereco_atual = get_address(lat, lon)
                
                st.success("✅ Localização capturada com sucesso!")
                st.markdown(f"**Coordenadas:** {lat}, {lon}")
                st.markdown(f"**Endereço Aproximado:** {endereco_atual}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Registrar Atendimento", type="primary", use_container_width=True):
                if not cliente_nome.strip():
                    st.error("O campo 'Nome do Cliente' é obrigatório.")
                elif not observacoes.strip():
                    st.error("O campo 'Observações' é obrigatório.")
                elif not lat or not lon:
                    st.error("É obrigatório capturar a localização no botão acima antes de registrar o atendimento.")
                else:
                    novo_atendimento = {
                        "colaborador_email": st.session_state.user_email,
                        "colaborador_nome": st.session_state.user_name,
                        "cliente_nome": cliente_nome,
                        "observacoes": observacoes,
                        "latitude": lat,
                        "longitude": lon,
                        "endereco": endereco_atual,
                        "data_hora": datetime.now()
                    }
                    visits_col.insert_one(novo_atendimento)
                    st.success("Atendimento registrado com sucesso!")
                    st.balloons()

    with tab2:
        st.markdown("### Meus Últimos Atendimentos")
        meus_atendimentos = list(visits_col.find({"colaborador_email": st.session_state.user_email}).sort("data_hora", -1).limit(50))
        
        if meus_atendimentos:
            hc1, hc2, hc3, hc4 = st.columns([2, 2, 3, 1])
            hc1.write("**Data/Hora**")
            hc2.write("**Cliente**")
            hc3.write("**Endereço**")
            hc4.write("**Ação**")
            st.divider()
            
            for item in meus_atendimentos:
                c1, c2, c3, c4 = st.columns([2, 2, 3, 1])
                c1.write(item['data_hora'].strftime('%d/%m/%Y %H:%M'))
                c2.write(item['cliente_nome'])
                c3.write(item.get('endereco', 'Endereço não registrado'))
                
                with c4:
                    with st.popover("🗑️ Excluir"):
                        st.write("Tem certeza que deseja apagar?")
                        if st.button("Sim, apagar", key=f"del_{item['_id']}", type="primary"):
                            visits_col.delete_one({"_id": item['_id']})
                            st.rerun()
                st.markdown("---")
        else:
            st.info("Você ainda não possui atendimentos registrados.")

def admin_page():
    st.title("Painel do Gestor")
    
    tab1, tab2, tab3 = st.tabs(["📊 Visualizar Atendimentos", "🧠 Inteligência de Dados", "👥 Gerenciar Equipe"])
    
    with tab1:
        st.header("Histórico Geral de Atendimentos")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_tempo = st.selectbox("Período", ["Hoje", "Esta Semana", "Este Mês", "Todos"])
        with col2:
            usuarios_ativos = list(users_col.find({"role": "colaborador"}, {"nome": 1, "email": 1}))
            lista_nomes = ["Todos"] + [u['nome'] for u in usuarios_ativos]
            filtro_colaborador = st.selectbox("Colaborador", lista_nomes)
            
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
            df['Data/Hora'] = df['data_hora'].dt.strftime('%d/%m/%Y %H:%M')
            
            if 'endereco' not in df.columns:
                df['endereco'] = "Endereço não registrado"
                
            df = df[['Data/Hora', 'colaborador_nome', 'cliente_nome', 'observacoes', 'endereco', 'latitude', 'longitude']]
            df.columns = ['Data/Hora', 'Colaborador', 'Cliente', 'Observações', 'Endereço', 'Lat', 'Lon']
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum atendimento encontrado para os filtros selecionados.")

    with tab2:
        st.header("Inteligência e KPIs")
        
        todos_dados = list(visits_col.find())
        if not todos_dados:
            st.warning("Não há dados suficientes para gerar os gráficos e mapa.")
        else:
            df_intel = pd.DataFrame(todos_dados)
            
            col_sel, _ = st.columns([1, 2])
            with col_sel:
                lista_intel = ["Todos da Equipe"] + list(df_intel['colaborador_nome'].unique())
                colab_selecionado = st.selectbox("Analisar Colaborador (Mapa)", lista_intel)
            
            if colab_selecionado != "Todos da Equipe":
                df_mapa = df_intel[df_intel['colaborador_nome'] == colab_selecionado]
            else:
                df_mapa = df_intel
                
            st.subheader("📍 Mapa de Atendimentos Realizados")
            if not df_mapa.empty and 'latitude' in df_mapa.columns and 'longitude' in df_mapa.columns:
                map_data = df_mapa[['latitude', 'longitude']].dropna()
                st.map(map_data, use_container_width=True)
            else:
                st.info("Nenhuma coordenada válida para exibir no mapa.")

            st.divider()
            
            st.subheader("📈 Desempenho e Comparativos")
            hoje = datetime.now()
            inicio_mes_atual = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            ultimo_dia_mes_anterior = inicio_mes_atual - timedelta(days=1)
            inicio_mes_anterior = ultimo_dia_mes_anterior.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            atendimentos_total = len(df_mapa)
            
            mask_mes_atual = (df_mapa['data_hora'] >= inicio_mes_atual)
            qtd_mes_atual = len(df_mapa[mask_mes_atual])
            
            mask_mes_anterior = (df_mapa['data_hora'] >= inicio_mes_anterior) & (df_mapa['data_hora'] <= ultimo_dia_mes_anterior)
            qtd_mes_anterior = len(df_mapa[mask_mes_anterior])
            
            delta_mes = qtd_mes_atual - qtd_mes_anterior

            col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
            col_kpi1.metric("Total Histórico", atendimentos_total)
            col_kpi2.metric("Neste Mês", qtd_mes_atual, delta=delta_mes, delta_color="normal")
            col_kpi3.metric("Mês Anterior", qtd_mes_anterior)
            
            dias_corridos = hoje.day
            media_diaria = round(qtd_mes_atual / dias_corridos, 1) if dias_corridos > 0 else 0
            col_kpi4.metric("Média Diária (Mês Atual)", media_diaria)

    with tab3:
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
                    
                    if u['email'] != "luiz.bicalho@rovemabank.com.br":
                        acao = "Desativar" if u['ativo'] else "Ativar"
                        if st.button(f"{acao} usuário", key=f"btn_{u['_id']}"):
                            users_col.update_one({"_id": u['_id']}, {"$set": {"ativo": not u['ativo']}})
                            st.rerun()

# ==========================================
# ROTEAMENTO PRINCIPAL
# ==========================================

if st.session_state.logged_in:
    with st.sidebar:
        st.write(f"Logado como: **{st.session_state.user_name}**")
        if st.button("Sair", use_container_width=True):
            logout()

if not st.session_state.logged_in:
    login_page()
else:
    if st.session_state.user_role == 'admin':
        admin_page()
    else:
        collaborator_page()

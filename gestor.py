import streamlit as st
import pandas as pd
from database import visits_col, users_col, metas_col, hash_pw
from datetime import datetime, timedelta

COR_STATUS = {"Venda Realizada": "#28a745", "Prospecção": "#0052cc", "Retorno Agendado": "#fd7e14", "Cliente Ausente": "#dc3545", "Outro": "#6c757d"}

def render_gestor():
    st.title("🛡️ Gestão Estratégica Rovema")
    menu = st.tabs(["📊 Acompanhamento", "📈 Inteligência", "🎯 Metas", "👥 Gestão de Usuários"])

    with menu[0]:
        st.subheader("Filtros")
        col1, col2, col3 = st.columns(3)
        status_f = col1.multiselect("Status", list(COR_STATUS.keys()), default=list(COR_STATUS.keys()))
        colab_f = col2.selectbox("Colaborador", ["Todos"] + list(users_col.distinct("nome", {"role": "colaborador"})))
        tempo_f = col3.selectbox("Período", ["Hoje", "Esta Semana", "Este Mês", "Todos"])
        
        query = {"status": {"$in": status_f}}
        if colab_f != "Todos": query["colaborador_nome"] = colab_f
        agora = datetime.now()
        if tempo_f == "Hoje": query["data_hora"] = {"$gte": agora.replace(hour=0, minute=0)}
        elif tempo_f == "Esta Semana": query["data_hora"] = {"$gte": agora - timedelta(days=agora.weekday())}
        elif tempo_f == "Este Mês": query["data_hora"] = {"$gte": agora.replace(day=1, hour=0, minute=0)}

        dados = list(visits_col.find(query).sort("data_hora", -1))
        if dados:
            df = pd.DataFrame(dados)
            st.markdown("### 📋 Lista de Atendimentos")
            st.dataframe(df[['data_hora', 'colaborador_nome', 'cliente_nome', 'status', 'endereco']], use_container_width=True, hide_index=True)
            st.markdown("### 📍 Mapa Comercial")
            df['color'] = df['status'].map(COR_STATUS)
            st.map(df, color="color", size=25)

    with menu[1]:
        if dados:
            st.subheader("Funil de Conversão")
            st.bar_chart(df['status'].value_counts(), color="#0052cc")

    with menu[2]:
        colabs = list(users_col.find({"role": "colaborador"}))
        for c in colabs:
            with st.container(border=True):
                meta_doc = metas_col.find_one({"email": c['email']})
                meta_val = meta_doc['meta'] if meta_doc else 100
                col_m1, col_m2 = st.columns([1, 2])
                nova_meta = col_m1.number_input(f"Meta: {c['nome']}", value=meta_val, key=f"meta_{c['email']}")
                if nova_meta != meta_val: metas_col.update_one({"email": c['email']}, {"$set": {"meta": nova_meta}}, upsert=True)
                realizado = visits_col.count_documents({"colaborador_email": c['email'], "data_hora": {"$gte": datetime.now().replace(day=1, hour=0)}})
                col_m2.progress(min(realizado/nova_meta, 1.0) if nova_meta > 0 else 0)
                col_m2.write(f"**{realizado}** de **{nova_meta}** visitas.")

    with menu[3]:
        st.subheader("Gerenciar Equipe")
        with st.expander("➕ Cadastrar Novo Usuário"):
            with st.form("new_user"):
                n = st.text_input("Nome")
                e = st.text_input("Email")
                s = st.text_input("Senha", type="password")
                r = st.selectbox("Perfil", ["colaborador", "admin"])
                if st.form_submit_button("Salvar"):
                    users_col.insert_one({"nome": n, "email": e, "senha": hash_pw(s), "role": r, "ativo": True})
                    st.rerun()

        st.divider()
        todos_u = list(users_col.find().sort("nome", 1))
        for u in todos_u:
            with st.container(border=True):
                cu1, cu2, cu3, cu4 = st.columns([2, 2, 1, 1])
                cu1.write(f"**{u['nome']}**")
                cu2.write(u['email'])
                cu3.write(f"Perfil: {u['role']}")
                with cu4:
                    with st.popover("⚙️ Editar"):
                        # CAMPOS DE EDIÇÃO (Incluindo Resete de Senha pelo Gestor)
                        novo_n = st.text_input("Nome", value=u['nome'], key=f"n_{u['email']}")
                        novo_p = st.selectbox("Perfil", ["colaborador", "admin"], index=0 if u['role'] == 'colaborador' else 1, key=f"p_{u['email']}")
                        nova_s = st.text_input("Definir Nova Senha (Opcional)", type="password", key=f"s_{u['email']}", help="Deixe em branco para manter a atual")
                        ativo = st.toggle("Ativo", value=u.get('ativo', True), key=f"t_{u['email']}")
                        
                        if st.button("Aplicar Alterações", key=f"btn_{u['email']}", type="primary"):
                            update_data = {"nome": novo_n, "role": novo_p, "ativo": ativo}
                            if nova_s: # Se o gestor digitou algo, aplica o hash e atualiza
                                update_data["senha"] = hash_pw(nova_s)
                            
                            users_col.update_one({"email": u['email']}, {"$set": update_data})
                            st.success("Dados atualizados!")
                            st.rerun()

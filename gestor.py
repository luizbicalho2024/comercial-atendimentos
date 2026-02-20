import streamlit as st
import pandas as pd
from database import visits_col, users_col, metas_col, hash_pw
from datetime import datetime, timedelta

COR_STATUS = {"Venda Realizada": "#28a745", "Prospecção": "#0052cc", "Retorno Agendado": "#fd7e14", "Cliente Ausente": "#dc3545", "Outro": "#6c757d"}

def render_gestor():
    st.title("🛡️ Gestão Estratégica Rovema")
    menu = st.tabs(["📊 Mapa & Filtros", "📈 Inteligência", "🎯 Metas", "👥 Usuários"])

    with menu[0]:
        col1, col2 = st.columns(2)
        status_f = col1.multiselect("Status", list(COR_STATUS.keys()), default=list(COR_STATUS.keys()))
        colab_f = col2.selectbox("Colaborador", ["Todos"] + list(users_col.distinct("nome", {"role": "colaborador"})))
        
        query = {"status": {"$in": status_f}}
        if colab_f != "Todos": query["colaborador_nome"] = colab_f
        
        dados = list(visits_col.find(query).sort("data_hora", -1))
        if dados:
            df = pd.DataFrame(dados)
            df['color'] = df['status'].map(COR_STATUS)
            st.map(df, color="color")
            st.dataframe(df[['data_hora', 'colaborador_nome', 'cliente_nome', 'status', 'endereco']], use_container_width=True)

    with menu[1]:
        if dados:
            st.subheader("Funil Comercial")
            st.bar_chart(df['status'].value_counts(), color="#0052cc")
            st.subheader("Top 5 Atividade")
            st.bar_chart(df['colaborador_nome'].value_counts().head(5), color="#28a745")

    with menu[2]:
        colabs = list(users_col.find({"role": "colaborador"}))
        for c in colabs:
            meta_doc = metas_col.find_one({"email": c['email']})
            meta_val = meta_doc['meta'] if meta_doc else 100
            nova_meta = st.number_input(f"Meta: {c['nome']}", value=meta_val, key=c['email'])
            if nova_meta != meta_val: metas_col.update_one({"email": c['email']}, {"$set": {"meta": nova_meta}}, upsert=True)
            
            realizado = visits_col.count_documents({"colaborador_email": c['email'], "data_hora": {"$gte": datetime.now().replace(day=1, hour=0)}})
            st.progress(min(realizado/nova_meta, 1.0))
            st.write(f"{realizado} de {nova_meta} visitas")

    with menu[3]:
        st.subheader("Cadastrar Novo Acesso")
        with st.form("new_user"):
            n = st.text_input("Nome")
            e = st.text_input("Email")
            s = st.text_input("Senha", type="password")
            r = st.selectbox("Perfil", ["colaborador", "admin"])
            if st.form_submit_button("Salvar"):
                users_col.insert_one({"nome": n, "email": e, "senha": hash_pw(s), "role": r, "ativo": True})
                st.success("Criado!")

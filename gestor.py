import streamlit as st
import pandas as pd
from database import visits_col, users_col, metas_col, hash_pw
from datetime import datetime, timedelta

COR_STATUS = {"Venda Realizada": "#28a745", "Prospecção": "#0052cc", "Retorno Agendado": "#fd7e14", "Cliente Ausente": "#dc3545", "Outro": "#6c757d"}

def render_gestor():
    st.title("🛡️ Gestão Estratégica Rovema")
    menu = st.tabs(["📊 Acompanhamento", "📈 Inteligência", "🎯 Metas", "👥 Gestão de Usuários"])

    with menu[0]:
        st.subheader("Filtros de Visibilidade")
        col1, col2, col3 = st.columns(3)
        status_f = col1.multiselect("Status", list(COR_STATUS.keys()), default=list(COR_STATUS.keys()))
        colab_f = col2.selectbox("Filtrar Colaborador", ["Todos"] + list(users_col.distinct("nome", {"role": "colaborador"})))
        tempo_f = col3.selectbox("Período", ["Hoje", "Esta Semana", "Este Mês", "Todos"])
        
        query = {"status": {"$in": status_f}}
        if colab_f != "Todos": query["colaborador_nome"] = colab_f
        
        # Filtro de tempo
        agora = datetime.now()
        if tempo_f == "Hoje": query["data_hora"] = {"$gte": agora.replace(hour=0, minute=0)}
        elif tempo_f == "Esta Semana": query["data_hora"] = {"$gte": agora - timedelta(days=agora.weekday())}
        elif tempo_f == "Este Mês": query["data_hora"] = {"$gte": agora.replace(day=1, hour=0, minute=0)}

        dados = list(visits_col.find(query).sort("data_hora", -1))
        
        if dados:
            df = pd.DataFrame(dados)
            
            # 1. LISTA PRIMEIRO (Conforme solicitado)
            st.markdown("### 📋 Lista de Atendimentos")
            st.dataframe(df[['data_hora', 'colaborador_nome', 'cliente_nome', 'status', 'endereco']], use_container_width=True, hide_index=True)
            
            # 2. MAPA ABAIXO
            st.markdown("### 📍 Mapa de Calor Comercial")
            df['color'] = df['status'].map(COR_STATUS)
            st.map(df, color="color", size=25)
            
            csv = df.to_csv(index=False, sep=";").encode('utf-8')
            st.download_button("📥 Baixar Relatório Completo", csv, "atendimentos_comercial.csv", "text/csv")
        else:
            st.info("Nenhum atendimento encontrado para os filtros atuais.")

    with menu[1]:
        if dados:
            st.subheader("Funil de Conversão")
            st.bar_chart(df['status'].value_counts(), color="#0052cc")
            st.subheader("Top Performers (Visitas)")
            st.bar_chart(df['colaborador_nome'].value_counts().head(5), color="#28a745")

    with menu[2]:
        st.subheader("Definição de Metas Mensais")
        colabs = list(users_col.find({"role": "colaborador"}))
        for c in colabs:
            with st.container(border=True):
                meta_doc = metas_col.find_one({"email": c['email']})
                meta_val = meta_doc['meta'] if meta_doc else 100
                
                col_m1, col_m2 = st.columns([1, 2])
                nova_meta = col_m1.number_input(f"Meta: {c['nome']}", value=meta_val, key=f"meta_{c['email']}")
                
                if nova_meta != meta_val:
                    metas_col.update_one({"email": c['email']}, {"$set": {"meta": nova_meta}}, upsert=True)
                
                realizado = visits_col.count_documents({
                    "colaborador_email": c['email'], 
                    "data_hora": {"$gte": datetime.now().replace(day=1, hour=0)}
                })
                
                perc = min(realizado/nova_meta, 1.0) if nova_meta > 0 else 0
                col_m2.progress(perc)
                col_m2.write(f"**{realizado}** de **{nova_meta}** visitas concluídas.")

    with menu[3]:
        # ABA DE USUÁRIOS COMPLETA
        st.subheader("Gerenciar Equipe")
        
        # Formulário de Cadastro
        with st.expander("➕ Cadastrar Novo Usuário"):
            with st.form("new_user"):
                n = st.text_input("Nome Completo")
                e = st.text_input("Email (Login)")
                s = st.text_input("Senha", type="password")
                r = st.selectbox("Perfil", ["colaborador", "admin"])
                if st.form_submit_button("Cadastrar"):
                    if n and e and s:
                        if users_col.find_one({"email": e}):
                            st.error("Email já cadastrado.")
                        else:
                            users_col.insert_one({"nome": n, "email": e, "senha": hash_pw(s), "role": r, "ativo": True})
                            st.success(f"Usuário {n} criado!")
                            st.rerun()
                    else:
                        st.error("Preencha todos os campos.")

        st.divider()
        st.subheader("Usuários Cadastrados")
        todos_usuarios = list(users_col.find().sort("nome", 1))
        
        for u in todos_usuarios:
            with st.container(border=True):
                col_u1, col_u2, col_u3, col_u4 = st.columns([2, 2, 1, 1])
                col_u1.write(f"**{u['nome']}**")
                col_u2.write(u['email'])
                
                status_atual = "Ativo" if u.get('ativo', True) else "Inativo"
                col_u3.write(f"Role: {u['role']}")
                
                # Ações de Gerenciamento
                with col_u4:
                    with st.popover("⚙️ Editar"):
                        novo_nome = st.text_input("Alterar Nome", value=u['nome'], key=f"edit_n_{u['email']}")
                        novo_perfil = st.selectbox("Alterar Perfil", ["colaborador", "admin"], 
                                                   index=0 if u['role'] == 'colaborador' else 1, key=f"edit_r_{u['email']}")
                        
                        ativo = st.toggle("Conta Ativa", value=u.get('ativo', True), key=f"togg_{u['email']}")
                        
                        if st.button("Salvar Alterações", key=f"save_{u['email']}", type="primary"):
                            users_col.update_one({"email": u['email']}, {"$set": {
                                "nome": novo_nome,
                                "role": novo_perfil,
                                "ativo": ativo
                            }})
                            st.success("Atualizado!")
                            st.rerun()

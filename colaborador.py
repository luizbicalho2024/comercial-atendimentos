import streamlit as st
from database import visits_col, users_col, get_address, hash_pw
from streamlit_geolocation import streamlit_geolocation
from datetime import datetime, timedelta
import pandas as pd
import time

# Cores consistentes
COR_STATUS = {
    "Venda Realizada": "#28a745", 
    "Prospecção": "#0052cc", 
    "Retorno Agendado": "#fd7e14", 
    "Cliente Ausente": "#dc3545", 
    "Outro": "#6c757d"
}

def render_colaborador():
    st.title(f"🚀 Painel Comercial: {st.session_state.user_name}")
    
    menu = st.tabs([
        "📝 Registrar Visita", 
        "🗓️ Minha Agenda", 
        "🕰️ Histórico Detalhado", 
        "🗺️ Meu Mapa", 
        "🔐 Segurança"
    ])
    
    # Busca lista de clientes para a lógica de busca
    clientes_cadastrados = sorted(visits_col.distinct("cliente_nome"))

    # 1. ABA: NOVO ATENDIMENTO
    with menu[0]:
        with st.container(border=True):
            st.markdown("### Registrar Visita")
            
            # Lógica de Pesquisa de Cliente com Autocompletar
            search_term = st.text_input("Digite o nome do cliente para pesquisar *", placeholder="Ex: Mercado Silva", key="input_cliente")
            
            cliente_nome = ""
            if search_term:
                sugestoes = [c for c in clientes_cadastrados if search_term.lower() in c.lower()]
                
                if sugestoes:
                    if search_term in sugestoes:
                        cliente_nome = search_term
                        st.success(f"✅ Cliente selecionado: **{cliente_nome}**")
                    else:
                        cliente_selecionado = st.selectbox(
                            "Clientes encontrados (Selecione um ou continue digitando se for novo):",
                            options=["Usar nome digitado: " + search_term] + sugestoes,
                            key="select_cliente_sugestao"
                        )
                        cliente_nome = search_term if "Usar nome digitado: " in cliente_selecionado else cliente_selecionado
                else:
                    cliente_nome = search_term
                    st.info(f"✨ Novo cliente detectado: **{cliente_nome}**")
            
            status = st.selectbox("Resultado *", list(COR_STATUS.keys()))
            
            data_retorno = None
            if status == "Retorno Agendado":
                data_retorno = st.date_input("Agendar retorno para:", min_value=datetime.now())

            obs = st.text_area("Observações *", placeholder="Descreva como foi o atendimento...")
            
            st.divider()
            st.write("🛰️ **Validação GPS**")
            loc = streamlit_geolocation()
            
            lat, lon, ender = None, None, ""
            if loc and loc.get('latitude'):
                acc = loc.get('accuracy', 9999)
                if acc > 150:
                    st.error(f"⚠️ Sinal impreciso ({acc:.0f}m). Vá para local aberto.")
                else:
                    lat, lon = loc['latitude'], loc['longitude']
                    ender = get_address(lat, lon)
                    st.success(f"✅ GPS Validado!")
                    st.markdown(f"**Lat:** `{lat}` | **Long:** `{lon}`")
                    st.markdown(f"**Endereço:** {ender}")

            # BOTÃO COM FEEDBACK DE PROCESSAMENTO
            if st.button("Finalizar Registro", type="primary", use_container_width=True):
                if not cliente_nome or not lat:
                    st.error("Preencha o cliente e valide o GPS antes de salvar.")
                elif not obs:
                    st.error("O campo observações é obrigatório.")
                else:
                    with st.spinner("Enviando dados para o servidor Rovema..."):
                        # Inserção no Banco
                        visits_col.insert_one({
                            "colaborador_email": st.session_state.user_email,
                            "colaborador_nome": st.session_state.user_name,
                            "cliente_nome": cliente_nome,
                            "status": status,
                            "data_retorno": datetime.combine(data_retorno, datetime.min.time()) if data_retorno else None,
                            "observacoes": obs,
                            "latitude": lat, "longitude": lon, "endereco": ender,
                            "data_hora": datetime.now()
                        })
                        
                        # MENSAGENS DE FEEDBACK PARA O USUÁRIO
                        st.toast("✅ Atendimento registrado com sucesso!", icon='🚀')
                        st.success(f"Tudo certo! O atendimento de '{cliente_nome}' foi salvo no sistema.")
                        st.balloons()
                        
                        # Pequena pausa para o usuário ler a mensagem de sucesso antes de resetar a tela
                        time.sleep(2)
                        st.rerun()

    # 2. ABA: AGENDA DE RETORNOS
    with menu[1]:
        st.subheader("🗓️ Retornos Agendados")
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        agenda = list(visits_col.find({
            "colaborador_email": st.session_state.user_email, 
            "data_retorno": {"$gte": hoje}
        }).sort("data_retorno", 1))
        
        if agenda:
            for a in agenda:
                with st.expander(f"📌 {a['cliente_nome']} - Voltar em: {a['data_retorno'].strftime('%d/%m/%Y')}"):
                    st.write(f"**Última Visita:** {a['observacoes']}")
                    st.write(f"**Endereço:** {a.get('endereco', 'Não registrado')}")
        else: st.info("Sua agenda de retornos está livre.")

    # 3. ABA: HISTÓRICO DETALHADO
    with menu[2]:
        st.subheader("🕰️ Histórico de Atendimentos")
        periodo_h = st.selectbox("Filtrar por Período:", ["Todos", "Hoje", "Esta Semana", "Este Mês"], key="filtro_hist_colab")
        
        query_h = {"colaborador_email": st.session_state.user_email}
        agora = datetime.now()
        
        if periodo_h == "Hoje":
            query_h["data_hora"] = {"$gte": agora.replace(hour=0, minute=0, second=0)}
        elif periodo_h == "Esta Semana":
            query_h["data_hora"] = {"$gte": agora - timedelta(days=agora.weekday())}
        elif periodo_h == "Este Mês":
            query_h["data_hora"] = {"$gte": agora.replace(day=1, hour=0, minute=0, second=0)}

        meus = list(visits_col.find(query_h).sort("data_hora", -1))
        
        if meus:
            st.write(f"Exibindo **{len(meus)}** atendimentos.")
            for item in meus:
                with st.container(border=True):
                    h_col, a_col = st.columns([5, 1])
                    with h_col:
                        st.markdown(f"#### {item['cliente_nome']}")
                        st.caption(f"📅 {item['data_hora'].strftime('%d/%m/%Y às %H:%M')}")
                    with a_col:
                        with st.popover("🗑️"):
                            if st.button("Apagar", key=f"del_{item['_id']}", type="primary"):
                                visits_col.delete_one({"_id": item['_id']})
                                st.toast("Registro excluído.")
                                st.rerun()

                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        st.write(f"**Status:** {item.get('status', 'N/A')}")
                    with col_d2:
                        if item.get('data_retorno'):
                            st.write(f"**📅 Retorno:** {item['data_retorno'].strftime('%d/%m/%Y')}")
                    
                    st.write(f"**🏠 Endereço:** {item.get('endereco', 'Não identificado')}")
                    st.info(item.get('observacoes', 'Sem observações.'))
        else:
            st.info("Nenhum atendimento encontrado.")

    # 4. ABA: MEU MAPA
    with menu[3]:
        st.subheader("🗺️ Mapa das Minhas Visitas")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            periodo_m = st.selectbox("Período do Mapa:", ["Todos", "Hoje", "Esta Semana", "Este Mês"], key="map_period")
        with col_f2:
            status_m = st.multiselect("Status no Mapa:", list(COR_STATUS.keys()), default=list(COR_STATUS.keys()), key="map_status")
            
        query_m = {"colaborador_email": st.session_state.user_email, "status": {"$in": status_m}}
        if periodo_m == "Hoje": query_m["data_hora"] = {"$gte": agora.replace(hour=0, minute=0)}
        elif periodo_m == "Esta Semana": query_m["data_hora"] = {"$gte": agora - timedelta(days=agora.weekday())}
        elif periodo_m == "Este Mês": query_m["data_hora"] = {"$gte": agora.replace(day=1, hour=0, minute=0)}

        dados_mapa = list(visits_col.find(query_m))
        if dados_mapa:
            df_m = pd.DataFrame(dados_mapa)
            df_m['color'] = df_m['status'].map(COR_STATUS)
            st.map(df_m, color="color", size=25)
        else:
            st.info("Nenhum dado para o mapa.")

    # 5. ABA: SEGURANÇA
    with menu[4]:
        st.subheader("🔐 Segurança da Conta")
        with st.form("alterar_senha_form"):
            nova_senha = st.text_input("Nova Senha", type="password")
            confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
            if st.form_submit_button("Atualizar Minha Senha", type="primary"):
                if len(nova_senha) < 4: st.error("Mínimo 4 caracteres.")
                elif nova_senha != confirmar_senha: st.error("Senhas não conferem.")
                else:
                    users_col.update_one({"email": st.session_state.user_email}, {"$set": {"senha": hash_pw(nova_senha)}})
                    st.success("Senha atualizada!")

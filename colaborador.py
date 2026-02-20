import streamlit as st
from database import visits_col, users_col, get_address, hash_pw
from streamlit_geolocation import streamlit_geolocation
from datetime import datetime

def render_colaborador():
    st.title(f"🚀 Painel Comercial: {st.session_state.user_name}")
    # Adicionada aba de Segurança
    menu = st.tabs(["📝 Novo Atendimento", "🗓️ Minha Agenda", "🕰️ Meu Histórico", "🔐 Segurança"])
    
    clientes_cadastrados = sorted(visits_col.distinct("cliente_nome"))

    with menu[0]:
        with st.container(border=True):
            st.markdown("### Registrar Visita")
            cliente_selecionado = st.selectbox(
                "Pesquisar Cliente", 
                options=["+ Novo Cliente"] + clientes_cadastrados
            )
            
            cliente_nome = st.text_input("Nome da Nova Empresa *") if cliente_selecionado == "+ Novo Cliente" else cliente_selecionado
            status = st.selectbox("Resultado *", ["Venda Realizada", "Prospecção", "Retorno Agendado", "Cliente Ausente", "Outro"])
            
            data_retorno = None
            if status == "Retorno Agendado":
                data_retorno = st.date_input("Agendar retorno para:", min_value=datetime.now())

            obs = st.text_area("Observações *")
            
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
                    st.success(f"✅ GPS Validado! | Lat: `{lat}` | Long: `{lon}`")
                    st.markdown(f"**Endereço:** {ender}")

            if st.button("Finalizar Registro", type="primary", use_container_width=True):
                if not cliente_nome or not lat:
                    st.error("Preencha o cliente e valide o GPS.")
                else:
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
                    st.success("Atendimento registrado!")
                    st.rerun()

    with menu[1]:
        st.subheader("🗓️ Retornos Agendados")
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        agenda = list(visits_col.find({"colaborador_email": st.session_state.user_email, "data_retorno": {"$gte": hoje}}).sort("data_retorno", 1))
        if agenda:
            for a in agenda:
                with st.expander(f"📍 {a['cliente_nome']} - {a['data_retorno'].strftime('%d/%m/%Y')}"):
                    st.write(f"**Obs:** {a['observacoes']}")
        else: st.info("Sua agenda está livre.")

    with menu[2]:
        st.subheader("🕰️ Meu Histórico")
        meus = list(visits_col.find({"colaborador_email": st.session_state.user_email}).sort("data_hora", -1).limit(30))
        for item in meus:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"**{item['cliente_nome']}**")
                c2.write(f"📅 {item['data_hora'].strftime('%d/%m - %H:%M')}")
                with c3:
                    with st.popover("🗑️"):
                        if st.button("Confirmar Exclusão", key=f"del_{item['_id']}", type="primary"):
                            visits_col.delete_one({"_id": item['_id']})
                            st.rerun()

    # NOVA ABA: ALTERAR PRÓPRIA SENHA
    with menu[3]:
        st.subheader("🔐 Segurança da Conta")
        with st.form("alterar_senha_form"):
            nova_senha = st.text_input("Nova Senha", type="password")
            confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
            
            if st.form_submit_button("Atualizar Minha Senha", type="primary"):
                if len(nova_senha) < 4:
                    st.error("A senha deve ter pelo menos 4 caracteres.")
                elif nova_senha != confirmar_senha:
                    st.error("As senhas não conferem.")
                else:
                    users_col.update_one(
                        {"email": st.session_state.user_email},
                        {"$set": {"senha": hash_pw(nova_senha)}}
                    )
                    st.success("Sua senha foi atualizada com sucesso!")

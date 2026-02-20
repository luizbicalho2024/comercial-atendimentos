import streamlit as st
from database import visits_col, get_address
from streamlit_geolocation import streamlit_geolocation
from datetime import datetime

def render_colaborador():
    st.title(f"🚀 Painel Comercial: {st.session_state.user_name}")
    menu = st.tabs(["📝 Novo Atendimento", "🗓️ Minha Agenda", "🕰️ Meu Histórico"])
    
    # Lista de clientes para Autocompletar (Anti-duplicidade)
    clientes_cadastrados = sorted(visits_col.distinct("cliente_nome"))

    with menu[0]:
        with st.container(border=True):
            cliente_nome = st.selectbox("Cliente *", options=["+ Novo Cliente"] + clientes_cadastrados)
            if cliente_nome == "+ Novo Cliente":
                cliente_nome = st.text_input("Nome da Empresa")
            
            status = st.selectbox("Resultado *", ["Venda Realizada", "Prospecção", "Retorno Agendado", "Cliente Ausente", "Outro"])
            
            # Follow-up Inteligente
            data_retorno = None
            if status == "Retorno Agendado":
                data_retorno = st.date_input("Agendar Retorno para:")

            obs = st.text_area("Observações *")
            
            st.divider()
            st.write("🛰️ **Validação GPS**")
            loc = streamlit_geolocation()
            
            lat, lon, ender = None, None, ""
            if loc and loc.get('latitude'):
                acc = loc.get('accuracy', 9999)
                if acc > 150:
                    st.error(f"Sinal impreciso ({acc:.0f}m). Vá para local aberto.")
                else:
                    lat, lon = loc['latitude'], loc['longitude']
                    ender = get_address(lat, lon)
                    st.success(f"GPS Validado ({acc:.0f}m)")

            if st.button("Salvar Atendimento", type="primary", use_container_width=True):
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
                    st.success("Registrado!")
                    st.balloons()

    with menu[1]:
        hoje = datetime.now().replace(hour=0, minute=0)
        agenda = list(visits_col.find({"colaborador_email": st.session_state.user_email, "data_retorno": {"$gte": hoje}}))
        if agenda:
            for a in agenda:
                st.info(f"📅 **{a['data_retorno'].strftime('%d/%m')}** - {a['cliente_nome']}")
        else:
            st.write("Sem retornos agendados.")

    with menu[2]:
        import pandas as pd
        meus = list(visits_col.find({"colaborador_email": st.session_state.user_email}).sort("data_hora", -1).limit(15))
        if meus:
            st.dataframe(pd.DataFrame(meus)[['data_hora', 'cliente_nome', 'status']], use_container_width=True)

import streamlit as st
from database import visits_col, get_address
from streamlit_geolocation import streamlit_geolocation
from datetime import datetime
import pandas as pd

def render_colaborador():
    st.title(f"🚀 Painel Comercial: {st.session_state.user_name}")
    menu = st.tabs(["📝 Novo Atendimento", "🗓️ Minha Agenda", "🕰️ Meu Histórico"])
    
    # Busca lista de clientes para o campo de busca
    clientes_cadastrados = sorted(visits_col.distinct("cliente_nome"))

    with menu[0]:
        with st.container(border=True):
            st.markdown("### Registrar Visita")
            # O st.selectbox no Streamlit já possui busca interna (digitar para filtrar)
            cliente_selecionado = st.selectbox(
                "Pesquisar Cliente (ou selecione '+ Novo' para cadastrar)", 
                options=["+ Novo Cliente"] + clientes_cadastrados,
                help="Digite o nome para filtrar rapidamente"
            )
            
            cliente_nome = ""
            if cliente_selecionado == "+ Novo Cliente":
                cliente_nome = st.text_input("Nome da Nova Empresa *")
            else:
                cliente_nome = cliente_selecionado
            
            status = st.selectbox("Resultado da Visita *", ["Venda Realizada", "Prospecção", "Retorno Agendado", "Cliente Ausente", "Outro"])
            
            data_retorno = None
            if status == "Retorno Agendado":
                data_retorno = st.date_input("Agendar data de retorno:", min_value=datetime.now())

            obs = st.text_area("Observações detalhadas *")
            
            st.divider()
            st.write("🛰️ **Validação de Localização**")
            loc = streamlit_geolocation()
            
            lat, lon, ender = None, None, ""
            if loc and loc.get('latitude'):
                acc = loc.get('accuracy', 9999)
                if acc > 150:
                    st.error(f"⚠️ Sinal GPS impreciso ({acc:.0f}m). Saia debaixo de coberturas e tente novamente.")
                else:
                    lat, lon = loc['latitude'], loc['longitude']
                    ender = get_address(lat, lon)
                    st.success(f"✅ GPS Validado!")
                    # Exibição detalhada conforme solicitado
                    st.markdown(f"**Lat:** `{lat}` | **Long:** `{lon}`")
                    st.markdown(f"**Endereço capturado:** {ender}")

            if st.button("Finalizar e Enviar", type="primary", use_container_width=True):
                if not cliente_nome or cliente_nome == "+ Novo Cliente":
                    st.error("Por favor, informe o nome do cliente.")
                elif not lat:
                    st.error("A localização GPS é obrigatória e precisa estar validada.")
                elif not obs:
                    st.error("Adicione uma observação sobre o atendimento.")
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
                    st.success("Atendimento registrado com sucesso!")
                    st.balloons()
                    st.rerun()

    with menu[1]:
        st.subheader("🗓️ Retornos Agendados")
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        agenda = list(visits_col.find({
            "colaborador_email": st.session_state.user_email, 
            "data_retorno": {"$gte": hoje}
        }).sort("data_retorno", 1))
        
        if agenda:
            for a in agenda:
                with st.expander(f"📍 {a['cliente_nome']} - {a['data_retorno'].strftime('%d/%m/%Y')}"):
                    st.write(f"**Última Obs:** {a['observacoes']}")
                    st.write(f"**Endereço:** {a['endereco']}")
        else:
            st.info("Sua agenda está livre por enquanto.")

    with menu[2]:
        st.subheader("🕰️ Meu Histórico Recente")
        meus = list(visits_col.find({"colaborador_email": st.session_state.user_email}).sort("data_hora", -1).limit(30))
        
        if meus:
            for item in meus:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.write(f"**{item['cliente_nome']}**")
                    c2.write(f"📅 {item['data_hora'].strftime('%d/%m - %H:%M')}")
                    
                    # Funcionalidade de Exclusão com confirmação
                    with c3:
                        with st.popover("🗑️"):
                            st.warning("Excluir?")
                            if st.button("Sim, apagar", key=f"del_{item['_id']}", type="primary"):
                                visits_col.delete_one({"_id": item['_id']})
                                st.rerun()
                    st.caption(f"Status: {item['status']} | Local: {item.get('endereco', 'N/A')}")
        else:
            st.write("Nenhum atendimento realizado ainda.")

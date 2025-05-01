import streamlit as st
import pandas as pd
import gspread
import streamlit.components.v1 as components
import json
from oauth2client.service_account import ServiceAccountCredentials

def carregar_dados():
    sheet_id = "1ZsHsE0OVq9v_gHiYuSkkkXv6IElW0QA6zpD3eBUQNs0"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(url)
    return df

def atualizar_checkin_google(nome, checkin_status):
    try:
        creds_dict = json.loads(st.secrets["google"]["credentials"])
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gc = gspread.authorize(credentials)

        sh = gc.open_by_key('1ZsHsE0OVq9v_gHiYuSkkkXv6IElW0QA6zpD3eBUQNs0')
        worksheet = sh.worksheet('Página1')
        lista_nomes = worksheet.col_values(1)
        for idx, nome_planilha in enumerate(lista_nomes):
            if nome_planilha.strip().lower() == nome.strip().lower():
                worksheet.update_cell(idx + 1, 33, checkin_status)  # coluna AG
                return True
        return False
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")
        return False

def leitor_qr_html():
    html_code = '''
    <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
    <div id="reader" style="width:100%"></div>
    <script>
        function onScanSuccess(decodedText, decodedResult) {
            window.location.href = window.location.href.split("?")[0] + "?qr_code=" + encodeURIComponent(decodedText);
        }
        var html5QrcodeScanner = new Html5QrcodeScanner(
            "reader",
            { fps: 10, qrbox: 250, rememberLastUsedCamera: true, facingMode: { exact: "environment" } },
            false
        );
        html5QrcodeScanner.render(onScanSuccess);
    </script>
    '''
    components.html(html_code, height=500)

st.set_page_config(page_title="Controle de Credenciamento", layout="centered")
st.title('Controle de Credenciamento')

if "df_participantes" not in st.session_state:
    st.session_state.df_participantes = carregar_dados()
if "mostrar_scanner" not in st.session_state:
    st.session_state.mostrar_scanner = False

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("📷 Abrir Scanner"):
        st.session_state.mostrar_scanner = True
        st.rerun()
with col2:
    if st.button("❌ Fechar Scanner"):
        st.session_state.mostrar_scanner = False
        st.rerun()

if st.session_state.mostrar_scanner:
    leitor_qr_html()

qr_code = st.query_params.get("qr_code", [None])[0]

if qr_code:
    df = st.session_state.df_participantes
    pessoa = df[df['eTicket'].astype(str).str.strip() == qr_code.strip()]
    if not pessoa.empty:
        nome = pessoa.iloc[0]['Nome']
        idx = pessoa.index[0]
        st.session_state.df_participantes.loc[idx, 'Checkin'] = 'Sim'
        sucesso = atualizar_checkin_google(nome, 'Sim')
        if sucesso:
            st.success(f"✅ Check-in feito e salvo com sucesso para {nome}")
        else:
            st.error("⚠️ Check-in não foi salvo. Verifique a planilha.")
    else:
        st.error("⚠️ QR Code não encontrado na lista.")
    st.session_state.mostrar_scanner = False
    st.experimental_set_query_params()
    st.rerun()

st.markdown("---")

df = st.session_state.df_participantes
total = df.shape[0]
credenciados = df[df['Checkin'] == 'Sim'].shape[0]
faltando = df[df['Checkin'] != 'Sim'].shape[0]
percentual = (credenciados / total) * 100 if total > 0 else 0

col1, col2, col3 = st.columns(3)
with col1: st.metric(label="Total", value=total)
with col2: st.metric(label="Credenciados", value=credenciados)
with col3: st.metric(label="Faltando", value=f"{faltando} ({percentual:.1f}%)")

st.markdown("---")

st.subheader('Participantes para Credenciar')
busca_faltantes = st.text_input('Buscar Faltantes', key="busca_faltantes")
faltantes = df[df['Checkin'] != 'Sim']
faltantes_view = faltantes if busca_faltantes.strip() == '' else faltantes

for idx, participante in faltantes_view.iterrows():
    if busca_faltantes.strip() == '' or busca_faltantes.lower() in participante['Nome'].lower():
        col1, col2 = st.columns([6, 2])
        with col1: st.write(participante['Nome'])
        with col2:
            if st.button("Fazer Check-in", key=f"checkin_{idx}"):
                st.session_state.df_participantes.loc[idx, 'Checkin'] = 'Sim'
                sucesso = atualizar_checkin_google(participante['Nome'], 'Sim')
                if sucesso:
                    st.success(f"✅ Check-in salvo com sucesso para {participante['Nome']}")
                else:
                    st.error("⚠️ Falha ao salvar na planilha.")
                st.rerun()

st.markdown("---")

st.subheader('Participantes Credenciados')
busca_credenciados = st.text_input('Buscar Credenciados', key="busca_credenciados")
credenciados_df = df[df['Checkin'] == 'Sim']
credenciados_view = credenciados_df if busca_credenciados.strip() == '' else credenciados_df

for idx, participante in credenciados_view.iterrows():
    if busca_credenciados.strip() == '' or busca_credenciados.lower() in participante['Nome'].lower():
        col1, col2 = st.columns([6, 2])
        with col1: st.write(participante['Nome'])
        with col2:
            if st.button("Desfazer Check-in", key=f"desfazer_{idx}"):
                st.session_state.df_participantes.loc[idx, 'Checkin'] = 'Não'
                sucesso = atualizar_checkin_google(participante['Nome'], 'Não')
                if sucesso:
                    st.success(f"✅ Check-in desfeito para {participante['Nome']}")
                else:
                    st.error("⚠️ Falha ao atualizar a planilha.")
                st.rerun()
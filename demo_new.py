import streamlit as st
from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from st_aggrid import StAggridTheme
import pandas as pd
from sqlalchemy.orm import Session
from fraud_ai.data import get_db, update_transaction
#from fraud_ai.config import OPENAI_API_KEY, ELEVEN_KEY, DATABASE_URL
from fraud_ai.config import DATABASE_URL
from fraud_ai.alerts import get_alerts, update_alert
from fraud_ai.models import Transaction
from fraud_ai.whitelist import add_to_whitelist, is_card_whitelisted, remove_from_whitelist
from fraud_ai.blocked import add_to_blocked, is_card_blocked, remove_from_blocked
from fraud_ai.reset_password import add_password_reset, has_password_reset, remove_password_reset
from fraud_ai.conversation import get_conversation
from datetime import datetime
import asyncio
import os
from demo_runner import run_demo
import time
from style_CSS import page_style, chat_style, tab_style, bottom_style

tts_backend_option = "openai"
stt_enabled_option = True
stt_provider_option = "openai"

def run_demo_thread(tts_backend, stt_enabled, stt_provider, name, surname):
    """Esegue il demo in background con asyncio"""
    if os.path.exists("fraud_ai.db"):
        os.remove("fraud_ai.db")
    asyncio.run(run_demo(tts_backend=tts_backend, stt_enabled=stt_enabled, stt_provider=stt_provider,name=name, surname=surname))

st.set_page_config(page_title="Agatha The AI Fraud Analyst ", page_icon="🕵️", layout="wide", initial_sidebar_state="expanded")
st.markdown(page_style, unsafe_allow_html=True)
# inizializza le variabili di sessione se non esistono
if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = None
if "name_input_option" not in st.session_state:
    st.session_state.name_input_option = 'John'
if "surname_input_option" not in st.session_state:
    st.session_state.surname_input_option = 'Doe'
if "demo_started" not in st.session_state:
    st.session_state.demo_started  = False
if "recalling" not in st.session_state:
    st.session_state.recalling = False
if "end" not in st.session_state:
    st.session_state.end = False

# se le chiavi non ci sono → chiedi login
if st.session_state.demo_started == False:
    if os.path.exists("fraud_ai.db"):
        os.remove("fraud_ai.db")
    _,log,_=st.columns([2,1,2])
    with log:
        st.image("logo.png", use_container_width="always")
    

    st.markdown("<br><span class='subTitle'>Enter your Name to personalize the demo</span>", unsafe_allow_html=True)
    openai_input = os.getenv('OPENAI_API_KEY')
    na, surna = st.columns([1,1])
    with na:
        name_input = st.text_input("Your Name", type="default", placeholder="Enter your name (default John)")
        if name_input == "":
            name_input = "John"
    with surna:
        surname_input = st.text_input("Your Surname", type="default", placeholder="Enter your surname (default Doe)")
        if surname_input == "":
            surname_input = "Doe"
    _, start_col, _ = st.columns([1,2,1])
    with start_col:
        if st.button("Start Demo", type="primary", use_container_width=True):
            if openai_input:# and eleven_input:
                st.session_state.openai_api_key = openai_input
                st.session_state.name_input_option = name_input
                st.session_state.surname_input_option = surname_input
                st.session_state.demo_started = True
                with st.spinner("Calling..."):
                    run_demo_thread(
                        tts_backend=tts_backend_option,
                        stt_enabled=stt_enabled_option,
                        stt_provider=stt_provider_option,
                        name=st.session_state.name_input_option,
                        surname=st.session_state.surname_input_option
                    )
                st.session_state.end=True
                st.rerun()
            #else:
            #    st.error("You must enter both keys to continue.", icon="⚠️")
    
else:
    log, _,  tit_col_log,res_col=st.columns([0.5,0.2, 4, 2])
    with log:
        st.image("/Users/andreaalessandrelli/Downloads/Agata/fraud_ai_project/logo.png", use_container_width="always")
    with tit_col_log:
        st.markdown("<br><span class='Title'>Agatha control dashboard</span>", unsafe_allow_html=True)

    # --- DB CONNECTION ---
    @st.cache_resource
    def get_db_cached():
        return next(get_db())

    db = get_db_cached()

    @st.cache_data(ttl=15)
    def load_alerts(refresh_counter):
        return get_alerts(db, limit=10)

    @st.cache_data(ttl=15)
    def load_transactions(card_number, refresh_counter):
        txs = db.query(Transaction).filter(
            Transaction.card_number == card_number
        ).order_by(Transaction.id.desc()).limit(10).all()
        return txs

    # --- Helpers ---
    def get_card_status(card_number):
        whitelisted = is_card_whitelisted(db, card_number) is not None
        blocked = is_card_blocked(db, card_number) is not None
        reset = has_password_reset(db, card_number) is not None
        return whitelisted, blocked, reset

    # --- Toggle actions ---
    def toggle_block_card(db: Session, card_number: str):
        try:
            if is_card_blocked(db, card_number):
                remove_from_blocked(db, card_number)
                return False
            else:
                add_to_blocked(db, card_number)
                return True
        except Exception:
            db.rollback()
            raise

    def toggle_whitelist_card(db: Session, card_number: str):
        try:
            if is_card_whitelisted(db, card_number):
                remove_from_whitelist(db, card_number)
                return False
            else:
                add_to_whitelist(db, card_number)
                return True
        except Exception:
            db.rollback()
            raise

    def toggle_password_reset(db: Session, card_number: str):
        try:
            if has_password_reset(db, card_number):
                remove_password_reset(db, card_number)
                return False
            else:
                add_password_reset(db, card_number, reason="manual analyst action")
                return True
        except Exception:
            db.rollback()
            raise



    c_succ, _, c_logout, c_reset = st.columns([2,1, 1,1])
    with c_succ:
        # inizializza flag nella sessione
        if "show_success" not in st.session_state:
            st.session_state.show_success = True

        if st.session_state.show_success:
            #st.markdown('<div class="custom-success">✅ API keys successfully uploaded!</div>', unsafe_allow_html=True)
            st.session_state.show_success = False  # non verrà più mostrato
    with c_reset:
        if st.button("New Call"):
            api_key = st.session_state.openai_api_key  # salvo la chiave
            name_input = st.session_state.name_input_option
            surname_input = st.session_state.surname_input_option
            st.session_state.clear()
            st.cache_data.clear()
            st.cache_resource.clear()
            st.session_state.openai_api_key = api_key  # la rimetto
            st.session_state.name_input_option =  name_input # la rimetto
            st.session_state.surname_input_option = surname_input  # la rimetto
            st.session_state.recalling = True
            st.session_state.end=False
            st.session_state.demo_started=False
            st.rerun()
            
            
    # --- Auto refresh ---
    st_autorefresh(interval=100, limit=None, key="refresh")

    if "alert_index" not in st.session_state:
        st.session_state.alert_index = 0
    if "analyst_notes" not in st.session_state:
        st.session_state.analyst_notes = ""
    if "refresh_counter" not in st.session_state:
        st.session_state.refresh_counter = 0
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    def transactions_to_df_editable(txs, alert_tx_id):
        data = []
        for tx in txs:
            data.append({
                "id": tx.id,
                "Timestamp": tx.timestamp.strftime('%Y-%m-%d %H:%M:%S') if isinstance(tx.timestamp, datetime) else str(tx.timestamp),
                "Amount": tx.amount,
                "Merchant": tx.merchant_name,
                "Status": tx.status,
                "Fraud Score": f"{tx.fraud_score:.2f}" if tx.fraud_score is not None else "N/A",
                "Fraudulent": tx.is_fraud,
                "Alerted": "⚠️" if tx.id == alert_tx_id else ""
            })
        return pd.DataFrame(data)

    # --- Conversation UI Premium Fixed (User Text Right-Aligned Corrected) ---
    def render_conversation(alert_id):
        messages = get_conversation(db, alert_id)
        # aggiorna solo i nuovi messaggi
        if len(messages) > len(st.session_state.chat_messages):
            st.session_state.chat_messages = messages
        # HTML chat
        with st.container(key = 'chatContainer', height=130):
            chat_html = ''
            for msg in st.session_state.chat_messages:
                role_class = "assistant" if msg.role == "assistant" else "user"
                icon = "🤖" if msg.role == "assistant" else "👤"
                content = msg.content.replace("\n", "<br>")  # gestisce a capo
                chat_html += f'''<span class="chat-row {role_class}">
                        <span class="icon">{icon}</span>
                        <span class="chat-bubble">
                        <span class="message-text">{content}</span>
                        </span>
                    </span>
                '''
            chat_html += ''
            return st.markdown(chat_style+chat_html, unsafe_allow_html=True)





    # --- Load alert ---
    alerts = load_alerts(st.session_state.refresh_counter)

    def load_alert(index, refresh_counter):
        if index < 0 or index >= len(alerts):
            return None, None, None, None, None
        alert = alerts[index]
        tx = db.query(Transaction).filter(Transaction.id == alert.transaction_id).first()
        if not tx:
            return alert, None, None, None, None
        card_number = tx.card_number
        customer_name = f"{tx.customer_first_name} {tx.customer_last_name}" if tx.customer_first_name and tx.customer_last_name else "Unknown"
        notes = alert.analyst_notes or ""
        tx_list = load_transactions(card_number, refresh_counter)
        return alert, card_number, customer_name, notes, tx_list

    alert, card_number, customer_name, notes, tx_list = load_alert(st.session_state.alert_index, st.session_state.refresh_counter)
    if notes != st.session_state.get("analyst_notes", ""):
        st.session_state.analyst_notes = notes
    # --- Header ---
    if alert is None:
        st.markdown(page_style + f"<span class='Title'>No alerts to display.</span><br>", unsafe_allow_html=True)
    else:
        whitelisted, blocked, reset = get_card_status(card_number)
        status_parts = []
        if whitelisted:
            status_parts.append("✅ Whitelisted")
        if blocked:
            status_parts.append("⛔ Blocked")
        if reset:
            status_parts.append("🔑 Password Reset")
        col_id1, col_id2, _  = st.columns([2,1,1])
        with col_id1:
            col_11, col_22,_= st.columns([3,1,1])
            with col_11:
                st.markdown(page_style + f"<span class='subTitle'>🚨 Alert ID: {alert.id}</span> <br><span class='identificativoCost'>Customer: </span> <span class='valoreCost'>{customer_name}</span><span class='identificativoCost'> | </span><span class='identificativoCost'>  Transaction ID: </span> <span class='valoreCost'>{alert.transaction_id}</span>", unsafe_allow_html=True)


    # --- Main Layout ---
    if alert is not None:
        col_conv, col_annotation = st.columns([1.5,1])
        with col_conv:
            with st.container(border=True, key='gino', height=250):
                    st.markdown(tab_style+"<span class='subTitle'> 💬 Conversation Transcript</span>", unsafe_allow_html=True)
                    render_conversation(alert.id)
        
        with col_annotation:
            # Analyst notes + actions
            st.markdown("<span class='subTitle'>✍️ Analyst Notes & Actions</span>", unsafe_allow_html=True)
            with st.container(border=True, height=130):
                text = st.session_state.analyst_notes.replace("$", "\$").replace("\n", "<br>")
                analyst_notes = st.markdown(f"<span class='notes'>{text}</span>", unsafe_allow_html=True)
                st.session_state.analyst_notes = analyst_notes
            st.markdown(f"<span class='identificativoCard'>Card: </span> <span class='valoreCard'>{card_number}</span><br><span class='identificativoCard'>Action: </span> <span class='valoreCard'>{' | '.join(status_parts) if status_parts else 'No special status'}</span>", unsafe_allow_html=True)

        _, col_buttons1, col_buttons2, col_buttons3,_ = st.columns([1,1,1,1,1])
        st.markdown(bottom_style, unsafe_allow_html=True)

        with col_buttons1:
            if st.button("Whitelist Card", key="Whitelist", icon="✅"):
                toggle_whitelist_card(db, card_number)
                st.session_state.refresh_counter += 1
                st.experimental_rerun()
        with col_buttons2:
            if st.button("Block Card", icon="⛔", key="Block"):
                toggle_block_card(db, card_number)
                st.session_state.refresh_counter += 1
                st.experimental_rerun()
        with col_buttons3:
            if st.button("Reset Password", icon = "🔑", key="Reset"):
                toggle_password_reset(db, card_number)
                st.session_state.refresh_counter += 1
                st.experimental_rerun()





        with st.container(border=True, height=200):
            with st.spinner("Loading transactions..."):
                df = transactions_to_df_editable(tx_list, alert.transaction_id)

                js_code = JsCode(f"""
                function(params) {{
                    if (params.data.id === {alert.transaction_id}) {{
                        return {{'fontWeight': 'bold', 'backgroundColor': '#ffff99'}};
                    }}
                    if (params.data.Fraudulent === true) {{
                        return {{'backgroundColor': '#ffcccc'}};
                    }}
                    return null;
                }}
                """)
                
                gb = GridOptionsBuilder.from_dataframe(df)
                gb.configure_column("Fraudulent", editable=True, cellEditor='agCheckboxCellEditor')
                gb.configure_column("Fraud Score", type=["numericColumn"], precision=2)
                gb.configure_column("Alerted", editable=False)
                gb.configure_selection(selection_mode="multiple", use_checkbox=True, pre_selected_rows=[0,1])
                gb.configure_grid_options(getRowStyle=js_code)
                gb.configure_auto_height(autoHeight=True)
                grid_options = gb.build()
                #rowClassRules = {"bg-danger": "params.data.Fraudulent == 1"}



                custom_theme = (  
                    StAggridTheme(base="alpine") 
                    .withParams(fontSize=15,
                    rowBorder=True,
                    backgroundColor="#FFFFFF")  
                    .withParts('iconSetQuartz')  
                )


                grid_response = AgGrid(
                    df,
                    update_mode=GridUpdateMode.MODEL_CHANGED,
                    allow_unsafe_jscode=True,
                    columnSize="sizeToFit",
                    theme = custom_theme,
                    gridOptions=grid_options,
                    fit_columns_on_grid_load=True,
                    use_container_width=True
                )

                edited_df = grid_response['data']


        

        with st.container(border=True, height=66, key='saving'):
            _, col1, col2, col3,_ = st.columns([2,1,1,1,2])
            with col1:
                if st.button("Previous Alert", icon="⬅️"):
                    st.session_state.alert_index = max(0, st.session_state.alert_index - 1)
                    st.experimental_rerun()
            with col2:
                if st.button("Save Changes", icon="💾"):
                    update_alert(db, alert.id, analyst_notes=analyst_notes)
                    for _, row in edited_df.iterrows():
                        update_transaction(db, row['id'], is_fraud=row['Fraudulent'])
                    st.session_state.refresh_counter += 1
                    st.success("Changes saved.")
                    st.experimental_rerun()
            with col3:
                if st.button("Next Alert", icon = "➡️"):
                    st.session_state.alert_index = min(len(alerts)-1, st.session_state.alert_index + 1)
                    st.experimental_rerun()



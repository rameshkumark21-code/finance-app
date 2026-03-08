import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
from streamlit_extras.stylable_container import stylable_container

# --- 1. SETTINGS ---
st.set_page_config(page_title="FinTrack India Pro", page_icon="₹", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #ffffff; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    div[data-testid="stDialog"] {
        background-color: #111111 !important;
        border: 1px solid #333333 !important;
        border-radius: 28px !important;
    }
    /* Summary Bubble Styling */
    .summary-box {
        background: #1c1c1e; 
        padding: 15px; 
        border-radius: 12px; 
        border-left: 4px solid #2563eb; 
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    try:
        e = conn.read(worksheet="Expenses", ttl=0)
        c = conn.read(worksheet="Categories", ttl=0)
        return e, c
    except:
        # Expected columns: Date, Amount, Category, Note, Mode
        return pd.DataFrame(columns=["Date", "Amount", "Category", "Note", "Mode"]), pd.DataFrame(columns=["Category"])

df, cat_df = load_data()
categories = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty else ["Bills", "Dining", "Fuel", "Groceries", "Medical", "Shopping"]
payment_modes = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]

# --- 3. EXPERT UI/UX MULTI-STEP DIALOG ---
@st.dialog("Log Expense")
def log_expense_modal():
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "temp_amount" not in st.session_state:
        st.session_state.temp_amount = None 
    if "temp_cat" not in st.session_state:
        st.session_state.temp_cat = categories[0]
    if "temp_mode" not in st.session_state:
        st.session_state.temp_mode = "UPI"
    if "temp_note" not in st.session_state:
        st.session_state.temp_note = ""

    # STEP 1: AMOUNT
    if st.session_state.step == 1:
        st.subheader("How much?")
        amount = st.number_input("Amount", min_value=0, step=1, value=st.session_state.temp_amount, placeholder="₹ 0", key="ux_amt", label_visibility="collapsed")
        st.components.v1.html("""<script>var input = window.parent.document.querySelector('input[placeholder="₹ 0"]'); if (input) { input.focus(); }</script>""", height=0)
        if st.button("Continue ➡️", use_container_width=True, type="primary"):
            if amount:
                st.session_state.temp_amount = amount
                st.session_state.step = 2
                st.rerun()

    # STEP 2: CATEGORY & MODE
    elif st.session_state.step == 2:
        st.subheader("Details")
        cat = st.selectbox("Category", categories, index=categories.index(st.session_state.temp_cat) if st.session_state.temp_cat in categories else 0)
        mode = st.selectbox("Payment Mode", payment_modes, index=payment_modes.index(st.session_state.temp_mode))
        
        nav = st.columns(2)
        if nav[0].button("⬅️ Back"):
            st.session_state.step = 1
            st.rerun()
        if nav[1].button("Next ➡️", type="primary"):
            st.session_state.temp_cat, st.session_state.temp_mode = cat, mode
            st.session_state.step = 3
            st.rerun()

    # STEP 3: NOTE & DONE
    elif st.session_state.step == 3:
        st.subheader("Finalize")
        st.markdown(f"<div class='summary-box'><b>₹{st.session_state.temp_amount}</b> via <b>{st.session_state.temp_mode}</b><br><small>{st.session_state.temp_cat}</small></div>", unsafe_allow_html=True)
        note = st.text_input("Note (Optional)", value=st.session_state.temp_note)
        
        nav = st.columns(2)
        if nav[0].button("⬅️ Back"):
            st.session_state.temp_note = note
            st.session_state.step = 2
            st.rerun()
        if nav[1].button("DONE ✅", type="primary"):
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz)
            new_row = pd.DataFrame([{"Date": now.strftime("%Y-%m-%d %H:%M:%S"), "Amount": st.session_state.temp_amount, "Category": st.session_state.temp_cat, "Note": note, "Mode": st.session_state.temp_mode}])
            conn.update(worksheet="Expenses", data=pd.concat([df, new_row], ignore_index=True))
            st.session_state.step = 1
            st.session_state.temp_amount = None
            st.session_state.show_modal = False
            st.rerun()

# --- 4. MILESTONE LOGIC ---
st.title("₹ FinTrack Pro")

if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'])
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    
    # Quarterly Milestone (Q1: Jan-Mar, Q2: Apr-Jun, etc.)
    q_map = {1:1, 2:1, 3:1, 4:2, 5:2, 6:2, 7:3, 8:3, 9:3, 10:4, 11:4, 12:4}
    curr_q = q_map[now.month]
    q_df = df[(df['Date'].dt.year == now.year) & (df['Date'].dt.month.map(q_map) == curr_q)]
    hdfc_q_spend = q_df[q_df['Mode'] == 'HDFC Credit Card']['Amount'].sum()
    
    # Dashboard Metrics
    m1, m2 = st.columns(2)
    m1.metric("Spent Today", f"₹{df[df['Date'].dt.date == now.date()]['Amount'].sum():,.0f}")
    m2.metric(f"Q{curr_q} HDFC Milestone", f"₹{hdfc_q_spend:,.0f}", help="Target: ₹1,00,000 for quarterly benefits")

    if hdfc_q_spend >= 100000:
        st.success("🎉 HDFC Quarterly Milestone Reached!")
    
    st.write("### Recent Activity")
    st.dataframe(df.tail(10).sort_values(by="Date", ascending=False), use_container_width=True)

# --- 5. FLOATING BUTTON ---
if "show_modal" not in st.session_state: st.session_state.show_modal = False
if st.session_state.show_modal: log_expense_modal()

with stylable_container(key="fab", css_styles="button { position: fixed; bottom: 35px; right: 25px; width: 65px !important; height: 65px !important; border-radius: 50% !important; background-color: #2563eb !important; color: white !important; font-size: 38px !important; z-index: 1000; border: none !important; box-shadow: 0 8px 24px rgba(37, 99, 235, 0.4); }"):
    if st.button("+", key="fab_trigger"):
        st.session_state.show_modal = True
        st.rerun()

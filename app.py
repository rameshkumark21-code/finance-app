import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
from streamlit_extras.stylable_container import stylable_container

# --- 1. SETTINGS & CUSTOM CSS ---
st.set_page_config(page_title="FinTrack India Pro", page_icon="₹", layout="centered")

st.markdown("""
    <style>
    /* Global Dark Theme Overrides */
    .stApp { background-color: #000000; color: #ffffff; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    
    /* Dialog Box (Popup) Styling */
    div[data-testid="stDialog"] {
        background-color: #0a0a0a !important;
        border: 1px solid #1a1a1a !important;
        border-radius: 24px !important;
    }
    
    /* Metrics Styling */
    [data-testid="stMetricValue"] {
        font-size: 48px !important;
        font-weight: 900 !important;
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA INITIALIZATION ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    try:
        e = conn.read(worksheet="Expenses", ttl=0)
        c = conn.read(worksheet="Categories", ttl=0)
        return e, c
    except:
        return pd.DataFrame(columns=["Date", "Amount", "Category", "Note"]), pd.DataFrame(columns=["Category"])

df, cat_df = load_data()
# Alphabetical sorting for categories
categories = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty else ["Bills", "Dining", "Fuel", "Groceries", "Medical", "Shopping"]

# --- 3. IMPROVED MULTI-STEP DIALOG ---
@st.dialog("Quick Log")
def log_expense_modal():
    # Initialize state ONLY if not present to stop the reset loop
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "temp_amount" not in st.session_state:
        st.session_state.temp_amount = 0
    if "temp_cat" not in st.session_state:
        st.session_state.temp_cat = categories[0]
    if "temp_note" not in st.session_state:
        st.session_state.temp_note = ""

    # --- STEP 1: AMOUNT ---
    if st.session_state.step == 1:
        st.subheader("₹ Enter Amount")
        amount = st.number_input("Amount", min_value=0, step=1, value=st.session_state.temp_amount, key="m_amt_input", placeholder="0")
        
        # JS to focus the keyboard automatically
        st.components.v1.html(f"""
            <script>
                var input = window.parent.document.querySelector('input[placeholder="0"]');
                if (input) {{ input.focus(); }}
            </script>
        """, height=0)

        st.markdown("<br>", unsafe_allow_html=True)
        cols = st.columns([0.8, 0.2])
        if cols[1].button("➡️", key="btn_next_1"):
            if amount > 0:
                st.session_state.temp_amount = amount
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("Enter an amount")

    # --- STEP 2: CATEGORY ---
    elif st.session_state.step == 2:
        st.subheader("📂 Select Category")
        try:
            current_idx = categories.index(st.session_state.temp_cat)
        except ValueError:
            current_idx = 0

        cat = st.selectbox("Category", categories, index=current_idx, key="m_cat_select")
        
        st.markdown("<br>", unsafe_allow_html=True)
        cols = st.columns([0.2, 0.6, 0.2])
        if cols[0].button("⬅️", key="btn_back_2"):
            st.session_state.step = 1
            st.rerun()
        if cols[2].button("➡️", key="btn_next_2"):
            st.session_state.temp_cat = cat
            st.session_state.step = 3
            st.rerun()

    # --- STEP 3: NOTE & SAVE ---
    elif st.session_state.step == 3:
        st.subheader("📝 Final Details")
        st.write(f"Logging **₹{st.session_state.temp_amount}** for **{st.session_state.temp_cat}**")
        
        note = st.text_input("Notes (Optional)", value=st.session_state.temp_note, key="m_note_input")
        
        st.markdown("<br>", unsafe_allow_html=True)
        cols = st.columns([0.2, 0.5, 0.3])
        if cols[0].button("⬅️", key="btn_back_3"):
            st.session_state.temp_note = note
            st.session_state.step = 2
            st.rerun()
            
        if cols[2].button("ADD", type="primary", key="btn_final_submit", use_container_width=True):
            with st.spinner("Saving..."):
                tz = pytz.timezone('Asia/Kolkata')
                now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                new_row = pd.DataFrame([{"Date": now, "Amount": st.session_state.temp_amount, "Category": st.session_state.temp_cat, "Note": note}])
                
                # Update GSheets
                conn.update(worksheet="Expenses", data=pd.concat([df, new_row], ignore_index=True))
                
                # Cleanup state
                st.session_state.step = 1
                st.session_state.temp_amount = 0
                st.session_state.temp_note = ""
                
                st.success("Transaction Saved!")
                st.rerun()

# --- 4. MAIN DASHBOARD ---
st.title("₹ FinTrack Pro")

# Today's Total Calculation
if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'])
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    today = datetime.now(pytz.timezone('Asia/Kolkata')).date()
    today_total = df[df['Date'].dt.date == today]['Amount'].sum()
    st.metric("Spent Today", f"₹{today_total:,.0f}")

st.write("### Recent Activity")
st.dataframe(df.tail(15).sort_values(by="Date", ascending=False), use_container_width=True)

# --- 5. FLOATING ACTION BUTTON ---
with stylable_container(
    key="fab",
    css_styles="""
        button {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 65px !important;
            height: 65px !important;
            border-radius: 50% !important;
            background-color: #2563eb !important;
            color: white !important;
            font-size: 36px !important;
            font-weight: bold !important;
            z-index: 1000;
            border: none !important;
            box-shadow: 0 4px 20px rgba(37, 99, 235, 0.6) !important;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        button:hover {
            transform: scale(1.1);
            background-color: #1d4ed8 !important;
        }
    """
):
    if st.button("+", key="main_fab_btn"):
        log_expense_modal()

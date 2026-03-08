import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
# Ensure you have 'pip install streamlit-extras'
from streamlit_extras.stylable_container import stylable_container

# --- 1. SETTINGS ---
st.set_page_config(page_title="FinTrack India Pro", page_icon="₹", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #ffffff; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    
    /* Dialog Box Styling */
    div[data-testid="stDialog"] {
        background-color: #0a0a0a !important;
        border: 1px solid #1a1a1a !important;
        border-radius: 24px !important;
    }
    
    /* Navigation Button Styles */
    .nav-btn { font-size: 24px !important; }
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
        return pd.DataFrame(columns=["Date", "Amount", "Category", "Note"]), pd.DataFrame(columns=["Category"])

df, cat_df = load_data()
# Alpha-sorted categories
categories = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty else ["Bills", "Dining", "Fuel", "Groceries", "Medical", "Shopping"]

# --- 3. MULTI-STEP LOGGING DIALOG ---
@st.dialog("Quick Log")
def log_expense_modal():
    # State setup
    if "step" not in st.session_state:
        st.session_state.step = 1
        st.session_state.temp_amount = None
        st.session_state.temp_cat = categories[0]
        st.session_state.temp_note = ""

    # --- STEP 1: AMOUNT ---
    if st.session_state.step == 1:
        st.subheader("₹ Enter Amount")
        amount = st.number_input("Amount", min_value=0, step=1, value=st.session_state.temp_amount, key="m_amt", placeholder="0")
        
        # JS to focus the keyboard automatically
        st.components.v1.html(f"""
            <script>
                var input = window.parent.document.querySelector('input[placeholder="0"]');
                if (input) {{ input.focus(); }}
            </script>
        """, height=0)

        cols = st.columns([0.8, 0.2])
        if cols[1].button("➡️", key="next1"):
            if amount:
                st.session_state.temp_amount = amount
                st.session_state.step = 2
                st.rerun()

    # --- STEP 2: CATEGORY ---
    elif st.session_state.step == 2:
        st.subheader("📂 Select Category")
        cat = st.selectbox("Category", categories, index=categories.index(st.session_state.temp_cat))
        
        cols = st.columns([0.2, 0.6, 0.2])
        if cols[0].button("⬅️", key="back2"):
            st.session_state.step = 1
            st.rerun()
        if cols[2].button("➡️", key="next2"):
            st.session_state.temp_cat = cat
            st.session_state.step = 3
            st.rerun()

    # --- STEP 3: NOTE & ADD ---
    elif st.session_state.step == 3:
        st.subheader("📝 Final Note")
        note = st.text_input("Notes (Optional)", value=st.session_state.temp_note)
        
        cols = st.columns([0.2, 0.5, 0.3])
        if cols[0].button("⬅️", key="back3"):
            st.session_state.temp_note = note
            st.session_state.step = 2
            st.rerun()
        if cols[2].button("ADD", type="primary"):
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{"Date": now, "Amount": st.session_state.temp_amount, "Category": st.session_state.temp_cat, "Note": note}])
            conn.update(worksheet="Expenses", data=pd.concat([df, new_row], ignore_index=True))
            
            # Reset state for next time
            st.session_state.step = 1
            st.session_state.temp_amount = None
            st.success("Logged!")
            st.rerun()

# --- 4. DASHBOARD ---
st.title("₹ FinTrack Pro")

# Total Spent Today
if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'])
    today = datetime.now(pytz.timezone('Asia/Kolkata')).date()
    today_total = df[df['Date'].dt.date == today]['Amount'].astype(float).sum()
    st.metric("Today", f"₹{today_total:,.0f}")

st.dataframe(df.tail(10).sort_index(ascending=False), use_container_width=True)

# --- 5. FLOATING "+" BUTTON ---
with stylable_container(
    key="add_button",
    css_styles="""
        button {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px !important;
            height: 60px !important;
            border-radius: 50% !important;
            background-color: #2563eb !important;
            color: white !important;
            font-size: 32px !important;
            font-weight: bold !important;
            z-index: 1000;
            border: none !important;
            box-shadow: 0 4px 15px rgba(37, 99, 235, 0.5);
        }
    """
):
    if st.button("+"):
        log_expense_modal()

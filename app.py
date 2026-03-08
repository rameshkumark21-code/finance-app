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
    .stApp { background-color: #000000; color: #ffffff; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    
    /* Floating Action Button (FAB) */
    .fab-container {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 999;
    }
    .fab-button button {
        background-color: #2563eb !important;
        color: white !important;
        border-radius: 50% !important;
        width: 60px !important;
        height: 60px !important;
        font-size: 30px !important;
        box-shadow: 0px 4px 15px rgba(37, 99, 235, 0.4) !important;
        border: none !important;
    }
    
    /* Dialog Styling */
    div[data-testid="stDialog"] {
        background-color: #0a0a0a !important;
        border: 1px solid #1a1a1a !important;
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
# Sorted Categories
categories = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty else ["Bills", "Clout Fit", "Dining", "Fuel", "Groceries", "Home", "Medical", "Shopping"]

# --- 3. THE MULTI-STEP DIALOG ---
@st.dialog("Log New Expense")
def log_expense_modal():
    # Initialize Modal State
    if "step" not in st.session_state:
        st.session_state.step = 1
        st.session_state.temp_amount = None
        st.session_state.temp_cat = categories[0]
        st.session_state.temp_note = ""

    # --- STEP 1: AMOUNT ---
    if st.session_state.step == 1:
        st.write("### 1. Enter Amount")
        amount = st.number_input("Amount", min_value=0, step=1, value=st.session_state.temp_amount, key="modal_amt", placeholder="₹ 0")
        
        # JS to focus the keyboard automatically
        st.components.v1.html("""
            <script>
                var input = window.parent.document.querySelector('input[aria-label="Amount"]');
                if (input) { input.focus(); }
            </script>
        """, height=0)

        col_next = st.columns([0.8, 0.2])[1]
        if col_next.button("➡️"):
            if amount:
                st.session_state.temp_amount = amount
                st.session_state.step = 2
                st.rerun()

    # --- STEP 2: CATEGORY ---
    elif st.session_state.step == 2:
        st.write("### 2. Select Category")
        cat = st.selectbox("Category", categories, index=categories.index(st.session_state.temp_cat))
        
        nav_cols = st.columns([0.2, 0.6, 0.2])
        if nav_cols[0].button("⬅️"):
            st.session_state.step = 1
            st.rerun()
        if nav_cols[2].button("➡️"):
            st.session_state.temp_cat = cat
            st.session_state.step = 3
            st.rerun()

    # --- STEP 3: NOTES & SAVE ---
    elif st.session_state.step == 3:
        st.write("### 3. Add Notes")
        note = st.text_input("Note (Optional)", value=st.session_state.temp_note)
        
        nav_cols = st.columns([0.2, 0.5, 0.3])
        if nav_cols[0].button("⬅️"):
            st.session_state.step = 2
            st.rerun()
        if nav_cols[2].button("ADD", type="primary"):
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{"Date": now, "Amount": st.session_state.temp_amount, "Category": st.session_state.temp_cat, "Note": note}])
            conn.update(worksheet="Expenses", data=pd.concat([df, new_row], ignore_index=True))
            
            # Reset and close
            del st.session_state.step
            st.success("Saved!")
            st.rerun()

# --- 4. MAIN DASHBOARD ---
st.title("₹ FinTrack Pro")

# Today's Summary Card
if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'])
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    today_total = df[df['Date'].dt.date == datetime.now(pytz.timezone('Asia/Kolkata')).date()]['Amount'].sum()
    st.metric("Spent Today", f"₹{today_total:,.0f}")

st.subheader("Recent History")
st.dataframe(df.tail(10).sort_index(ascending=False), use_container_width=True)

# --- 5. FLOATING ACTION BUTTON ---
with stylable_container(key="fab", css_styles="""
    {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 1000;
    }
"""):
    if st.button("+", key="fab_btn", help="Add Expense"):
        log_expense_modal()

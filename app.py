import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
from streamlit_extras.stylable_container import stylable_container

# --- 1. SETTINGS & THEME ---
st.set_page_config(page_title="FinTrack India Pro", page_icon="₹", layout="centered")

st.markdown("""
    <style>
    /* Global Dark Theme */
    .stApp { background-color: #000000; color: #ffffff; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    
    /* Dialog Box (Popup) Styling */
    div[data-testid="stDialog"] {
        background-color: #0a0a0a !important;
        border: 1px solid #1a1a1a !important;
        border-radius: 24px !important;
    }
    
    /* Custom Metric Styling */
    [data-testid="stMetricValue"] {
        font-size: 42px !important;
        font-weight: 800 !important;
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

# Logic to sort categories alphabetically
if not cat_df.empty:
    categories = sorted(cat_df["Category"].dropna().tolist())
else:
    categories = ["Bills", "Dining", "Fuel", "Groceries", "Medical", "Shopping"]

# --- 3. THE MULTI-STEP POPUP (DIALOG) ---
@st.dialog("Log New Expense")
def log_expense_modal():
    # Initialize multi-step state
    if "step" not in st.session_state:
        st.session_state.step = 1
        st.session_state.temp_amount = None
        st.session_state.temp_cat = categories[0]
        st.session_state.temp_note = ""

    # --- STEP 1: AMOUNT ---
    if st.session_state.step == 1:
        st.write("### 1. Enter Amount")
        # Blank by default using value=None
        amount = st.number_input(
            "Amount", 
            min_value=0, 
            step=1, 
            value=st.session_state.temp_amount, 
            key="modal_amt", 
            placeholder="0"
        )
        
        # Auto-focus keyboard JS
        st.components.v1.html("""
            <script>
                var input = window.parent.document.querySelector('input[placeholder="0"]');
                if (input) { input.focus(); }
            </script>
        """, height=0)

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns([0.8, 0.2])
        if col2.button("➡️", key="step1_next"):
            if amount and amount > 0:
                st.session_state.temp_amount = amount
                st.session_state.step = 2
                st.rerun()
            else:
                st.warning("Enter an amount")

    # --- STEP 2: CATEGORY ---
    elif st.session_state.step == 2:
        st.write("### 2. Select Category")
        # Alphabetically sorted dropdown
        selected_cat = st.selectbox(
            "Choose a category", 
            categories, 
            index=categories.index(st.session_state.temp_cat) if st.session_state.temp_cat in categories else 0
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        nav_cols = st.columns([0.2, 0.6, 0.2])
        if nav_cols[0].button("⬅️", key="step2_back"):
            st.session_state.step = 1
            st.rerun()
        if nav_cols[2].button("➡️", key="step2_next"):
            st.session_state.temp_cat = selected_cat
            st.session_state.step = 3
            st.rerun()

    # --- STEP 3: NOTES & ADD ---
    elif st.session_state.step == 3:
        st.write("### 3. Final Details")
        st.info(f"Amount: ₹{st.session_state.temp_amount} | Category: {st.session_state.temp_cat}")
        
        note = st.text_input("Note (Optional)", value=st.session_state.temp_note, placeholder="e.g. Weekly milk")
        
        st.markdown("<br>", unsafe_allow_html=True)
        nav_cols = st.columns([0.2, 0.5, 0.3])
        if nav_cols[0].button("⬅️", key="step3_back"):
            st.session_state.temp_note = note
            st.session_state.step = 2
            st.rerun()
        
        if nav_cols[2].button("ADD", type="primary", use_container_width=True):
            # Final Save Logic
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            
            new_row = pd.DataFrame([{
                "Date": now, 
                "Amount": st.session_state.temp_amount, 
                "Category": st.session_state.temp_cat, 
                "Note": note
            }])
            
            conn.update(worksheet="Expenses", data=pd.concat([df, new_row], ignore_index=True))
            
            # Reset state and cleanup
            st.session_state.step = 1
            st.session_state.temp_amount = None
            st.session_state.temp_note = ""
            st.success("Expense Saved!")
            st.rerun()

# --- 4. MAIN DASHBOARD ---
st.title("₹ FinTrack Pro")

# Today's Spending Calculation
if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'])
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    today = datetime.now(pytz.timezone('Asia/Kolkata')).date()
    today_total = df[df['Date'].dt.date == today]['Amount'].sum()
    st.metric("Spent Today", f"₹{today_total:,.0f}")

st.write("### Recent Activity")
st.dataframe(df.tail(15).sort_values(by="Date", ascending=False), use_container_width=True)

# --- 5. FLOATING "+" BUTTON ---
with stylable_container(
    key="floating_plus",
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
            font-size: 35px !important;
            font-weight: bold !important;
            z-index: 1000;
            border: none !important;
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5) !important;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        button:hover {
            background-color: #1d4ed8 !important;
            transform: scale(1.05);
        }
    """
):
    if st.button("+"):
        log_expense_modal()

import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
from streamlit_extras.stylable_container import stylable_container

# --- 1. SETTINGS (FROZEN) ---
st.set_page_config(page_title="FinTrack India Pro", page_icon="₹", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #ffffff; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    
    /* Native Mobile Sheet Feel */
    div[data-testid="stDialog"] {
        background-color: #111111 !important;
        border: 1px solid #333333 !important;
        border-radius: 28px !important;
        padding: 20px !important;
    }
    
    /* Clean Typography */
    h3 {
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
        margin-bottom: 20px !important;
    }
    
    /* Input Styling */
    input {
        background-color: #1c1c1e !important;
        border-radius: 12px !important;
        border: 1px solid #3a3a3c !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA (FROZEN) ---
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
categories = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty else ["Bills", "Dining", "Fuel", "Groceries", "Medical", "Shopping"]

# --- 3. EXPERT UI/UX MULTI-STEP DIALOG ---
@st.dialog("Log Expense")
def log_expense_modal():
    # Persistent State Management
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "temp_amount" not in st.session_state:
        st.session_state.temp_amount = None 
    if "temp_cat" not in st.session_state:
        st.session_state.temp_cat = categories[0]
    if "temp_note" not in st.session_state:
        st.session_state.temp_note = ""

    # --- STEP 1: AMOUNT (The Hook) ---
    if st.session_state.step == 1:
        st.markdown("<p style='color: #8e8e93; font-size: 14px;'>STEP 1 OF 3</p>", unsafe_allow_html=True)
        st.subheader("How much did you spend?")
        
        amount = st.number_input(
            "Amount", 
            min_value=0, 
            step=1, 
            value=st.session_state.temp_amount, 
            placeholder="₹ 0.00", 
            key="ux_amt_in",
            label_visibility="collapsed"
        )
        
        # Expert UX: Auto-focus for speed
        st.components.v1.html("""<script>var input = window.parent.document.querySelector('input[placeholder="₹ 0.00"]'); if (input) { input.focus(); }</script>""", height=0)

        st.markdown("<br><br>", unsafe_allow_html=True)
        # Primary Action Button
        if st.button("Continue  ➡️", use_container_width=True, type="primary", key="next_to_cat"):
            if amount and amount > 0:
                st.session_state.temp_amount = amount
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("Please enter a valid amount")

    # --- STEP 2: CATEGORY (The Context) ---
    elif st.session_state.step == 2:
        st.markdown("<p style='color: #8e8e93; font-size: 14px;'>STEP 2 OF 3</p>", unsafe_allow_html=True)
        st.subheader("What was it for?")
        
        # Vertical spacing for thumb-friendly select
        cat = st.selectbox(
            "Category", 
            categories, 
            index=categories.index(st.session_state.temp_cat) if st.session_state.temp_cat in categories else 0,
            key="ux_cat_sel"
        )
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        nav_cols = st.columns([1, 1])
        if nav_cols[0].button("⬅️  Back", use_container_width=True, key="back_to_amt"):
            st.session_state.step = 1
            st.rerun()
        if nav_cols[1].button("Next  ➡️", use_container_width=True, type="primary", key="next_to_note"):
            st.session_state.temp_cat = cat
            st.session_state.step = 3
            st.rerun()

    # --- STEP 3: NOTE (The Detail) ---
    elif st.session_state.step == 3:
        st.markdown("<p style='color: #8e8e93; font-size: 14px;'>STEP 3 OF 3</p>", unsafe_allow_html=True)
        st.subheader("Any extra details?")
        
        # Summary bubble for verification
        st.markdown(f"""
            <div style='background: #1c1c1e; padding: 15px; border-radius: 12px; border-left: 4px solid #2563eb; margin-bottom: 20px;'>
                <span style='color: #8e8e93;'>Logging:</span><br>
                <b style='font-size: 18px;'>₹{st.session_state.temp_amount}</b> in <b>{st.session_state.temp_cat}</b>
            </div>
        """, unsafe_allow_html=True)

        note = st.text_input("Note (Optional)", value=st.session_state.temp_note, placeholder="e.g. Starbucks lunch", key="ux_note_in")
        
        st.markdown("<br>", unsafe_allow_html=True)
        nav_cols = st.columns([1, 1])
        if nav_cols[0].button("⬅️  Back", use_container_width=True, key="back_to_cat"):
            st.session_state.temp_note = note
            st.session_state.step = 2
            st.rerun()
        if nav_cols[1].button("DONE  ✅", use_container_width=True, type="primary", key="finalize_log"):
            with st.spinner("Syncing..."):
                tz = pytz.timezone('Asia/Kolkata')
                now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                new_row = pd.DataFrame([{"Date": now, "Amount": st.session_state.temp_amount, "Category": st.session_state.temp_cat, "Note": note}])
                
                conn.update(worksheet="Expenses", data=pd.concat([df, new_row], ignore_index=True))
                
                # Cleanup and Exit
                st.session_state.step = 1
                st.session_state.temp_amount = None
                st.session_state.temp_note = ""
                st.session_state.show_modal = False
                st.success("Successfully Logged!")
                st.rerun()

# --- 4. DASHBOARD (FROZEN) ---
st.title("₹ FinTrack Pro")

if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'])
    today = datetime.now(pytz.timezone('Asia/Kolkata')).date()
    today_total = df[df['Date'].dt.date == today]['Amount'].astype(float).sum()
    st.metric("Spent Today", f"₹{today_total:,.0f}")

st.write("### Recent Activity")
st.dataframe(df.tail(15).sort_index(ascending=False), use_container_width=True)

# --- 5. FLOATING "+" BUTTON (UX LOCK) ---
if "show_modal" not in st.session_state:
    st.session_state.show_modal = False

if st.session_state.show_modal:
    log_expense_modal()

with stylable_container(
    key="fab",
    css_styles="""
        button {
            position: fixed;
            bottom: 35px;
            right: 25px;
            width: 65px !important;
            height: 65px !important;
            border-radius: 50% !important;
            background-color: #2563eb !important;
            color: white !important;
            font-size: 38px !important;
            font-weight: 300 !important;
            z-index: 1000;
            border: none !important;
            box-shadow: 0 8px 24px rgba(37, 99, 235, 0.4);
            transition: all 0.2s ease-in-out;
        }
        button:active {
            transform: scale(0.9);
            background-color: #1d4ed8 !important;
        }
    """
):
    if st.button("+", key="fab_trigger"):
        st.session_state.show_modal = True
        st.rerun()

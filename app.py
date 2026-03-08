import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
from streamlit_extras.stylable_container import stylable_container

# --- 1. SETTINGS & EXPERT UI ---
st.set_page_config(page_title="FinTrack Pro", page_icon="₹", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #ffffff; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    .dashboard-tile {
        background-color: #111111;
        border: 1px solid #222222;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 10px;
    }
    .tile-label { color: #888888; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }
    .tile-value { font-size: 1.8rem; font-weight: 700; margin-top: 5px; }
    .stProgress > div > div > div > div { background-color: #2563eb; }
    div[data-testid="stDialog"] {
        background-color: #0a0a0a !important;
        border: 1px solid #333333 !important;
        border-radius: 28px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA LOAD ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    try:
        e = conn.read(worksheet="Expenses", ttl=0)
        c = conn.read(worksheet="Categories", ttl=0)
        s = conn.read(worksheet="Settings", ttl=0)
        return e, c, s
    except:
        return (pd.DataFrame(columns=["Date", "Amount", "Category", "Note", "Mode"]), 
                pd.DataFrame(columns=["Category"]),
                pd.DataFrame(columns=["Category", "Budget", "Is_Recurring", "Day_of_Month"]))

df, cat_df, settings_df = load_data()
categories = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty else ["Bills", "Dining", "Fuel", "Groceries", "Medical", "Shopping"]
payment_modes = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]

# --- 3. SIDEBAR: MAINTAIN SETTINGS ---
with st.sidebar:
    st.title("⚙️ App Settings")
    st.subheader("Manage Guardrails")
    
    with st.form("settings_form"):
        sel_cat = st.selectbox("Select Category", categories)
        
        # Get existing values if they exist
        existing = settings_df[settings_df['Category'] == sel_cat]
        def_budget = int(existing['Budget'].values[0]) if not existing.empty else 0
        def_rec = bool(existing['Is_Recurring'].values[0]) if not existing.empty else False
        def_day = int(existing['Day_of_Month'].values[0]) if not existing.empty else 1

        new_budget = st.number_input("Monthly Budget (₹)", min_value=0, value=def_budget, step=500)
        is_rec = st.checkbox("Is Recurring Expense?", value=def_rec)
        rec_day = st.slider("Auto-log Day", 1, 31, value=def_day)
        
        if st.form_submit_button("Update Settings"):
            # Update local settings_df
            new_entry = pd.DataFrame([{"Category": sel_cat, "Budget": new_budget, "Is_Recurring": is_rec, "Day_of_Month": rec_day}])
            updated_settings = pd.concat([settings_df[settings_df['Category'] != sel_cat], new_entry], ignore_index=True)
            conn.update(worksheet="Settings", data=updated_settings)
            st.success(f"Updated {sel_cat}!")
            st.rerun()

# --- 4. RECURRING ENGINE ---
def process_recurring():
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    if not settings_df.empty and not df.empty:
        rules = settings_df[settings_df['Is_Recurring'] == True]
        for _, rule in rules.iterrows():
            if now.day >= int(rule['Day_of_Month']):
                month_str = now.strftime("%Y-%m")
                mask = (df['Date'].str.contains(month_str)) & (df['Category'] == rule['Category'])
                if df[mask].empty:
                    new_row = pd.DataFrame([{"Date": now.strftime("%Y-%m-%d %H:%M:%S"), "Amount": rule['Budget'], "Category": rule['Category'], "Mode": "Auto-Debit", "Note": "Auto-Log"}])
                    conn.update(worksheet="Expenses", data=pd.concat([df, new_row], ignore_index=True))
                    st.toast(f"✅ Recurring {rule['Category']} logged.")

process_recurring()

# --- 5. DASHBOARD ---
st.title("₹ FinTrack Pro")

if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'])
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    
    # Metrics Tiles
    c1, c2 = st.columns(2)
    today_total = df[df['Date'].dt.date == now.date()]['Amount'].sum()
    c1.markdown(f'<div class="dashboard-tile"><div class="tile-label">Today</div><div class="tile-value">₹{today_total:,.0f}</div></div>', unsafe_allow_html=True)
    
    q_map = {1:1, 2:1, 3:1, 4:2, 5:2, 6:2, 7:3, 8:3, 9:3, 10:4, 11:4, 12:4}
    curr_q = q_map[now.month]
    h_spend = df[(df['Date'].dt.month.map(q_map) == curr_q) & (df['Mode'] == 'HDFC Credit Card')]['Amount'].sum()
    color = "#2563eb" if h_spend < 100000 else "#22c55e"
    c2.markdown(f'<div class="dashboard-tile" style="border-left: 4px solid {color};"><div class="tile-label">HDFC Q{curr_q}</div><div class="tile-value">₹{h_spend:,.0f}</div></div>', unsafe_allow_html=True)

    # Budget Guardrails
    st.write("### Budget Guardrails")
    for _, b_row in settings_df.iterrows():
        if b_row['Budget'] > 0:
            spent = df[(df['Date'].dt.month == now.month) & (df['Category'] == b_row['Category'])]['Amount'].sum()
            ratio = min(spent / b_row['Budget'], 1.0)
            st.write(f"**{b_row['Category']}** (₹{spent:,.0f} / ₹{b_row['Budget']:,.0f})")
            st.progress(ratio)

# --- 6. ADD EXPENSE MODAL ---
@st.dialog("Log Expense")
def log_expense_modal():
    if "step" not in st.session_state: st.session_state.step = 1
    if "temp_amt" not in st.session_state: st.session_state.temp_amt = None
    
    if st.session_state.step == 1:
        amt = st.number_input("Amount", min_value=0, step=1, value=st.session_state.temp_amt, placeholder="₹ 0", key="ux_amt", label_visibility="collapsed")
        st.components.v1.html("""<script>var input = window.parent.document.querySelector('input[placeholder="₹ 0"]'); if (input) { input.focus(); }</script>""", height=0)
        if st.button("Continue ➡️", use_container_width=True, type="primary"):
            if amt: st.session_state.temp_amt, st.session_state.step = amt, 2; st.rerun()
    elif st.session_state.step == 2:
        cat = st.selectbox("Category", categories)
        mode = st.selectbox("Mode", payment_modes)
        cols = st.columns(2)
        if cols[0].button("⬅️ Back"): st.session_state.step = 1; st.rerun()
        if cols[1].button("Done ✅", type="primary", use_container_width=True):
            now_tz = datetime.now(pytz.timezone('Asia/Kolkata'))
            new_data = pd.DataFrame([{"Date": now_tz.strftime("%Y-%m-%d %H:%M:%S"), "Amount": st.session_state.temp_amt, "Category": cat, "Mode": mode, "Note": ""}])
            conn.update(worksheet="Expenses", data=pd.concat([df, new_data], ignore_index=True))
            st.session_state.step = 1; st.session_state.temp_amt = None; st.session_state.show_modal = False; st.rerun()

# --- 7. FLOATING BUTTON ---
if "show_modal" not in st.session_state: st.session_state.show_modal = False
if st.session_state.show_modal: log_expense_modal()

with stylable_container(key="fab", css_styles="button { position: fixed; bottom: 35px; right: 25px; width: 65px !important; height: 65px !important; border-radius: 50% !important; background-color: #2563eb !important; color: white !important; font-size: 38px !important; z-index: 1000; box-shadow: 0 8px 24px rgba(37,99,235,0.4); }"):
    if st.button("+", key="fab_trigger"):
        st.session_state.show_modal = True
        st.rerun()

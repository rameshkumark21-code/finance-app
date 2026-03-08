import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
from streamlit_extras.stylable_container import stylable_container

# --- 1. SETTINGS & EXPERT UI CSS ---
st.set_page_config(page_title="FinTrack Pro", page_icon="₹", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #ffffff; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    
    /* Tile Styling */
    .dashboard-tile {
        background-color: #111111;
        border: 1px solid #222222;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 10px;
        height: 100%;
    }
    .tile-label { color: #888888; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }
    .tile-value { font-size: 1.8rem; font-weight: 700; margin-top: 5px; }
    .tile-sub { font-size: 0.75rem; color: #444444; margin-top: 5px; }
    
    /* Progress Bar Theme */
    .stProgress > div > div > div > div { background-color: #2563eb; }
    
    /* Dialog / Popup */
    div[data-testid="stDialog"] {
        background-color: #0a0a0a !important;
        border: 1px solid #333333 !important;
        border-radius: 28px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA LOAD & AUTOMATION ---
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

# --- 2b. RECURRING EXPENSE AUTO-ENGINE ---
def process_recurring():
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    if not settings_df.empty and not df.empty:
        recurring_rules = settings_df[settings_df['Is_Recurring'] == True]
        for _, rule in recurring_rules.iterrows():
            if now.day >= int(rule['Day_of_Month']):
                # Check if this category was already logged this month
                month_check = now.strftime("%Y-%m")
                mask = (df['Date'].str.contains(month_check)) & (df['Category'] == rule['Category'])
                if df[mask].empty:
                    new_row = pd.DataFrame([{
                        "Date": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "Amount": rule['Budget'],
                        "Category": rule['Category'],
                        "Mode": "Auto-Debit",
                        "Note": "Automated Recurring Payment"
                    }])
                    conn.update(worksheet="Expenses", data=pd.concat([df, new_row], ignore_index=True))
                    st.toast(f"✅ Auto-logged {rule['Category']}")

process_recurring()

# --- 3. ADD EXPENSE MODAL ---
@st.dialog("Log Expense")
def log_expense_modal():
    if "step" not in st.session_state: st.session_state.step = 1
    if "temp_amt" not in st.session_state: st.session_state.temp_amt = None
    
    if st.session_state.step == 1:
        st.write("### Amount")
        amt = st.number_input("Amount", min_value=0, step=1, value=st.session_state.temp_amt, placeholder="₹ 0", key="ux_amt", label_visibility="collapsed")
        st.components.v1.html("""<script>var input = window.parent.document.querySelector('input[placeholder="₹ 0"]'); if (input) { input.focus(); }</script>""", height=0)
        if st.button("Continue ➡️", use_container_width=True, type="primary"):
            if amt: st.session_state.temp_amt, st.session_state.step = amt, 2
            st.rerun()
    elif st.session_state.step == 2:
        st.write("### Details")
        cat = st.selectbox("Category", categories)
        mode = st.selectbox("Mode", payment_modes)
        cols = st.columns(2)
        if cols[0].button("⬅️ Back"): st.session_state.step = 1; st.rerun()
        if cols[1].button("Done ✅", type="primary", use_container_width=True):
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz)
            new_row = pd.DataFrame([{"Date": now.strftime("%Y-%m-%d %H:%M:%S"), "Amount": st.session_state.temp_amt, "Category": cat, "Mode": mode, "Note": ""}])
            conn.update(worksheet="Expenses", data=pd.concat([df, new_row], ignore_index=True))
            st.session_state.step = 1; st.session_state.temp_amt = None; st.session_state.show_modal = False
            st.rerun()

# --- 4. DASHBOARD TILES LOGIC ---
st.title("₹ FinTrack Pro")

if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'])
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    
    q_map = {1:1, 2:1, 3:1, 4:2, 5:2, 6:2, 7:3, 8:3, 9:3, 10:4, 11:4, 12:4}
    curr_q = q_map[now.month]
    
    today_total = df[df['Date'].dt.date == now.date()]['Amount'].sum()
    
    hdfc_q_spend = 0
    if 'Mode' in df.columns:
        q_df = df[(df['Date'].dt.year == now.year) & (df['Date'].dt.month.map(q_map) == curr_q)]
        hdfc_q_spend = q_df[q_df['Mode'] == 'HDFC Credit Card']['Amount'].sum()
    
    # ROW 1: PRIMARY TILES
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        st.markdown(f"""<div class="dashboard-tile"><div class="tile-label">Spent Today</div><div class="tile-value">₹{today_total:,.0f}</div></div>""", unsafe_allow_html=True)
    with r1c2:
        color = "#2563eb" if hdfc_q_spend < 100000 else "#22c55e"
        st.markdown(f"""<div class="dashboard-tile" style="border-left: 4px solid {color};"><div class="tile-label">HDFC Q{curr_q}</div><div class="tile-value">₹{hdfc_q_spend:,.0f}</div><div class="tile-sub">Target: ₹1,00,000</div></div>""", unsafe_allow_html=True)

    # ROW 2: BUDGET GUARDRAILS (The Upgrade)
    st.write("")
    st.markdown('<div class="tile-label">Budget Guardrails</div>', unsafe_allow_html=True)
    if not settings_df.empty:
        for _, b_row in settings_df.iterrows():
            if b_row['Budget'] > 0:
                month_total = df[(df['Date'].dt.month == now.month) & (df['Category'] == b_row['Category'])]['Amount'].sum()
                percent = min(month_total / b_row['Budget'], 1.0)
                
                # Dynamic Color Feedback
                status_text = "Safe"
                if percent >= 1.0: status_text = "LIMIT EXCEEDED"
                elif percent >= 0.8: status_text = "Warning"
                
                cols = st.columns([0.4, 0.6])
                cols[0].write(f"**{b_row['Category']}**")
                cols[1].progress(percent)
                st.caption(f"₹{month_total:,.0f} of ₹{b_row['Budget']:,.0f} spent • {status_text}")

    # ROW 3: RECENT ACTIVITY
    st.write("")
    st.markdown('<div class="tile-label">Recent Transactions</div>', unsafe_allow_html=True)
    st.dataframe(df.tail(8).sort_values(by="Date", ascending=False)[['Date', 'Amount', 'Category', 'Mode']], use_container_width=True, hide_index=True)

# --- 5. FLOATING BUTTON ---
if "show_modal" not in st.session_state: st.session_state.show_modal = False
if st.session_state.show_modal: log_expense_modal()

with stylable_container(key="fab", css_styles="button { position: fixed; bottom: 35px; right: 25px; width: 65px !important; height: 65px !important; border-radius: 50% !important; background-color: #2563eb !important; color: white !important; font-size: 38px !important; z-index: 1000; box-shadow: 0 8px 24px rgba(37,99,235,0.4); }"):
    if st.button("+", key="fab_trigger"):
        st.session_state.show_modal = True
        st.rerun()

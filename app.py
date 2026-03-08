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
        margin-bottom: 15px;
    }
    .tile-label { color: #888888; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }
    .tile-value { font-size: 1.8rem; font-weight: 700; margin-top: 5px; }
    /* Hide Sidebar Navigation Label */
    section[data-testid="stSidebarNav"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA LOAD ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=2)
def load_all_data():
    try:
        e = conn.read(worksheet="Expenses", ttl=0)
        c = conn.read(worksheet="Categories", ttl=0)
        s = conn.read(worksheet="Settings", ttl=0)
        return e, c, s
    except:
        return (pd.DataFrame(columns=["Date", "Amount", "Category", "Note", "Mode"]), 
                pd.DataFrame(columns=["Category"]),
                pd.DataFrame(columns=["Category", "Budget", "Is_Recurring", "Day_of_Month"]))

df, cat_df, settings_df = load_all_data()
categories = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty else []
payment_modes = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]

# --- 3. NAVIGATION SYSTEM ---
with st.sidebar:
    st.title("₹ FinTrack")
    page = st.radio("Navigate", ["🏠 Home", "🔄 Recurring", "🏷️ Categories"])
    st.divider()
    st.caption("Family Sync Active (Shared GSheet)")

# --- 4. PAGE: HOME ---
if page == "🏠 Home":
    st.title("Dashboard")
    
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        now = datetime.now(pytz.timezone('Asia/Kolkata'))
        
        # Tile 1: Today
        today_total = df[df['Date'].dt.date == now.date()]['Amount'].sum()
        st.markdown(f'<div class="dashboard-tile"><div class="tile-label">Spent Today</div><div class="tile-value">₹{today_total:,.0f}</div></div>', unsafe_allow_html=True)
        
        # Tile 2: Q1 (or current Quarter)
        q_map = {1:1, 2:1, 3:1, 4:2, 5:2, 6:2, 7:3, 8:3, 9:3, 10:4, 11:4, 12:4}
        curr_q = q_map[now.month]
        h_spend = df[(df['Date'].dt.month.map(q_map) == curr_q) & (df['Mode'] == 'HDFC Credit Card')]['Amount'].sum()
        color = "#2563eb" if h_spend < 100000 else "#22c55e"
        st.markdown(f'<div class="dashboard-tile" style="border-left: 4px solid {color};"><div class="tile-label">HDFC Q{curr_q} Milestone</div><div class="tile-value">₹{h_spend:,.0f}</div></div>', unsafe_allow_html=True)
        
        # Recent 6 Expenses
        st.write("### Latest 6 Transactions")
        recent = df.tail(6).sort_values(by="Date", ascending=False)[['Amount', 'Category', 'Mode']]
        st.dataframe(recent, use_container_width=True, hide_index=True)

# --- 5. PAGE: RECURRING MAINTENANCE ---
elif page == "🔄 Recurring":
    st.title("Recurring Rules")
    
    # Add New Rule
    with st.expander("➕ Add New Recurring Expense"):
        with st.form("new_rec_form"):
            new_cat = st.selectbox("Category", categories)
            new_amt = st.number_input("Amount (Budget)", min_value=0)
            new_day = st.slider("Day of Month", 1, 31, 1)
            if st.form_submit_button("Save Rule"):
                new_entry = pd.DataFrame([{"Category": new_cat, "Budget": new_amt, "Is_Recurring": True, "Day_of_Month": new_day}])
                updated = pd.concat([settings_df, new_entry], ignore_index=True)
                conn.update(worksheet="Settings", data=updated)
                st.rerun()

    # List & Edit Existing
    for i, row in settings_df.iterrows():
        with st.container(border=True):
            cols = st.columns([2, 1, 1])
            cols[0].write(f"**{row['Category']}**\n₹{row['Budget']} on day {row['Day_of_Month']}")
            if cols[1].button("Edit", key=f"edit_rec_{i}"):
                st.session_state.editing_rec = i
            if cols[2].button("Delete", key=f"del_rec_{i}"):
                updated = settings_df.drop(i)
                conn.update(worksheet="Settings", data=updated)
                st.rerun()

# --- 6. PAGE: CATEGORIES ---
elif page == "🏷️ Categories":
    st.title("Manage Categories")
    
    with st.form("add_cat"):
        new_c = st.text_input("New Category Name")
        if st.form_submit_button("Add Category"):
            new_df = pd.DataFrame([{"Category": new_c}])
            updated = pd.concat([cat_df, new_df], ignore_index=True)
            conn.update(worksheet="Categories", data=updated)
            st.rerun()

    st.write("### Existing Categories")
    for i, row in cat_df.iterrows():
        c1, c2 = st.columns([3, 1])
        c1.write(row['Category'])
        if c2.button("🗑️", key=f"del_cat_{i}"):
            updated = cat_df.drop(i)
            conn.update(worksheet="Categories", data=updated)
            st.rerun()

# --- 7. FLOATING ADD BUTTON (Global) ---
@st.dialog("Quick Log")
def log_modal():
    amt = st.number_input("Amount", min_value=0, step=1, placeholder="₹ 0", key="modal_amt")
    cat = st.selectbox("Category", categories)
    mode = st.selectbox("Mode", payment_modes)
    if st.button("Save Transaction", type="primary", use_container_width=True):
        now_tz = datetime.now(pytz.timezone('Asia/Kolkata'))
        new_row = pd.DataFrame([{"Date": now_tz.strftime("%Y-%m-%d %H:%M:%S"), "Amount": amt, "Category": cat, "Mode": mode, "Note": ""}])
        conn.update(worksheet="Expenses", data=pd.concat([df, new_row], ignore_index=True))
        st.session_state.show_modal = False
        st.rerun()

if "show_modal" not in st.session_state: st.session_state.show_modal = False
if st.session_state.show_modal: log_modal()

with stylable_container(key="fab", css_styles="button { position: fixed; bottom: 35px; right: 25px; width: 65px; height: 65px; border-radius: 50%; background-color: #2563eb; color: white; font-size: 38px; z-index: 1000; shadow: 0 4px 12px rgba(0,0,0,0.5); border: none; }"):
    if st.button("+"):
        st.session_state.show_modal = True
        st.rerun()

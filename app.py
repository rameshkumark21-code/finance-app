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
    
    /* Top Tab Navigation Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #000000;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #111111;
        border-radius: 10px 10px 0px 0px;
        padding: 10px 20px;
        color: #888888;
    }
    .stTabs [aria-selected="true"] {
        background-color: #222222 !important;
        color: #ffffff !important;
        border-bottom: 2px solid #2563eb !important;
    }

    /* Tile Styling */
    .dashboard-tile {
        background-color: #111111;
        border: 1px solid #222222;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
    }
    .tile-label { color: #888888; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }
    .tile-value { font-size: 1.8rem; font-weight: 700; margin-top: 5px; }
    
    /* Dialog / Popup */
    div[data-testid="stDialog"] {
        background-color: #0a0a0a !important;
        border: 1px solid #333333 !important;
        border-radius: 28px !important;
    }
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

# --- 3. TOP NAVIGATION TABS ---
tab_home, tab_rec, tab_cat = st.tabs(["🏠 Home", "🔄 Recurring", "🏷️ Categories"])

# --- 4. TAB: HOME ---
with tab_home:
    st.write("## Dashboard")
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        now = datetime.now(pytz.timezone('Asia/Kolkata'))
        
        # Today's Tile
        today_total = df[df['Date'].dt.date == now.date()]['Amount'].sum()
        st.markdown(f'<div class="dashboard-tile"><div class="tile-label">Spent Today</div><div class="tile-value">₹{today_total:,.0f}</div></div>', unsafe_allow_html=True)
        
        # Q Milestone Tile
        q_map = {1:1, 2:1, 3:1, 4:2, 5:2, 6:2, 7:3, 8:3, 9:3, 10:4, 11:4, 12:4}
        curr_q = q_map[now.month]
        h_spend = df[(df['Date'].dt.month.map(q_map) == curr_q) & (df['Mode'] == 'HDFC Credit Card')]['Amount'].sum()
        color = "#2563eb" if h_spend < 100000 else "#22c55e"
        st.markdown(f'<div class="dashboard-tile" style="border-left: 4px solid {color};"><div class="tile-label">HDFC Q{curr_q} Milestone</div><div class="tile-value">₹{h_spend:,.0f}</div></div>', unsafe_allow_html=True)
        
        st.write("### Latest 6 Transactions")
        st.dataframe(df.tail(6).sort_values(by="Date", ascending=False)[['Amount', 'Category', 'Mode']], use_container_width=True, hide_index=True)

# --- 5. TAB: RECURRING MAINTENANCE ---
with tab_rec:
    st.write("## Recurring Maintenance")
    with st.expander("➕ Create New Rule"):
        with st.form("new_rec"):
            c_sel = st.selectbox("Category", categories)
            a_sel = st.number_input("Amount", min_value=0.0, value=None, placeholder="₹ Enter Amount")
            d_sel = st.slider("Log Day", 1, 31, 1)
            if st.form_submit_button("Add to System"):
                if a_sel:
                    new_r = pd.DataFrame([{"Category": c_sel, "Budget": a_sel, "Is_Recurring": True, "Day_of_Month": d_sel}])
                    conn.update(worksheet="Settings", data=pd.concat([settings_df, new_r], ignore_index=True))
                    st.rerun()

    for i, row in settings_df.iterrows():
        with st.container(border=True):
            cols = st.columns([3, 1])
            cols[0].write(f"**{row['Category']}**\n₹{row['Budget']} on Day {row['Day_of_Month']}")
            if cols[1].button("🗑️", key=f"del_rec_{i}"):
                conn.update(worksheet="Settings", data=settings_df.drop(i))
                st.rerun()

# --- 6. TAB: CATEGORIES ---
with tab_cat:
    st.write("## Category List")
    with st.form("new_cat"):
        nc = st.text_input("New Category Name")
        if st.form_submit_button("Add"):
            if nc:
                conn.update(worksheet="Categories", data=pd.concat([cat_df, pd.DataFrame([{"Category": nc}])], ignore_index=True))
                st.rerun()
            
    for i, row in cat_df.iterrows():
        cols = st.columns([4, 1])
        cols[0].write(row['Category'])
        if cols[1].button("🗑️", key=f"del_cat_{i}"):
            conn.update(worksheet="Categories", data=cat_df.drop(i))
            st.rerun()

# --- 7. GLOBAL FLOATING QUICK LOG ---
@st.dialog("Quick Log")
def log_modal():
    if "form_id" not in st.session_state:
        st.session_state.form_id = 0

    if "last_log" in st.session_state:
        st.success(f"✅ Logged: ₹{st.session_state.last_log['amt']} for {st.session_state.last_log['cat']}")

    # Amount field - using 0.0 + value=None to ensure the box is empty
    amt = st.number_input("Amount", min_value=0.0, value=None, 
                          placeholder="₹ Enter Amount", 
                          key=f"amt_{st.session_state.form_id}")
    
    tz = pytz.timezone('Asia/Kolkata')
    today = datetime.now(tz).date()
    log_date = st.date_input("Transaction Date", value=today, 
                             key=f"date_{st.session_state.form_id}")
    
    cat = st.selectbox("Category", categories, key=f"cat_{st.session_state.form_id}")
    mode = st.selectbox("Mode", payment_modes, key=f"mode_{st.session_state.form_id}")
    
    col1, col2 = st.columns(2)
    
    if col1.button("Save & Add More", type="primary", use_container_width=True):
        if amt:
            now_time = datetime.now(tz).strftime("%H:%M:%S")
            final_dt = f"{log_date.strftime('%Y-%m-%d')} {now_time}"
            
            new_row = pd.DataFrame([{
                "Date": final_dt, "Amount": amt, "Category": cat, "Mode": mode, "Note": ""
            }])
            
            conn.update(worksheet="Expenses", data=pd.concat([df, new_row], ignore_index=True))
            
            st.session_state.last_log = {"amt": amt, "cat": cat}
            st.session_state.form_id += 1
            st.rerun()
        else:
            st.warning("Please enter an amount.")

    if col2.button("Finish", use_container_width=True):
        st.session_state.show_modal = False
        if "last_log" in st.session_state:
            del st.session_state.last_log
        st.rerun()

# --- 8. TRIGGER LOGIC (Bottom of script) ---
if "show_modal" not in st.session_state:
    st.session_state.show_modal = False

if st.session_state.show_modal:
    log_modal()

with stylable_container(key="fab", css_styles="button { position: fixed; bottom: 35px; right: 25px; width: 65px; height: 65px; border-radius: 50%; background-color: #2563eb; color: white; font-size: 38px; z-index: 1000; border: none; box-shadow: 0 4px 15px rgba(37,99,235,0.4); }"):
    if st.button("+", key="main_plus_btn"):
        st.session_state.show_modal = True
        st.rerun()

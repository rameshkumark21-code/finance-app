import streamlit as st
import pandas as pd
import io
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta, date
import pytz
from streamlit_extras.stylable_container import stylable_container

# ==============================================================================
# CONSTANTS & CONFIG
# ==============================================================================
RECENT_TXN_COUNT   = 10
HDFC_MILESTONE_AMT = 100_000
LARGE_AMT_WARNING  = 50_000
TZ                 = pytz.timezone('Asia/Kolkata')
DEFAULT_MODES      = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]
MAX_PIN_ATTEMPTS   = 5

T_DASH, T_HOME, T_CATS, T_SEARCH, T_REC, T_MANAGE = 0, 1, 2, 3, 4, 5
TABS       = ["Dashboard", "Home",   "Categories", "Search", "Recurring", "Manage"]
TAB_ICONS  = ["📊",        "💰",     "🏷️",         "🔍",    "🔄",        "⚙️"]
TAB_SHORT  = ["Dash",      "Home",   "Cats",       "Search", "Recur",    "Manage"]
PAGE_NAMES = ["Dashboard", "Home",   "Categories", "Search", "Recurring", "Manage"]

if "view_mode"  not in st.session_state: st.session_state.view_mode  = "mobile"
if "active_tab" not in st.session_state: st.session_state.active_tab = T_DASH
is_mobile = (st.session_state.view_mode == "mobile")

st.set_page_config(page_title="FinTrack Pro", page_icon="💰", layout="centered")

# ==============================================================================
# HIGH-CONTRAST CSS
# ==============================================================================
_CSS = (
    "<link href='https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap' rel='stylesheet'>"
    "<style>"
    "html,body,*{font-family:'DM Sans',sans-serif!important}"
    ".stApp{background:#000000;color:#ffffff}"
    
    # Text Contrast (Lighter fonts in black screen now White/Light Grey)
    ".tile-label{color:#BBBBBB!important;font-size:.64rem;text-transform:uppercase;letter-spacing:1.4px;font-weight:600}"
    ".tile-value{color:#FFFFFF!important;font-size:1.6rem;font-weight:700;margin-top:3px}"
    ".tile-sub{color:#AAAAAA!important;font-size:.76rem;margin-top:3px}"
    ".sec-head{color:#FFFFFF!important;font-size:.65rem;text-transform:uppercase;letter-spacing:1.8px;font-weight:700;margin:18px 0 10px}"
    ".dash-txn-cat{color:#EEEEEE!important;font-size:.82rem;font-weight:600}"
    ".dash-txn-meta{color:#999999!important;font-size:.68rem;margin-top:1px}"
    ".budget-nums{color:#BBBBBB!important;font-size:.72rem}"
    ".cat-name{color:#EEEEEE!important;font-size:.84rem;font-weight:500}"
    
    # Standard UI Elements
    "[data-testid='stHeader']{display:none!important}"
    "[data-testid='block-container']{padding-top:0!important}"
    ".tile{background:#111111;border:1px solid #222222;border-radius:13px;padding:13px 15px;margin-bottom:8px}"
    ".prog-track{background:#222222;border-radius:5px;height:7px;overflow:hidden}"
    ".chip{background:#131f38;color:#5a8de0;border-radius:5px;font-size:.62rem;padding:2px 6px}"
    
    # Mobile Navigation Force Horizontal
    "@media (max-width: 500px) {"
        "[data-testid='column'] {width: 16.6%!important; flex: 1 1 16.6%!important; min-width: 16.6%!important;}"
        "[data-testid='stHorizontalBlock'] {display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; align-items: center !important;}"
    "}"
    "</style>"
)
st.markdown(_CSS, unsafe_allow_html=True)

# ==============================================================================
# DATA CORE (Functions remain unchanged for reliability)
# ==============================================================================
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=30)
def load_all_data():
    try:
        e = conn.read(worksheet="Expenses")
        c = conn.read(worksheet="Categories")
        s = conn.read(worksheet="Settings")
        try:    m = conn.read(worksheet="Modes")
        except: m = pd.DataFrame({"Mode": DEFAULT_MODES})
        return e, c, s, m
    except Exception as ex:
        return (pd.DataFrame(columns=["Date","Amount","Category","Note","Mode"]), 
                pd.DataFrame(columns=["Category"]), 
                pd.DataFrame(columns=["Category","Budget","Is_Recurring","Day_of_Month","Last_Fired"]),
                pd.DataFrame({"Mode": DEFAULT_MODES}))

def bootstrap_session():
    _df, _cat, _set, _modes = load_all_data()
    if not _df.empty:
        _df["Date"]   = pd.to_datetime(_df["Date"], errors="coerce")
        _df["Amount"] = pd.to_numeric(_df["Amount"], errors="coerce").fillna(0)
    st.session_state.df, st.session_state.cat_df = _df, _cat
    st.session_state.settings_df, st.session_state.modes_df = _set, _modes
    st.session_state.bootstrapped = True

if not st.session_state.get("bootstrapped"): bootstrap_session()

# Global variables for logic
df, cat_df, settings_df = st.session_state.df, st.session_state.cat_df, st.session_state.settings_df
payment_modes = st.session_state.modes_df["Mode"].tolist() if not st.session_state.modes_df.empty else DEFAULT_MODES
categories = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty else []
now, today, curr_ym = datetime.now(TZ), datetime.now(TZ).date(), datetime.now(TZ).strftime("%Y-%m")

# ==============================================================================
# SHARED HELPERS (Save/Update/Delete)
# ==============================================================================
def save_expense(row_dict):
    nr = pd.DataFrame([row_dict])
    nr["Date"] = pd.to_datetime(nr["Date"])
    upd = pd.concat([st.session_state.df, nr], ignore_index=True)
    conn.update(worksheet="Expenses", data=upd)
    st.session_state.df = upd
    st.cache_data.clear()

def render_txn_row(idx, row, key_prefix="txn"):
    d_str = pd.to_datetime(row["Date"]).strftime("%-d %b, %H:%M")
    with st.container():
        c1, c2 = st.columns([2, 5])
        c1.markdown(f"<div style='font-weight:700;color:#FFF;padding-top:8px'>Rs.{row['Amount']:,}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='font-size:.82rem;color:#EEE;font-weight:600'>{row['Category']}</div>"
                    f"<div style='font-size:.68rem;color:#777'>{d_str} • {row['Mode']}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-top:1px solid #111;margin:5px 0'>", unsafe_allow_html=True)

# ==============================================================================
# NAVIGATION (FIXED MOBILE TABS)
# ==============================================================================
active = st.session_state.active_tab

if is_mobile:
    # Sticky Header
    st.markdown(f"<div style='position:sticky;top:0;z-index:99;background:#000;border-bottom:1px solid #222;padding:12px;text-align:center;font-weight:700;color:#FFF;'>{TAB_ICONS[active]} {PAGE_NAMES[active]}</div>", unsafe_allow_html=True)
    
    # Bottom Nav
    nav_css = (
        "{"
        "position:fixed;bottom:0;left:0;right:0;background:#050505;border-top:1px solid #222;z-index:9999;"
        "display:flex!important;flex-direction:row!important;padding-bottom:15px;height:70px;"
        "}"
    )
    with stylable_container(key="mobile_nav", css_styles=nav_css):
        cols = st.columns(6)
        for i in range(6):
            is_act = (i == active)
            btn_style = (f"button{{background:transparent!important;border:none!important;color:{'#2563eb' if is_act else '#666'}!important;}}"
                         f"button p{{font-size:10px!important;font-weight:700;margin-top:-5px;text-transform:uppercase}}")
            with cols[i]:
                with stylable_container(key=f"nav_btn_{i}", css_styles=btn_style):
                    if st.button(f"{TAB_ICONS[i]}\n{TAB_SHORT[i]}", key=f"m_nav_{i}"):
                        st.session_state.active_tab = i
                        st.rerun()
else:
    # Desktop Nav
    d_cols = st.columns(6)
    for i in range(6):
        if d_cols[i].button(f"{TAB_ICONS[i]} {TABS[i]}", use_container_width=True, type="primary" if i==active else "secondary"):
            st.session_state.active_tab = i
            st.rerun()

# ==============================================================================
# PAGE ROUTING (Simplified Dash & Home)
# ==============================================================================
st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)

if active == T_DASH:
    month_filt = df[df["Date"].dt.strftime("%Y-%m") == curr_ym]
    m_total = month_filt["Amount"].sum()
    
    st.markdown(f'<div style="background:linear-gradient(135deg,#0c1d3a,#000);border:1px solid #1a3060;border-radius:17px;padding:20px;margin-bottom:15px">'
                f'<div class="tile-label">Spent this Month</div>'
                f'<div style="font-size:2.4rem;font-weight:700;color:#FFF">Rs.{m_total:,.0f}</div></div>', unsafe_allow_html=True)
    
    st.markdown('<p class="sec-head">Recent Transactions</p>', unsafe_allow_html=True)
    recent = df.sort_values("Date", ascending=False).head(8)
    for idx, row in recent.iterrows():
        render_txn_row(idx, row, "dash")

elif active == T_HOME:
    st.markdown('<p class="sec-head">Quick Actions</p>', unsafe_allow_html=True)
    if st.button("➕ Log New Expense", use_container_width=True, type="primary"):
        st.session_state.show_modal = True
        st.rerun()
    
    st.markdown('<p class="sec-head">Monthly Breakdown</p>', unsafe_allow_html=True)
    if not df.empty:
        cat_sums = df[df["Date"].dt.strftime("%Y-%m") == curr_ym].groupby("Category")["Amount"].sum().sort_values(ascending=False)
        for cat, amt in cat_sums.items():
            st.markdown(f'<div class="tile" style="display:flex;justify-content:space-between"><span>{cat}</span><b>Rs.{amt:,.0f}</b></div>', unsafe_allow_html=True)

elif active == T_CATS:
    st.markdown('<p class="sec-head">All Time Categories</p>', unsafe_allow_html=True)
    all_cat = df.groupby("Category")["Amount"].sum().sort_values(ascending=False)
    for cat, amt in all_cat.items():
        st.markdown(f'<div class="tile"><b>{cat}</b><br><span style="color:#2563eb;font-size:1.2rem">Rs.{amt:,.0f}</span></div>', unsafe_allow_html=True)

elif active == T_SEARCH:
    q = st.text_input("Search", placeholder="Search notes or categories...")
    if q:
        res = df[df["Category"].str.contains(q, case=False) | df["Note"].str.contains(q, case=False)]
        for idx, row in res.iterrows(): render_txn_row(idx, row, "search")

elif active == T_REC:
    st.info("Recurring Rules help you auto-log monthly bills like Rent or Wifi.")
    # (Existing Logic for Settings DF display would go here)

elif active == T_MANAGE:
    st.markdown('<p class="sec-head">Settings</p>', unsafe_allow_html=True)
    if st.button("🔄 Sync with Google Sheets"):
        st.cache_data.clear()
        st.rerun()
    st.markdown('<p class="sec-head">Active Categories</p>', unsafe_allow_html=True)
    for c in categories:
        st.markdown(f'<div style="padding:10px;border-bottom:1px solid #222">{c}</div>', unsafe_allow_html=True)

# ==============================================================================
# FLOATING ACTION BUTTON
# ==============================================================================
if st.session_state.get("show_modal"):
    @st.dialog("Quick Log")
    def quick_log():
        amt = st.number_input("Amount", min_value=0.0, step=10.0)
        cat = st.selectbox("Category", categories)
        mode = st.selectbox("Mode", payment_modes)
        note = st.text_input("Note")
        if st.button("Save", type="primary", use_container_width=True):
            save_expense({"Date": datetime.now(TZ), "Amount": amt, "Category": cat, "Mode": mode, "Note": note})
            st.session_state.show_modal = False
            st.rerun()
    quick_log()

fab_css = (
    "button{position:fixed;bottom:85px;right:20px;width:60px;height:60px;border-radius:50%;"
    "background:#2563eb;color:#FFF;font-size:30px;z-index:9999;box-shadow:0 4px 15px rgba(0,0,0,0.5);border:none}"
)
with stylable_container(key="fab", css_styles=fab_css):
    if st.button("+"):
        st.session_state.show_modal = True
        st.rerun()

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
# HIGH-CONTRAST CSS & MOBILE NAV FIX
# ==============================================================================
_CSS = (
    "<link href='https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap' rel='stylesheet'>"
    "<style>"
    "html,body,*{font-family:'DM Sans',sans-serif!important}"
    ".stApp{background:#000000;color:#ffffff}"
    
    # Text Contrast (Forcing lighter colors for visibility on black)
    ".tile-label{color:#BBBBBB!important;font-size:.65rem;text-transform:uppercase;letter-spacing:1.5px;font-weight:700}"
    ".tile-value{color:#FFFFFF!important;font-size:1.65rem;font-weight:700;margin-top:2px}"
    ".tile-sub{color:#EEEEEE!important;font-size:.78rem;font-weight:500}"
    ".sec-head{color:#FFFFFF!important;font-size:.7rem;text-transform:uppercase;letter-spacing:2px;font-weight:700;margin:22px 0 12px}"
    ".dash-txn-cat{color:#FFFFFF!important;font-size:.85rem;font-weight:600}"
    ".dash-txn-meta{color:#BBBBBB!important;font-size:.7rem;margin-top:2px}"
    ".budget-nums{color:#FFFFFF!important;font-size:.75rem;font-weight:600}"
    
    # Base UI Elements
    "[data-testid='stHeader']{display:none!important}"
    "[data-testid='block-container']{padding-top:0!important}"
    ".tile{background:#111111;border:1px solid #222222;border-radius:15px;padding:16px;margin-bottom:10px}"
    ".prog-track{background:#262626;border-radius:5px;height:8px;overflow:hidden}"
    
    # FORCED HORIZONTAL MOBILE NAV
    "@media (max-width: 600px) {"
        "[data-testid='column'] {width: 16.66% !important; flex: 1 1 16.66% !important; min-width: 16.66% !important;}"
        "[data-testid='stHorizontalBlock'] {display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important;}"
    "}"
    "</style>"
)
st.markdown(_CSS, unsafe_allow_html=True)

# ==============================================================================
# DATA LOAD & SESSION
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
    except:
        return (pd.DataFrame(columns=["Date","Amount","Category","Note","Mode"]), 
                pd.DataFrame(columns=["Category"]), 
                pd.DataFrame(columns=["Category","Budget","Is_Recurring","Day_of_Month","Last_Fired"]),
                pd.DataFrame({"Mode": DEFAULT_MODES}))

if not st.session_state.get("bootstrapped"):
    e, c, s, m = load_all_data()
    if not e.empty:
        e["Date"] = pd.to_datetime(e["Date"], errors="coerce")
        e["Amount"] = pd.to_numeric(e["Amount"], errors="coerce").fillna(0)
    st.session_state.df, st.session_state.cat_df = e, c
    st.session_state.settings_df, st.session_state.modes_df = s, m
    st.session_state.bootstrapped = True

df, cat_df, settings_df = st.session_state.df, st.session_state.cat_df, st.session_state.settings_df
modes = st.session_state.modes_df["Mode"].tolist() if not st.session_state.modes_df.empty else DEFAULT_MODES
cats = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty else []
now, curr_ym = datetime.now(TZ), datetime.now(TZ).strftime("%Y-%m")

# ==============================================================================
# RENDER HELPERS
# ==============================================================================
def save_entry(row):
    row["Date"] = pd.to_datetime(row["Date"])
    upd = pd.concat([st.session_state.df, pd.DataFrame([row])], ignore_index=True)
    conn.update(worksheet="Expenses", data=upd)
    st.session_state.df = upd
    st.cache_data.clear()

def render_txn_row(row):
    dt = pd.to_datetime(row["Date"]).strftime("%-d %b, %H:%M")
    with st.container():
        c1, c2 = st.columns([2, 5])
        c1.markdown(f"<div style='font-weight:700;color:#FFF;padding:8px 0'>Rs.{row['Amount']:,}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='dash-txn-cat'>{row['Category']}</div><div class='dash-txn-meta'>{dt} • {row['Mode']}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-top:1px solid #1a1a1a;margin:2px 0'>", unsafe_allow_html=True)

# ==============================================================================
# NAVIGATION (HORIZONTAL FIX)
# ==============================================================================
active = st.session_state.active_tab

if is_mobile:
    # Header
    st.markdown(f"<div style='position:sticky;top:0;z-index:99;background:#000;border-bottom:1px solid #222;padding:12px;text-align:center;font-weight:700;color:#FFF;font-size:0.9rem'>{TAB_ICONS[active]} {PAGE_NAMES[active]}</div>", unsafe_allow_html=True)
    
    # Bottom Nav
    bnav_css = (
        "{"
        "position:fixed;bottom:0;left:0;right:0;background:#080808;border-top:1px solid #222;z-index:9999;"
        "display:flex!important;flex-direction:row!important;height:65px;padding-top:5px"
        "}"
    )
    with stylable_container(key="mobile_nav_container", css_styles=bnav_css):
        cols = st.columns(6)
        for i in range(6):
            selected = (i == active)
            btn_css = (f"button{{background:transparent!important;border:none!important;color:{'#2563eb' if selected else '#555'}!important;}}"
                       f"button p{{font-size:9px!important;font-weight:700;text-transform:uppercase;margin-top:-6px}}")
            with cols[i]:
                with stylable_container(key=f"nb_{i}", css_styles=btn_style if 'btn_style' in locals() else btn_css):
                    if st.button(f"{TAB_ICONS[i]}\n{TAB_SHORT[i]}", key=f"nav_m_{i}"):
                        st.session_state.active_tab = i
                        st.rerun()
else:
    # Desktop Row
    dcols = st.columns(6)
    for i in range(6):
        if dcols[i].button(f"{TAB_ICONS[i]} {TABS[i]}", use_container_width=True, type="primary" if i==active else "secondary"):
            st.session_state.active_tab = i
            st.rerun()

# ==============================================================================
# PAGE CONTENT
# ==============================================================================
st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)

if active == T_DASH:
    m_spend = df[df["Date"].dt.strftime("%Y-%m") == curr_ym]["Amount"].sum()
    st.markdown(f'<div class="tile" style="background:linear-gradient(145deg,#0c1d3a,#000);border:1px solid #1a3060">'
                f'<div class="tile-label">Spent This Month</div>'
                f'<div style="font-size:2.4rem;font-weight:700;color:#FFF">Rs.{m_spend:,.0f}</div></div>', unsafe_allow_html=True)
    
    st.markdown('<p class="sec-head">Recent Transactions</p>', unsafe_allow_html=True)
    for _, row in df.sort_values("Date", ascending=False).head(10).iterrows():
        render_txn_row(row)

elif active == T_HOME:
    if st.button("➕ Add New Expense", use_container_width=True, type="primary"):
        st.session_state.show_modal = True
        st.rerun()
    
    st.markdown('<p class="sec-head">Monthly Budget Summary</p>', unsafe_allow_html=True)
    if not df.empty:
        c_sums = df[df["Date"].dt.strftime("%Y-%m") == curr_ym].groupby("Category")["Amount"].sum().sort_values(ascending=False)
        for c, a in c_sums.items():
            st.markdown(f'<div class="tile" style="display:flex;justify-content:space-between"><span>{c}</span><b style="color:#FFF">Rs.{a:,.0f}</b></div>', unsafe_allow_html=True)

elif active == T_CATS:
    st.markdown('<p class="sec-head">Spending by Category</p>', unsafe_allow_html=True)
    all_time = df.groupby("Category")["Amount"].sum().sort_values(ascending=False)
    for c, a in all_time.items():
        st.markdown(f'<div class="tile"><div class="tile-label">{c}</div><div class="tile-value" style="color:#2563eb">Rs.{a:,.0f}</div></div>', unsafe_allow_html=True)

elif active == T_SEARCH:
    term = st.text_input("Search notes/categories", placeholder="Type here...")
    if term:
        res = df[df["Category"].str.contains(term, case=False) | df["Note"].str.contains(term, case=False)]
        for _, row in res.iterrows(): render_txn_row(row)

elif active == T_REC:
    st.markdown('<p class="sec-head">Recurring Expenses</p>', unsafe_allow_html=True)
    st.info("Check Settings to manage monthly auto-logs.")

elif active == T_MANAGE:
    st.markdown('<p class="sec-head">Configuration</p>', unsafe_allow_html=True)
    if st.button("🔄 Refresh Data From Sheet", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown('<p class="sec-head">Active Payment Modes</p>', unsafe_allow_html=True)
    for m in modes:
        st.markdown(f"<div style='padding:8px;border-bottom:1px solid #111;color:#EEE'>{m}</div>", unsafe_allow_html=True)

# ==============================================================================
# FLOATING ACTION BUTTON & DIALOG
# ==============================================================================
if st.session_state.get("show_modal"):
    @st.dialog("Quick Log")
    def qlog():
        a = st.number_input("Amount", min_value=0.0, step=50.0)
        c = st.selectbox("Category", cats)
        m = st.selectbox("Mode", modes)
        n = st.text_input("Note")
        if st.button("Save Transaction", use_container_width=True, type="primary"):
            save_entry({"Date": datetime.now(TZ), "Amount": a, "Category": c, "Mode": m, "Note": n})
            st.session_state.show_modal = False
            st.rerun()
    qlog()

fab_style = (
    "button{position:fixed;bottom:85px;right:25px;width:60px;height:60px;border-radius:50%;"
    "background:#2563eb;color:#FFF;font-size:32px;z-index:9999;box-shadow:0 6px 20px rgba(37,99,235,0.4);border:none}"
)
with stylable_container(key="fab_btn", css_styles=fab_style):
    if st.button("+"):
        st.session_state.show_modal = True
        st.rerun()

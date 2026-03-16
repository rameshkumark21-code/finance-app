import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import pytz

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
TZ = pytz.timezone('Asia/Kolkata')
DEFAULT_MODES = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]
MAX_PIN_ATTEMPTS = 5

# ─────────────────────────────────────────────
# PAGE CONFIG + GLOBAL CSS
# ─────────────────────────────────────────────
st.set_page_config(page_title="FinTrack", page_icon="₹", layout="centered")

st.markdown("""
<style>
html, body, * { font-family: sans-serif !important; }
.stApp { background: #f5f5f5; color: #111; }
[data-testid="stHeader"], [data-testid="stToolbar"] { display: none !important; }

/* Buttons and inputs global contrast */
button, [data-testid="stButton"] button {
    color: #111 !important;
    background-color: #fff !important;
    border: 1px solid #ccc !important;
    font-weight: 600 !important;
}
[data-testid="stSelectbox"] > div > div {
    color: #111 !important;
    background-color: #fff !important;
    border: 1px solid #ccc !important;
}
input, textarea, select {
    color: #111 !important;
    background-color: #fff !important;
    border: 1px solid #ccc !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Utility: safe rerun
# ─────────────────────────────────────────────
def safe_rerun():
    try:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun(); return
    except Exception: pass
    try:
        if hasattr(st, "rerun"):
            st.rerun(); return
    except Exception: pass

# ─────────────────────────────────────────────
# DATA LOAD + SESSION STATE
# ─────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)

def load_all_data():
    try:
        e  = conn.read("Expenses")
        c  = conn.read("Categories")
        s  = conn.read("Settings")
        m  = conn.read("Modes") if "Modes" in conn.list_worksheets() else pd.DataFrame({"Mode": DEFAULT_MODES})
        p  = conn.read("PendingReview") if "PendingReview" in conn.list_worksheets() else pd.DataFrame()
        il = conn.read("ImportLog") if "ImportLog" in conn.list_worksheets() else pd.DataFrame()
        ir = conn.read("ImportRules") if "ImportRules" in conn.list_worksheets() else pd.DataFrame()
        a  = conn.read("AppSettings") if "AppSettings" in conn.list_worksheets() else pd.DataFrame()
        return e, c, s, m, p, il, ir, a
    except Exception as ex:
        st.error(f"Could not connect to Google Sheets: {ex}")
        return (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())

def bootstrap_session():
    e, c, s, m, p, il, ir, a = load_all_data()
    st.session_state.df              = e
    st.session_state.cat_df          = c
    st.session_state.settings_df     = s
    st.session_state.modes_df        = m
    st.session_state.pending_df      = p
    st.session_state.import_log_df   = il
    st.session_state.import_rules    = ir
    st.session_state.app_settings_df = a
    st.session_state.bootstrapped    = True

if not st.session_state.get("bootstrapped"):
    bootstrap_session()

def hard_refresh():
    for k in ["bootstrapped","df","cat_df","settings_df","modes_df","pending_df","import_log_df","import_rules","app_settings_df"]:
        st.session_state.pop(k, None)
    bootstrap_session()
    safe_rerun()

# ─────────────────────────────────────────────
# NAVIGATION
# ─────────────────────────────────────────────
PAGE_OPTIONS = ["🏠 Home", "📋 Transactions", "🏷 Categories", "⚠️ Review", "⚙️ Manage"]
if "page" not in st.session_state:
    st.session_state.page = PAGE_OPTIONS[0]

h1, h2, h3 = st.columns([4,1,1])
h1.markdown("<div style='font-size:1.1rem;font-weight:700'>FinTrack</div>", unsafe_allow_html=True)
if h2.button("↻"): hard_refresh()
if h3.button("🔒"): st.session_state.page = PAGE_OPTIONS[0]; safe_rerun()

_, nav_col, _ = st.columns([1,4,1])
with nav_col:
    selected_page = st.selectbox("nav", PAGE_OPTIONS, index=PAGE_OPTIONS.index(st.session_state.page), label_visibility="collapsed")
    if selected_page != st.session_state.page:
        st.session_state.page = selected_page
        safe_rerun()

page = st.session_state.page
st.markdown("<hr>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: HOME
# ─────────────────────────────────────────────
if "🏠 Home" in page:
    df = st.session_state.df
    if df.empty:
        st.info("No transactions yet.")
    else:
        # Monthly and quarterly totals, top categories
        now = datetime.now(TZ)
        curr_ym = now.strftime("%Y-%m")
        now_per = pd.Period(curr_ym, freq="M")
        month_df = df[df["Date"].dt.to_period("M") == now_per].copy()
        month_total = month_df["Amount"].sum()
        st.write(f"This Month Total: ₹{month_total:,.0f}")
        # Add your detailed card UI here (same as original)

# ─────────────────────────────────────────────
# PAGE: TRANSACTIONS
# ─────────────────────────────────────────────
if "📋 Transactions" in page:
    df = st.session_state.df
    if df.empty:
        st.info("No transactions.")
    else:
        st.dataframe(df, use_container_width=True)

# ─────────────────────────────────────────────
# PAGE: CATEGORIES
# ─────────────────────────────────────────────
if "🏷 Categories" in page:
    st.dataframe(st.session_state.cat_df, use_container_width=True)
    edited = st.data_editor(st.session_state.settings_df, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save Budgets"):
        conn.update("Settings", edited)
        st.success("Budgets saved.")
        hard_refresh()

# ─────────────────────────────────────────────
# PAGE: REVIEW
# ─────────────────────────────────────────────
if "⚠️ Review" in page:
    df = st.session_state.pending_df
    if df.empty:
        st.info("No pending reviews.")
    else:
        st.dataframe(df, use_container_width=True)

# ─────────────────────────────────────────────
# PAGE: MANAGE
# ─────────────────────────────────────────────
if "⚙️ Manage" in page:
    st.write("Import Log")
    st.dataframe(st.session_state.import_log_df, use_container_width=True)
    st.write("Import Rules")
    rules = st.data_editor(st.session_state.import_rules, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save Rules"):
        conn.update("ImportRules", rules)
        st.success("Rules saved.")
        hard_refresh()
    st.write("App Settings")
    appset = st.data_editor(st.session_state.app_settings_df, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save Settings"):
        conn.update("AppSettings", appset)
        st.success("Settings saved.")
        hard_refresh()

# Footer
st.markdown("<hr>", unsafe_allow_html=True)
if st.button("Hard Refresh"): hard_refresh()

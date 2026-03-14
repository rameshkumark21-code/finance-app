import streamlit as st
import pandas as pd
import io
import requests
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta, date
import pytz
from streamlit_extras.stylable_container import stylable_container

# ==============================================================================
# 1. CONSTANTS  (unchanged)
# ==============================================================================
RECENT_TXN_COUNT    = 10
HDFC_MILESTONE_AMT  = 100_000
LARGE_AMT_WARNING   = 50_000
TZ                  = pytz.timezone('Asia/Kolkata')
DEFAULT_MODES       = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]
MAX_PIN_ATTEMPTS    = 5
ANOMALY_MULT        = 3.0
RECUR_MIN_MONTHS    = 3

KEY_INCOME          = "Monthly_Income"
KEY_ALERT_PCT       = "Budget_Alert_Threshold"
KEY_ALERT_ON        = "Budget_Alert_Enabled"
KEY_PULSE_ON        = "Weekly_Pulse_Enabled"

# ==============================================================================
# 2. PAGE CONFIG + CSS
# ==============================================================================
st.set_page_config(page_title="FinTrack Pro", page_icon="₹", layout="centered")

_CSS = (
    "<link href='https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700"
    "&family=JetBrains+Mono:wght@400;500&display=swap' rel='stylesheet'>"
    "<style>"
    "html,body,*{font-family:'Sora',sans-serif!important}"
    ".stApp{background-color:#0a0a0f;color:#e8e8f0}"
    "[data-testid='stHeader']{background:transparent}"
    "h1,h2,h3,h4{letter-spacing:-0.3px;color:#e8e8f0}"
    # Tabs
    ".stTabs [data-baseweb='tab-list']{gap:2px;background:transparent;border-bottom:1px solid #2a2a3a}"
    ".stTabs [data-baseweb='tab']{height:40px;background:transparent;border-radius:8px 8px 0 0;"
    "padding:0 10px;color:#444460;font-size:.78rem;font-weight:500}"
    ".stTabs [aria-selected='true']{background:transparent!important;color:#f0f0f0!important;"
    "border-bottom:2px solid #f0a500!important;font-weight:600!important}"
    # Core tiles
    ".tile{background:#13131a;border:1px solid #2a2a3a;border-radius:14px;padding:16px 18px;margin-bottom:10px}"
    ".tile-accent{height:3px;border-radius:2px 2px 0 0;margin-bottom:12px}"
    ".tile-label{color:#444460;font-size:.7rem;text-transform:uppercase;letter-spacing:1.4px;font-weight:600}"
    ".tile-value{font-size:1.85rem;font-weight:700;margin-top:4px;letter-spacing:-.8px;color:#e8e8f0;"
    "font-family:'JetBrains Mono',monospace!important}"
    ".tile-sub{font-size:.78rem;margin-top:4px}"
    ".trend-up{color:#f75676;font-weight:600}"
    ".trend-down{color:#2dce89;font-weight:600}"
    ".trend-flat{color:#444460}"
    # Progress bars
    ".prog-wrap{margin-top:10px}"
    ".prog-track{background:#22222f;border-radius:6px;height:8px;overflow:hidden}"
    ".prog-fill{height:8px;border-radius:6px;transition:width .6s ease}"
    ".prog-meta{display:flex;justify-content:space-between;margin-top:5px;font-size:.72rem;color:#444460}"
    # Section headings
    ".sec-head{font-size:.68rem;text-transform:uppercase;letter-spacing:1.6px;color:#444460;"
    "font-weight:700;margin:22px 0 10px}"
    # Category rows
    ".cat-row{display:flex;align-items:center;justify-content:space-between;"
    "padding:9px 14px;border-radius:10px;margin-bottom:5px;background:#13131a;border:1px solid #2a2a3a}"
    ".cat-name{font-size:.88rem;font-weight:500;color:#ccc;flex:1}"
    ".cat-bar-wrap{width:72px;height:3px;background:#22222f;border-radius:2px;margin:0 12px;flex-shrink:0}"
    ".cat-bar-fill{height:3px;border-radius:2px;background:#f0a500}"
    ".cat-amt{font-size:.88rem;font-weight:600;color:#e8e8f0;white-space:nowrap;"
    "font-family:'JetBrains Mono',monospace!important}"
    # Budget rows
    ".budget-row{padding:12px 14px;border-radius:10px;background:#13131a;"
    "border:1px solid #2a2a3a;margin-bottom:7px}"
    ".budget-header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px}"
    ".budget-name{font-size:.88rem;font-weight:600;color:#ccc}"
    ".budget-nums{font-size:.78rem;color:#444460;font-family:'JetBrains Mono',monospace!important}"
    # Recurring cards
    ".rec-card{background:#13131a;border:1px solid #2a2a3a;border-radius:12px;"
    "padding:13px 15px;margin-bottom:6px}"
    ".rec-fired{border-left:3px solid #2dce89}"
    ".rec-pending{border-left:3px solid #f0a500}"
    ".rec-title{font-size:.93rem;font-weight:600;color:#e0e0e0}"
    ".rec-meta{font-size:.76rem;color:#444460;margin-top:3px;font-family:'JetBrains Mono',monospace!important}"
    # Category list rows
    ".catlist-row{font-size:.9rem;font-weight:500;color:#ccc;padding:9px 0;border-bottom:1px solid #1a1a24}"
    # Empty states
    ".empty-box{text-align:center;padding:48px 20px;color:#444460}"
    ".empty-box .ico{font-size:2.2rem;margin-bottom:10px}"
    ".empty-box .msg{font-size:.88rem;line-height:1.5}"
    # Category hero
    ".cat-hero{background:#13131a;border:1px solid #2a2a3a;border-radius:14px;"
    "padding:16px 18px;margin-bottom:6px}"
    ".cat-hero-name{font-size:1rem;font-weight:700;color:#e8e8f0}"
    ".cat-hero-meta{font-size:.74rem;color:#444460;margin-top:3px}"
    ".cat-hero-amt{font-size:1.2rem;font-weight:700;color:#f0a500;white-space:nowrap;"
    "font-family:'JetBrains Mono',monospace!important}"
    # Search cards
    ".srch-card{background:#13131a;border:1px solid #2a2a3a;border-radius:12px;"
    "padding:13px 16px;margin-bottom:5px}"
    ".srch-top{display:flex;justify-content:space-between;align-items:center}"
    ".srch-cat{font-size:.9rem;font-weight:700;color:#e0e0e0}"
    ".srch-amt{font-size:.95rem;font-weight:700;color:#f0a500;white-space:nowrap;"
    "font-family:'JetBrains Mono',monospace!important}"
    ".srch-meta{font-size:.74rem;color:#444460;margin-top:3px}"
    ".srch-note{font-size:.76rem;color:#8888aa;margin-top:3px;font-style:italic}"
    # Chips / badges
    ".chip{display:inline-block;background:#1a2035;color:#7c9eff;border-radius:6px;"
    "font-size:.68rem;font-weight:600;padding:2px 7px;margin-right:4px;letter-spacing:.4px}"
    # Review cards
    ".review-card{background:#13131a;border:1px solid #2a1f05;border-left:3px solid #f0a500;"
    "border-radius:14px;padding:16px 18px;margin-bottom:12px}"
    ".review-card-amt{font-size:1.25rem;font-weight:700;color:#e8e8f0;letter-spacing:-.5px;"
    "font-family:'JetBrains Mono',monospace!important}"
    ".review-card-txn{font-size:.9rem;font-weight:500;color:#ccc;margin-top:4px}"
    ".review-card-meta{font-size:.73rem;color:#444460;margin-top:5px;line-height:1.6}"
    ".review-badge-remarks{display:inline-block;background:#0f2a1a;color:#86efac;"
    "border-radius:6px;font-size:.68rem;font-weight:600;padding:2px 8px;margin-right:4px}"
    ".review-badge-tags{display:inline-block;background:#0f1a2a;color:#93c5fd;"
    "border-radius:6px;font-size:.68rem;font-weight:600;padding:2px 8px;margin-right:4px}"
    ".review-badge-sug{display:inline-block;background:#2a1f05;color:#f0a500;"
    "border-radius:6px;font-size:.68rem;font-weight:600;padding:2px 8px}"
    # Intel badges
    ".badge-anomaly{display:inline-block;background:#1f0505;color:#f75676;"
    "border-radius:6px;font-size:.68rem;font-weight:700;padding:2px 8px;margin-right:4px}"
    ".badge-dup{display:inline-block;background:#1f1005;color:#fb923c;"
    "border-radius:6px;font-size:.68rem;font-weight:700;padding:2px 8px;margin-right:4px}"
    ".badge-recur{display:inline-block;background:#050f1a;color:#60a5fa;"
    "border-radius:6px;font-size:.68rem;font-weight:700;padding:2px 8px;margin-right:4px}"
    ".badge-intel{display:inline-block;background:#0a1a0a;color:#4ade80;"
    "border-radius:6px;font-size:.68rem;font-weight:700;padding:2px 8px;margin-right:4px}"
    # Anomaly panel on Home
    ".anomaly-panel{background:#100505;border:1px solid #200a0a;border-left:3px solid #f75676;"
    "border-radius:12px;padding:12px 16px;margin-bottom:14px}"
    ".anomaly-panel-title{font-size:.75rem;font-weight:700;color:#f75676;margin-bottom:8px;"
    "text-transform:uppercase;letter-spacing:1px}"
    ".anomaly-item{display:flex;justify-content:space-between;align-items:center;"
    "padding:5px 0;font-size:.8rem;border-bottom:1px solid #180808}"
    # ImportLog table
    ".log-row{display:flex;justify-content:space-between;align-items:center;"
    "padding:8px 14px;border-bottom:1px solid #1a1a24;font-size:.8rem}"
    ".log-ok{color:#2dce89;font-weight:600}"
    ".log-err{color:#f75676;font-weight:600}"
    ".log-num{color:#e8e8f0;font-weight:600;font-family:'JetBrains Mono',monospace!important}"
    ".log-dim{color:#444460}"
    # Sync panel
    ".sync-card{background:#13131a;border:1px solid #2a2a3a;border-radius:14px;"
    "padding:20px 20px;margin-bottom:16px}"
    ".sync-title{font-size:.95rem;font-weight:700;color:#e8e8f0;margin-bottom:6px}"
    ".sync-meta{font-size:.78rem;color:#444460}"
    # Filter panel
    ".filter-panel{background:#0f0f15;border:1px solid #2a2a3a;border-radius:14px;"
    "padding:16px 18px;margin-bottom:16px}"
    # Analytics cards
    ".analytics-card{background:#13131a;border:1px solid #2a2a3a;border-radius:14px;"
    "padding:18px 20px;margin-bottom:14px}"
    ".analytics-title{font-size:.68rem;text-transform:uppercase;letter-spacing:1.4px;"
    "color:#444460;font-weight:700;margin-bottom:14px}"
    ".heatmap-wrap{overflow-x:auto;padding:4px 0}"
    ".dow-row{display:flex;align-items:center;margin-bottom:6px;gap:8px}"
    ".dow-label{font-size:.72rem;color:#444460;width:28px;flex-shrink:0;text-align:right}"
    ".dow-bar-fill{height:16px;border-radius:4px;min-width:3px}"
    ".dow-bar-amt{font-size:.7rem;color:#444460;white-space:nowrap;"
    "font-family:'JetBrains Mono',monospace!important}"
    ".merchant-rank-row{display:flex;align-items:center;justify-content:space-between;"
    "padding:9px 0;border-bottom:1px solid #1a1a24}"
    ".merchant-rank-name{font-size:.86rem;color:#ccc;flex:1}"
    ".merchant-rank-bar{height:4px;border-radius:2px;background:#f0a500;margin:0 12px;flex-shrink:0}"
    ".merchant-rank-amt{font-size:.88rem;font-weight:600;color:#f0a500;white-space:nowrap;"
    "font-family:'JetBrains Mono',monospace!important}"
    # Split form
    ".split-row{background:#0a0a05;border:1px solid #2a2a10;border-left:2px solid #f0a500;"
    "border-radius:10px;padding:10px 14px;margin-bottom:8px}"
    # Dialog
    "div[data-testid='stDialog']{background:#0f0f15!important;border:1px solid #2a2a3a!important;"
    "border-radius:22px!important}"
    "[data-testid='stTextInput'] input,[data-testid='stNumberInput'] input"
    "{background:#1a1a24!important;border:1px solid #2a2a3a!important;"
    "border-radius:8px!important;color:#e8e8f0!important}"
    "[data-testid='stSelectbox']>div>div{background:#1a1a24!important;"
    "border:1px solid #2a2a3a!important;border-radius:8px!important}"
    "[data-testid='stExpander']{background:#13131a!important;border:1px solid #2a2a3a!important;"
    "border-radius:10px!important;margin-bottom:5px}"
    "[data-testid='stExpander'] summary{font-size:.87rem!important;font-weight:500!important;"
    "color:#ccc!important}"
    "[data-testid='stForm']{border:1px solid #2a2a3a!important;border-radius:12px!important;"
    "padding:16px!important;background:#0f0f15!important}"
    ".stAlert{border-radius:10px!important}"
    "[data-testid='stMultiSelect'] span{background:#1a2035!important;color:#7c9eff!important;"
    "border-radius:5px!important;font-size:.74rem!important}"
    "</style>"
)
st.markdown(_CSS, unsafe_allow_html=True)


# ==============================================================================
# 3. DATA LOAD + SESSION STATE  (unchanged)
# ==============================================================================
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=30)
def load_all_data():
    try:
        e = conn.read(worksheet="Expenses")
        c = conn.read(worksheet="Categories")
        s = conn.read(worksheet="Settings")
        try:
            m = conn.read(worksheet="Modes")
        except Exception:
            m = pd.DataFrame({"Mode": DEFAULT_MODES})
        try:
            p = conn.read(worksheet="PendingReview")
        except Exception:
            p = pd.DataFrame(columns=[
                "Date","Amount","Category","Note","Mode",
                "UPI_Ref","Source_Account","Import_Source","Review_Status",
                "Suggested_Category","Remarks_Raw","Tags_Raw","Transaction_Details"
            ])
        try:
            il = conn.read(worksheet="ImportLog")
        except Exception:
            il = pd.DataFrame(columns=["Run_Time","Emails_Found","Imported","Skipped","Pending","Status","Notes"])
        try:
            ir = conn.read(worksheet="ImportRules")
        except Exception:
            ir = pd.DataFrame(columns=["Keyword","Match_In","Category"])
        try:
            a = conn.read(worksheet="AppSettings")
        except Exception:
            a = pd.DataFrame(columns=["Key","Value"])
        return e, c, s, m, p, il, ir, a
    except Exception as ex:
        st.error(f"Could not connect to Google Sheets: {ex}")
        return (
            pd.DataFrame(columns=["Date","Amount","Category","Note","Mode","UPI_Ref","Source_Account","Import_Source","Review_Status"]),
            pd.DataFrame(columns=["Category"]),
            pd.DataFrame(columns=["Category","Budget","Is_Recurring","Day_of_Month","Last_Fired"]),
            pd.DataFrame({"Mode": DEFAULT_MODES}),
            pd.DataFrame(columns=["Date","Amount","Category","Note","Mode","UPI_Ref","Source_Account","Import_Source","Review_Status","Suggested_Category","Remarks_Raw","Tags_Raw","Transaction_Details"]),
            pd.DataFrame(columns=["Run_Time","Emails_Found","Imported","Skipped","Pending","Status","Notes"]),
            pd.DataFrame(columns=["Keyword","Match_In","Category"]),
            pd.DataFrame(columns=["Key","Value"]),
        )

@st.cache_data(ttl=30)
def load_pin():
    try:
        sec = conn.read(worksheet="Security", usecols=[0], nrows=1)
        raw = str(sec.iloc[0, 0]).strip()
        return raw if raw.isdigit() and len(raw) == 4 else "1234"
    except Exception:
        return "1234"

def bootstrap_session():
    _df, _cat, _set, _modes, _pend, _log, _rules, _app = load_all_data()
    if not _df.empty:
        _df["Date"]   = pd.to_datetime(_df["Date"], errors="coerce")
        _df["Amount"] = pd.to_numeric(_df["Amount"], errors="coerce").fillna(0)
    if not _pend.empty:
        _pend["Date"]   = pd.to_datetime(_pend["Date"], errors="coerce")
        _pend["Amount"] = pd.to_numeric(_pend["Amount"], errors="coerce").fillna(0)
    if "Last_Fired" not in _set.columns:
        _set["Last_Fired"] = ""
    st.session_state.df              = _df
    st.session_state.cat_df          = _cat
    st.session_state.settings_df     = _set
    st.session_state.modes_df        = _modes
    st.session_state.pending_df      = _pend
    st.session_state.import_log_df   = _log
    st.session_state.import_rules    = _rules
    st.session_state.app_settings_df = _app
    st.session_state.active_pin      = load_pin()
    st.session_state.bootstrapped    = True

if not st.session_state.get("bootstrapped"):
    bootstrap_session()

def hard_refresh():
    st.cache_data.clear()
    for k in ["bootstrapped","df","cat_df","settings_df","modes_df",
              "pending_df","import_log_df","import_rules","app_settings_df","active_pin"]:
        st.session_state.pop(k, None)
    st.rerun()

df             = st.session_state.df
cat_df         = st.session_state.cat_df
settings_df    = st.session_state.settings_df
modes_df       = st.session_state.modes_df
pending_df     = st.session_state.pending_df
import_log_df  = st.session_state.import_log_df
import_rules   = st.session_state.import_rules

categories    = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty   else []
payment_modes = modes_df["Mode"].dropna().tolist()           if not modes_df.empty else DEFAULT_MODES
now           = datetime.now(TZ)
today         = now.date()
curr_ym       = now.strftime("%Y-%m")


# ==============================================================================
# 4. SAVE HELPERS  (unchanged)
# ==============================================================================
def save_expense(row_dict):
    with st.spinner("Saving..."):
        new_row = pd.DataFrame([row_dict])
        new_row["Date"]   = pd.to_datetime(new_row["Date"], errors="coerce")
        new_row["Amount"] = pd.to_numeric(new_row["Amount"], errors="coerce").fillna(0)
        updated = pd.concat([st.session_state.df, new_row], ignore_index=True)
        conn.update(worksheet="Expenses", data=updated)
        st.session_state.df = updated
        st.cache_data.clear()

def update_expense(idx, fields):
    with st.spinner("Updating..."):
        for k, v in fields.items():
            st.session_state.df.at[idx, k] = v
        conn.update(worksheet="Expenses", data=st.session_state.df)
        st.cache_data.clear()

def delete_expense(idx):
    with st.spinner("Deleting..."):
        updated = st.session_state.df.drop(idx).reset_index(drop=True)
        conn.update(worksheet="Expenses", data=updated)
        st.session_state.df = updated
        st.cache_data.clear()

def save_settings(new_df):
    with st.spinner("Saving..."):
        conn.update(worksheet="Settings", data=new_df)
        st.session_state.settings_df = new_df
        st.cache_data.clear()

def save_categories(new_df):
    with st.spinner("Saving..."):
        conn.update(worksheet="Categories", data=new_df)
        st.session_state.cat_df = new_df
        st.cache_data.clear()

def save_modes(new_df):
    with st.spinner("Saving..."):
        conn.update(worksheet="Modes", data=new_df)
        st.session_state.modes_df = new_df
        st.cache_data.clear()

def save_pin(new_pin: str):
    with st.spinner("Saving PIN..."):
        pin_df = pd.DataFrame({"PIN": [new_pin]})
        conn.update(worksheet="Security", data=pin_df)
        st.session_state.active_pin = new_pin
        st.cache_data.clear()

def save_import_rules(new_df):
    with st.spinner("Saving rules..."):
        conn.update(worksheet="ImportRules", data=new_df)
        st.session_state.import_rules = new_df
        st.cache_data.clear()

def get_app_setting(key, default="0"):
    df_a = st.session_state.get("app_settings_df", pd.DataFrame())
    if df_a.empty or "Key" not in df_a.columns:
        return default
    mask = df_a["Key"].astype(str).str.strip() == key
    if not mask.any():
        return default
    return str(df_a.loc[mask, "Value"].iloc[0]).strip()

def set_app_setting(key, value):
    df_a = st.session_state.get("app_settings_df", pd.DataFrame(columns=["Key","Value"])).copy()
    mask = df_a["Key"].astype(str).str.strip() == key if not df_a.empty else pd.Series([], dtype=bool)
    if not df_a.empty and mask.any():
        df_a.loc[mask, "Value"] = str(value)
    else:
        df_a = pd.concat([df_a, pd.DataFrame([{"Key": key, "Value": str(value)}])], ignore_index=True)
    conn.update(worksheet="AppSettings", data=df_a)
    st.session_state.app_settings_df = df_a
    st.cache_data.clear()

def split_expense_row(idx, amt1, cat1, amt2, cat2):
    """Delete one expense row and replace with two split rows (single write)."""
    with st.spinner("Splitting..."):
        orig = st.session_state.df.loc[idx]
        note_base = str(orig.get("Note", "") or "").strip()
        row1 = {
            "Date": orig.get("Date",""), "Amount": amt1, "Category": cat1,
            "Note": f"{note_base} (split 1/2)".strip(),
            "Mode": orig.get("Mode",""), "UPI_Ref": str(orig.get("UPI_Ref","") or ""),
            "Source_Account": orig.get("Source_Account",""),
            "Import_Source": orig.get("Import_Source",""), "Review_Status": orig.get("Review_Status",""),
        }
        row2 = {
            "Date": orig.get("Date",""), "Amount": amt2, "Category": cat2,
            "Note": f"{note_base} (split 2/2)".strip(),
            "Mode": orig.get("Mode",""), "UPI_Ref": "",
            "Source_Account": orig.get("Source_Account",""),
            "Import_Source": orig.get("Import_Source",""), "Review_Status": orig.get("Review_Status",""),
        }
        base  = st.session_state.df.drop(idx).reset_index(drop=True)
        r1_df = pd.DataFrame([row1])
        r2_df = pd.DataFrame([row2])
        r1_df["Date"] = pd.to_datetime(r1_df["Date"], errors="coerce")
        r2_df["Date"] = pd.to_datetime(r2_df["Date"], errors="coerce")
        updated = pd.concat([base, r1_df, r2_df], ignore_index=True)
        conn.update(worksheet="Expenses", data=updated)
        st.session_state.df = updated
        st.cache_data.clear()


# ==============================================================================
# 5. ANALYTICS UTILITY FUNCTIONS  (logic unchanged; heatmap/DOW colors updated)
# ==============================================================================
def extract_merchant(row):
    txn  = str(row.get("Transaction_Details", "") or "").strip()
    note = str(row.get("Note", "") or "").strip()
    src  = txn or note.split("·")[0].strip()
    for prefix in ["Paid to ","paid to ","Money sent to ","money sent to "]:
        if src.lower().startswith(prefix.lower()):
            src = src[len(prefix):]
            break
    return src.strip() or "Unknown Merchant"

def build_heatmap_html(df_h):
    now_date = datetime.now(TZ).date()
    if df_h.empty:
        return "<div style='color:#444460;font-size:.82rem;padding:20px 0'>No data yet — sync transactions to see your heatmap</div>"
    dfc = df_h[df_h["Date"].notna()].copy()
    if dfc.empty:
        return "<div style='color:#444460;font-size:.82rem'>No dated transactions</div>"
    dfc["_day"] = dfc["Date"].dt.date
    daily = dfc.groupby("_day")["Amount"].sum()
    mx = float(daily.max()) if not daily.empty else 1.0
    if mx == 0: mx = 1.0
    start = now_date - timedelta(weeks=52)
    start = start - timedelta(days=start.weekday())
    week_starts, month_marks, last_m, wi = [], [], None, 0
    cur = start
    while cur <= now_date:
        m = cur.strftime("%b")
        if m != last_m:
            month_marks.append((wi, m))
            last_m = m
        week_starts.append(cur)
        cur += timedelta(weeks=1)
        wi += 1
    total_weeks = len(week_starts)
    mh = '<div style="display:flex;margin-bottom:4px;margin-left:18px">'
    for i, (wk, mn) in enumerate(month_marks):
        nxt = month_marks[i+1][0] if i+1 < len(month_marks) else total_weeks
        px  = (nxt - wk) * 12
        mh += f'<div style="min-width:{px}px;font-size:.6rem;color:#444460;overflow:hidden;white-space:nowrap">{mn}</div>'
    mh += '</div>'
    dlabels = ["M","","W","","F","","S"]
    lc = '<div style="display:flex;flex-direction:column;gap:2px;margin-right:4px;flex-shrink:0">'
    for d in dlabels:
        lc += f'<div style="width:10px;height:10px;font-size:.55rem;color:#333;line-height:10px;text-align:center">{d}</div>'
    lc += '</div>'
    gc = ""
    for ws in week_starts:
        col = '<div style="display:flex;flex-direction:column;gap:2px">'
        for d in range(7):
            day = ws + timedelta(days=d)
            if day > now_date:
                col += '<div style="width:10px;height:10px"></div>'
                continue
            amt = float(daily.get(day, 0))
            if amt == 0:
                color, tip = "#1a1a24", f"Rs.0 · {day.strftime('%d %b')}"
            else:
                inten = amt / mx
                if   inten < 0.2: color = "#2a1f05"
                elif inten < 0.4: color = "#3a2c05"
                elif inten < 0.6: color = "#5a4010"
                elif inten < 0.8: color = "#8a6200"
                else:             color = "#f0a500"
                tip = f"Rs.{amt:,.0f} · {day.strftime('%d %b')}"
            col += f'<div title="{tip}" style="width:10px;height:10px;border-radius:2px;background:{color}"></div>'
        col += '</div>'
        gc += col
    legend = (
        '<div style="display:flex;align-items:center;gap:6px;margin-top:8px;font-size:.62rem;color:#444460">'
        '<span>Less</span>'
        + "".join([f'<div style="width:10px;height:10px;border-radius:2px;background:{c}"></div>'
                   for c in ["#1a1a24","#2a1f05","#5a4010","#8a6200","#f0a500"]])
        + '<span>More</span></div>'
    )
    return f'<div class="heatmap-wrap">{mh}<div style="display:flex;gap:2px">{lc}{gc}</div>{legend}</div>'

def build_dow_html(df_d):
    if df_d.empty:
        return "<div style='color:#444460;font-size:.82rem'>No data</div>"
    dfc = df_d[df_d["Date"].notna()].copy()
    dfc["_dow"] = dfc["Date"].dt.dayofweek
    dow_avg = dfc.groupby("_dow")["Amount"].mean()
    days  = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    mx    = float(dow_avg.max()) if not dow_avg.empty else 1.0
    if mx == 0: mx = 1.0
    html = ""
    for i, day in enumerate(days):
        avg    = float(dow_avg.get(i, 0))
        pct    = avg / mx * 100
        color  = "#5e72e4" if i >= 5 else "#f0a500"
        html  += (
            f'<div class="dow-row">'
            f'<span class="dow-label">{day}</span>'
            f'<div style="flex:1;background:#1a1a24;border-radius:4px;height:16px;overflow:hidden">'
            f'<div class="dow-bar-fill" style="width:{pct:.1f}%;background:{color}"></div>'
            f'</div>'
            f'<span class="dow-bar-amt">Rs.{avg:,.0f}</span>'
            f'</div>'
        )
    return html

def detect_anomalies(pending_df_a, expenses_df_a):
    if pending_df_a.empty or expenses_df_a.empty:
        return {}
    hist = expenses_df_a[expenses_df_a["Date"].notna()].copy()
    hist["_m"] = hist.apply(extract_merchant, axis=1)
    stats = hist.groupby("_m")["Amount"].agg(["mean","count"])
    stats = stats[stats["count"] >= 3]
    stats_map = stats["mean"].to_dict()
    anomalies = {}
    _rs = pending_df_a["Review_Status"].astype(str) if "Review_Status" in pending_df_a.columns else pd.Series("", index=pending_df_a.index)
    active = pending_df_a[_rs == "pending"].copy()
    if active.empty:
        return {}
    active["_m"] = active.apply(extract_merchant, axis=1)
    for idx, row in active.iterrows():
        m   = row["_m"]
        amt = float(row.get("Amount", 0))
        if m in stats_map and stats_map[m] > 0 and amt > stats_map[m] * ANOMALY_MULT:
            anomalies[idx] = {"merchant": m, "amount": amt, "avg": stats_map[m]}
    return anomalies

def detect_duplicates(pending_df_d):
    if pending_df_d.empty:
        return set()
    _rs = pending_df_d["Review_Status"].astype(str) if "Review_Status" in pending_df_d.columns else pd.Series("", index=pending_df_d.index)
    active = pending_df_d[_rs == "pending"].copy()
    if active.empty:
        return set()
    active["_m"] = active.apply(extract_merchant, axis=1)
    active["_dt"] = pd.to_datetime(active["Date"], errors="coerce")
    dup_idx = set()
    rows = list(active.iterrows())
    for i, (idx1, r1) in enumerate(rows):
        for idx2, r2 in rows[i+1:]:
            if r1["_m"] == r2["_m"] and r1["Amount"] == r2["Amount"]:
                d1, d2 = r1["_dt"], r2["_dt"]
                if pd.notna(d1) and pd.notna(d2) and abs((d1-d2).total_seconds()) <= 86400:
                    dup_idx.add(idx1)
                    dup_idx.add(idx2)
    return dup_idx

def detect_recurring_merchants(pending_df_r, expenses_df_r):
    if pending_df_r.empty or expenses_df_r.empty:
        return set()
    _rs = pending_df_r["Review_Status"].astype(str) if "Review_Status" in pending_df_r.columns else pd.Series("", index=pending_df_r.index)
    active = pending_df_r[_rs == "pending"].copy()
    if active.empty:
        return set()
    active["_m"] = active.apply(extract_merchant, axis=1)
    pending_merchants = set(active["_m"].unique())
    hist = expenses_df_r[expenses_df_r["Date"].notna()].copy()
    hist["_m"]  = hist.apply(extract_merchant, axis=1)
    hist["_mo"] = hist["Date"].dt.to_period("M").astype(str)
    mnth = hist[hist["_m"].isin(pending_merchants)].groupby("_m")["_mo"].nunique()
    return set(mnth[mnth >= RECUR_MIN_MONTHS].index)

def get_merchant_trend(merchant, expenses_df_t):
    if expenses_df_t.empty:
        return None
    hist = expenses_df_t[expenses_df_t["Date"].notna()].copy()
    hist["_m"] = hist.apply(extract_merchant, axis=1)
    hist["_mo"] = hist["Date"].dt.to_period("M")
    last3 = sorted(hist["_mo"].unique())[-3:]
    sub = hist[(hist["_m"] == merchant) & (hist["_mo"].isin(last3))]
    if sub.empty:
        return None
    return sub.groupby("_mo")["Amount"].sum().mean()


# ==============================================================================
# 6. REVIEW HELPERS  (unchanged)
# ==============================================================================
def approve_pending_row(idx, chosen_category, create_new_cat=False):
    with st.spinner("Approving..."):
        row = st.session_state.pending_df.loc[idx]
        if create_new_cat and chosen_category not in [
            c for c in st.session_state.cat_df["Category"].dropna().tolist()
        ]:
            save_categories(pd.concat([
                st.session_state.cat_df,
                pd.DataFrame([{"Category": chosen_category}])
            ], ignore_index=True))
        expense_row = {
            "Date": row.get("Date",""), "Amount": row.get("Amount",0),
            "Category": chosen_category, "Note": row.get("Note",""),
            "Mode": row.get("Mode","UPI"), "UPI_Ref": row.get("UPI_Ref",""),
            "Source_Account": row.get("Source_Account",""),
            "Import_Source": row.get("Import_Source","paytm_auto"),
            "Review_Status": "approved",
        }
        exp_new = pd.DataFrame([expense_row])
        exp_new["Date"]   = pd.to_datetime(exp_new["Date"], errors="coerce")
        exp_new["Amount"] = pd.to_numeric(exp_new["Amount"], errors="coerce").fillna(0)
        updated_exp = pd.concat([st.session_state.df, exp_new], ignore_index=True)
        conn.update(worksheet="Expenses", data=updated_exp)
        st.session_state.df = updated_exp
        updated_pend = st.session_state.pending_df.drop(idx).reset_index(drop=True)
        conn.update(worksheet="PendingReview", data=updated_pend)
        st.session_state.pending_df = updated_pend
        st.cache_data.clear()

def skip_pending_row(idx):
    with st.spinner("Skipping..."):
        st.session_state.pending_df.at[idx, "Review_Status"] = "skipped"
        conn.update(worksheet="PendingReview", data=st.session_state.pending_df)
        st.cache_data.clear()

def approve_all_with_suggestions():
    pend = st.session_state.pending_df
    if pend.empty:
        return 0
    _rs  = pend["Review_Status"].astype(str) if "Review_Status" in pend.columns else pd.Series("", index=pend.index)
    _sug = pend["Suggested_Category"].astype(str) if "Suggested_Category" in pend.columns else pd.Series("", index=pend.index)
    to_approve = pend[
        (_rs == "pending") &
        (_sug.str.strip().ne("")) &
        (_sug.str.strip().ne("nan"))
    ]
    if to_approve.empty:
        return 0
    count = 0
    for idx, row in to_approve.iterrows():
        sug = str(row.get("Suggested_Category","")).strip()
        if sug and sug != "nan":
            approve_pending_row(idx, sug, create_new_cat=True)
            count += 1
    return count

def auto_save_import_rule(merchant, category):
    rules = st.session_state.import_rules
    words = [w for w in merchant.split() if len(w) > 3]
    keyword = words[0] if words else merchant[:10]
    keyword = keyword.strip()
    if len(keyword) < 3:
        return
    existing = rules["Keyword"].astype(str).str.lower().str.strip().tolist() if not rules.empty else []
    if keyword.lower() in existing:
        return
    new_rule = pd.DataFrame([{"Keyword": keyword, "Match_In": "Any", "Category": category}])
    updated  = pd.concat([rules, new_rule], ignore_index=True) if not rules.empty else new_rule
    save_import_rules(updated)

def approve_merchant_group(indices, chosen_category, create_new_cat=False, merchant_name=""):
    with st.spinner(f"Approving {len(indices)} transactions..."):
        existing_cats = st.session_state.cat_df["Category"].dropna().tolist()
        if create_new_cat and chosen_category not in existing_cats:
            save_categories(pd.concat([
                st.session_state.cat_df,
                pd.DataFrame([{"Category": chosen_category}])
            ], ignore_index=True))
        pend = st.session_state.pending_df
        new_expense_rows = []
        for idx in indices:
            if idx not in pend.index:
                continue
            row = pend.loc[idx]
            new_expense_rows.append({
                "Date": row.get("Date",""), "Amount": row.get("Amount",0),
                "Category": chosen_category, "Note": row.get("Note",""),
                "Mode": row.get("Mode","UPI"), "UPI_Ref": row.get("UPI_Ref",""),
                "Source_Account": row.get("Source_Account",""),
                "Import_Source": row.get("Import_Source","paytm_auto"),
                "Review_Status": "approved",
            })
        if new_expense_rows:
            exp_new = pd.DataFrame(new_expense_rows)
            exp_new["Date"]   = pd.to_datetime(exp_new["Date"], errors="coerce")
            exp_new["Amount"] = pd.to_numeric(exp_new["Amount"], errors="coerce").fillna(0)
            updated_exp = pd.concat([st.session_state.df, exp_new], ignore_index=True)
            conn.update(worksheet="Expenses", data=updated_exp)
            st.session_state.df = updated_exp
        updated_pend = pend.drop(index=indices).reset_index(drop=True)
        conn.update(worksheet="PendingReview", data=updated_pend)
        st.session_state.pending_df = updated_pend
        st.cache_data.clear()
        if merchant_name and chosen_category:
            auto_save_import_rule(merchant_name, chosen_category)

def skip_merchant_group(indices):
    with st.spinner("Skipping..."):
        for idx in indices:
            if idx in st.session_state.pending_df.index:
                st.session_state.pending_df.at[idx, "Review_Status"] = "skipped"
        conn.update(worksheet="PendingReview", data=st.session_state.pending_df)
        st.cache_data.clear()

def approve_split_group(split_map, create_cats=None):
    with st.spinner(f"Approving {len(split_map)} transactions..."):
        create_cats = create_cats or []
        existing_cats = st.session_state.cat_df["Category"].dropna().tolist()
        for cat in create_cats:
            if cat and cat not in existing_cats:
                save_categories(pd.concat([
                    st.session_state.cat_df,
                    pd.DataFrame([{"Category": cat}])
                ], ignore_index=True))
                existing_cats.append(cat)
        pend = st.session_state.pending_df
        new_rows = []
        for idx, cat in split_map.items():
            if idx not in pend.index or not cat or cat == "-- New category --":
                continue
            row = pend.loc[idx]
            new_rows.append({
                "Date": row.get("Date",""), "Amount": row.get("Amount",0),
                "Category": cat, "Note": row.get("Note",""),
                "Mode": row.get("Mode","UPI"), "UPI_Ref": row.get("UPI_Ref",""),
                "Source_Account": row.get("Source_Account",""),
                "Import_Source": row.get("Import_Source","paytm_auto"),
                "Review_Status": "approved",
            })
        if new_rows:
            exp_new = pd.DataFrame(new_rows)
            exp_new["Date"]   = pd.to_datetime(exp_new["Date"], errors="coerce")
            exp_new["Amount"] = pd.to_numeric(exp_new["Amount"], errors="coerce").fillna(0)
            updated_exp = pd.concat([st.session_state.df, exp_new], ignore_index=True)
            conn.update(worksheet="Expenses", data=updated_exp)
            st.session_state.df = updated_exp
        indices = list(split_map.keys())
        updated_pend = pend.drop(index=indices).reset_index(drop=True)
        conn.update(worksheet="PendingReview", data=updated_pend)
        st.session_state.pending_df = updated_pend
        st.cache_data.clear()


# ==============================================================================
# 7. SHARED TRANSACTION ROW RENDERER  (same keys; visual lift only)
# ==============================================================================
def render_txn_row(idx, row, key_prefix="txn", show_edit=True):
    date_disp = pd.to_datetime(row["Date"]).strftime("%-d %b %Y, %H:%M") if pd.notna(row["Date"]) else "-"
    note_val  = str(row.get("Note", "") or "").strip()
    edit_key  = f"{key_prefix}_edit_{idx}"
    del_key   = f"{key_prefix}_del_{idx}"
    split_key = f"{key_prefix}_split_{idx}"
    for k, v in [(edit_key, False), (del_key, False), (split_key, False)]:
        if k not in st.session_state:
            st.session_state[k] = v

    c_amt, c_info, c_btn = st.columns([2, 5, 1])
    c_amt.markdown(
        f"<div style='font-size:.97rem;font-weight:700;color:#e8e8f0;padding:10px 0;"
        f"font-family:\"JetBrains Mono\",monospace'>"
        f"Rs.{float(row['Amount']):,.0f}</div>",
        unsafe_allow_html=True
    )
    mode_chip = f"<span class='chip'>{row['Mode']}</span>" if str(row.get("Mode","")).strip() else ""
    note_html = (f"<div style='font-size:.72rem;color:#8888aa;margin-top:2px;font-style:italic'>"
                 f"{note_val}</div>") if note_val else ""
    c_info.markdown(
        f"<div style='padding:10px 0;line-height:1.35'>"
        f"<span style='font-size:.88rem;font-weight:600;color:#ccc'>{row['Category']}</span>"
        f"<br><span style='font-size:.72rem;color:#444460'>{date_disp}</span> {mode_chip}"
        f"{note_html}</div>",
        unsafe_allow_html=True
    )
    if show_edit and c_btn.button("✏️", key=f"{key_prefix}_tgl_{idx}", help="Edit / Split / Delete"):
        st.session_state[edit_key]  = not st.session_state[edit_key]
        st.session_state[split_key] = False
        st.rerun()
    st.markdown(
        "<hr style='border:none;border-top:1px solid #1a1a24;margin:0'>",
        unsafe_allow_html=True
    )

    if show_edit and st.session_state[edit_key]:
        with st.container(border=True):
            ea, eb = st.columns(2)
            new_amt  = ea.number_input("Amount", value=float(row["Amount"]), min_value=0.0,
                                       key=f"{key_prefix}_eamt_{idx}")
            new_cat  = eb.selectbox(
                "Category", categories,
                index=categories.index(row["Category"]) if row["Category"] in categories else 0,
                key=f"{key_prefix}_ecat_{idx}"
            )
            ec, ed = st.columns(2)
            new_mode = ec.selectbox(
                "Mode", payment_modes,
                index=payment_modes.index(row["Mode"]) if row["Mode"] in payment_modes else 0,
                key=f"{key_prefix}_emode_{idx}"
            )
            new_note = ed.text_input("Note", value=note_val, key=f"{key_prefix}_enote_{idx}")
            btn1, btn2, btn3 = st.columns(3)
            if btn1.button("Save", key=f"{key_prefix}_save_{idx}",
                           use_container_width=True, type="primary"):
                update_expense(idx, {"Amount": new_amt, "Category": new_cat,
                                     "Mode": new_mode, "Note": new_note.strip()})
                st.session_state[edit_key] = False
                st.toast("Updated ✓")
                st.rerun()
            if btn2.button("✂ Split", key=f"{key_prefix}_splbtn_{idx}", use_container_width=True):
                st.session_state[split_key] = True
                st.session_state[edit_key]  = False
                st.rerun()
            if not st.session_state[del_key]:
                if btn3.button("Delete", key=f"{key_prefix}_delb_{idx}", use_container_width=True):
                    st.session_state[del_key] = True
                    st.rerun()
            else:
                btn3.warning("Sure?")
                y_, n_ = btn3.columns(2)
                if y_.button("Yes", key=f"{key_prefix}_ydel_{idx}"):
                    delete_expense(idx)
                    st.session_state[edit_key] = False
                    st.session_state[del_key]  = False
                    st.rerun()
                if n_.button("No", key=f"{key_prefix}_ndel_{idx}"):
                    st.session_state[del_key] = False
                    st.rerun()

    if show_edit and st.session_state[split_key]:
        total_amt = float(row["Amount"])
        st.markdown(
            f'<div class="split-row">'
            f'<span style="font-size:.8rem;font-weight:700;color:#f0a500">✂ Split Rs.{total_amt:,.0f} into two</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        with st.container(border=True):
            s1a, s1b = st.columns([1, 2])
            spl1_amt = s1a.number_input("Part 1 Rs.", min_value=1.0, max_value=total_amt-1,
                                         value=round(total_amt/2, 2), key=f"spl1a_{idx}")
            spl1_cat = s1b.selectbox("Category 1", categories, key=f"spl1c_{idx}",
                                      label_visibility="collapsed")
            spl2_amt = total_amt - spl1_amt
            s2a, s2b = st.columns([1, 2])
            s2a.markdown(
                f'<div style="padding:8px 0;font-size:.92rem;font-weight:600;color:#e8e8f0;'
                f'font-family:\'JetBrains Mono\',monospace">'
                f'Rs.{spl2_amt:,.0f}</div>',
                unsafe_allow_html=True
            )
            spl2_cat = s2b.selectbox("Category 2", categories, key=f"spl2c_{idx}",
                                      label_visibility="collapsed")
            sb1, sb2 = st.columns(2)
            if sb1.button("✂ Split & Save", key=f"do_split_{key_prefix}_{idx}",
                          type="primary", use_container_width=True):
                split_expense_row(idx, spl1_amt, spl1_cat, spl2_amt, spl2_cat)
                st.session_state[split_key] = False
                st.toast(f"Split → {spl1_cat} + {spl2_cat} ✓")
                st.rerun()
            if sb2.button("Cancel", key=f"cancel_split_{key_prefix}_{idx}",
                          use_container_width=True):
                st.session_state[split_key] = False
                st.rerun()


# ==============================================================================
# 8. PIN GATE  (same logic; amber colour scheme)
# ==============================================================================
for _k, _v in [("pin_unlocked", False), ("pin_input", ""), ("pin_attempts", 0), ("pin_error", "")]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

if not st.session_state.pin_unlocked:
    locked_out = st.session_state.pin_attempts >= MAX_PIN_ATTEMPTS
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(
            "<div style='text-align:center;margin-bottom:6px'>"
            "<span style='font-size:1.5rem;font-weight:700;color:#e8e8f0;"
            "font-family:\"Sora\",sans-serif;letter-spacing:-.5px'>Fin"
            "<span style='color:#f0a500'>Track</span> Pro</span></div>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<p style='color:#444460;font-size:.8rem;margin-bottom:24px;text-align:center'>"
            "Enter your 4-digit PIN to continue</p>",
            unsafe_allow_html=True
        )
        entered  = len(st.session_state.pin_input)
        is_error = bool(st.session_state.pin_error)
        dots_html = "<div style='display:flex;gap:14px;margin-bottom:24px;justify-content:center'>"
        for i in range(4):
            if is_error:
                style = "width:13px;height:13px;border-radius:50%;background:#f75676;border:1.5px solid #f75676"
            elif i < entered:
                style = "width:13px;height:13px;border-radius:50%;background:#f0a500;border:1.5px solid #f0a500"
            else:
                style = "width:13px;height:13px;border-radius:50%;background:transparent;border:1.5px solid #2a2a3a"
            dots_html += f"<div style='{style}'></div>"
        dots_html += "</div>"
        st.markdown(dots_html, unsafe_allow_html=True)
        if locked_out:
            st.error("Too many incorrect attempts. Restart the app to try again.")
            st.stop()
        if st.session_state.pin_error:
            remaining = MAX_PIN_ATTEMPTS - st.session_state.pin_attempts
            st.markdown(
                f"<p style='color:#f75676;font-size:.76rem;text-align:center;margin-bottom:12px'>"
                f"Incorrect PIN. {remaining} attempt{'s' if remaining != 1 else ''} left.</p>",
                unsafe_allow_html=True
            )
        keys_layout = [["1","2","3"],["4","5","6"],["7","8","9"],["","0","del"]]
        for row_keys in keys_layout:
            k1, k2, k3 = st.columns(3)
            for col_w, digit in zip([k1, k2, k3], row_keys):
                if digit == "":
                    col_w.markdown("")
                elif digit == "del":
                    if col_w.button("⌫", use_container_width=True, key="pin_del"):
                        st.session_state.pin_input = st.session_state.pin_input[:-1]
                        st.session_state.pin_error = ""
                        st.rerun()
                else:
                    if col_w.button(digit, use_container_width=True, key=f"pin_{digit}"):
                        if len(st.session_state.pin_input) < 4:
                            st.session_state.pin_input += digit
                            st.session_state.pin_error  = ""
                            if len(st.session_state.pin_input) == 4:
                                if st.session_state.pin_input == st.session_state.active_pin:
                                    st.session_state.pin_unlocked = True
                                    st.session_state.pin_input    = ""
                                    st.session_state.pin_error    = ""
                                    st.session_state.pin_attempts = 0
                                else:
                                    st.session_state.pin_attempts += 1
                                    st.session_state.pin_error    = "wrong"
                                    st.session_state.pin_input    = ""
                            st.rerun()
    st.stop()


# ==============================================================================
# 9. RECURRING AUTO-LOG  (unchanged)
# ==============================================================================
if not st.session_state.get("auto_log_checked") and not settings_df.empty:
    fired_any   = False
    updated_sdf = st.session_state.settings_df.copy()
    for i, row in st.session_state.settings_df.iterrows():
        try:
            is_rec = str(row.get("Is_Recurring", "")).strip().lower() in ("true", "1", "yes")
            if not is_rec:
                continue
            last_fired = str(row.get("Last_Fired", "")).strip()
            day_of_mon = int(row.get("Day_of_Month", 32))
            amt        = float(row.get("Budget", 0) or 0)
            if last_fired == curr_ym or today.day < day_of_mon:
                continue
            fire_dt = f"{today.strftime('%Y-%m-%d')} {now.strftime('%H:%M:%S')}"
            save_expense({"Date": fire_dt, "Amount": amt, "Category": row["Category"],
                          "Mode": "Auto", "Note": "Auto-logged (recurring)"})
            updated_sdf.at[i, "Last_Fired"] = curr_ym
            fired_any = True
            st.toast(f"Auto-logged: {row['Category']}  Rs.{amt:,.0f}")
        except Exception:
            pass
    if fired_any:
        save_settings(updated_sdf)
    st.session_state.auto_log_checked = True


# ==============================================================================
# 10. TABS
# ==============================================================================
pending_count = 0
if not st.session_state.pending_df.empty and "Review_Status" in st.session_state.pending_df.columns:
    pending_count = int((st.session_state.pending_df["Review_Status"].astype(str) == "pending").sum())

review_label = f"Review ⚠️ {pending_count}" if pending_count > 0 else "Review"

tab_home, tab_cat_view, tab_search, tab_rec, tab_analytics, tab_review, tab_manage = st.tabs([
    "Home", "Categories", "Search", "Recurring", "Analytics", review_label, "Manage"
])


# ==============================================================================
# TAB 1 — HOME
# ==============================================================================
with tab_home:
    hc1, hc2, hc3 = st.columns([5, 1, 1])
    hc1.markdown(
        "<span style='font-size:1.4rem;font-weight:700;color:#e8e8f0;letter-spacing:-.5px'>"
        "Fin<span style='color:#f0a500'>Track</span></span>",
        unsafe_allow_html=True
    )
    if hc2.button("Lock", use_container_width=True):
        st.session_state.pin_unlocked = False
        st.session_state.pin_input    = ""
        st.session_state.pin_error    = ""
        st.rerun()
    if hc3.button("Refresh", use_container_width=True):
        hard_refresh()

    if df.empty:
        st.markdown(
            "<div class='empty-box'><div class='ico'>💸</div>"
            "<div class='msg'>No expenses yet. Tap + to get started.</div></div>",
            unsafe_allow_html=True
        )
    else:
        all_months = sorted(
            df["Date"].dropna().dt.to_period("M").unique().astype(str).tolist(), reverse=True
        )
        sel_month  = st.selectbox("Period", all_months, index=0, label_visibility="collapsed")
        sel_period = pd.Period(sel_month, freq="M")
        prev_period= sel_period - 1
        filt = df[df["Date"].dt.to_period("M") == sel_period].copy()
        prev = df[df["Date"].dt.to_period("M") == prev_period].copy()

        month_total = filt["Amount"].sum()
        prev_total  = prev["Amount"].sum()

        if prev_total > 0:
            pct_diff   = (month_total - prev_total) / prev_total * 100
            t_cls      = "trend-up" if pct_diff > 0 else "trend-down"
            t_sign     = "+" if pct_diff > 0 else ""
            trend_html = f'<span class="{t_cls}">{t_sign}{pct_diff:.0f}% vs {str(prev_period)}</span>'
        else:
            trend_html = '<span class="trend-flat">First month on record</span>'

        # ── Tile row: Today spend + Monthly total ─────────────────────────────
        tc1, tc2 = st.columns(2)
        if sel_month == curr_ym:
            today_total = df[df["Date"].dt.date == today]["Amount"].sum()
            tc1.markdown(
                f'<div class="tile"><div class="tile-accent" style="background:#f0a500"></div>'
                f'<div class="tile-label">Spent Today</div>'
                f'<div class="tile-value">Rs.{today_total:,.0f}</div></div>',
                unsafe_allow_html=True
            )
        else:
            tc1.markdown(
                f'<div class="tile"><div class="tile-accent" style="background:#2a2a3a"></div>'
                f'<div class="tile-label">Period</div>'
                f'<div class="tile-value" style="font-size:1.1rem;padding-top:6px">{sel_month}</div></div>',
                unsafe_allow_html=True
            )
        tc2.markdown(
            f'<div class="tile"><div class="tile-accent" style="background:#5e72e4"></div>'
            f'<div class="tile-label">Total Spend</div>'
            f'<div class="tile-value">Rs.{month_total:,.0f}</div>'
            f'<div class="tile-sub">{trend_html}</div></div>',
            unsafe_allow_html=True
        )

        # ── Savings Rate tile (only when income is set + current month) ───────
        monthly_income = float(get_app_setting(KEY_INCOME, "0") or "0")
        if monthly_income > 0 and sel_month == curr_ym:
            savings      = monthly_income - month_total
            savings_pct  = savings / monthly_income * 100
            sav_color    = "#2dce89" if savings >= 0 else "#f75676"
            sav_sign     = "+" if savings >= 0 else ""
            sav_label    = "Saving" if savings >= 0 else "Over budget by"
            sav_pct_fill = min(abs(savings_pct), 100)
            sav_bar_col  = "#2dce89" if savings >= 0 else "#f75676"
            st.markdown(
                f'<div class="tile" style="border-left:3px solid {sav_color}">'
                f'<div class="tile-label">Savings Rate</div>'
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:4px">'
                f'<span style="font-size:1.6rem;font-weight:700;color:{sav_color};font-family:JetBrains Mono,monospace">{sav_sign}{savings_pct:.1f}%</span>'
                f'<span style="font-size:.78rem;color:#444460">{sav_label} Rs.{abs(savings):,.0f}</span>'
                f'</div>'
                f'<div class="prog-wrap"><div class="prog-track">'
                f'<div class="prog-fill" style="width:{sav_pct_fill:.1f}%;background:{sav_bar_col}"></div>'
                f'</div></div>'
                f'</div>',
                unsafe_allow_html=True
            )

        # ── HDFC Quarterly Milestone ──────────────────────────────────────────
        q_map  = {1:1,2:1,3:1,4:2,5:2,6:2,7:3,8:3,9:3,10:4,11:4,12:4}
        curr_q = q_map[now.month]
        h_spend = df[
            (df["Date"].dt.month.map(q_map) == curr_q) &
            (df["Date"].dt.year == now.year) &
            (df["Mode"] == "HDFC Credit Card")
        ]["Amount"].sum()
        h_pct     = min(h_spend / HDFC_MILESTONE_AMT * 100, 100)
        h_color   = "#5e72e4" if h_pct < 75 else ("#f0a500" if h_pct < 100 else "#2dce89")
        remaining = max(HDFC_MILESTONE_AMT - h_spend, 0)
        st.markdown(
            f'<div class="tile" style="border-left:3px solid {h_color}">'
            f'<div class="tile-label">HDFC Q{curr_q} Milestone</div>'
            f'<div class="tile-value">Rs.{h_spend:,.0f}'
            f'<span style="font-size:.82rem;color:#444460;font-weight:400"> / Rs.{HDFC_MILESTONE_AMT:,.0f}</span></div>'
            f'<div class="prog-wrap"><div class="prog-track">'
            f'<div class="prog-fill" style="width:{h_pct:.1f}%;background:{h_color}"></div>'
            f'</div><div class="prog-meta"><span>{h_pct:.1f}% reached</span>'
            f'<span>Rs.{remaining:,.0f} to go</span></div></div></div>',
            unsafe_allow_html=True
        )

        # ── Anomaly alerts ────────────────────────────────────────────────────
        if not st.session_state.pending_df.empty:
            anomalies = detect_anomalies(st.session_state.pending_df, df)
            if anomalies:
                items_html = ""
                for info in list(anomalies.values())[:5]:
                    items_html += (
                        f'<div class="anomaly-item">'
                        f'<span style="color:#ccc">{info["merchant"][:30]}</span>'
                        f'<span style="color:#f75676;font-weight:600">Rs.{info["amount"]:,.0f}'
                        f' <span style="color:#444460;font-weight:400;font-size:.72rem">'
                        f'(avg Rs.{info["avg"]:,.0f})</span></span>'
                        f'</div>'
                    )
                st.markdown(
                    f'<div class="anomaly-panel">'
                    f'<div class="anomaly-panel-title">🚨 {len(anomalies)} Unusual Amount{"s" if len(anomalies)>1 else ""} in Pending Review</div>'
                    f'{items_html}'
                    f'</div>',
                    unsafe_allow_html=True
                )

        # ── Budget tracker ────────────────────────────────────────────────────
        budgets = st.session_state.settings_df[
            st.session_state.settings_df["Budget"].notna() &
            (st.session_state.settings_df["Budget"].astype(str).str.strip() != "")
        ].copy() if not st.session_state.settings_df.empty else pd.DataFrame()
        if not budgets.empty:
            st.markdown('<p class="sec-head">Budget Tracker</p>', unsafe_allow_html=True)
            for _, brow in budgets.iterrows():
                bcat   = brow["Category"]
                blimit = float(brow.get("Budget", 0) or 0)
                if blimit <= 0:
                    continue
                bspent = filt[filt["Category"] == bcat]["Amount"].sum()
                bpct   = min(bspent / blimit * 100, 100)
                bcolor = "#2dce89" if bspent/blimit < 0.75 else ("#f0a500" if bspent <= blimit else "#f75676")
                over   = " ⚠ Over!" if bspent > blimit else ""
                st.markdown(
                    f'<div class="budget-row"><div class="budget-header">'
                    f'<span class="budget-name">{bcat}{over}</span>'
                    f'<span class="budget-nums">Rs.{bspent:,.0f} / Rs.{blimit:,.0f}</span></div>'
                    f'<div class="prog-track"><div class="prog-fill" style="width:{bpct:.1f}%;background:{bcolor}"></div></div></div>',
                    unsafe_allow_html=True
                )

        # ── By Category (with 3-month trend arrows) ───────────────────────────
        st.markdown('<p class="sec-head">By Category</p>', unsafe_allow_html=True)
        if not filt.empty:
            cat_sum = filt.groupby("Category")["Amount"].sum().sort_values(ascending=False).reset_index()
            max_amt = cat_sum["Amount"].max() or 1
            three_mo_ago = sel_period - 3
            prev3 = df[df["Date"].dt.to_period("M") > three_mo_ago]
            prev3 = prev3[df["Date"].dt.to_period("M") < sel_period]
            cat_3mo_avg = prev3.groupby("Category")["Amount"].mean() if not prev3.empty else pd.Series(dtype=float)
            for _, crow in cat_sum.iterrows():
                bar_pct = crow["Amount"] / max_amt * 100
                cat_nm  = crow["Category"]
                avg_3   = float(cat_3mo_avg.get(cat_nm, 0))
                if avg_3 > 0:
                    delta_pct = (crow["Amount"] - avg_3) / avg_3 * 100
                    if delta_pct > 10:
                        trend_arrow = f'<span style="color:#f75676;font-size:.7rem">↑{delta_pct:.0f}%</span>'
                    elif delta_pct < -10:
                        trend_arrow = f'<span style="color:#2dce89;font-size:.7rem">↓{abs(delta_pct):.0f}%</span>'
                    else:
                        trend_arrow = ""
                else:
                    trend_arrow = ""
                st.markdown(
                    f'<div class="cat-row">'
                    f'<span class="cat-name">{cat_nm} {trend_arrow}</span>'
                    f'<div class="cat-bar-wrap"><div class="cat-bar-fill" style="width:{bar_pct:.0f}%"></div></div>'
                    f'<span class="cat-amt">Rs.{crow["Amount"]:,.0f}</span></div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<div class="empty-box"><div class="ico">📊</div>'
                        '<div class="msg">No data for this period.</div></div>', unsafe_allow_html=True)

        # ── Recent transactions ───────────────────────────────────────────────
        st.markdown('<p class="sec-head">Recent Transactions</p>', unsafe_allow_html=True)
        search_q = st.text_input("search_home", placeholder="Filter by category, mode or note...",
                                 label_visibility="collapsed")
        txn_df = filt.copy()
        if search_q.strip():
            q    = search_q.strip()
            mask = (
                txn_df["Category"].astype(str).str.contains(q, case=False, na=False) |
                txn_df["Note"].astype(str).str.contains(q, case=False, na=False)     |
                txn_df["Mode"].astype(str).str.contains(q, case=False, na=False)
            )
            txn_df = txn_df[mask]
        txn_df = txn_df.sort_values("Date", ascending=False).head(RECENT_TXN_COUNT)
        if txn_df.empty:
            st.markdown('<div class="empty-box"><div class="ico">🔍</div>'
                        '<div class="msg">No transactions match.</div></div>', unsafe_allow_html=True)
        else:
            for idx, row in txn_df.iterrows():
                render_txn_row(idx, row, key_prefix="home")


# ==============================================================================
# TAB 2 — CATEGORIES
# ==============================================================================
with tab_cat_view:
    st.markdown(
        "<span style='font-size:1.2rem;font-weight:700;color:#e8e8f0'>Categories</span>",
        unsafe_allow_html=True
    )
    if df.empty:
        st.markdown('<div class="empty-box"><div class="ico">🏷️</div>'
                    '<div class="msg">No data yet.</div></div>', unsafe_allow_html=True)
    else:
        total_all  = df["Amount"].sum()
        total_txns = len(df)
        oldest     = df["Date"].min()
        newest     = df["Date"].max()
        span_days  = max((newest - oldest).days, 1)
        s1, s2, s3 = st.columns(3)
        s1.markdown(
            f'<div class="tile"><div class="tile-accent" style="background:#f0a500"></div>'
            f'<div class="tile-label">All Time Spend</div>'
            f'<div class="tile-value" style="font-size:1.4rem">Rs.{total_all:,.0f}</div></div>',
            unsafe_allow_html=True
        )
        s2.markdown(
            f'<div class="tile"><div class="tile-accent" style="background:#5e72e4"></div>'
            f'<div class="tile-label">Transactions</div>'
            f'<div class="tile-value" style="font-size:1.4rem">{total_txns:,}</div></div>',
            unsafe_allow_html=True
        )
        s3.markdown(
            f'<div class="tile"><div class="tile-accent" style="background:#2dce89"></div>'
            f'<div class="tile-label">Daily Average</div>'
            f'<div class="tile-value" style="font-size:1.4rem">Rs.{total_all/span_days:,.0f}</div></div>',
            unsafe_allow_html=True
        )
        st.markdown('<p class="sec-head">Category Breakdown — All Time</p>', unsafe_allow_html=True)
        sort_opt = st.radio(
            "Sort by", ["Total Spend","No. of Transactions","Avg Transaction","A to Z"],
            horizontal=True, label_visibility="collapsed"
        )
        cat_grp = df.groupby("Category").agg(
            Total=("Amount","sum"), Count=("Amount","count"),
            Avg=("Amount","mean"), Last=("Date","max"),
        ).reset_index()
        if sort_opt == "Total Spend":           cat_grp = cat_grp.sort_values("Total", ascending=False)
        elif sort_opt == "No. of Transactions": cat_grp = cat_grp.sort_values("Count", ascending=False)
        elif sort_opt == "Avg Transaction":     cat_grp = cat_grp.sort_values("Avg",   ascending=False)
        else:                                   cat_grp = cat_grp.sort_values("Category")
        max_total = cat_grp["Total"].max() or 1
        for _, crow in cat_grp.iterrows():
            cat_name  = crow["Category"]
            cat_total = crow["Total"]
            cat_count = int(crow["Count"])
            cat_avg   = crow["Avg"]
            cat_last  = pd.to_datetime(crow["Last"]).strftime("%-d %b %Y") if pd.notna(crow["Last"]) else "-"
            bar_pct   = cat_total / max_total * 100
            share_pct = cat_total / total_all * 100 if total_all > 0 else 0
            st.markdown(
                f'<div class="cat-hero"><div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div><div class="cat-hero-name">{cat_name}</div>'
                f'<div class="cat-hero-meta">{cat_count} transactions &nbsp;·&nbsp; Avg Rs.{cat_avg:,.0f}'
                f' &nbsp;·&nbsp; Last {cat_last} &nbsp;·&nbsp; {share_pct:.1f}% of total</div></div>'
                f'<div class="cat-hero-amt">Rs.{cat_total:,.0f}</div></div>'
                f'<div style="margin-top:10px;background:#22222f;border-radius:4px;height:4px">'
                f'<div style="width:{bar_pct:.1f}%;background:#f0a500;height:4px;border-radius:4px"></div></div></div>',
                unsafe_allow_html=True
            )
            view_key = f"view_cat_{cat_name}"
            if view_key not in st.session_state:
                st.session_state[view_key] = False
            btn_label = "Hide entries" if st.session_state[view_key] else f"Show all {cat_count} entries"
            if st.button(btn_label, key=f"btn_cat_{cat_name}"):
                st.session_state[view_key] = not st.session_state[view_key]
                st.rerun()
            if st.session_state[view_key]:
                cat_entries = df[df["Category"] == cat_name].sort_values("Date", ascending=False)
                with st.container(border=True):
                    cat_months = sorted(
                        cat_entries["Date"].dropna().dt.to_period("M").unique().astype(str).tolist(), reverse=True
                    )
                    month_filt = st.selectbox(
                        "Filter month", ["All months"] + cat_months,
                        key=f"mf_{cat_name}", label_visibility="collapsed"
                    )
                    if month_filt != "All months":
                        cat_entries = cat_entries[
                            cat_entries["Date"].dt.to_period("M").astype(str) == month_filt
                        ]
                    sub_total = cat_entries["Amount"].sum()
                    st.markdown(
                        f"<p style='font-size:.75rem;color:#444460;margin-bottom:8px'>"
                        f"Showing {len(cat_entries)} entries &nbsp;·&nbsp; Total Rs.{sub_total:,.0f}</p>",
                        unsafe_allow_html=True
                    )
                    for idx, erow in cat_entries.iterrows():
                        render_txn_row(idx, erow, key_prefix=f"cat_{cat_name}")
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


# ==============================================================================
# TAB 3 — SEARCH
# ==============================================================================
with tab_search:
    st.markdown(
        "<span style='font-size:1.2rem;font-weight:700;color:#e8e8f0'>Search & Filter</span>",
        unsafe_allow_html=True
    )
    if df.empty:
        st.markdown('<div class="empty-box"><div class="ico">🔍</div>'
                    '<div class="msg">No data to search yet.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="sec-head">Filters</p>', unsafe_allow_html=True)
        keyword = st.text_input("Keyword", placeholder="Search across category, note, mode...",
                                label_visibility="collapsed")
        dr1, dr2 = st.columns(2)
        min_date  = df["Date"].min().date() if not df.empty else date(2020, 1, 1)
        max_date  = max(df["Date"].max().date() if not df.empty else today, today)
        date_from = dr1.date_input("From", value=min_date, min_value=min_date, max_value=max_date, key="sf_from")
        date_to   = dr2.date_input("To",   value=today,   min_value=min_date, max_value=max_date, key="sf_to")
        fm1, fm2  = st.columns(2)
        sel_cats  = fm1.multiselect("Categories", options=sorted(df["Category"].dropna().unique().tolist()), placeholder="All categories")
        sel_modes = fm2.multiselect("Modes",      options=sorted(df["Mode"].dropna().unique().tolist()),     placeholder="All modes")
        fa1, fa2  = st.columns(2)
        amt_min   = fa1.number_input("Min amount (Rs.)", min_value=0.0, value=0.0, step=100.0, key="sf_amin")
        amt_max   = fa2.number_input("Max amount (Rs.)", min_value=0.0,
                                      value=float(df["Amount"].max() or 100000), step=100.0, key="sf_amax")
        fc1, fc2, fc3, fc4 = st.columns(4)
        only_noted    = fc1.checkbox("Has note",    key="sf_noted")
        only_auto     = fc2.checkbox("Auto-logged", key="sf_auto")
        only_credited = fc3.checkbox("Credit card", key="sf_cc")
        only_today    = fc4.checkbox("Today only",  key="sf_today")
        fs1, fs2 = st.columns([3, 1])
        sort_by  = fs1.selectbox(
            "Sort by", ["Date (newest)","Date (oldest)","Amount (highest)","Amount (lowest)","Category A-Z"],
            label_visibility="collapsed"
        )
        if fs2.button("Clear filters", use_container_width=True):
            for k in ["sf_from","sf_to","sf_amin","sf_amax","sf_noted","sf_auto","sf_cc","sf_today"]:
                st.session_state.pop(k, None)
            st.rerun()

        result = df.copy()
        result = result[result["Date"].dt.date >= date_from]
        result = result[result["Date"].dt.date <= date_to]
        if keyword.strip():
            kw   = keyword.strip()
            mask = (
                result["Category"].astype(str).str.contains(kw, case=False, na=False) |
                result["Note"].astype(str).str.contains(kw, case=False, na=False)     |
                result["Mode"].astype(str).str.contains(kw, case=False, na=False)
            )
            result = result[mask]
        if sel_cats:  result = result[result["Category"].isin(sel_cats)]
        if sel_modes: result = result[result["Mode"].isin(sel_modes)]
        result = result[(result["Amount"] >= amt_min) & (result["Amount"] <= amt_max)]
        if only_noted:    result = result[result["Note"].astype(str).str.strip().ne("").ne("nan")]
        if only_auto:     result = result[result["Note"].astype(str).str.contains("Auto-logged", case=False, na=False)]
        if only_credited: result = result[result["Mode"].astype(str).str.contains("Credit Card", case=False, na=False)]
        if only_today:    result = result[result["Date"].dt.date == today]

        if sort_by == "Date (newest)":        result = result.sort_values("Date",     ascending=False)
        elif sort_by == "Date (oldest)":      result = result.sort_values("Date",     ascending=True)
        elif sort_by == "Amount (highest)":   result = result.sort_values("Amount",   ascending=False)
        elif sort_by == "Amount (lowest)":    result = result.sort_values("Amount",   ascending=True)
        else:                                 result = result.sort_values("Category", ascending=True)

        r_count = len(result)
        r_total = result["Amount"].sum()
        r_avg   = result["Amount"].mean() if r_count > 0 else 0
        ra1, ra2, ra3 = st.columns(3)
        ra1.markdown(
            f'<div class="tile"><div class="tile-accent" style="background:#f0a500"></div>'
            f'<div class="tile-label">Results</div>'
            f'<div class="tile-value" style="font-size:1.4rem">{r_count:,}</div></div>',
            unsafe_allow_html=True
        )
        ra2.markdown(
            f'<div class="tile"><div class="tile-accent" style="background:#5e72e4"></div>'
            f'<div class="tile-label">Total</div>'
            f'<div class="tile-value" style="font-size:1.4rem">Rs.{r_total:,.0f}</div></div>',
            unsafe_allow_html=True
        )
        ra3.markdown(
            f'<div class="tile"><div class="tile-accent" style="background:#2dce89"></div>'
            f'<div class="tile-label">Avg per txn</div>'
            f'<div class="tile-value" style="font-size:1.4rem">Rs.{r_avg:,.0f}</div></div>',
            unsafe_allow_html=True
        )

        if r_count > 0 and len(sel_cats) != 1:
            r_cat_split = result.groupby("Category")["Amount"].sum().sort_values(ascending=False)
            split_str   = "  |  ".join([f"{c}: Rs.{v:,.0f}" for c, v in r_cat_split.items()])
            st.markdown(
                f"<p style='font-size:.72rem;color:#444460;margin:-6px 0 12px'>{split_str}</p>",
                unsafe_allow_html=True
            )

        if r_count > 0:
            csv_buf = io.StringIO()
            result[["Date","Category","Amount","Mode","Note"]].to_csv(csv_buf, index=False)
            st.download_button(
                label=f"Export {r_count} results as CSV",
                data=csv_buf.getvalue(),
                file_name=f"fintrack_export_{today}.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.markdown('<p class="sec-head">Results</p>', unsafe_allow_html=True)
        if result.empty:
            st.markdown('<div class="empty-box"><div class="ico">🔍</div>'
                        '<div class="msg">No transactions match these filters.</div></div>',
                        unsafe_allow_html=True)
        else:
            for idx, row in result.iterrows():
                render_txn_row(idx, row, key_prefix="srch")


# ==============================================================================
# TAB 4 — RECURRING
# ==============================================================================
with tab_rec:
    st.markdown(
        "<span style='font-size:1.2rem;font-weight:700;color:#e8e8f0'>Recurring Rules</span>",
        unsafe_allow_html=True
    )
    with st.expander("Create New Rule"):
        with st.form("new_rec"):
            rc1, rc2 = st.columns(2)
            c_sel = rc1.selectbox("Category", categories)
            a_sel = rc2.number_input("Amount (Rs.)", min_value=0.0, value=None, placeholder="0.00")
            d_sel = st.slider("Auto-log on day of month", 1, 31, 1)
            if st.form_submit_button("Add Rule", type="primary"):
                if a_sel:
                    new_r   = pd.DataFrame([{"Category": c_sel, "Budget": a_sel,
                                              "Is_Recurring": True, "Day_of_Month": d_sel, "Last_Fired": ""}])
                    updated = pd.concat([st.session_state.settings_df, new_r], ignore_index=True)
                    save_settings(updated)
                    st.rerun()
                else:
                    st.warning("Please enter an amount.")

    if st.session_state.settings_df.empty:
        st.markdown('<div class="empty-box"><div class="ico">🔄</div>'
                    '<div class="msg">No recurring rules yet.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="sec-head">Active Rules</p>', unsafe_allow_html=True)
        for i, row in st.session_state.settings_df.iterrows():
            try:
                dom        = int(row.get("Day_of_Month", 0))
                last_fired = str(row.get("Last_Fired", "")).strip()
                fired_this = last_fired == curr_ym
                status_cls = "rec-fired" if fired_this else "rec-pending"
                status_txt = f"Fired {curr_ym}" if fired_this else f"Due on day {dom}"
                st.markdown(
                    f'<div class="rec-card {status_cls}">'
                    f'<div class="rec-title">{row["Category"]}</div>'
                    f'<div class="rec-meta">Rs.{float(row["Budget"]):,.0f}  ·  {status_txt}</div></div>',
                    unsafe_allow_html=True
                )
                ck = f"crec_{i}"
                if ck not in st.session_state:
                    st.session_state[ck] = False
                rcol1, rcol2, rcol3 = st.columns([5, 1, 1])
                if not st.session_state[ck]:
                    if rcol3.button("Delete", key=f"del_rec_{i}", use_container_width=True):
                        st.session_state[ck] = True
                        st.rerun()
                else:
                    rcol2.warning("Sure?")
                    if rcol2.button("Yes", key=f"yrec_{i}"):
                        updated = st.session_state.settings_df.drop(i).reset_index(drop=True)
                        save_settings(updated)
                        st.session_state[ck] = False
                        st.rerun()
                    if rcol3.button("No", key=f"nrec_{i}"):
                        st.session_state[ck] = False
                        st.rerun()
            except Exception:
                pass


# ==============================================================================
# TAB 5 — ANALYTICS
# ==============================================================================
with tab_analytics:
    st.markdown(
        "<span style='font-size:1.2rem;font-weight:700;color:#e8e8f0'>Analytics</span>",
        unsafe_allow_html=True
    )
    if df.empty:
        st.markdown('<div class="empty-box"><div class="ico">📈</div>'
                    '<div class="msg">No data yet. Sync transactions to unlock analytics.</div></div>',
                    unsafe_allow_html=True)
    else:
        all_months_a = sorted(
            df["Date"].dropna().dt.to_period("M").unique().astype(str).tolist(), reverse=True
        )
        an_opts = ["Last 3 months","Last 6 months","Last 12 months"] + all_months_a
        an_sel  = st.selectbox("Analyse period", an_opts, index=0, label_visibility="collapsed")

        now_per = pd.Period(curr_ym, freq="M")
        if an_sel == "Last 3 months":
            an_df = df[df["Date"].dt.to_period("M") > (now_per - 3)]
        elif an_sel == "Last 6 months":
            an_df = df[df["Date"].dt.to_period("M") > (now_per - 6)]
        elif an_sel == "Last 12 months":
            an_df = df[df["Date"].dt.to_period("M") > (now_per - 12)]
        else:
            an_period = pd.Period(an_sel, freq="M")
            an_df     = df[df["Date"].dt.to_period("M") == an_period]

        # ── SPEND HEATMAP ─────────────────────────────────────────────────────
        st.markdown(
            '<div class="analytics-card">'
            '<div class="analytics-title">Spend Heatmap — Last 52 Weeks</div>',
            unsafe_allow_html=True
        )
        st.markdown(build_heatmap_html(df), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── BUDGET vs ACTUAL ──────────────────────────────────────────────────
        budgets_a = settings_df[
            settings_df["Budget"].notna() &
            (settings_df["Budget"].astype(str).str.strip() != "")
        ].copy() if not settings_df.empty else pd.DataFrame()

        if not budgets_a.empty and an_sel in all_months_a:
            st.markdown('<div class="analytics-card">', unsafe_allow_html=True)
            st.markdown('<div class="analytics-title">Budget vs Actual</div>', unsafe_allow_html=True)
            for _, brow in budgets_a.iterrows():
                bcat   = brow["Category"]
                blimit = float(brow.get("Budget", 0) or 0)
                if blimit <= 0:
                    continue
                bspent = an_df[an_df["Category"] == bcat]["Amount"].sum()
                bpct   = bspent / blimit * 100
                bcolor = "#2dce89" if bpct < 75 else ("#f0a500" if bpct < 100 else "#f75676")
                bar_w  = min(bpct, 100)
                over   = (f'<span style="color:#f75676;font-size:.7rem"> +Rs.{bspent-blimit:,.0f} over</span>'
                          if bspent > blimit else "")
                st.markdown(
                    f'<div style="margin-bottom:12px">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:5px">'
                    f'<span style="font-size:.86rem;font-weight:600;color:#ccc">{bcat}{over}</span>'
                    f'<span style="font-size:.8rem;color:#444460;font-family:\'JetBrains Mono\',monospace">'
                    f'Rs.{bspent:,.0f} / Rs.{blimit:,.0f} &nbsp; {bpct:.0f}%</span>'
                    f'</div>'
                    f'<div class="prog-track"><div class="prog-fill" style="width:{bar_w:.1f}%;background:{bcolor}"></div></div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

        # ── CATEGORY TREND vs 3-MONTH AVG ─────────────────────────────────────
        if an_sel in all_months_a:
            an_period   = pd.Period(an_sel, freq="M")
            prev3_start = an_period - 3
            prev3_df    = df[(df["Date"].dt.to_period("M") > prev3_start) &
                             (df["Date"].dt.to_period("M") < an_period)]
            if not prev3_df.empty and not an_df.empty:
                this_cat  = an_df.groupby("Category")["Amount"].sum()
                prev3_avg = prev3_df.groupby("Category")["Amount"].mean()
                trend_rows = []
                for cat_t in this_cat.index:
                    this_v = float(this_cat.get(cat_t, 0))
                    avg_v  = float(prev3_avg.get(cat_t, 0))
                    if avg_v > 0:
                        delta = (this_v - avg_v) / avg_v * 100
                        trend_rows.append({"Category": cat_t, "This": this_v, "Avg": avg_v, "Delta": delta})
                if trend_rows:
                    trend_df = pd.DataFrame(trend_rows).sort_values("Delta", ascending=False)
                    st.markdown('<div class="analytics-card">', unsafe_allow_html=True)
                    st.markdown(
                        '<div class="analytics-title">Category Trend vs 3-Month Average</div>',
                        unsafe_allow_html=True
                    )
                    for _, tr in trend_df.iterrows():
                        d     = tr["Delta"]
                        col   = "#f75676" if d > 10 else ("#2dce89" if d < -10 else "#444460")
                        sign  = "+" if d >= 0 else ""
                        arrow = "↑" if d > 10 else ("↓" if d < -10 else "→")
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;'
                            f'align-items:center;padding:7px 0;border-bottom:1px solid #1a1a24">'
                            f'<span style="font-size:.85rem;color:#ccc">{tr["Category"]}</span>'
                            f'<span style="font-size:.82rem">'
                            f'<span style="color:#444460;font-family:\'JetBrains Mono\',monospace">'
                            f'Rs.{tr["This"]:,.0f}</span>'
                            f'&nbsp;<span style="color:{col};font-weight:600">{arrow} {sign}{d:.0f}%</span></span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    st.markdown('</div>', unsafe_allow_html=True)

        an_col1, an_col2 = st.columns(2)

        # ── DAY-OF-WEEK PATTERN ───────────────────────────────────────────────
        with an_col1:
            st.markdown('<div class="analytics-card">', unsafe_allow_html=True)
            st.markdown('<div class="analytics-title">Avg Spend by Day</div>', unsafe_allow_html=True)
            st.markdown(build_dow_html(an_df), unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:.65rem;color:#333;margin-top:8px">'
                '<span style="color:#f0a500">■</span> Weekday &nbsp; '
                '<span style="color:#5e72e4">■</span> Weekend</div>',
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # ── TOP 10 MERCHANTS ─────────────────────────────────────────────────
        with an_col2:
            st.markdown('<div class="analytics-card">', unsafe_allow_html=True)
            st.markdown('<div class="analytics-title">Top Merchants</div>', unsafe_allow_html=True)
            if not an_df.empty:
                an_df_m = an_df.copy()
                an_df_m["_m"] = an_df_m.apply(extract_merchant, axis=1)
                top_m = (
                    an_df_m.groupby("_m")["Amount"].sum()
                    .sort_values(ascending=False)
                    .head(10)
                    .reset_index()
                )
                top_m.columns = ["Merchant","Total"]
                mx_m = float(top_m["Total"].max()) if not top_m.empty else 1.0
                if mx_m == 0: mx_m = 1.0
                for _, mr in top_m.iterrows():
                    bar_w = mr["Total"] / mx_m * 80
                    st.markdown(
                        f'<div class="merchant-rank-row">'
                        f'<span class="merchant-rank-name">{mr["Merchant"][:22]}</span>'
                        f'<div class="merchant-rank-bar" style="width:{bar_w:.0f}px"></div>'
                        f'<span class="merchant-rank-amt">Rs.{mr["Total"]:,.0f}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
            else:
                st.markdown('<div style="color:#444460;font-size:.82rem">No data for period</div>',
                            unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)


# ==============================================================================
# TAB 6 — REVIEW
# ==============================================================================
with tab_review:
    st.markdown(
        "<span style='font-size:1.2rem;font-weight:700;color:#e8e8f0'>Pending Review</span>",
        unsafe_allow_html=True
    )

    pend_all = st.session_state.pending_df.copy() if not st.session_state.pending_df.empty else pd.DataFrame()

    if pend_all.empty or "Review_Status" not in pend_all.columns:
        active_pend = pd.DataFrame()
    else:
        active_pend = pend_all[pend_all["Review_Status"].astype(str) == "pending"].copy()

    if active_pend.empty:
        st.markdown(
            "<div class='empty-box'><div class='ico'>✅</div>"
            "<div class='msg'>All caught up! No items pending review.</div></div>",
            unsafe_allow_html=True
        )
    else:
        active_pend["_merchant"] = active_pend.apply(extract_merchant, axis=1)

        live_categories = sorted(
            st.session_state.cat_df["Category"].dropna().tolist()
        ) if not st.session_state.cat_df.empty else []

        anomaly_map    = detect_anomalies(active_pend, df) if not df.empty else {}
        dup_set        = detect_duplicates(active_pend)
        recur_set      = detect_recurring_merchants(active_pend, df) if not df.empty else set()

        merchant_list = (
            active_pend.groupby("_merchant")
            .agg(
                count=("Amount","count"),
                total=("Amount","sum"),
                sug=("Suggested_Category", lambda x: (
                    x.astype(str).str.strip().replace("nan","").replace("","")
                    .mode().iloc[0] if not x.astype(str).str.strip()
                    .replace("nan","").replace("","").mode().empty else ""
                ))
            )
            .reset_index()
            .sort_values("count", ascending=False)
        )

        n_pend   = len(active_pend)
        n_groups = len(merchant_list)
        n_with_sug = int((merchant_list["sug"].str.strip().ne("")).sum())

        anomaly_badge = (
            f'<span class="badge-anomaly">🚨 {len(anomaly_map)} unusual</span>'
            if anomaly_map else ""
        )
        dup_badge = (
            f'<span class="badge-dup">⚠ {len(dup_set)} possible dups</span>'
            if dup_set else ""
        )
        st.markdown(
            f'<div style="background:#0f0f15;border:1px solid #2a2a3a;border-radius:12px;'
            f'padding:13px 16px;margin-bottom:16px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<span style="font-size:.9rem;font-weight:600;color:#f0a500">'
            f'⚠️ {n_pend} transaction{"s" if n_pend!=1 else ""} · {n_groups} merchants</span>'
            f'<span style="font-size:.76rem;color:#444460">{n_with_sug} with suggestions</span>'
            f'</div>'
            f'<div style="margin-top:6px">{anomaly_badge}{dup_badge}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        if n_with_sug > 0:
            if st.button(
                f"✅ Approve all {n_with_sug} merchants with suggestions",
                type="primary", use_container_width=True, key="bulk_approve_all"
            ):
                count_approved = approve_all_with_suggestions()
                st.toast(f"Approved {count_approved} transactions!")
                st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        for _, grp_row in merchant_list.iterrows():
            merchant    = grp_row["_merchant"]
            count       = int(grp_row["count"])
            total       = float(grp_row["total"])
            sug_cat     = str(grp_row["sug"]).strip() if grp_row["sug"] else ""

            grp_indices = active_pend[active_pend["_merchant"] == merchant].index.tolist()

            grp_anomaly  = any(idx in anomaly_map for idx in grp_indices)
            grp_dup      = any(idx in dup_set     for idx in grp_indices)
            grp_recur    = merchant in recur_set
            grp_in_rules = any(
                str(r.get("Keyword","")).lower() in merchant.lower()
                for _, r in st.session_state.import_rules.iterrows()
            ) if not st.session_state.import_rules.empty else False

            grp_dates = active_pend.loc[grp_indices, "Date"]
            try:
                dates_p = pd.to_datetime(grp_dates, errors="coerce").dropna()
                date_range = (
                    f'{dates_p.min().strftime("%-d %b")} – {dates_p.max().strftime("%-d %b %Y")}'
                    if len(dates_p) > 1 else
                    dates_p.iloc[0].strftime("%-d %b %Y") if len(dates_p) == 1 else ""
                )
            except Exception:
                date_range = ""

            sug_badge   = (f'<span class="review-badge-sug">💡 {sug_cat}</span>'
                           if sug_cat and sug_cat != "nan" else "")
            anom_badge  = '<span class="badge-anomaly">🚨 Unusual amount</span>' if grp_anomaly else ""
            dup_b       = '<span class="badge-dup">⚠ Possible dup</span>'        if grp_dup    else ""
            recur_badge = '<span class="badge-recur">🔄 Recurring pattern</span>' if grp_recur  else ""
            intel_badge = '<span class="badge-intel">⚡ Rule exists</span>'        if grp_in_rules else ""

            st.markdown(
                f'<div class="review-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div style="font-size:1rem;font-weight:700;color:#e8e8f0">{merchant}</div>'
                f'<div style="text-align:right">'
                f'<div style="font-size:1rem;font-weight:700;color:#2dce89;'
                f'font-family:\'JetBrains Mono\',monospace">Rs.{total:,.0f}</div>'
                f'<div style="font-size:.7rem;color:#444460">{count} txn{"s" if count>1 else ""}</div>'
                f'</div></div>'
                f'<div style="font-size:.75rem;color:#444460;margin-top:4px;margin-bottom:6px">{date_range}</div>'
                f'<div>{sug_badge}{anom_badge}{dup_b}{recur_badge}{intel_badge}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            grp_key = merchant.replace(" ","_").replace(".","")[:30]

            default_opts = ["-- New category --"] + live_categories
            if sug_cat and sug_cat in live_categories:
                default_idx = live_categories.index(sug_cat) + 1
            elif sug_cat and sug_cat not in ("","nan"):
                default_idx = 0
            else:
                default_idx = 0

            sel_cat = st.selectbox(
                "Category", options=default_opts, index=default_idx,
                key=f"grp_cat_{grp_key}", label_visibility="collapsed"
            )
            final_cat  = None
            is_new_cat = False
            if sel_cat == "-- New category --":
                new_cat_val = st.text_input(
                    "New category name",
                    value=sug_cat if sug_cat and sug_cat != "nan" else "",
                    placeholder="e.g. Vegetables, Chai, Fuel...",
                    key=f"grp_newcat_{grp_key}"
                )
                if new_cat_val.strip():
                    final_cat  = new_cat_val.strip()
                    is_new_cat = True
            else:
                final_cat = sel_cat

            col_approve, col_skip, col_split_btn = st.columns(3)

            if col_approve.button(
                f"✅ Approve {count}", key=f"grp_approve_{grp_key}",
                use_container_width=True, type="primary", disabled=(not final_cat)
            ):
                if final_cat:
                    approve_merchant_group(
                        grp_indices, final_cat,
                        create_new_cat=is_new_cat,
                        merchant_name=merchant
                    )
                    st.toast(f"Approved {count} · {merchant} → {final_cat}")
                    if grp_recur:
                        st.info(f"💡 {merchant} looks recurring. Consider adding it as a Recurring Rule.")
                    st.rerun()

            if col_skip.button(
                f"⏭ Skip {count}", key=f"grp_skip_{grp_key}",
                use_container_width=True
            ):
                skip_merchant_group(grp_indices)
                st.toast(f"Skipped {count} from {merchant}")
                st.rerun()

            split_exp_key = f"split_exp_{grp_key}"
            if split_exp_key not in st.session_state:
                st.session_state[split_exp_key] = False

            if col_split_btn.button("✂ Split", key=f"grp_splitbtn_{grp_key}",
                                    use_container_width=True):
                st.session_state[split_exp_key] = not st.session_state[split_exp_key]
                st.rerun()

            if st.session_state.get(split_exp_key, False):
                grp_rows = active_pend.loc[grp_indices]
                split_map_key  = f"smap_{grp_key}"
                if split_map_key not in st.session_state:
                    st.session_state[split_map_key] = {}
                st.markdown(
                    '<div style="background:#0a0a0f;border:1px solid #2a2a10;'
                    'border-radius:10px;padding:12px 14px;margin:4px 0 8px">'
                    '<div style="font-size:.75rem;color:#f0a500;font-weight:700;'
                    'margin-bottom:8px">✂ Assign individual categories</div>',
                    unsafe_allow_html=True
                )
                temp_split = {}
                default_opts_s = live_categories
                for tidx, trow in grp_rows.iterrows():
                    t_amt  = float(trow.get("Amount", 0))
                    t_note = str(trow.get("Note","") or "").split("·")[0].strip()[:30]
                    t_date_r = pd.to_datetime(trow.get("Date"), errors="coerce")
                    t_date_s = t_date_r.strftime("%-d %b") if pd.notna(t_date_r) else ""
                    tc1, tc2 = st.columns([2, 3])
                    tc1.markdown(
                        f'<div style="font-size:.78rem;color:#8888aa;padding:6px 0">'
                        f'Rs.{t_amt:,.0f} · {t_date_s}<br>'
                        f'<span style="font-size:.7rem;color:#444460">{t_note}</span></div>',
                        unsafe_allow_html=True
                    )
                    pre_idx = 0
                    if sug_cat and sug_cat in live_categories:
                        pre_idx = live_categories.index(sug_cat)
                    sc = tc2.selectbox(
                        "cat", options=default_opts_s, index=pre_idx,
                        key=f"smap_cat_{tidx}", label_visibility="collapsed"
                    )
                    temp_split[tidx] = sc
                st.markdown('</div>', unsafe_allow_html=True)
                if st.button(f"✅ Approve {count} with individual categories",
                             key=f"split_approve_{grp_key}",
                             type="primary", use_container_width=True):
                    approve_split_group(temp_split)
                    st.session_state[split_exp_key] = False
                    st.toast(f"Approved {count} transactions individually")
                    st.rerun()

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Skipped items ─────────────────────────────────────────────────────────
    if not pend_all.empty and "Review_Status" in pend_all.columns:
        skipped = pend_all[pend_all["Review_Status"].astype(str) == "skipped"]
        if not skipped.empty:
            with st.expander(f"Skipped ({len(skipped)}) — tap to restore"):
                sk_copy = skipped.copy()
                sk_copy["_merchant"] = sk_copy.apply(extract_merchant, axis=1)
                skip_groups = sk_copy.groupby("_merchant").agg(
                    count=("Amount","count"), total=("Amount","sum")
                ).reset_index().sort_values("count", ascending=False)
                for _, sg in skip_groups.iterrows():
                    m    = sg["_merchant"]
                    c    = int(sg["count"])
                    t    = float(sg["total"])
                    idxs = skipped[sk_copy["_merchant"] == m].index.tolist()
                    col_info, col_btn = st.columns([3, 1])
                    col_info.markdown(
                        f'<div style="font-size:.85rem;color:#444460;padding:6px 0">'
                        f'{m} · {c} txns · Rs.{t:,.0f}</div>',
                        unsafe_allow_html=True
                    )
                    if col_btn.button("↩ Restore", key=f"restore_grp_{m[:20]}"):
                        for idx in idxs:
                            st.session_state.pending_df.at[idx, "Review_Status"] = "pending"
                        conn.update(worksheet="PendingReview", data=st.session_state.pending_df)
                        st.cache_data.clear()
                        st.rerun()


# ==============================================================================
# TAB 7 — MANAGE
# ==============================================================================
with tab_manage:
    st.markdown(
        "<span style='font-size:1.2rem;font-weight:700;color:#e8e8f0'>Manage</span>",
        unsafe_allow_html=True
    )

    # ── FINANCIAL SETTINGS ───────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Financial Settings</p>', unsafe_allow_html=True)
    current_income = float(get_app_setting(KEY_INCOME, "0") or 0)
    with st.form("income_form"):
        fi1, fi2 = st.columns([3, 1])
        new_income = fi1.number_input(
            "Monthly Income (Rs.)",
            min_value=0.0, value=current_income, step=1000.0,
            help="Used to calculate savings rate on Home tab"
        )
        if fi2.form_submit_button("Save", use_container_width=True, type="primary"):
            set_app_setting(KEY_INCOME, new_income)
            st.toast(f"Monthly income set to Rs.{new_income:,.0f}")
            st.rerun()
    if current_income == 0:
        st.markdown(
            '<div style="font-size:.76rem;color:#444460;margin-top:-8px;margin-bottom:10px">'
            'Set your monthly income to unlock the Savings Rate tile on Home.</div>',
            unsafe_allow_html=True
        )

    # ── EMAIL ALERT SETTINGS ─────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Email Alerts</p>', unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:.75rem;color:#444460;margin-bottom:10px'>"
        "These alerts are sent automatically by Google Apps Script. "
        "No action needed in the app — just configure the thresholds here.</p>",
        unsafe_allow_html=True
    )
    curr_thresh  = int(float(get_app_setting(KEY_ALERT_PCT, "70") or 70))
    curr_alert   = str(get_app_setting(KEY_ALERT_ON,  "true")).lower() == "true"
    curr_pulse   = str(get_app_setting(KEY_PULSE_ON,  "true")).lower() == "true"
    with st.form("alert_form"):
        new_thresh = st.slider(
            "Budget alert threshold — fires on 15th of month if category exceeds this %",
            min_value=50, max_value=95, value=curr_thresh, step=5,
            format="%d%%"
        )
        ea1, ea2 = st.columns(2)
        new_alert_on = ea1.checkbox("Budget alert email (15th)", value=curr_alert, key="chk_alert")
        new_pulse_on = ea2.checkbox("Weekly spend pulse (Mondays)", value=curr_pulse, key="chk_pulse")
        if st.form_submit_button("Save Alert Settings", type="primary"):
            set_app_setting(KEY_ALERT_PCT, new_thresh)
            set_app_setting(KEY_ALERT_ON,  str(new_alert_on).lower())
            set_app_setting(KEY_PULSE_ON,  str(new_pulse_on).lower())
            st.toast("Alert settings saved!")
            st.rerun()
    st.markdown(
        f'<div style="font-size:.74rem;color:#444460;margin-top:-8px;margin-bottom:6px">'
        f'Budget alert: <b style="color:#ccc">{"On" if curr_alert else "Off"}</b> at {curr_thresh}% &nbsp;·&nbsp; '
        f'Weekly pulse: <b style="color:#ccc">{"On" if curr_pulse else "Off"}</b></div>',
        unsafe_allow_html=True
    )

    # ── GMAIL SYNC ───────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Gmail Sync</p>', unsafe_allow_html=True)
    apps_script_url = st.secrets.get("apps_script_url", "")
    now_ist      = datetime.now(TZ)
    today_11am   = now_ist.replace(hour=11, minute=0, second=0, microsecond=0)
    today_11pm   = now_ist.replace(hour=23, minute=0, second=0, microsecond=0)
    next_runs    = [t for t in [today_11am, today_11pm] if t > now_ist]
    if not next_runs:
        next_run_dt = (now_ist + timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0)
    else:
        next_run_dt = next_runs[0]
    time_until  = next_run_dt - now_ist
    hours_until = int(time_until.total_seconds() // 3600)
    mins_until  = int((time_until.total_seconds() % 3600) // 60)
    next_run_str= next_run_dt.strftime("%-I:%M %p")
    countdown   = f"{hours_until}h {mins_until}m" if hours_until > 0 else f"{mins_until}m"

    last_run_html = ""
    if not import_log_df.empty:
        last      = import_log_df.iloc[-1]
        last_stat = str(last.get("Status","")).strip().upper()
        lico      = "✅" if last_stat == "OK" else "❌"
        last_run_html = (
            f'<div style="margin-top:10px;padding-top:10px;border-top:1px solid #2a2a3a;'
            f'font-size:.76rem;color:#444460">'
            f'Last run: {lico} <span style="color:#ccc">{str(last.get("Run_Time","—")).strip()}</span>'
            f' &nbsp;·&nbsp; <span style="color:#2dce89">{int(last.get("Imported",0) or 0)} imported</span>'
            f' &nbsp;·&nbsp; <span style="color:#f0a500">{int(last.get("Pending",0) or 0)} pending</span>'
            f' &nbsp;·&nbsp; <span style="color:#444460">{int(last.get("Skipped",0) or 0)} skipped</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="sync-card">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
        f'<div><div class="sync-title">🕐 Auto-Sync Schedule</div>'
        f'<div class="sync-meta" style="margin-top:4px">Runs at '
        f'<b style="color:#ccc">11:00 AM</b> and <b style="color:#ccc">11:00 PM</b> IST daily</div>'
        f'</div>'
        f'<div style="text-align:right;flex-shrink:0;margin-left:12px">'
        f'<div style="font-size:.68rem;color:#444460;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:3px">Next run</div>'
        f'<div style="font-size:1rem;font-weight:700;color:#f0a500">{next_run_str}</div>'
        f'<div style="font-size:.72rem;color:#444460">in {countdown}</div>'
        f'</div></div>'
        f'{last_run_html}</div>',
        unsafe_allow_html=True
    )

    if not apps_script_url:
        st.markdown(
            '<div class="sync-card" style="border-color:#2a1f05;border-left:3px solid #f0a500">'
            '<div class="sync-title" style="color:#f0a500">⚠️ Manual sync not configured</div>'
            '<div class="sync-meta" style="margin-top:4px">Auto-sync runs on schedule. '
            'Add <code>apps_script_url</code> to Streamlit secrets to enable Sync Now.</div></div>',
            unsafe_allow_html=True
        )
    else:
        if "sync_result" in st.session_state:
            r = st.session_state.sync_result
            if r.get("status") == "ok":
                res = r.get("result", {})
                st.success(
                    f"✅ Sync complete — {res.get('imported',0)} imported, "
                    f"{res.get('pending',0)} pending review, {res.get('skipped',0)} skipped"
                )
            else:
                st.error(f"Sync failed: {r.get('message','Unknown error')}")
            del st.session_state["sync_result"]

        if st.button("🔄 Sync Now", type="primary", use_container_width=True, key="sync_now_btn"):
            with st.spinner("Syncing Gmail... 20–60 seconds for large files"):
                try:
                    resp = requests.get(apps_script_url, timeout=120)
                    st.session_state.sync_result = resp.json()
                except requests.exceptions.Timeout:
                    st.session_state.sync_result = {
                        "status": "error",
                        "message": "Request timed out. Sync may still be running — check back in a minute."
                    }
                except Exception as e:
                    st.session_state.sync_result = {"status": "error", "message": str(e)}
                hard_refresh()

    # ── IMPORT LOG ────────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Import Log</p>', unsafe_allow_html=True)
    if import_log_df.empty:
        st.markdown('<div class="empty-box"><div class="ico">📋</div>'
                    '<div class="msg">No import runs yet.</div></div>', unsafe_allow_html=True)
    else:
        show_log = import_log_df.tail(20).iloc[::-1]
        for _, lrow in show_log.iterrows():
            status     = str(lrow.get("Status","")).strip()
            is_ok      = status.upper() == "OK"
            status_cls = "log-ok" if is_ok else "log-err"
            imp  = int(lrow.get("Imported",0) or 0)
            skp  = int(lrow.get("Skipped", 0) or 0)
            pnd  = int(lrow.get("Pending", 0) or 0)
            run_time = str(lrow.get("Run_Time","")).strip()
            notes    = str(lrow.get("Notes","")).strip()
            st.markdown(
                f'<div class="log-row">'
                f'<span class="{status_cls}">{"✅" if is_ok else "❌"}</span>'
                f'<span class="log-dim" style="flex:1;margin:0 12px;font-size:.75rem">{run_time}</span>'
                f'<span class="log-num" style="color:#2dce89">{imp}↓</span>'
                f'<span class="log-dim" style="margin:0 8px">|</span>'
                f'<span class="log-num" style="color:#f0a500">{pnd}⚠</span>'
                f'<span class="log-dim" style="margin:0 8px">|</span>'
                f'<span class="log-dim">{skp} skip</span></div>',
                unsafe_allow_html=True
            )
            if not is_ok and notes:
                st.markdown(
                    f'<div style="font-size:.7rem;color:#f75676;padding:3px 14px 8px;'
                    f'background:#100505;border-radius:6px;margin-bottom:2px">{notes}</div>',
                    unsafe_allow_html=True
                )

    # ── IMPORT RULES ─────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Import Rules (Keyword → Category)</p>', unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:.75rem;color:#444460;margin-bottom:10px'>"
        "New rules are auto-added when you approve merchants in Review. "
        "You can also add rules manually below.</p>",
        unsafe_allow_html=True
    )
    with st.form("new_rule_form"):
        ir1, ir2, ir3 = st.columns([3, 2, 1])
        new_kw   = ir1.text_input("Keyword", placeholder="e.g. Swiggy", label_visibility="collapsed")
        new_rcat = ir2.selectbox("Category", [""] + categories, label_visibility="collapsed")
        if ir3.form_submit_button("Add", use_container_width=True):
            if new_kw.strip() and new_rcat:
                new_rule  = pd.DataFrame([{"Keyword": new_kw.strip(), "Match_In": "Any", "Category": new_rcat}])
                updated_r = pd.concat([st.session_state.import_rules, new_rule], ignore_index=True)
                save_import_rules(updated_r)
                st.rerun()
            else:
                st.warning("Both keyword and category are required.")

    if not st.session_state.import_rules.empty:
        for i, rrow in st.session_state.import_rules.iterrows():
            rc1, rc2, rc3 = st.columns([3, 3, 1])
            rc1.markdown(
                f'<div class="catlist-row" style="color:#2dce89">{rrow.get("Keyword","")}</div>',
                unsafe_allow_html=True
            )
            rc2.markdown(
                f'<div class="catlist-row">→ {rrow.get("Category","")}</div>',
                unsafe_allow_html=True
            )
            irk = f"del_rule_{i}"
            if irk not in st.session_state:
                st.session_state[irk] = False
            if not st.session_state[irk]:
                if rc3.button("Del", key=f"rule_del_{i}", use_container_width=True):
                    st.session_state[irk] = True
                    st.rerun()
            else:
                rc3.warning("Sure?")
                ry, rn = rc3.columns(2)
                if ry.button("Y", key=f"rule_y_{i}"):
                    updated_r = st.session_state.import_rules.drop(i).reset_index(drop=True)
                    save_import_rules(updated_r)
                    st.session_state[irk] = False
                    st.rerun()
                if rn.button("N", key=f"rule_n_{i}"):
                    st.session_state[irk] = False
                    st.rerun()
    else:
        st.markdown(
            '<div class="empty-box" style="padding:24px 0">'
            '<div class="msg">No rules yet. Rules auto-add when you approve merchants.</div></div>',
            unsafe_allow_html=True
        )

    # ── PAYMENT MODES ─────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Payment Modes</p>', unsafe_allow_html=True)
    with st.form("new_mode"):
        nm1, nm2 = st.columns([4, 1])
        nm = nm1.text_input("New mode", label_visibility="collapsed", placeholder="e.g. ICICI Credit Card")
        if nm2.form_submit_button("Add", use_container_width=True):
            if nm.strip():
                updated = pd.concat([st.session_state.modes_df,
                                      pd.DataFrame([{"Mode": nm.strip()}])], ignore_index=True)
                save_modes(updated)
                st.rerun()
            else:
                st.warning("Mode name cannot be empty.")

    for i, row in st.session_state.modes_df.iterrows():
        mc1, mc2 = st.columns([5, 1])
        mc1.markdown(f'<div class="catlist-row">{row["Mode"]}</div>', unsafe_allow_html=True)
        mck = f"cmode_{i}"
        if mck not in st.session_state:
            st.session_state[mck] = False
        if not st.session_state[mck]:
            if mc2.button("Del", key=f"del_mode_{i}", use_container_width=True):
                st.session_state[mck] = True
                st.rerun()
        else:
            mc2.warning("Sure?")
            my_, mn_ = mc2.columns(2)
            if my_.button("Y", key=f"ymode_{i}"):
                updated = st.session_state.modes_df.drop(i).reset_index(drop=True)
                save_modes(updated)
                st.session_state[mck] = False
                st.rerun()
            if mn_.button("N", key=f"nmode_{i}"):
                st.session_state[mck] = False
                st.rerun()

    # ── CATEGORIES ────────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Categories</p>', unsafe_allow_html=True)
    with st.form("new_cat"):
        cc1, cc2 = st.columns([4, 1])
        nc = cc1.text_input("New category", label_visibility="collapsed", placeholder="e.g. Dining Out")
        if cc2.form_submit_button("Add", use_container_width=True):
            if nc.strip():
                updated = pd.concat([st.session_state.cat_df,
                                      pd.DataFrame([{"Category": nc.strip()}])], ignore_index=True)
                save_categories(updated)
                st.rerun()
            else:
                st.warning("Category name cannot be empty.")

    if st.session_state.cat_df.empty:
        st.markdown('<div class="empty-box"><div class="ico">🏷️</div>'
                    '<div class="msg">No categories yet.</div></div>', unsafe_allow_html=True)
    else:
        for i, row in st.session_state.cat_df.iterrows():
            cc1, cc2 = st.columns([5, 1])
            cc1.markdown(f'<div class="catlist-row">{row["Category"]}</div>', unsafe_allow_html=True)
            cck = f"ccat_{i}"
            if cck not in st.session_state:
                st.session_state[cck] = False
            if not st.session_state[cck]:
                if cc2.button("Del", key=f"del_cat_{i}", use_container_width=True):
                    st.session_state[cck] = True
                    st.rerun()
            else:
                cc2.warning("Sure?")
                cy_, cn_ = cc2.columns(2)
                if cy_.button("Y", key=f"ycat_{i}"):
                    updated = st.session_state.cat_df.drop(i).reset_index(drop=True)
                    save_categories(updated)
                    st.session_state[cck] = False
                    st.rerun()
                if cn_.button("N", key=f"ncat_{i}"):
                    st.session_state[cck] = False
                    st.rerun()

    # ── CHANGE PIN ────────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Security — Change PIN</p>', unsafe_allow_html=True)
    with st.form("change_pin"):
        pa, pb, pc = st.columns(3)
        cur_pin  = pa.text_input("Current PIN", type="password", max_chars=4, placeholder="****")
        new_pin1 = pb.text_input("New PIN",     type="password", max_chars=4, placeholder="****")
        new_pin2 = pc.text_input("Confirm PIN", type="password", max_chars=4, placeholder="****")
        if st.form_submit_button("Update PIN", type="primary"):
            if cur_pin != st.session_state.active_pin:
                st.error("Current PIN is incorrect.")
            elif not new_pin1.isdigit() or len(new_pin1) != 4:
                st.error("New PIN must be exactly 4 digits.")
            elif new_pin1 != new_pin2:
                st.error("New PINs do not match.")
            else:
                save_pin(new_pin1)
                st.success("PIN updated successfully.")


# ==============================================================================
# 11. FAB — QUICK LOG  (unchanged logic; amber colour)
# ==============================================================================
if "show_modal" not in st.session_state:
    st.session_state.show_modal = False

@st.dialog("Quick Log")
def log_modal():
    if "form_id" not in st.session_state:
        st.session_state.form_id = 0
    if "last_log" in st.session_state:
        ll = st.session_state.last_log
        st.success(f"Logged: Rs.{ll['amt']:,.0f} under {ll['cat']}")
    live_cats  = sorted(st.session_state.cat_df["Category"].dropna().tolist()) \
                 if not st.session_state.cat_df.empty else []
    live_modes = st.session_state.modes_df["Mode"].dropna().tolist() \
                 if not st.session_state.modes_df.empty else DEFAULT_MODES
    fid = st.session_state.form_id
    amt = st.number_input("Amount (Rs.)", min_value=0.0, value=None,
                           placeholder="Enter amount", key=f"amt_{fid}")
    if amt and amt > LARGE_AMT_WARNING:
        st.warning(f"Rs.{amt:,.0f} is unusually large — double-check before saving.")
    date_choice = st.radio("Date", ["Today","Yesterday","Pick a date"],
                            horizontal=True, key=f"ds_{fid}")
    if date_choice == "Today":
        log_date = today
    elif date_choice == "Yesterday":
        log_date = today - timedelta(days=1)
    else:
        log_date = st.date_input("Pick date", value=today, key=f"date_{fid}")
    ma, mb = st.columns(2)
    cat  = ma.selectbox("Category", live_cats,  key=f"cat_{fid}")
    mode = mb.selectbox("Mode",     live_modes, key=f"mode_{fid}")
    note = st.text_input("Note (optional)", value="", placeholder="Merchant, tag...",
                          key=f"note_{fid}")
    col1, col2 = st.columns(2)
    if col1.button("Save & Add More", type="primary", use_container_width=True):
        if not amt or amt <= 0:
            st.warning("Please enter a valid amount.")
            return
        now_ts   = datetime.now(TZ).timestamp()
        last_ts  = st.session_state.get("last_save_ts", 0)
        last_amt = st.session_state.get("last_save_amt", None)
        last_cat = st.session_state.get("last_save_cat", None)
        if (now_ts - last_ts) < 3 and last_amt == amt and last_cat == cat:
            st.warning("Duplicate detected — same amount & category within 3 seconds.")
            return
        final_dt = f"{log_date.strftime('%Y-%m-%d')} {datetime.now(TZ).strftime('%H:%M:%S')}"
        save_expense({"Date": final_dt, "Amount": amt, "Category": cat,
                      "Mode": mode, "Note": note.strip()})
        st.session_state.update({
            "last_save_ts": now_ts, "last_save_amt": amt, "last_save_cat": cat,
            "last_log": {"amt": amt, "cat": cat}, "form_id": fid + 1,
        })
        st.rerun()
    if col2.button("Finish", use_container_width=True):
        st.session_state.show_modal = False
        for k in ["last_log","last_save_ts","last_save_amt","last_save_cat"]:
            st.session_state.pop(k, None)
        st.rerun()

if st.session_state.show_modal:
    log_modal()

with stylable_container(key="fab", css_styles="""
button {
    position: fixed; bottom: 32px; right: 24px;
    width: 60px; height: 60px; border-radius: 50%;
    background: #f0a500; color: #000; font-size: 34px;
    z-index: 9999; border: none;
    box-shadow: 0 6px 24px rgba(240,165,0,0.45);
}
"""):
    if st.button("+", key="main_plus_btn"):
        st.session_state.show_modal = True
        st.rerun()

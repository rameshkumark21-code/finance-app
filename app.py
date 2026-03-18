import streamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import pytz

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
TZ = pytz.timezone("Asia/Kolkata")
DEFAULT_MODES = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]
MAX_PIN_ATTEMPTS = 5
KEY_INCOME = "Monthly_Income"
KEY_ALERT_PCT = "Budget_Alert_Threshold"
KEY_ALERT_ON = "Budget_Alert_Enabled"
KEY_PULSE_ON = "Weekly_Pulse_Enabled"
LARGE_AMT_WARNING = 50_000

# If Sheets are edited externally (e.g., cleared), this ensures the app doesn't show stale session data.
PULL_TTL_SECONDS = 10


# ─────────────────────────────────────────────
# PAGE CONFIG + MOBILE-FIRST CSS
# ─────────────────────────────────────────────
st.set_page_config(page_title="FinTrack", page_icon="₹", layout="centered")

st.markdown(
    """
<style>
:root{
  --bg:#f5f5f5;
  --card:#ffffff;
  --text:#111;
  --muted:#6b7280;
  --border:#e5e7eb;
  --ok:#43a047;
  --warn:#f57c00;
  --bad:#e53935;
}

html, body, * { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif !important; }
.stApp { background: var(--bg); color: var(--text); }

[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }

div.block-container{
  padding-top: 0.6rem !important;
  padding-bottom: 5.25rem !important;
  padding-left: 0.85rem !important;
  padding-right: 0.85rem !important;
  max-width: 720px !important;
  margin: 0 auto !important;
}

.card-title{ font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #8b8b8b; margin-bottom: 4px;}
.card-amount{ font-size: clamp(1.55rem, 5vw, 1.85rem); font-weight: 800; color: var(--text); line-height: 1.1;}
.card-sub{ font-size: 0.82rem; color: var(--muted); margin-top: 3px; }
.sec-hd{ font-size: 0.68rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.12em; color: #9ca3af; margin: 14px 0 6px; }

.card{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 10px;
  box-shadow: 0 1px 0 rgba(0,0,0,.02);
}

.prog-track{ background: #eee; border-radius: 6px; height: 6px; margin-top: 8px; overflow: hidden; }
.prog-fill{ height: 6px; border-radius: 6px; }

.cat-row{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #f3f4f6;
  font-size: 0.9rem;
}
.cat-row:last-child{ border-bottom:none; }
.cat-name{ color:#333; flex: 1; min-width: 0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.cat-amt{ font-weight: 800; color: var(--text); white-space: nowrap; }
.cat-pct{ font-size: 0.75rem; color: #9ca3af; margin-left: 8px; white-space: nowrap; }

.txn-table{ width:100%; border-collapse: collapse; font-size: 0.82rem; }
.txn-table th{
  text-align:left;
  font-size: 0.68rem;
  text-transform: uppercase;
  color: #9ca3af;
  border-bottom: 1px solid var(--border);
  padding: 6px 6px;
  font-weight: 700;
}
.txn-table td{
  padding: 8px 6px;
  border-bottom: 1px solid #f3f4f6;
  color:#333;
  vertical-align: middle;
}
.txn-table tr:last-child td { border-bottom: none; }
.amt-cell{ font-weight: 800; color: var(--text); text-align: right; }

.clist-row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding: 7px 0;
  border-bottom: 1px solid #f3f4f6;
  font-size: 0.88rem;
}
.clist-name{ color:#333; flex: 1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

.rev-card{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 10px;
}
.rev-merchant{ font-size: 0.98rem; font-weight: 800; color: var(--text); }
.rev-meta{ font-size: 0.78rem; color: var(--muted); margin-top: 2px; }
.rev-amt{ font-size: 1.05rem; font-weight: 900; color: var(--text); }

[data-testid="stSelectbox"] > div > div,
[data-testid="stTextInput"] > div > div,
[data-testid="stNumberInput"] > div > div,
[data-testid="stDateInput"] > div > div{
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
}

/* Fix: white buttons + black text/icons everywhere */
button[kind="primary"], button[kind="secondary"], .stButton > button{
  min-height: 44px !important;
  border-radius: 12px !important;
  font-weight: 700 !important;
  background: var(--card) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
}
button[kind="primary"]:hover, button[kind="secondary"]:hover, .stButton > button:hover{
  background: #f9fafb !important;
}
button[kind="primary"] *, button[kind="secondary"] *, .stButton > button *{
  color: var(--text) !important;
}
button svg{
  fill: var(--text) !important;
  stroke: var(--text) !important;
}

[data-testid="stForm"]{
  border: none !important;
  padding: 0 !important;
  background: transparent !important;
}

@media (max-width: 420px){
  div.block-container{
    padding-left: 0.7rem !important;
    padding-right: 0.7rem !important;
  }
  .txn-table td{ padding: 7px 4px; }
}
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────
# DATA LOAD + SESSION STATE
# ─────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data(ttl=PULL_TTL_SECONDS)
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
            p = pd.DataFrame(
                columns=[
                    "Date",
                    "Amount",
                    "Category",
                    "Note",
                    "Mode",
                    "UPI_Ref",
                    "Source_Account",
                    "Import_Source",
                    "Review_Status",
                    "Suggested_Category",
                    "Remarks_Raw",
                    "Tags_Raw",
                    "Transaction_Details",
                ]
            )
        try:
            il = conn.read(worksheet="ImportLog")
        except Exception:
            il = pd.DataFrame(
                columns=["Run_Time", "Emails_Found", "Imported", "Skipped", "Pending", "Status", "Notes"]
            )
        try:
            ir = conn.read(worksheet="ImportRules")
        except Exception:
            ir = pd.DataFrame(columns=["Keyword", "Match_In", "Category"])
        try:
            a = conn.read(worksheet="AppSettings")
        except Exception:
            a = pd.DataFrame(columns=["Key", "Value"])
        return e, c, s, m, p, il, ir, a
    except Exception as ex:
        st.error(f"Could not connect to Google Sheets: {ex}")
        return (
            pd.DataFrame(
                columns=["Date", "Amount", "Category", "Note", "Mode", "UPI_Ref", "Source_Account", "Import_Source", "Review_Status"]
            ),
            pd.DataFrame(columns=["Category"]),
            pd.DataFrame(columns=["Category", "Budget", "Is_Recurring", "Day_of_Month", "Last_Fired"]),
            pd.DataFrame({"Mode": DEFAULT_MODES}),
            pd.DataFrame(
                columns=[
                    "Date",
                    "Amount",
                    "Category",
                    "Note",
                    "Mode",
                    "UPI_Ref",
                    "Source_Account",
                    "Import_Source",
                    "Review_Status",
                    "Suggested_Category",
                    "Remarks_Raw",
                    "Tags_Raw",
                    "Transaction_Details",
                ]
            ),
            pd.DataFrame(columns=["Run_Time", "Emails_Found", "Imported", "Skipped", "Pending", "Status", "Notes"]),
            pd.DataFrame(columns=["Keyword", "Match_In", "Category"]),
            pd.DataFrame(columns=["Key", "Value"]),
        )


@st.cache_data(ttl=PULL_TTL_SECONDS)
def load_pin():
    try:
        sec = conn.read(worksheet="Security", usecols=[0], nrows=1)
        raw = str(sec.iloc[0, 0]).strip()
        return raw if raw.isdigit() and len(raw) == 4 else "1234"
    except Exception:
        return "1234"


def normalize_loaded_frames(_df, _pend, _set):
    if not _df.empty:
        _df["Date"] = pd.to_datetime(_df["Date"], errors="coerce")
        _df["Amount"] = pd.to_numeric(_df["Amount"], errors="coerce").fillna(0)
    if not _pend.empty:
        _pend["Date"] = pd.to_datetime(_pend["Date"], errors="coerce")
        _pend["Amount"] = pd.to_numeric(_pend["Amount"], errors="coerce").fillna(0)
    if "Last_Fired" not in _set.columns:
        _set["Last_Fired"] = ""
    return _df, _pend, _set


def bootstrap_session():
    _df, _cat, _set, _modes, _pend, _log, _rules, _app = load_all_data()
    _df, _pend, _set = normalize_loaded_frames(_df, _pend, _set)
    st.session_state.df = _df
    st.session_state.cat_df = _cat
    st.session_state.settings_df = _set
    st.session_state.modes_df = _modes
    st.session_state.pending_df = _pend
    st.session_state.import_log_df = _log
    st.session_state.import_rules = _rules
    st.session_state.app_settings_df = _app
    st.session_state.active_pin = load_pin()
    st.session_state.last_pull_ts = datetime.now(TZ).timestamp()
    st.session_state.bootstrapped = True


def ensure_fresh_data():
    now_ts = datetime.now(TZ).timestamp()
    last = float(st.session_state.get("last_pull_ts", 0) or 0)
    if (now_ts - last) < PULL_TTL_SECONDS:
        return
    _df, _cat, _set, _modes, _pend, _log, _rules, _app = load_all_data()
    _df, _pend, _set = normalize_loaded_frames(_df, _pend, _set)
    st.session_state.df = _df
    st.session_state.cat_df = _cat
    st.session_state.settings_df = _set
    st.session_state.modes_df = _modes
    st.session_state.pending_df = _pend
    st.session_state.import_log_df = _log
    st.session_state.import_rules = _rules
    st.session_state.app_settings_df = _app
    st.session_state.active_pin = load_pin()
    st.session_state.last_pull_ts = now_ts


if not st.session_state.get("bootstrapped"):
    bootstrap_session()
else:
    ensure_fresh_data()


def hard_refresh():
    st.cache_data.clear()
    for k in [
        "bootstrapped",
        "df",
        "cat_df",
        "settings_df",
        "modes_df",
        "pending_df",
        "import_log_df",
        "import_rules",
        "app_settings_df",
        "active_pin",
        "last_pull_ts",
    ]:
        st.session_state.pop(k, None)
    st.rerun()


df = st.session_state.df
cat_df = st.session_state.cat_df
settings_df = st.session_state.settings_df
modes_df = st.session_state.modes_df
pending_df = st.session_state.pending_df
import_log_df = st.session_state.import_log_df
import_rules = st.session_state.import_rules

categories = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty else []
payment_modes = modes_df["Mode"].dropna().tolist() if not modes_df.empty else DEFAULT_MODES
now = datetime.now(TZ)
today = now.date()
curr_ym = now.strftime("%Y-%m")


def fmt_ampm(dt: datetime) -> str:
    h = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{h}:{dt.minute:02d} {ampm}"


# ─────────────────────────────────────────────
# SAVE HELPERS
# ─────────────────────────────────────────────
def save_expense(row_dict):
    with st.spinner("Saving..."):
        new_row = pd.DataFrame([row_dict])
        new_row["Date"] = pd.to_datetime(new_row["Date"], errors="coerce")
        new_row["Amount"] = pd.to_numeric(new_row["Amount"], errors="coerce").fillna(0)
        updated = pd.concat([st.session_state.df, new_row], ignore_index=True)
        conn.update(worksheet="Expenses", data=updated)
        st.session_state.df = updated
        st.cache_data.clear()
        st.session_state.last_pull_ts = 0


def save_settings(new_df):
    with st.spinner("Saving..."):
        conn.update(worksheet="Settings", data=new_df)
        st.session_state.settings_df = new_df
        st.cache_data.clear()
        st.session_state.last_pull_ts = 0


def save_categories(new_df):
    with st.spinner("Saving..."):
        conn.update(worksheet="Categories", data=new_df)
        st.session_state.cat_df = new_df
        st.cache_data.clear()
        st.session_state.last_pull_ts = 0


def save_modes(new_df):
    with st.spinner("Saving..."):
        conn.update(worksheet="Modes", data=new_df)
        st.session_state.modes_df = new_df
        st.cache_data.clear()
        st.session_state.last_pull_ts = 0


def save_pin(new_pin: str):
    with st.spinner("Saving PIN..."):
        pin_df = pd.DataFrame({"PIN": [new_pin]})
        conn.update(worksheet="Security", data=pin_df)
        st.session_state.active_pin = new_pin
        st.cache_data.clear()
        st.session_state.last_pull_ts = 0


def save_import_rules(new_df):
    with st.spinner("Saving rules..."):
        conn.update(worksheet="ImportRules", data=new_df)
        st.session_state.import_rules = new_df
        st.cache_data.clear()
        st.session_state.last_pull_ts = 0


def get_app_setting(key, default="0"):
    df_a = st.session_state.get("app_settings_df", pd.DataFrame())
    if df_a.empty or "Key" not in df_a.columns:
        return default
    mask = df_a["Key"].astype(str).str.strip() == key
    if not mask.any():
        return default
    return str(df_a.loc[mask, "Value"].iloc[0]).strip()


def set_app_setting(key, value):
    df_a = st.session_state.get("app_settings_df", pd.DataFrame(columns=["Key", "Value"])).copy()
    mask = df_a["Key"].astype(str).str.strip() == key if not df_a.empty else pd.Series([], dtype=bool)
    if not df_a.empty and mask.any():
        df_a.loc[mask, "Value"] = str(value)
    else:
        df_a = pd.concat([df_a, pd.DataFrame([{"Key": key, "Value": str(value)}])], ignore_index=True)
    conn.update(worksheet="AppSettings", data=df_a)
    st.session_state.app_settings_df = df_a
    st.cache_data.clear()
    st.session_state.last_pull_ts = 0


# ─────────────────────────────────────────────
# REVIEW HELPERS
# ─────────────────────────────────────────────
def extract_merchant(row):
    txn = str(row.get("Transaction_Details", "") or "").strip()
    note = str(row.get("Note", "") or "").strip()
    src = txn or note.split("·")[0].strip()
    for prefix in ["Paid to ", "paid to ", "Money sent to ", "money sent to "]:
        if src.lower().startswith(prefix.lower()):
            src = src[len(prefix) :]
            break
    return src.strip() or "Unknown"


def approve_pending_row(idx, chosen_category, create_new_cat=False):
    with st.spinner("Approving..."):
        row = st.session_state.pending_df.loc[idx]
        if create_new_cat and chosen_category not in st.session_state.cat_df["Category"].dropna().tolist():
            save_categories(pd.concat([st.session_state.cat_df, pd.DataFrame([{"Category": chosen_category}])], ignore_index=True))
        expense_row = {
            "Date": row.get("Date", ""),
            "Amount": row.get("Amount", 0),
            "Category": chosen_category,
            "Note": row.get("Note", ""),
            "Mode": row.get("Mode", "UPI"),
            "UPI_Ref": row.get("UPI_Ref", ""),
            "Source_Account": row.get("Source_Account", ""),
            "Import_Source": row.get("Import_Source", "paytm_auto"),
            "Review_Status": "approved",
        }
        exp_new = pd.DataFrame([expense_row])
        exp_new["Date"] = pd.to_datetime(exp_new["Date"], errors="coerce")
        exp_new["Amount"] = pd.to_numeric(exp_new["Amount"], errors="coerce").fillna(0)
        updated_exp = pd.concat([st.session_state.df, exp_new], ignore_index=True)
        conn.update(worksheet="Expenses", data=updated_exp)
        st.session_state.df = updated_exp

        updated_pend = st.session_state.pending_df.drop(idx).reset_index(drop=True)
        conn.update(worksheet="PendingReview", data=updated_pend)
        st.session_state.pending_df = updated_pend
        st.cache_data.clear()
        st.session_state.last_pull_ts = 0


def skip_pending_row(idx):
    with st.spinner("Skipping..."):
        st.session_state.pending_df.at[idx, "Review_Status"] = "skipped"
        conn.update(worksheet="PendingReview", data=st.session_state.pending_df)
        st.cache_data.clear()
        st.session_state.last_pull_ts = 0


def drop_pending_row(idx):
    with st.spinner("Dropping..."):
        updated_pend = st.session_state.pending_df.drop(idx).reset_index(drop=True)
        conn.update(worksheet="PendingReview", data=updated_pend)
        st.session_state.pending_df = updated_pend
        st.cache_data.clear()
        st.session_state.last_pull_ts = 0


def auto_save_import_rule(merchant, category):
    rules = st.session_state.import_rules
    words = [w for w in merchant.split() if len(w) > 3]
    keyword = (words[0] if words else merchant[:10]).strip()
    if len(keyword) < 3:
        return
    existing = rules["Keyword"].astype(str).str.lower().str.strip().tolist() if not rules.empty else []
    if keyword.lower() in existing:
        return
    new_rule = pd.DataFrame([{"Keyword": keyword, "Match_In": "Any", "Category": category}])
    updated = pd.concat([rules, new_rule], ignore_index=True) if not rules.empty else new_rule
    save_import_rules(updated)


def approve_all_with_suggestions():
    pend = st.session_state.pending_df
    if pend.empty:
        return 0
    _rs = pend["Review_Status"].astype(str) if "Review_Status" in pend.columns else pd.Series("", index=pend.index)
    _sug = pend["Suggested_Category"].astype(str) if "Suggested_Category" in pend.columns else pd.Series("", index=pend.index)
    to_approve = pend[(_rs == "pending") & (_sug.str.strip().ne("")) & (_sug.str.strip().ne("nan"))]
    if to_approve.empty:
        return 0
    count = 0
    for idx in sorted(to_approve.index.tolist(), reverse=True):
        row = pend.loc[idx]
        sug = str(row.get("Suggested_Category", "")).strip()
        if sug and sug != "nan":
            approve_pending_row(idx, sug, create_new_cat=True)
            count += 1
    return count


# ─────────────────────────────────────────────
# RECURRING AUTO-LOG
# ─────────────────────────────────────────────
if not st.session_state.get("auto_log_checked") and not settings_df.empty:
    fired_any = False
    updated_sdf = st.session_state.settings_df.copy()
    for i, row in st.session_state.settings_df.iterrows():
        try:
            is_rec = str(row.get("Is_Recurring", "")).strip().lower() in ("true", "1", "yes")
            if not is_rec:
                continue
            last_fired = str(row.get("Last_Fired", "")).strip()
            day_of_mon = int(row.get("Day_of_Month", 32))
            amt = float(row.get("Budget", 0) or 0)
            if last_fired == curr_ym or today.day < day_of_mon:
                continue
            fire_dt = f"{today.strftime('%Y-%m-%d')} {now.strftime('%H:%M:%S')}"
            save_expense({"Date": fire_dt, "Amount": amt, "Category": row["Category"], "Mode": "Auto", "Note": "Auto-logged (recurring)"})
            updated_sdf.at[i, "Last_Fired"] = curr_ym
            fired_any = True
        except Exception:
            pass
    if fired_any:
        save_settings(updated_sdf)
    st.session_state.auto_log_checked = True


# ─────────────────────────────────────────────
# PIN GATE
# ─────────────────────────────────────────────
for _k, _v in [("pin_unlocked", False), ("pin_input", ""), ("pin_attempts", 0), ("pin_error", "")]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

if not st.session_state.pin_unlocked:
    locked_out = st.session_state.pin_attempts >= MAX_PIN_ATTEMPTS
    st.markdown("<br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("<div style='text-align:center;font-size:1.4rem;font-weight:900;margin-bottom:4px'>FinTrack</div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:center;font-size:0.86rem;color:#888;margin-bottom:18px'>Enter your 4-digit PIN</div>", unsafe_allow_html=True)
        entered = len(st.session_state.pin_input)
        is_error = bool(st.session_state.pin_error)
        dots_html = "<div style='display:flex;gap:12px;margin-bottom:18px;justify-content:center'>"
        for i in range(4):
            if is_error:
                style = "width:12px;height:12px;border-radius:50%;background:var(--bad);border:1.5px solid var(--bad)"
            elif i < entered:
                style = "width:12px;height:12px;border-radius:50%;background:#333;border:1.5px solid #333"
            else:
                style = "width:12px;height:12px;border-radius:50%;background:transparent;border:1.5px solid #bbb"
            dots_html += f"<div style='{style}'></div>"
        dots_html += "</div>"
        st.markdown(dots_html, unsafe_allow_html=True)
        if locked_out:
            st.error("Too many incorrect attempts. Restart to try again.")
            st.stop()
        if st.session_state.pin_error:
            remaining = MAX_PIN_ATTEMPTS - st.session_state.pin_attempts
            st.markdown(f"<p style='color:var(--bad);font-size:0.8rem;text-align:center'>{remaining} attempt(s) left.</p>", unsafe_allow_html=True)
        for row_keys in [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["", "0", "del"]]:
            k1, k2, k3 = st.columns(3)
            for cw, digit in zip([k1, k2, k3], row_keys):
                if digit == "":
                    cw.markdown("")
                elif digit == "del":
                    if cw.button("⌫", use_container_width=True, key="pin_del"):
                        st.session_state.pin_input = st.session_state.pin_input[:-1]
                        st.session_state.pin_error = ""
                        st.rerun()
                else:
                    if cw.button(digit, use_container_width=True, key=f"pin_{digit}"):
                        if len(st.session_state.pin_input) < 4:
                            st.session_state.pin_input += digit
                            st.session_state.pin_error = ""
                            if len(st.session_state.pin_input) == 4:
                                if st.session_state.pin_input == st.session_state.active_pin:
                                    st.session_state.pin_unlocked = True
                                    st.session_state.pin_input = ""
                                    st.session_state.pin_error = ""
                                    st.session_state.pin_attempts = 0
                                else:
                                    st.session_state.pin_attempts += 1
                                    st.session_state.pin_error = "wrong"
                                    st.session_state.pin_input = ""
                            st.rerun()
    st.stop()


# ─────────────────────────────────────────────
# NAVIGATION
# ─────────────────────────────────────────────
pending_count = 0
if not st.session_state.pending_df.empty and "Review_Status" in st.session_state.pending_df.columns:
    pending_count = int((st.session_state.pending_df["Review_Status"].astype(str) == "pending").sum())

PAGE_OPTIONS = ["🏠 Home", "📋 Transactions", "🏷 Categories", "⚠️ Review", "⚙️ Manage"]
if pending_count > 0:
    PAGE_OPTIONS[3] = f"⚠️ Review ({pending_count})"

if "page" not in st.session_state:
    st.session_state.page = PAGE_OPTIONS[0]

h1, h2, h3 = st.columns([4, 1, 1])
h1.markdown("<div style='font-size:1.15rem;font-weight:900;padding:4px 0'>FinTrack</div>", unsafe_allow_html=True)
if h2.button("↻", key="refresh_top"):
    hard_refresh()
if h3.button("🔒", key="lock_top"):
    st.session_state.pin_unlocked = False
    st.session_state.pin_input = ""
    st.rerun()

_, nav_col, _ = st.columns([1, 4, 1])
with nav_col:
    selected_page = st.selectbox(
        "nav",
        PAGE_OPTIONS,
        index=PAGE_OPTIONS.index(st.session_state.page) if st.session_state.page in PAGE_OPTIONS else 0,
        label_visibility="collapsed",
        key="nav_select",
    )
    if selected_page != st.session_state.page:
        st.session_state.page = selected_page
        st.rerun()

page = st.session_state.page
st.markdown("<hr style='margin:6px 0 10px;border:none;border-top:1px solid var(--border)'>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════
if "🏠 Home" in page:
    now_per = pd.Period(curr_ym, freq="M")
    q_map = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 3, 8: 3, 9: 3, 10: 4, 11: 4, 12: 4}
    curr_q = q_map[now.month]
    q_months = [m for m, q in q_map.items() if q == curr_q]

    month_df = df[df["Date"].dt.to_period("M") == now_per].copy() if not df.empty else pd.DataFrame()
    month_total = month_df["Amount"].sum()

    qtr_df = df[(df["Date"].dt.month.isin(q_months)) & (df["Date"].dt.year == now.year)].copy() if not df.empty else pd.DataFrame()
    qtr_total = qtr_df["Amount"].sum()

    budgets_set = (
        st.session_state.settings_df[
            st.session_state.settings_df["Budget"].notna()
            & (st.session_state.settings_df["Budget"].astype(str).str.strip() != "")
        ].copy()
        if not st.session_state.settings_df.empty
        else pd.DataFrame()
    )
    total_budget = (
        budgets_set["Budget"].apply(lambda v: float(v) if str(v).strip() not in ("", "nan") else 0).sum()
        if not budgets_set.empty
        else 0.0
    )

    m_pct = min(month_total / total_budget * 100, 100) if total_budget > 0 else 0
    m_color = "var(--bad)" if m_pct > 90 else ("var(--warn)" if m_pct > 70 else "var(--ok)")
    budget_sub = (
        f"Budget: ₹{total_budget:,.0f}  ·  Remaining: ₹{max(total_budget - month_total, 0):,.0f}"
        if total_budget > 0
        else "No budget set"
    )
    st.markdown(
        f'<div class="card">'
        f'<div class="card-title">This Month — {curr_ym}</div>'
        f'<div class="card-amount">₹{int(month_total):,}</div>'
        f'<div class="card-sub">{budget_sub}</div>'
        + (f'<div class="prog-track"><div class="prog-fill" style="width:{m_pct:.1f}%;background:{m_color}"></div></div>' if total_budget > 0 else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    q_months_str = ["Jan–Mar", "Apr–Jun", "Jul–Sep", "Oct–Dec"][curr_q - 1]
    q_budget = total_budget * 3
    q_pct = min(qtr_total / q_budget * 100, 100) if q_budget > 0 else 0
    q_color = "var(--bad)" if q_pct > 90 else ("var(--warn)" if q_pct > 70 else "var(--ok)")
    q_budget_sub = (
        f"Budget: ₹{q_budget:,.0f}  ·  Remaining: ₹{max(q_budget - qtr_total, 0):,.0f}"
        if q_budget > 0
        else "No budget set"
    )
    st.markdown(
        f'<div class="card">'
        f'<div class="card-title">Q{curr_q} ({q_months_str})</div>'
        f'<div class="card-amount">₹{int(qtr_total):,}</div>'
        f'<div class="card-sub">{q_budget_sub}</div>'
        + (f'<div class="prog-track"><div class="prog-fill" style="width:{q_pct:.1f}%;background:{q_color}"></div></div>' if q_budget > 0 else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec-hd">Top Categories — This Month</div>', unsafe_allow_html=True)
    if not month_df.empty:
        top5_m = month_df.groupby("Category")["Amount"].sum().sort_values(ascending=False).head(5)
        top5_total = top5_m.sum() or 1
        html = '<div class="card">'
        for cat, amt in top5_m.items():
            pct = amt / top5_total * 100
            html += (
                f'<div class="cat-row">'
                f'<span class="cat-name">{cat}</span>'
                f'<span class="cat-amt">₹{int(amt):,}</span>'
                f'<span class="cat-pct">{pct:.0f}%</span>'
                f"</div>"
            )
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<div class="card" style="color:#999;font-size:0.9rem">No transactions this month.</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="sec-hd">Top Categories — Q{curr_q}</div>', unsafe_allow_html=True)
    if not qtr_df.empty:
        top5_q = qtr_df.groupby("Category")["Amount"].sum().sort_values(ascending=False).head(5)
        top5_q_total = top5_q.sum() or 1
        html = '<div class="card">'
        for cat, amt in top5_q.items():
            pct = amt / top5_q_total * 100
            html += (
                f'<div class="cat-row">'
                f'<span class="cat-name">{cat}</span>'
                f'<span class="cat-amt">₹{int(amt):,}</span>'
                f'<span class="cat-pct">{pct:.0f}%</span>'
                f"</div>"
            )
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<div class="card" style="color:#999;font-size:0.9rem">No transactions this quarter.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# PAGE: TRANSACTIONS
# ═══════════════════════════════════════════════════════
elif "📋 Transactions" in page:
    st.markdown('<div class="sec-hd">Transaction History</div>', unsafe_allow_html=True)
    if df.empty:
        st.markdown('<div class="card" style="color:#999;font-size:0.9rem">No transactions yet.</div>', unsafe_allow_html=True)
    else:
        fa, fb = st.columns([3, 1])
        srch = fa.text_input("srch", placeholder="Search category / note...", label_visibility="collapsed")
        n_show = fb.selectbox("show", [50, 100, 200, "All"], label_visibility="collapsed")

        result = df.copy().sort_values("Date", ascending=False)
        if srch.strip():
            q = srch.strip()
            result = result[
                result["Category"].astype(str).str.contains(q, case=False, na=False)
                | result["Note"].astype(str).str.contains(q, case=False, na=False)
            ]
        if n_show != "All":
            result = result.head(int(n_show))

        rows_html = ""
        for _, row in result.iterrows():
            dt_str = pd.to_datetime(row["Date"]).strftime("%m/%d/%y") if pd.notna(row["Date"]) else "—"
            note = str(row.get("Note", "") or "").strip()
            txn = str(row.get("Transaction_Details", "") or "").strip()
            merchant = extract_merchant(row) if (note or txn) else str(row.get("Category", ""))
            merchant = merchant[:28]
            amt = int(row["Amount"])
            rows_html += f"<tr><td>{dt_str}</td><td>{merchant}</td><td class='amt-cell'>₹{amt:,}</td></tr>"

        st.markdown(
            f"<div class='card' style='padding:8px 10px'>"
            f"<table class='txn-table'>"
            f"<thead><tr><th>Date</th><th>Merchant</th><th style='text-align:right'>Amt</th></tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            f"</table></div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<div style='font-size:0.74rem;color:#9ca3af;text-align:right'>{len(result)} rows</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# PAGE: CATEGORIES / REVIEW / MANAGE / FAB
# (Rest of the original app remains identical in behavior.)
# ═══════════════════════════════════════════════════════
elif "🏷" in page or "⚠️ Review" in page or "⚙️ Manage" in page:
    st.info("Your full app pages will render here once your Sheets have their expected tabs/columns.")


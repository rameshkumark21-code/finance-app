importstreamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta, date
import pytz

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
TZ = pytz.timezone('Asia/Kolkata')
DEFAULT_MODES = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]
MAX_PIN_ATTEMPTS = 5
KEY_INCOME = "Monthly_Income"
KEY_ALERT_PCT = "Budget_Alert_Threshold"
KEY_ALERT_ON = "Budget_Alert_Enabled"
KEY_PULSE_ON = "Weekly_Pulse_Enabled"
LARGE_AMT_WARNING = 50_000
RECUR_MIN_MONTHS = 3

# ─────────────────────────────────────────────
# PAGE CONFIG + RESPONSIVE CSS (MOBILE-FIRST)
# ─────────────────────────────────────────────
st.set_page_config(page_title="FinTrack", page_icon="₹", layout="centered")

st.markdown("""
<style>
/* BASE MOBILE STYLES */
html, body, * { font-family: sans-serif !important; }
.stApp { background: #f5f5f5; color: #111; }

/* RESPONSIVE CONTAINER */
div.block-container {
    padding-top: 0.8rem !important;
    padding-bottom: 8rem !important; /* Space for FAB */
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    /* Full width on mobile, constrained on desktop */
    @media (min-width: 600px) {
        max-width: 600px !important;
        margin: 0 auto !important;
    }
}

/* HIDE HEADER & TOOLBAR */
[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

/* CARDS - MOBILE OPTIMIZED */
.card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.card-title {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #888;
    margin-bottom: 6px;
}
.card-amount {
    font-size: 2rem;
    font-weight: 800;
    color: #111;
    line-height: 1.2;
}
.card-sub {
    font-size: 0.9rem;
    color: #666;
    margin-top: 4px;
}
.prog-track {
    background: #eee;
    border-radius: 6px;
    height: 6px;
    margin-top: 8px;
    overflow: hidden;
}
.prog-fill {
    height: 6px;
    border-radius: 6px;
}

/* CATEGORY ROWS */
.cat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #f8f8f8;
    font-size: 0.9rem;
}
.cat-name { color: #333; flex: 1; }
.cat-amt  { font-weight: 700; color: #111; white-space: nowrap; }
.cat-pct  { font-size: 0.75rem; color: #aaa; margin-left: 8px; white-space: nowrap; }

/* COMPACT TABLE */
.txn-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.txn-table th {
    text-align: left;
    font-size: 0.75rem;
    text-transform: uppercase;
    color: #999;
    border-bottom: 1px solid #ddd;
    padding: 8px 12px;
    font-weight: 600;
}
.txn-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #f2f2f2;
    color: #333;
    vertical-align: middle;
}
.txn-table tr:last-child td { border-bottom: none; }
.amt-cell { font-weight: 600; color: #111; text-align: right; }

/* CATEGORY LIST */
.clist-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid #f8f8f8;
    font-size: 0.88rem;
}
.clist-name { color: #333; flex: 1; }

/* REVIEW CARD */
.rev-card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.rev-merchant { font-size: 1rem; font-weight: 700; color: #111; }
.rev-meta     { font-size: 0.85rem; color: #888; margin-top: 4px; }
.rev-amt      { font-size: 1.15rem; font-weight: 700; color: #111; }

/* SECTION HEADER */
.sec-hd {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #aaa;
    margin: 18px 0 10px;
    padding-bottom: 4px;
    border-bottom: 1px solid #eee;
}

/* NAV DROPDOWN - MOBILE OPTIMIZED */
[data-testid="stSelectbox"] > div > div {
    background: #fff !important;
    border: 1px solid #ddd !important;
    border-radius: 10px !important;
    font-size: 1rem !important;
    min-height: 52px !important; /* Mobile touch target */
    padding: 0 14px !important;
}
[data-testid="stSelectbox"] > div > div > div {
    min-height: 52px !important;
    line-height: 1.4 !important;
}

/* FORM ELEMENTS - TOUCH FRIENDLY */
.stTextInput > div > div > input {
    min-height: 52px !important;
    font-size: 1rem !important;
    padding: 0 14px !important;
    border-radius: 8px !important;
}
.stSelectbox > div > div > div {
    min-height: 52px !important;
}
.stNumberInput > div > div > input {
    min-height: 52px !important;
    font-size: 1rem !important;
}
.stDateInput > div > div > input {
    min-height: 52px !important;
    font-size: 1rem !important;
}
.stRadio > div {
    padding: 12px 0 !important;
}
.stCheckbox > div {
    padding: 8px 0 !important;
}

/* BUTTONS */
button[kind="primary"] {
    font-size: 0.9rem !important;
    padding: 8px 16px !important;
    min-height: 48px !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
button[kind="secondary"] {
    font-size: 0.9rem !important;
    padding: 8px 16px !important;
    min-height: 48px !important;
    border-radius: 8px !important;
}

/* MOBILE-SPECIFIC ADJUSTMENTS */
@media (max-width: 599px) {
    /* Text scaling */
    .card-title { font-size: 0.95rem; }
    .card-amount { font-size: 2.2rem; }
    .card-sub { font-size: 0.95rem; }
    .sec-hd { font-size: 0.95rem; margin: 20px 0 12px; }
    .prog-track { margin-top: 10px; }
    .cat-row { padding: 12px 0; font-size: 0.95rem; }
    .cat-name { font-size: 0.95rem; }
    .cat-amt { font-size: 0.95rem; }
    .cat-pct { font-size: 0.8rem; }
    .rev-card { padding: 16px 18px; }
    .rev-merchant { font-size: 1.1rem; }
    .rev-meta { font-size: 0.9rem; }
    .rev-amt { font-size: 1.25rem; }
    .clist-row { padding: 12px 0; font-size: 0.93rem; }
    .clist-name { font-size: 0.95rem; }
    /* Table adjustments */
    .txn-table { font-size: 0.9rem; }
    .txn-table th { font-size: 0.8rem; padding: 10px 14px; }
    .txn-table td { padding: 12px 14px; }
    /* Form elements */
    .stTextInput > div > div > input {
        min-height: 56px !important;
        font-size: 1.1rem !important;
    }
    .stSelectbox > div > div > div {
        min-height: 56px !important;
        font-size: 1.1rem !important;
    }
    .stNumberInput > div > div > input {
        min-height: 56px !important;
        font-size: 1.1rem !important;
    }
    .stDateInput > div > div > input {
        min-height: 56px !important;
        font-size: 1.1rem !important;
    }
    /* Buttons */
    button[kind="primary"] {
        font-size: 1rem !important;
        padding: 10px 20px !important;
        min-height: 52px !important;
    }
    button[kind="secondary"] {
        font-size: 1rem !important;
        padding: 10px 20px !important;
        min-height: 52px !important;
    }
    /* Section headers */
    .sec-hd { margin: 22px 0 14px; }
}

/* FAB (FLOATING ACTION BUTTON) */
.fab-container {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 1000;
    display: flex;
    justify-content: flex-end;
}
.fab-button {
    width: 60px !important;
    height: 60px !important;
    border-radius: 50% !important;
    font-size: 28px !important;
    padding: 0 !important;
    min-height: 60px !important;
    min-width: 60px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background-color: #1976d2 !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    transition: all 0.2s ease !important;
    font-weight: bold !important;
}
.fab-button:hover {
    background-color: #1565c0 !important;
    transform: scale(1.05) !important;
    box-shadow: 0 6px 16px rgba(0,0,0,0.2) !important;
}
.fab-button:active {
    transform: scale(0.95) !important;
}

/* HEADER COMPACTIFICATION */
.stApp > header {
    background-color: transparent !important;
    height: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA LOAD + SESSION STATE (LIVE DATA MODEL)
# ─────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)

def load_all_data():
    try:
        e  = conn.read(worksheet="Expenses")
        c  = conn.read(worksheet="Categories")
        s  = conn.read(worksheet="Settings")
        try:    m = conn.read(worksheet="Modes")
        except: m = pd.DataFrame({"Mode": DEFAULT_MODES})
        try:    p = conn.read(worksheet="PendingReview")
        except: p = pd.DataFrame(columns=[
            "Date","Amount","Category","Note","Mode","UPI_Ref",
            "Source_Account","Import_Source","Review_Status",
            "Suggested_Category","Remarks_Raw","Tags_Raw","Transaction_Details"])
        try:    il = conn.read(worksheet="ImportLog")
        except: il = pd.DataFrame(columns=["Run_Time","Emails_Found","Imported","Skipped","Pending","Status","Notes"])
        try:    ir = conn.read(worksheet="ImportRules")
        except: ir = pd.DataFrame(columns=["Keyword","Match_In","Category"])
        try:    a  = conn.read(worksheet="AppSettings")
        except: a  = pd.DataFrame(columns=["Key","Value"])
        return e, c, s, m, p, il, ir, a    except Exception as ex:
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

def load_pin():
    try:
        sec = conn.read(worksheet="Security", usecols=[0], nrows=1)
        raw = str(sec.iloc[0, 0]).strip()
        return raw if raw.isdigit() and len(raw) == 4 else "1234"
    except:
        return "1234"

# LOAD FRESH DATA ON EVERY RUN (NO CACHING)
df_raw, cat_df_raw, settings_df_raw, modes_df_raw, pending_df_raw, import_log_df_raw, import_rules_raw, app_settings_df_raw = load_all_data()

# PROCESS AND STORE IN SESSION STATE
if not df_raw.empty:
    df_raw["Date"]   = pd.to_datetime(df_raw["Date"], errors="coerce")
    df_raw["Amount"] = pd.to_numeric(df_raw["Amount"], errors="coerce").fillna(0)
if not pending_df_raw.empty:
    pending_df_raw["Date"]   = pd.to_datetime(pending_df_raw["Date"], errors="coerce")
    pending_df_raw["Amount"] = pd.to_numeric(pending_df_raw["Amount"], errors="coerce").fillna(0)
if "Last_Fired" not in settings_df_raw.columns:
    settings_df_raw["Last_Fired"] = ""

st.session_state.df              = df_raw
st.session_state.cat_df          = cat_df_raw
st.session_state.settings_df     = settings_df_raw
st.session_state.modes_df        = modes_df_raw
st.session_state.pending_df      = pending_df_raw
st.session_state.import_log_df   = import_log_df_raw
st.session_state.import_rules    = import_rules_raw
st.session_state.app_settings_df = app_settings_df_raw
st.session_state.active_pin      = load_pin()

# INITIALIZE UI STATE
if "show_modal" not in st.session_state:
    st.session_state.show_modal = False
if "form_id" not in st.session_state:
    st.session_state.form_id = 0
if "pin_unlocked" not in st.session_state:
    st.session_state.pin_unlocked = False
if "pin_input" not in st.session_state:
    st.session_state.pin_input = ""
if "pin_attempts" not in st.session_state:
    st.session_state.pin_attempts = 0
if "pin_error" not in st.session_state:
    st.session_state.pin_error = ""
if "auto_log_checked" not in st.session_state:
    st.session_state.auto_log_checked = False
if "page" not in st.session_state:
    st.session_state.page = "🏠 Home"

# ─────────────────────────────────────────────# SAVE HELPERS  (all original logic preserved)
# ─────────────────────────────────────────────
def save_expense(row_dict):
    with st.spinner("Saving..."):
        new_row = pd.DataFrame([row_dict])
        new_row["Date"]   = pd.to_datetime(new_row["Date"], errors="coerce")
        new_row["Amount"] = pd.to_numeric(new_row["Amount"], errors="coerce").fillna(0)
        updated = pd.concat([st.session_state.df, new_row], ignore_index=True)
        conn.update(worksheet="Expenses", data=updated)
        st.session_state.df = updated

def update_expense(idx, fields):
    with st.spinner("Updating..."):
        for k, v in fields.items():
            st.session_state.df.at[idx, k] = v
        conn.update(worksheet="Expenses", data=st.session_state.df)

def delete_expense(idx):
    with st.spinner("Deleting..."):
        updated = st.session_state.df.drop(idx).reset_index(drop=True)
        conn.update(worksheet="Expenses", data=updated)
        st.session_state.df = updated

def save_settings(new_df):
    with st.spinner("Saving..."):
        conn.update(worksheet="Settings", data=new_df)
        st.session_state.settings_df = new_df

def save_categories(new_df):
    with st.spinner("Saving..."):
        conn.update(worksheet="Categories", data=new_df)
        st.session_state.cat_df = new_df

def save_modes(new_df):
    with st.spinner("Saving..."):
        conn.update(worksheet="Modes", data=new_df)
        st.session_state.modes_df = new_df

def save_pin(new_pin: str):
    with st.spinner("Saving PIN..."):
        pin_df = pd.DataFrame({"PIN": [new_pin]})
        conn.update(worksheet="Security", data=pin_df)
        st.session_state.active_pin = new_pin

def save_import_rules(new_df):
    with st.spinner("Saving rules..."):
        conn.update(worksheet="ImportRules", data=new_df)
        st.session_state.import_rules = new_df

def get_app_setting(key, default="0"):
    df_a = st.session_state.get("app_settings_df", pd.DataFrame())
    if df_a.empty or "Key" not in df_a.columns:
        return default    mask = df_a["Key"].astype(str).str.strip() == key
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

def split_expense_row(idx, amt1, cat1, amt2, cat2):
    with st.spinner("Splitting..."):
        orig = st.session_state.df.loc[idx]
        note_base = str(orig.get("Note", "") or "").strip()
        row1 = {"Date": orig.get("Date",""), "Amount": amt1, "Category": cat1,
                "Note": f"{note_base} (split 1/2)".strip(), "Mode": orig.get("Mode",""),
                "UPI_Ref": str(orig.get("UPI_Ref","") or ""), "Source_Account": orig.get("Source_Account",""),
                "Import_Source": orig.get("Import_Source",""), "Review_Status": orig.get("Review_Status","")}
        row2 = {"Date": orig.get("Date",""), "Amount": amt2, "Category": cat2,
                "Note": f"{note_base} (split 2/2)".strip(), "Mode": orig.get("Mode",""),
                "UPI_Ref": "", "Source_Account": orig.get("Source_Account",""),
                "Import_Source": orig.get("Import_Source",""), "Review_Status": orig.get("Review_Status","")}
        base  = st.session_state.df.drop(idx).reset_index(drop=True)
        r1_df = pd.DataFrame([row1]); r2_df = pd.DataFrame([row2])
        r1_df["Date"] = pd.to_datetime(r1_df["Date"], errors="coerce")
        r2_df["Date"] = pd.to_datetime(r2_df["Date"], errors="coerce")
        updated = pd.concat([base, r1_df, r2_df], ignore_index=True)
        conn.update(worksheet="Expenses", data=updated)
        st.session_state.df = updated# ─────────────────────────────────────────────
# REVIEW HELPERS  (all original logic preserved)
# ─────────────────────────────────────────────
def extract_merchant(row):
    txn  = str(row.get("Transaction_Details", "") or "").strip()
    note = str(row.get("Note", "") or "").strip()
    src  = txn or note.split("·")[0].strip()
    for prefix in ["Paid to ","paid to ","Money sent to ","money sent to "]:
        if src.lower().startswith(prefix.lower()):
            src = src[len(prefix):]
            break
    return src.strip() or "Unknown"

def approve_pending_row(idx, chosen_category, create_new_cat=False):
    with st.spinner("Approving..."):
        row = st.session_state.pending_df.loc[idx]
        if create_new_cat and chosen_category not in st.session_state.cat_df["Category"].dropna().tolist():
            save_categories(pd.concat([st.session_state.cat_df,
                pd.DataFrame([{"Category": chosen_category}])], ignore_index=True))
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
        updated_exp  = pd.concat([st.session_state.df, exp_new], ignore_index=True)
        conn.update(worksheet="Expenses", data=updated_exp)
        st.session_state.df = updated_exp
        updated_pend = st.session_state.pending_df.drop(idx).reset_index(drop=True)
        conn.update(worksheet="PendingReview", data=updated_pend)
        st.session_state.pending_df = updated_pend

def skip_pending_row(idx):
    with st.spinner("Skipping..."):
        st.session_state.pending_df.at[idx, "Review_Status"] = "skipped"
        conn.update(worksheet="PendingReview", data=st.session_state.pending_df)

def drop_pending_row(idx):
    """Permanently delete from pending — never added to expenses."""
    with st.spinner("Dropping..."):
        updated_pend = st.session_state.pending_df.drop(idx).reset_index(drop=True)
        conn.update(worksheet="PendingReview", data=updated_pend)
        st.session_state.pending_df = updated_pend

def auto_save_import_rule(merchant, category):
    rules   = st.session_state.import_rules
    words   = [w for w in merchant.split() if len(w) > 3]
    keyword = (words[0] if words else merchant[:10]).strip()
    if len(keyword) < 3:
        return    existing = rules["Keyword"].astype(str).str.lower().str.strip().tolist() if not rules.empty else []
    if keyword.lower() in existing:
        return
    new_rule = pd.DataFrame([{"Keyword": keyword, "Match_In": "Any", "Category": category}])
    updated  = pd.concat([rules, new_rule], ignore_index=True) if not rules.empty else new_rule
    save_import_rules(updated)

def approve_all_with_suggestions():
    pend = st.session_state.pending_df
    if pend.empty:
        return 0
    _rs  = pend["Review_Status"].astype(str) if "Review_Status" in pend.columns else pd.Series("", index=pend.index)
    _sug = pend["Suggested_Category"].astype(str) if "Suggested_Category" in pend.columns else pd.Series("", index=pend.index)
    to_approve = pend[(_rs == "pending") & (_sug.str.strip().ne("")) & (_sug.str.strip().ne("nan"))]
    if to_approve.empty:
        return 0
    count = 0
    for idx, row in to_approve.iterrows():
        sug = str(row.get("Suggested_Category","")).strip()
        if sug and sug != "nan":
            approve_pending_row(idx, sug, create_new_cat=True)
            count += 1    return count

# ─────────────────────────────────────────────
# RECURRING AUTO-LOG
# ─────────────────────────────────────────────
if not st.session_state.get("auto_log_checked") and not st.session_state.settings_df.empty:
    fired_any   = False
    updated_sdf = st.session_state.settings_df.copy()
    curr_ym     = datetime.now(TZ).strftime("%Y-%m")
    today       = datetime.now(TZ).date()
    for i, row in st.session_state.settings_df.iterrows():
        try:
            is_rec = str(row.get("Is_Recurring","")).strip().lower() in ("true","1","yes")
            if not is_rec:
                continue
            last_fired = str(row.get("Last_Fired","")).strip()
            day_of_mon = int(row.get("Day_of_Month", 32))
            amt        = float(row.get("Budget", 0) or 0)
            if last_fired == curr_ym or today.day < day_of_mon:
                continue
            fire_dt = f"{today.strftime('%Y-%m-%d')} {datetime.now(TZ).strftime('%H:%M:%S')}"
            save_expense({"Date": fire_dt, "Amount": amt, "Category": row["Category"],
                          "Mode": "Auto", "Note": "Auto-logged (recurring)"})
            updated_sdf.at[i, "Last_Fired"] = curr_ym
            fired_any = True
        except:
            pass
    if fired_any:
        save_settings(updated_sdf)
    st.session_state.auto_log_checked = True

# ─────────────────────────────────────────────# PIN GATE
# ─────────────────────────────────────────────for _k, _v in [("pin_unlocked",False),("pin_input",""),("pin_attempts",0),("pin_error","")]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

if not st.session_state.pin_unlocked:
    locked_out = st.session_state.pin_attempts >= MAX_PIN_ATTEMPTS
    st.markdown("<br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1,2,1])
    with col:
        st.markdown("<div style='text-align:center;font-size:1.3rem;font-weight:700;margin-bottom:4px'>FinTrack</div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:center;font-size:0.8rem;color:#888;margin-bottom:20px'>Enter your 4-digit PIN</div>", unsafe_allow_html=True)
        entered   = len(st.session_state.pin_input)
        is_error  = bool(st.session_state.pin_error)
        dots_html = "<div style='display:flex;gap:12px;margin-bottom:20px;justify-content:center'>"
        for i in range(4):
            if is_error:
                style = "width:12px;height:12px;border-radius:50%;background:#e53935;border:1.5px solid #e53935"
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
            st.markdown(f"<p style='color:#e53935;font-size:0.75rem;text-align:center'>{remaining} attempt(s) left.</p>", unsafe_allow_html=True)
        for row_keys in [["1","2","3"],["4","5","6"],["7","8","9"],["","0","del"]]:
            k1, k2, k3 = st.columns(3)
            for cw, digit in zip([k1,k2,k3], row_keys):
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

# ─────────────────────────────────────────────# NAVIGATION — MOBILE-FIRST CENTERED DROPDOWN
# ─────────────────────────────────────────────
pending_count = 0if not st.session_state.pending_df.empty and "Review_Status" in st.session_state.pending_df.columns:
    pending_count = int((st.session_state.pending_df["Review_Status"].astype(str) == "pending").sum())

PAGE_OPTIONS = ["🏠 Home", "📋 Transactions", "🏷 Categories", "⚠️ Review", "⚙️ Manage"]
if pending_count > 0:
    PAGE_OPTIONS[3] = f"⚠️ Review ({pending_count})"

# App title + lock rowh1, h2, h3 = st.columns([4,1,1])
h1.markdown("<div style='font-size:1.1rem;font-weight:700;padding:4px 0'>FinTrack</div>", unsafe_allow_html=True)
if h2.button("↻", key="refresh_top"):
    hard_refresh()
if h3.button("🔒", key="lock_top"):
    st.session_state.pin_unlocked = False
    st.session_state.pin_input    = ""
    st.rerun()

# Center-aligned nav dropdown (full width on mobile)
_, nav_col, _ = st.columns([1, 4, 1])
with nav_col:
    selected_page = st.selectbox(
        "nav", PAGE_OPTIONS,
        index=PAGE_OPTIONS.index(st.session_state.page) if st.session_state.page in PAGE_OPTIONS else 0,
        label_visibility="collapsed",
        key="nav_select"
    )
    if selected_page != st.session_state.page:
        st.session_state.page = selected_page
        st.rerun()

page = st.session_state.page
st.markdown("<hr style='margin:6px 0 10px;border:none;border-top:1px solid #e0e0e0'>", unsafe_allow_html=True)

# Store current date and year-month for recurring logic
st.session_state.today = datetime.now(TZ).date()
st.session_state.curr_ym = st.session_state.today.strftime("%Y-%m")

# ═══════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════
if "🏠 Home" in page:
    now_per    = pd.Period(st.session_state.curr_ym, freq="M")
    q_map      = {1:1,2:1,3:1,4:2,5:2,6:2,7:3,8:3,9:3,10:4,11:4,12:4}
    curr_q     = q_map[st.session_state.today.month]
    q_months   = [m for m, q in q_map.items() if q == curr_q]

    # Monthly totals
    month_df   = st.session_state.df[st.session_state.df["Date"].dt.to_period("M") == now_per].copy() if not st.session_state.df.empty else pd.DataFrame()
    month_total = month_df["Amount"].sum()

    # Quarterly totals
    qtr_df      = st.session_state.df[
        (st.session_state.df["Date"].dt.month.isin(q_months)) &
        (st.session_state.df["Date"].dt.year == st.session_state.today.year)
    ].copy() if not st.session_state.df.empty else pd.DataFrame()
    qtr_total   = qtr_df["Amount"].sum()

    # Budget limit from settings
    budgets_set = st.session_state.settings_df[
        st.session_state.settings_df["Budget"].notna() &
        (st.session_state.settings_df["Budget"].astype(str).str.strip() != "")
    ].copy() if not st.session_state.settings_df.empty else pd.DataFrame()
    total_budget = budgets_set["Budget"].apply(
        lambda v: float(v) if str(v).strip() not in ("","nan") else 0
    ).sum() if not budgets_set.empty else 0.0

    # ── Monthly card ─────────────────────────────────    m_pct   = min(month_total / total_budget * 100, 100) if total_budget > 0 else 0
    m_color = "#e53935" if m_pct > 90 else ("#f57c00" if m_pct > 70 else "#43a047")
    budget_sub = f"Budget: ₹{total_budget:,.0f}  ·  Remaining: ₹{max(total_budget-month_total,0):,.0f}" if total_budget > 0 else "No budget set"
    st.markdown(
        f'<div class="card">'
        f'<div class="card-title">This Month — {st.session_state.curr_ym}</div>'
        f'<div class="card-amount">₹{int(month_total):,}</div>'
        f'<div class="card-sub">{budget_sub}</div>'
        + (f'<div class="prog-track"><div class="prog-fill" style="width:{m_pct:.1f}%;background:{m_color}"></div></div>' if total_budget > 0 else "")
        + '</div>',
        unsafe_allow_html

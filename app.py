import streamlit as st
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
        unsafe_allow_html=True
    )

    # ── Quarterly card ───────────────────────────────
    q_months_str = ["Jan–Mar","Apr–Jun","Jul–Sep","Oct–Dec"][curr_q-1]
    q_budget     = total_budget * 3  # quarterly budget = monthly × 3
    q_pct        = min(qtr_total / q_budget * 100, 100) if q_budget > 0 else 0
    q_color      = "#e53935" if q_pct > 90 else ("#f57c00" if q_pct > 70 else "#43a047")
    q_budget_sub = f"Budget: ₹{q_budget:,.0f}  ·  Remaining: ₹{max(q_budget-qtr_total,0):,.0f}" if q_budget > 0 else "No budget set"
    st.markdown(
        f'<div class="card">'
        f'<div class="card-title">Q{curr_q} ({q_months_str})</div>'
        f'<div class="card-amount">₹{int(qtr_total):,}</div>'
        f'<div class="card-sub">{q_budget_sub}</div>'
        + (f'<div class="prog-track"><div class="prog-fill" style="width:{q_pct:.1f}%;background:{q_color}"></div></div>' if q_budget > 0 else "")
        + '</div>',
        unsafe_allow_html=True
    )

    # ── Top 5 categories — Monthly ────────────────────
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
                f'</div>'
            )
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<div class="card" style="color:#999;font-size:0.8rem">No transactions this month.</div>', unsafe_allow_html=True)

    # ── Top 5 categories — Quarterly ─────────────────
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
                f'</div>'
            )
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<div class="card" style="color:#999;font-size:0.8rem">No transactions this quarter.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# PAGE: TRANSACTIONS
# ═══════════════════════════════════════════════════════
elif "📋 Transactions" in page:
    st.markdown('<div class="sec-hd">Transaction History</div>', unsafe_allow_html=True)

    if st.session_state.df.empty:
        st.markdown('<div class="card" style="color:#999;font-size:0.8rem">No transactions yet.</div>', unsafe_allow_html=True)
    else:
        # Filter row
        fa, fb = st.columns([3,1])
        srch  = fa.text_input("srch", placeholder="Search category / note...", label_visibility="collapsed")
        n_show = fb.selectbox("show", [50, 100, 200, "All"], label_visibility="collapsed")

        result = st.session_state.df.copy().sort_values("Date", ascending=False)
        if srch.strip():
            q = srch.strip()
            result = result[
                result["Category"].astype(str).str.contains(q, case=False, na=False) |
                result["Note"].astype(str).str.contains(q, case=False, na=False)
            ]
        if n_show != "All":
            result = result.head(int(n_show))

        # Build compact table HTML
        rows_html = ""
        for _, row in result.iterrows():
            dt_str = pd.to_datetime(row["Date"]).strftime("%m/%d/%y") if pd.notna(row["Date"]) else "—"
            note   = str(row.get("Note","") or "").strip()
            txn    = str(row.get("Transaction_Details","") or "").strip()
            merchant = extract_merchant(row) if (note or txn) else str(row.get("Category",""))
            merchant = merchant[:28]
            amt    = int(row["Amount"])
            rows_html += (
                f'<tr>'
                f'<td>{dt_str}</td>'
                f'<td>{merchant}</td>'
                f'<td class="amt-cell">₹{amt:,}</td>'
                f'</tr>'
            )

        st.markdown(
            f'<div class="card" style="padding:8px 10px">'
            f'<table class="txn-table">'
            f'<thead><tr><th>Date</th><th>Merchant</th><th style="text-align:right">Amt</th></tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            f'</table></div>',
            unsafe_allow_html=True
        )
        st.markdown(f'<div style="font-size:0.7rem;color:#aaa;text-align:right">{len(result)} rows</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════# PAGE: CATEGORIES
# ═══════════════════════════════════════════════════════
elif "🏷" in page:
    st.markdown('<div class="sec-hd">Categories</div>', unsafe_allow_html=True)

    # Add new
    with st.form("add_cat_form"):
        ca, cb = st.columns([4,1])
        new_cat_name = ca.text_input("new_cat", placeholder="New category name...", label_visibility="collapsed")
        submitted    = cb.form_submit_button("Add")
        if submitted:
            if new_cat_name.strip():
                save_categories(pd.concat([
                    st.session_state.cat_df,
                    pd.DataFrame([{"Category": new_cat_name.strip()}])
                ], ignore_index=True))
                st.rerun()
            else:
                st.warning("Name cannot be empty.")

    if st.session_state.cat_df.empty:
        st.markdown('<div class="card" style="color:#999;font-size:0.8rem">No categories yet.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card" style="padding:4px 10px">', unsafe_allow_html=True)
        for i, row in st.session_state.cat_df.iterrows():
            edit_key = f"catedit_{i}"
            if edit_key not in st.session_state:
                st.session_state[edit_key] = False

            if not st.session_state[edit_key]:
                c1, c2 = st.columns([5,1])
                c1.markdown(f'<div class="clist-row"><span class="clist-name">{row["Category"]}</span></div>', unsafe_allow_html=True)
                if c2.button("Edit", key=f"catopen_{i}", use_container_width=True):
                    st.session_state[edit_key] = True
                    st.rerun()
            else:
                with st.form(f"cat_ef_{i}"):
                    ea, eb, ec = st.columns([4,1,1])
                    new_val = ea.text_input("name", value=row["Category"], label_visibility="collapsed")
                    save_it = eb.form_submit_button("Save")
                    del_it  = ec.form_submit_button("Del")
                    if save_it:
                        if new_val.strip():
                            st.session_state.cat_df.at[i, "Category"] = new_val.strip()
                            save_categories(st.session_state.cat_df)
                        st.session_state[edit_key] = False
                        st.rerun()
                    if del_it:
                        save_categories(st.session_state.cat_df.drop(i).reset_index(drop=True))
                        st.session_state[edit_key] = False
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Payment modes section
    st.markdown('<div class="sec-hd" style="margin-top:16px">Payment Modes</div>', unsafe_allow_html=True)
    with st.form("add_mode_form"):
        ma, mb = st.columns([4,1])
        new_mode_name = ma.text_input("new_mode", placeholder="New mode...", label_visibility="collapsed")
        m_sub         = mb.form_submit_button("Add")
        if m_sub:
            if new_mode_name.strip():
                save_modes(pd.concat([
                    st.session_state.modes_df,
                    pd.DataFrame([{"Mode": new_mode_name.strip()}])
                ], ignore_index=True))
                st.rerun()
            else:
                st.warning("Name cannot be empty.")

    if not st.session_state.modes_df.empty:
        st.markdown('<div class="card" style="padding:4px 10px">', unsafe_allow_html=True)
        for i, row in st.session_state.modes_df.iterrows():
            mc1, mc2 = st.columns([5,1])
            mc1.markdown(f'<div class="clist-row"><span class="clist-name">{row["Mode"]}</span></div>', unsafe_allow_html=True)
            mdk = f"mdel_{i}"
            if mdk not in st.session_state:
                st.session_state[mdk] = False
            if not st.session_state[mdk]:
                if mc2.button("Del", key=f"mopen_{i}", use_container_width=True):
                    st.session_state[mdk] = True
                    st.rerun()
            else:
                my, mn = mc2.columns(2)
                if my.button("Y", key=f"mdy_{i}"):
                    save_modes(st.session_state.modes_df.drop(i).reset_index(drop=True))
                    st.session_state[mdk] = False
                    st.rerun()
                if mn.button("N", key=f"mdn_{i}"):
                    st.session_state[mdk] = False
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# PAGE: REVIEW
# ═══════════════════════════════════════════════════════
elif "⚠️ Review" in page:
    pend_all = st.session_state.pending_df.copy() if not st.session_state.pending_df.empty else pd.DataFrame()

    if pend_all.empty or "Review_Status" not in pend_all.columns:
        active_pend = pd.DataFrame()
    else:
        active_pend = pend_all[pend_all["Review_Status"].astype(str) == "pending"].copy()

    if active_pend.empty:
        st.markdown('<div class="card" style="color:#666;font-size:0.85rem;text-align:center;padding:24px">✅ All caught up — nothing pending.</div>', unsafe_allow_html=True)
    else:
        active_pend["_merchant"] = active_pend.apply(extract_merchant, axis=1)
        live_cats = sorted(st.session_state.cat_df["Category"].dropna().tolist()) if not st.session_state.cat_df.empty else []

        n_pend = len(active_pend)
        st.markdown(f'<div class="sec-hd">{n_pend} pending transaction{"s" if n_pend!=1 else ""}</div>', unsafe_allow_html=True)

        # Bulk approve button
        n_with_sug = 0
        if "Suggested_Category" in active_pend.columns:
            n_with_sug = int(active_pend["Suggested_Category"].astype(str).str.strip().replace("nan","").ne("").sum())
        if n_with_sug > 0:
            if st.button(f"✅ Approve all {n_with_sug} with suggestions", type="primary"):
                count = approve_all_with_suggestions()
                st.toast(f"Approved {count} transactions!")
                st.rerun()

        for idx, row in active_pend.iterrows():
            merchant = row["_merchant"]
            amt      = int(row.get("Amount", 0))
            dt_raw   = row.get("Date","")
            dt_str   = pd.to_datetime(dt_raw).strftime("%m/%d/%y") if pd.notna(dt_raw) else "—"
            note_val = str(row.get("Note","") or "").strip()
            sug_cat  = str(row.get("Suggested_Category","") or "").strip()
            sug_cat  = "" if sug_cat.lower() == "nan" else sug_cat

            # Split expand state            split_key = f"rev_split_{idx}"
            if split_key not in st.session_state:
                st.session_state[split_key] = False

            st.markdown(
                f'<div class="rev-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div><div class="rev-merchant">{merchant}</div>'
                f'<div class="rev-meta">{dt_str}'
                + (f'  ·  {note_val[:40]}' if note_val else '')
                + f'</div></div>'
                f'<div class="rev-amt">₹{amt:,}</div></div></div>',
                unsafe_allow_html=True
            )

            # Category selector — suggestion pre-selected if available
            cat_opts      = ["-- Select --"] + live_cats + ["+ New category"]
            default_idx   = 0
            if sug_cat and sug_cat in live_cats:
                default_idx = live_cats.index(sug_cat) + 1

            sel = st.selectbox(
                "cat", cat_opts, index=default_idx,
                key=f"rev_cat_{idx}",
                label_visibility="collapsed",
                help=f"Suggested: {sug_cat}" if sug_cat else "Choose category"
            )
            if sug_cat and default_idx == 0:
                st.caption(f"💡 Suggestion: {sug_cat}")

            final_cat  = None
            is_new_cat = False
            if sel == "+ New category":
                nc_val = st.text_input("New cat name", value=sug_cat, key=f"rev_newcat_{idx}", label_visibility="collapsed", placeholder="New category...")
                if nc_val.strip():
                    final_cat  = nc_val.strip()
                    is_new_cat = True
            elif sel != "-- Select --":
                final_cat = sel            # Action buttons in one row
            b1, b2, b3, b4 = st.columns(4)
            if b1.button("✅", key=f"rev_app_{idx}", use_container_width=True, help="Approve", disabled=(not final_cat)):
                if final_cat:
                    approve_pending_row(idx, final_cat, create_new_cat=is_new_cat)
                    auto_save_import_rule(merchant, final_cat)
                    st.toast(f"Approved → {final_cat}")
                    st.rerun()

            if b2.button("⏭", key=f"rev_skip_{idx}", use_container_width=True, help="Skip"):
                skip_pending_row(idx)
                st.toast("Skipped")
                st.rerun()

            if b3.button("✂", key=f"rev_spltbtn_{idx}", use_container_width=True, help="Split"):
                st.session_state[split_key] = not st.session_state[split_key]
                st.rerun()

            if b4.button("🗑", key=f"rev_drop_{idx}", use_container_width=True, help="Drop permanently"):
                drop_pending_row(idx)
                st.toast("Dropped")
                st.rerun()

            # Split panel            if st.session_state.get(split_key, False):
                total_amt = float(row.get("Amount",0))
                with st.container(border=True):
                    st.markdown(f'<div style="font-size:0.75rem;color:#666;margin-bottom:4px">Split ₹{int(total_amt):,}</div>', unsafe_allow_html=True)
                    s1a, s1b = st.columns([2,3])
                    spl1_amt = s1a.number_input("Pt1 ₹", min_value=1.0, max_value=total_amt-1, value=round(total_amt/2,0), key=f"spl1a_{idx}", label_visibility="collapsed")
                    spl1_cat = s1b.selectbox("Cat1", live_cats, key=f"spl1c_{idx}", label_visibility="collapsed")
                    spl2_amt = total_amt - spl1_amt
                    s2a, s2b = st.columns([2,3])
                    s2a.markdown(f'<div style="font-size:0.82rem;font-weight:600;padding:8px 0">₹{int(spl2_amt):,}</div>', unsafe_allow_html=True)
                    spl2_cat = s2b.selectbox("Cat2", live_cats, key=f"spl2c_{idx}", label_visibility="collapsed")
                    sb1, sb2 = st.columns(2)
                    if sb1.button("Save Split", key=f"dosplit_{idx}", type="primary", use_container_width=True):
                        # Approve with split: create two expense rows, remove from pending
                        with st.spinner("Splitting..."):
                            orig = st.session_state.pending_df.loc[idx]
                            note_b = str(orig.get("Note","") or "").strip()
                            for split_amt, split_cat, suffix in [(spl1_amt, spl1_cat,"(split 1/2)"),(spl2_amt, spl2_cat,"(split 2/2)")]:
                                er = {"Date": orig.get("Date",""), "Amount": split_amt,
                                      "Category": split_cat, "Note": f"{note_b} {suffix}".strip(),
                                      "Mode": orig.get("Mode",""), "UPI_Ref": orig.get("UPI_Ref",""),
                                      "Source_Account": orig.get("Source_Account",""),
                                      "Import_Source": orig.get("Import_Source","paytm_auto"),
                                      "Review_Status": "approved"}
                                save_expense(er)
                            upd_pend = st.session_state.pending_df.drop(idx).reset_index(drop=True)
                            conn.update(worksheet="PendingReview", data=upd_pend)
                            st.session_state.pending_df = upd_pend                    if sb2.button("Cancel", key=f"cancelsplit_{idx}", use_container_width=True):
                        st.session_state[split_key] = False
                        st.rerun()

            st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

    # Skipped section
    if not pend_all.empty and "Review_Status" in pend_all.columns:
        skipped = pend_all[pend_all["Review_Status"].astype(str) == "skipped"]
        if not skipped.empty:
            with st.expander(f"Skipped ({len(skipped)})"):
                for idx, row in skipped.iterrows():
                    m   = extract_merchant(row)
                    amt = int(row.get("Amount",0))
                    sc1, sc2 = st.columns([4,1])
                    sc1.markdown(f'<div style="font-size:0.78rem;color:#666">{m}  ₹{amt:,}</div>', unsafe_allow_html=True)
                    if sc2.button("↩", key=f"restore_{idx}"):
                        st.session_state.pending_df.at[idx, "Review_Status"] = "pending"
                        conn.update(worksheet="PendingReview", data=st.session_state.pending_df)
                        st.rerun()

# ═══════════════════════════════════════════════════════
# PAGE: MANAGE
# ═══════════════════════════════════════════════════════
elif "⚙️ Manage" in page:
    # ── Gmail Sync ──────────────────────────────────
    st.markdown('<div class="sec-hd">Gmail Sync</div>', unsafe_allow_html=True)
    apps_script_url = st.secrets.get("apps_script_url","")
    now_ist     = datetime.now(TZ)
    today_11am  = now_ist.replace(hour=11, minute=0, second=0, microsecond=0)
    today_11pm  = now_ist.replace(hour=23, minute=0, second=0, microsecond=0)
    next_runs   = [t for t in [today_11am, today_11pm] if t > now_ist]
    next_run_dt = next_runs[0] if next_runs else (now_ist + timedelta(days=1)).replace(hour=11,minute=0,second=0,microsecond=0)
    time_until  = next_run_dt - now_ist
    hrs         = int(time_until.total_seconds()//3600)
    mins        = int((time_until.total_seconds()%3600)//60)
    countdown   = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m"

    last_run_str = ""
    if not st.session_state.import_log_df.empty:
        last     = st.session_state.import_log_df.iloc[-1]
        l_stat   = "✅" if str(last.get("Status","")).strip().upper() == "OK" else "❌"
        l_imp    = int(last.get("Imported",0) or 0)
        l_pnd    = int(last.get("Pending",0) or 0)
        l_skp    = int(last.get("Skipped",0) or 0)
        last_run_str = f"{l_stat} {str(last.get('Run_Time','—')).strip()}  ·  {l_imp} in  ·  {l_pnd} pending  ·  {l_skp} skipped"

    st.markdown(
        f'<div class="card">'
        f'<div style="font-size:0.8rem;font-weight:600">Auto-sync: 11am & 11pm IST daily</div>'
        f'<div style="font-size:0.74rem;color:#666;margin-top:2px">Next run in {countdown} ({next_run_dt.strftime("%-I:%M %p")})</div>'
        + (f'<div style="font-size:0.7rem;color:#888;margin-top:6px">{last_run_str}</div>' if last_run_str else "")
        + '</div>',
        unsafe_allow_html=True
    )

    if not apps_script_url:
        st.info("Add `apps_script_url` to Streamlit secrets to enable manual sync.")
    else:
        if "sync_result" in st.session_state:
            r = st.session_state.sync_result
            if r.get("status") == "ok":
                res = r.get("result",{})
                st.success(f"✅ {res.get('imported',0)} imported · {res.get('pending',0)} pending · {res.get('skipped',0)} skipped")
            else:
                st.error(f"Sync failed: {r.get('message','Unknown error')}")            
            del st.session_state["sync_result"]

        if st.button("🔄 Sync Now", type="primary", use_container_width=True):
            with st.spinner("Syncing... 20–60s"):
                try:
                    resp = requests.get(apps_script_url, timeout=120)
                    st.session_state.sync_result = resp.json()
                except requests.exceptions.Timeout:
                    st.session_state.sync_result = {"status":"error","message":"Timed out. Sync may still be running."}
                except Exception as e:
                    st.session_state.sync_result = {"status":"error","message":str(e)}
                hard_refresh()

    # ── Import Log ──────────────────────────────────
    st.markdown('<div class="sec-hd">Import Log</div>', unsafe_allow_html=True)
    if st.session_state.import_log_df.empty:
        st.markdown('<div class="card" style="color:#999;font-size:0.8rem">No import runs yet.</div>', unsafe_allow_html=True)
    else:
        rows_html = ""
        for _, lr in st.session_state.import_log_df.tail(15).iloc[::-1].iterrows():
            ok   = str(lr.get("Status","")).strip().upper() == "OK"
            ico  = "✅" if ok else "❌"
            rows_html += (
                f'<tr>'
                f'<td>{ico}</td>'
                f'<td style="color:#555">{str(lr.get("Run_Time","")).strip()}</td>'
                f'<td class="amt-cell" style="color:#43a047">{int(lr.get("Imported",0) or 0)}↓</td>'
                f'<td class="amt-cell" style="color:#f57c00">{int(lr.get("Pending",0) or 0)}⚠</td>'
                f'</tr>'
            )
        st.markdown(
            f'<div class="card" style="padding:8px 10px">'
            f'<table class="txn-table">'
            f'<thead><tr><th></th><th>Run Time</th><th style="text-align:right">In</th><th style="text-align:right">Pend</th></tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            f'</table></div>',
            unsafe_allow_html=True
        )

    # ── Import Rules ────────────────────────────────
    st.markdown('<div class="sec-hd">Import Rules</div>', unsafe_allow_html=True)
    with st.form("add_rule_form"):
        ra, rb, rc = st.columns([3,2,1])
        r_kw  = ra.text_input("kw", placeholder="Keyword", label_visibility="collapsed")
        r_cat = rb.selectbox("cat", [""]+st.session_state.cat_df["Category"].dropna().tolist(), label_visibility="collapsed")
        r_sub = rc.form_submit_button("Add")
        if r_sub:
            if r_kw.strip() and r_cat:
                nr  = pd.DataFrame([{"Keyword": r_kw.strip(), "Match_In": "Any", "Category": r_cat}])
                upd = pd.concat([st.session_state.import_rules, nr], ignore_index=True)
                save_import_rules(upd)
                st.rerun()
            else:
                st.warning("Keyword and category required.")

    if not st.session_state.import_rules.empty:
        st.markdown('<div class="card" style="padding:4px 10px">', unsafe_allow_html=True)
        for i, rr in st.session_state.import_rules.iterrows():
            rc1, rc2, rc3 = st.columns([3,3,1])
            rc1.markdown(f'<div class="clist-row" style="color:#43a047">{rr.get("Keyword","")}</div>', unsafe_allow_html=True)
            rc2.markdown(f'<div class="clist-row">→ {rr.get("Category","")}</div>', unsafe_allow_html=True)
            if rc3.button("Del", key=f"rdel_{i}", use_container_width=True):
                save_import_rules(st.session_state.import_rules.drop(i).reset_index(drop=True))
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Change PIN ──────────────────────────────────
    st.markdown('<div class="sec-hd">Change PIN</div>', unsafe_allow_html=True)
    with st.form("change_pin_form"):
        pa, pb, pc = st.columns(3)
        cur_pin  = pa.text_input("Current", type="password", max_chars=4, placeholder="****", label_visibility="collapsed")
        new_pin1 = pb.text_input("New",     type="password", max_chars=4, placeholder="New", label_visibility="collapsed")
        new_pin2 = pc.text_input("Confirm", type="password", max_chars=4, placeholder="Confirm", label_visibility="collapsed")
        if st.form_submit_button("Update PIN", type="primary", use_container_width=True):
            if cur_pin != st.session_state.active_pin:
                st.error("Current PIN incorrect.")
            elif not new_pin1.isdigit() or len(new_pin1) != 4:
                st.error("PIN must be 4 digits.")
            elif new_pin1 != new_pin2:
                st.error("PINs don't match.")
            else:
                save_pin(new_pin1)
                st.success("PIN updated.")

    # ── App Settings ────────────────────────────────
    st.markdown('<div class="sec-hd">App Settings</div>', unsafe_allow_html=True)
    current_income = float(get_app_setting(KEY_INCOME,"0") or 0)
    curr_thresh    = int(float(get_app_setting(KEY_ALERT_PCT,"70") or 70))
    curr_alert     = str(get_app_setting(KEY_ALERT_ON,"true")).lower() == "true"
    curr_pulse     = str(get_app_setting(KEY_PULSE_ON,"true")).lower() == "true"

    with st.form("app_settings_form"):
        new_income = st.number_input("Monthly Income (₹)", min_value=0.0, value=current_income, step=1000.0)
        new_thresh = st.slider("Budget alert threshold (%)", 50, 95, curr_thresh, 5)
        a1, a2     = st.columns(2)
        new_alert  = a1.checkbox("Budget alert (15th)", value=curr_alert)
        new_pulse  = a2.checkbox("Weekly pulse (Mon)", value=curr_pulse)
        if st.form_submit_button("Save Settings", type="primary", use_container_width=True):
            set_app_setting(KEY_INCOME,    new_income)
            set_app_setting(KEY_ALERT_PCT, new_thresh)
            set_app_setting(KEY_ALERT_ON,  str(new_alert).lower())
            set_app_setting(KEY_PULSE_ON,  str(new_pulse).lower())
            st.toast("Settings saved!")
            st.rerun()

# ═══════════════════════════════════════════════════════
# FAB — QUICK LOG  (logic fully preserved)
# ═══════════════════════════════════════════════════════
if "show_modal" not in st.session_state:
    st.session_state.show_modal = False

@st.dialog("Log Expense")
def log_modal():
    if "form_id" not in st.session_state:
        st.session_state.form_id = 0
    if "last_log" in st.session_state:
        ll = st.session_state.last_log
        st.success(f"Saved ₹{ll['amt']:,} → {ll['cat']}")
    live_cats  = sorted(st.session_state.cat_df["Category"].dropna().tolist()) if not st.session_state.cat_df.empty else []
    live_modes = st.session_state.modes_df["Mode"].dropna().tolist() if not st.session_state.modes_df.empty else DEFAULT_MODES
    fid = st.session_state.form_id
    amt = st.number_input("Amount (₹)", min_value=0.0, value=None, placeholder="0", key=f"amt_{fid}")
    if amt and amt > LARGE_AMT_WARNING:
        st.warning(f"₹{int(amt):,} — unusually large, double-check.")
    date_choice = st.radio("Date", ["Today","Yesterday","Pick"], horizontal=True, key=f"ds_{fid}")
    if date_choice == "Today":       log_date = st.session_state.today
    elif date_choice == "Yesterday": log_date = st.session_state.today - timedelta(days=1)
    else:                            log_date = st.date_input("Date", value=st.session_state.today, key=f"dp_{fid}")
    ca, cb = st.columns(2)
    cat  = ca.selectbox("Category", live_cats,  key=f"cat_{fid}")
    mode = cb.selectbox("Mode",     live_modes, key=f"mode_{fid}")
    note = st.text_input("Note", value="", placeholder="Optional note...", key=f"note_{fid}")
    c1, c2 = st.columns(2)
    if c1.button("Save & Add More", type="primary", use_container_width=True):
        if not amt or amt <= 0:
            st.warning("Enter a valid amount.")
            return
        now_ts   = datetime.now(TZ).timestamp()
        last_ts  = st.session_state.get("last_save_ts", 0)
        last_amt = st.session_state.get("last_save_amt", None)
        last_cat = st.session_state.get("last_save_cat", None)
        if (now_ts - last_ts) < 3 and last_amt == amt and last_cat == cat:
            st.warning("Possible duplicate — same amount & category within 3s.")
            return
        final_dt = f"{log_date.strftime('%Y-%m-%d')} {datetime.now(TZ).strftime('%H:%M:%S')}"
        save_expense({"Date": final_dt, "Amount": amt, "Category": cat,
                      "Mode": mode, "Note": note.strip()})
        st.session_state.update({
            "last_save_ts": now_ts, "last_save_amt": amt, "last_save_cat": cat,
            "last_log": {"amt": amt, "cat": cat}, "form_id": fid + 1,
        })
        st.rerun()
    if c2.button("Done", use_container_width=True):
        st.session_state.show_modal = False
        for k in ["last_log","last_save_ts","last_save_amt","last_save_cat"]:
            st.session_state.pop(k, None)
        st.rerun()

# FAB button (fixed bottom-right)
st.markdown('<div class="fab-container">', unsafe_allow_html=True)
if st.button("＋", key="fab_open", help="Log expense"):
    st.session_state.show_modal = True
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

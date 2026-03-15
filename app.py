import streamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta, date
import pytz

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
TZ                = pytz.timezone('Asia/Kolkata')
DEFAULT_MODES     = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]
MAX_PIN_ATTEMPTS  = 5
KEY_INCOME        = "Monthly_Income"
KEY_ALERT_PCT     = "Budget_Alert_Threshold"
KEY_ALERT_ON      = "Budget_Alert_Enabled"
KEY_PULSE_ON      = "Weekly_Pulse_Enabled"
LARGE_AMT_WARNING = 50_000
RECUR_MIN_MONTHS  = 3

# ─────────────────────────────────────────────
# PAGE CONFIG + CSS
# ─────────────────────────────────────────────
st.set_page_config(page_title="FinTrack", page_icon="₹", layout="centered")

st.markdown("""
<style>
/* ── Base ── */
html, body, * { font-family: sans-serif !important; color: #111 !important; }
.stApp { background: #f5f5f5 !important; }
div.block-container {
    padding-top: 0.6rem !important;
    padding-bottom: 5rem !important;
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
    max-width: 600px !important;
    margin: 0 auto !important;
}
[data-testid="stHeader"]  { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }

/* ── GLOBAL BUTTON FIX — all buttons light bg, dark text ── */
button, [data-testid="baseButton-secondary"],
[data-testid="baseButton-primary"],
[data-testid="baseButton-minimal"] {
    background-color: #e8e8e8 !important;
    color: #111 !important;
    border: 1px solid #ccc !important;
    border-radius: 6px !important;
    font-size: 0.78rem !important;
}
button[kind="primary"],
[data-testid="baseButton-primary"] {
    background-color: #d94f00 !important;
    color: #fff !important;
    border: none !important;
}
button:hover { background-color: #d0d0d0 !important; }
button[kind="primary"]:hover { background-color: #b84300 !important; }

/* ── GLOBAL SELECTBOX / DROPDOWN FIX ── */
[data-testid="stSelectbox"] * { color: #111 !important; }
[data-testid="stSelectbox"] > div > div {
    background: #fff !important;
    border: 1px solid #ccc !important;
    border-radius: 8px !important;
}
/* dropdown options list */
[data-baseweb="select"] * { color: #111 !important; background: #fff !important; }
[data-baseweb="menu"]   * { color: #111 !important; background: #fff !important; }
li[role="option"]          { color: #111 !important; background: #fff !important; }
li[role="option"]:hover    { background: #f0f0f0 !important; }

/* ── GLOBAL INPUT / TEXTAREA FIX ── */
input, textarea, [data-baseweb="input"] * {
    color: #111 !important;
    background: #fff !important;
}

/* ── GLOBAL RADIO + CHECKBOX ── */
[data-testid="stRadio"] *    { color: #111 !important; }
[data-testid="stCheckbox"] * { color: #111 !important; }

/* ── GLOBAL SLIDER ── */
[data-testid="stSlider"] * { color: #111 !important; }

/* ── GLOBAL FORM ── */
[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

/* ── GLOBAL EXPANDER ── */
[data-testid="stExpander"] * { color: #111 !important; }

/* ── Cards ── */
.card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 8px;
}
.card-title {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #888 !important;
    margin-bottom: 4px;
}
.card-amount {
    font-size: 1.6rem;
    font-weight: 700;
    color: #111 !important;
}
.card-sub { font-size: 0.75rem; color: #666 !important; margin-top: 2px; }
.prog-track {
    background: #eee;
    border-radius: 4px;
    height: 5px;
    margin-top: 6px;
    overflow: hidden;
}
.prog-fill { height: 5px; border-radius: 4px; }

/* ── Category rows ── */
.cat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px solid #f0f0f0;
    font-size: 0.82rem;
}
.cat-name { color: #333 !important; flex: 1; }
.cat-amt  { font-weight: 700; color: #111 !important; white-space: nowrap; }
.cat-pct  { font-size: 0.7rem; color: #aaa !important; margin-left: 8px; white-space: nowrap; }

/* ── Compact table ── */
.txn-table { width: 100%; border-collapse: collapse; font-size: 0.76rem; }
.txn-table th {
    text-align: left;
    font-size: 0.65rem;
    text-transform: uppercase;
    color: #999 !important;
    border-bottom: 1px solid #ddd;
    padding: 4px 6px;
    font-weight: 600;
}
.txn-table td {
    padding: 5px 6px;
    border-bottom: 1px solid #f2f2f2;
    color: #333 !important;
    vertical-align: middle;
}
.txn-table tr:last-child td { border-bottom: none; }
.amt-cell { font-weight: 600; color: #111 !important; text-align: right; }

/* ── Category list ── */
.clist-row {
    display: flex;
    align-items: center;
    padding: 5px 0;
    border-bottom: 1px solid #f2f2f2;
    font-size: 0.78rem;
    color: #333 !important;
}

/* ── Review card ── */
.rev-card {
    background: #fff;
    border: 1px solid #ddd;
    border-left: 3px solid #d94f00;
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 6px;
}
.rev-merchant { font-size: 0.88rem; font-weight: 700; color: #111 !important; }
.rev-meta     { font-size: 0.7rem;  color: #666 !important; margin-top: 2px; }
.rev-amt      { font-size: 0.95rem; font-weight: 700; color: #111 !important; }

/* ── Section header ── */
.sec-hd {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #999 !important;
    margin: 14px 0 6px;
}

/* ── Number input ── */
[data-testid="stNumberInput"] * { color: #111 !important; background: #fff !important; }
[data-testid="stNumberInput"] input { border: 1px solid #ccc !important; border-radius: 6px !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# DATA LOAD  — NO cache_data so hard_refresh
# always fetches live from GSheets
# ─────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)

def load_all_data():
    """Always fetches live — no @st.cache_data so stale data can never persist."""
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
    """
    Full reset: clear ALL session state (including cached data frames)
    then rerun so bootstrap_session() re-fetches live from GSheets.
    """
    keys_to_clear = list(st.session_state.keys())
    for k in keys_to_clear:
        del st.session_state[k]
    st.rerun()

df            = st.session_state.df
cat_df        = st.session_state.cat_df
settings_df   = st.session_state.settings_df
modes_df      = st.session_state.modes_df
pending_df    = st.session_state.pending_df
import_log_df = st.session_state.import_log_df
import_rules  = st.session_state.import_rules

categories    = sorted(cat_df["Category"].dropna().tolist())    if not cat_df.empty   else []
payment_modes = modes_df["Mode"].dropna().tolist()              if not modes_df.empty else DEFAULT_MODES
now           = datetime.now(TZ)
today         = now.date()
curr_ym       = now.strftime("%Y-%m")


# ─────────────────────────────────────────────
# SAVE HELPERS
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

def get_budget_for_cat(cat_name):
    """Return budget amount for a category from settings_df, or 0."""
    sdf = st.session_state.settings_df
    if sdf.empty or "Budget" not in sdf.columns:
        return 0.0
    mask = sdf["Category"].astype(str).str.strip() == cat_name
    if not mask.any():
        return 0.0
    val = sdf.loc[mask, "Budget"].iloc[0]
    try:
        return float(val) if str(val).strip() not in ("","nan") else 0.0
    except:
        return 0.0

def set_budget_for_cat(cat_name, amount):
    """Upsert budget row in settings_df for the given category."""
    sdf = st.session_state.settings_df.copy()
    mask = sdf["Category"].astype(str).str.strip() == cat_name if not sdf.empty else pd.Series([], dtype=bool)
    if not sdf.empty and mask.any():
        sdf.loc[mask, "Budget"] = amount
    else:
        new_row = pd.DataFrame([{
            "Category": cat_name, "Budget": amount,
            "Is_Recurring": False, "Day_of_Month": "", "Last_Fired": ""
        }])
        sdf = pd.concat([sdf, new_row], ignore_index=True)
    save_settings(sdf)

def split_expense_row(idx, amt1, cat1, amt2, cat2):
    with st.spinner("Splitting..."):
        orig = st.session_state.df.loc[idx]
        note_base = str(orig.get("Note","") or "").strip()
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
        st.session_state.df = updated


# ─────────────────────────────────────────────
# REVIEW HELPERS
# ─────────────────────────────────────────────
def extract_merchant(row):
    txn  = str(row.get("Transaction_Details","") or "").strip()
    note = str(row.get("Note","") or "").strip()
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
    with st.spinner("Dropping..."):
        updated_pend = st.session_state.pending_df.drop(idx).reset_index(drop=True)
        conn.update(worksheet="PendingReview", data=updated_pend)
        st.session_state.pending_df = updated_pend

def auto_save_import_rule(merchant, category):
    rules   = st.session_state.import_rules
    words   = [w for w in merchant.split() if len(w) > 3]
    keyword = (words[0] if words else merchant[:10]).strip()
    if len(keyword) < 3:
        return
    existing = rules["Keyword"].astype(str).str.lower().str.strip().tolist() if not rules.empty else []
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
            count += 1
    return count


# ─────────────────────────────────────────────
# RECURRING AUTO-LOG
# ─────────────────────────────────────────────
if not st.session_state.get("auto_log_checked") and not settings_df.empty:
    fired_any   = False
    updated_sdf = st.session_state.settings_df.copy()
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
            fire_dt = f"{today.strftime('%Y-%m-%d')} {now.strftime('%H:%M:%S')}"
            save_expense({"Date": fire_dt, "Amount": amt, "Category": row["Category"],
                          "Mode": "Auto", "Note": "Auto-logged (recurring)"})
            updated_sdf.at[i, "Last_Fired"] = curr_ym
            fired_any = True
        except:
            pass
    if fired_any:
        save_settings(updated_sdf)
    st.session_state.auto_log_checked = True


# ─────────────────────────────────────────────
# PIN GATE
# ─────────────────────────────────────────────
for _k, _v in [("pin_unlocked",False),("pin_input",""),("pin_attempts",0),("pin_error","")]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

if not st.session_state.pin_unlocked:
    locked_out = st.session_state.pin_attempts >= MAX_PIN_ATTEMPTS
    st.markdown("<br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1,2,1])
    with col:
        st.markdown("<div style='text-align:center;font-size:1.3rem;font-weight:700;margin-bottom:4px;color:#111'>FinTrack</div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:center;font-size:0.8rem;color:#666;margin-bottom:20px'>Enter your 4-digit PIN</div>", unsafe_allow_html=True)
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

# Title row
h1, h2, h3 = st.columns([4,1,1])
h1.markdown("<div style='font-size:1.1rem;font-weight:700;padding:4px 0;color:#111'>FinTrack</div>", unsafe_allow_html=True)
if h2.button("↻", key="refresh_top"):
    hard_refresh()
if h3.button("🔒", key="lock_top"):
    st.session_state.pin_unlocked = False
    st.session_state.pin_input    = ""
    st.rerun()

# Center-aligned nav dropdown
_, nav_col, _ = st.columns([1, 4, 1])
with nav_col:
    # Resolve current index safely (page label may have changed if pending_count changed)
    cur_page = st.session_state.page
    cur_idx  = 0
    for pi, po in enumerate(PAGE_OPTIONS):
        if po == cur_page or po.startswith(cur_page.split(" (")[0]):
            cur_idx = pi
            break
    selected_page = st.selectbox(
        "nav", PAGE_OPTIONS, index=cur_idx,
        label_visibility="collapsed", key="nav_select"
    )
    if selected_page != st.session_state.page:
        st.session_state.page      = selected_page
        st.session_state.show_modal = False   # ← reset modal on page change
        st.rerun()

page = st.session_state.page
st.markdown("<hr style='margin:6px 0 10px;border:none;border-top:1px solid #e0e0e0'>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════
if "🏠 Home" in page:
    st.session_state.show_modal = False

    now_per  = pd.Period(curr_ym, freq="M")
    q_map    = {1:1,2:1,3:1,4:2,5:2,6:2,7:3,8:3,9:3,10:4,11:4,12:4}
    curr_q   = q_map[now.month]
    q_months = [m for m, q in q_map.items() if q == curr_q]

    month_df    = df[df["Date"].dt.to_period("M") == now_per].copy() if not df.empty else pd.DataFrame()
    month_total = month_df["Amount"].sum()

    qtr_df    = df[(df["Date"].dt.month.isin(q_months)) & (df["Date"].dt.year == now.year)].copy() if not df.empty else pd.DataFrame()
    qtr_total = qtr_df["Amount"].sum()

    budgets_set  = st.session_state.settings_df[
        st.session_state.settings_df["Budget"].notna() &
        (st.session_state.settings_df["Budget"].astype(str).str.strip() != "")
    ].copy() if not st.session_state.settings_df.empty else pd.DataFrame()
    total_budget = budgets_set["Budget"].apply(
        lambda v: float(v) if str(v).strip() not in ("","nan") else 0
    ).sum() if not budgets_set.empty else 0.0

    # Monthly card
    m_pct      = min(month_total / total_budget * 100, 100) if total_budget > 0 else 0
    m_color    = "#e53935" if m_pct > 90 else ("#f57c00" if m_pct > 70 else "#43a047")
    budget_sub = f"Budget: ₹{total_budget:,.0f}  ·  Remaining: ₹{max(total_budget-month_total,0):,.0f}" if total_budget > 0 else "No budget set"
    st.markdown(
        f'<div class="card">'
        f'<div class="card-title">This Month — {curr_ym}</div>'
        f'<div class="card-amount">₹{int(month_total):,}</div>'
        f'<div class="card-sub">{budget_sub}</div>'
        + (f'<div class="prog-track"><div class="prog-fill" style="width:{m_pct:.1f}%;background:{m_color}"></div></div>' if total_budget > 0 else "")
        + '</div>', unsafe_allow_html=True
    )

    # Quarterly card
    q_months_str = ["Jan–Mar","Apr–Jun","Jul–Sep","Oct–Dec"][curr_q-1]
    q_budget     = total_budget * 3
    q_pct        = min(qtr_total / q_budget * 100, 100) if q_budget > 0 else 0
    q_color      = "#e53935" if q_pct > 90 else ("#f57c00" if q_pct > 70 else "#43a047")
    q_budget_sub = f"Budget: ₹{q_budget:,.0f}  ·  Remaining: ₹{max(q_budget-qtr_total,0):,.0f}" if q_budget > 0 else "No budget set"
    st.markdown(
        f'<div class="card">'
        f'<div class="card-title">Q{curr_q} ({q_months_str})</div>'
        f'<div class="card-amount">₹{int(qtr_total):,}</div>'
        f'<div class="card-sub">{q_budget_sub}</div>'
        + (f'<div class="prog-track"><div class="prog-fill" style="width:{q_pct:.1f}%;background:{q_color}"></div></div>' if q_budget > 0 else "")
        + '</div>', unsafe_allow_html=True
    )

    # Top 5 — Monthly
    st.markdown('<div class="sec-hd">Top Categories — This Month</div>', unsafe_allow_html=True)
    if not month_df.empty:
        top5_m = month_df.groupby("Category")["Amount"].sum().sort_values(ascending=False).head(5)
        top5_t = top5_m.sum() or 1
        html = '<div class="card">'
        for cat, amt in top5_m.items():
            html += f'<div class="cat-row"><span class="cat-name">{cat}</span><span class="cat-amt">₹{int(amt):,}</span><span class="cat-pct">{amt/top5_t*100:.0f}%</span></div>'
        st.markdown(html + '</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card" style="color:#999;font-size:0.8rem">No transactions this month.</div>', unsafe_allow_html=True)

    # Top 5 — Quarterly
    st.markdown(f'<div class="sec-hd">Top Categories — Q{curr_q}</div>', unsafe_allow_html=True)
    if not qtr_df.empty:
        top5_q = qtr_df.groupby("Category")["Amount"].sum().sort_values(ascending=False).head(5)
        top5_qt = top5_q.sum() or 1
        html = '<div class="card">'
        for cat, amt in top5_q.items():
            html += f'<div class="cat-row"><span class="cat-name">{cat}</span><span class="cat-amt">₹{int(amt):,}</span><span class="cat-pct">{amt/top5_qt*100:.0f}%</span></div>'
        st.markdown(html + '</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card" style="color:#999;font-size:0.8rem">No transactions this quarter.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# PAGE: TRANSACTIONS
# ═══════════════════════════════════════════════════════
elif "📋 Transactions" in page:
    st.session_state.show_modal = False
    st.markdown('<div class="sec-hd">Transaction History</div>', unsafe_allow_html=True)

    if df.empty:
        st.markdown('<div class="card" style="color:#999;font-size:0.8rem">No transactions yet.</div>', unsafe_allow_html=True)
    else:
        fa, fb = st.columns([3,1])
        srch   = fa.text_input("srch", placeholder="Search category / note...", label_visibility="collapsed")
        n_show = fb.selectbox("show", [50, 100, 200, "All"], label_visibility="collapsed")

        result = df.copy().sort_values("Date", ascending=False)
        if srch.strip():
            q = srch.strip()
            result = result[
                result["Category"].astype(str).str.contains(q, case=False, na=False) |
                result["Note"].astype(str).str.contains(q, case=False, na=False)
            ]
        if n_show != "All":
            result = result.head(int(n_show))

        rows_html = ""
        for _, row in result.iterrows():
            dt_str   = pd.to_datetime(row["Date"]).strftime("%m/%d/%y") if pd.notna(row["Date"]) else "—"
            note_v   = str(row.get("Note","") or "").strip()
            txn_v    = str(row.get("Transaction_Details","") or "").strip()
            merchant = extract_merchant(row) if (note_v or txn_v) else str(row.get("Category",""))
            merchant = merchant[:30]
            amt      = int(row["Amount"])
            rows_html += f'<tr><td>{dt_str}</td><td>{merchant}</td><td class="amt-cell">₹{amt:,}</td></tr>'

        st.markdown(
            f'<div class="card" style="padding:8px 10px">'
            f'<table class="txn-table"><thead><tr>'
            f'<th>Date</th><th>Merchant</th><th style="text-align:right">Amt</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table></div>',
            unsafe_allow_html=True
        )
        st.markdown(f'<div style="font-size:0.7rem;color:#aaa;text-align:right">{len(result)} rows</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# PAGE: CATEGORIES  (with inline budget)
# ═══════════════════════════════════════════════════════
elif "🏷" in page:
    st.session_state.show_modal = False
    st.markdown('<div class="sec-hd">Categories</div>', unsafe_allow_html=True)

    # Add new category
    with st.form("add_cat_form"):
        ca, cb = st.columns([4,1])
        new_cat_name = ca.text_input("new_cat", placeholder="New category name...", label_visibility="collapsed")
        if cb.form_submit_button("Add"):
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
        for i, row in st.session_state.cat_df.iterrows():
            edit_key   = f"catedit_{i}"
            budget_key = f"catbudget_{i}"
            if edit_key   not in st.session_state: st.session_state[edit_key]   = False
            if budget_key not in st.session_state: st.session_state[budget_key] = False

            cat_name      = row["Category"]
            current_bgt   = get_budget_for_cat(cat_name)

            if not st.session_state[edit_key] and not st.session_state[budget_key]:
                c1, c2, c3 = st.columns([5, 1, 1])
                bgt_label = f"₹{int(current_bgt):,}" if current_bgt > 0 else "₹—"
                c1.markdown(
                    f'<div class="clist-row">'
                    f'<span style="flex:1">{cat_name}</span>'
                    f'<span style="font-size:0.7rem;color:#999;margin-right:8px">{bgt_label}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if c2.button("Edit", key=f"catopen_{i}", use_container_width=True):
                    st.session_state[edit_key] = True
                    st.rerun()
                if c3.button("₹", key=f"catbgtopen_{i}", use_container_width=True):
                    st.session_state[budget_key] = True
                    st.rerun()

            elif st.session_state[edit_key]:
                with st.form(f"cat_ef_{i}"):
                    ea, eb, ec = st.columns([4,1,1])
                    new_val = ea.text_input("name", value=cat_name, label_visibility="collapsed")
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

            elif st.session_state[budget_key]:
                with st.form(f"cat_bgt_{i}"):
                    ba, bb, bc = st.columns([4,1,1])
                    new_bgt = ba.number_input(
                        f"Budget for {cat_name}",
                        min_value=0.0,
                        value=current_bgt,
                        step=100.0,
                        label_visibility="collapsed"
                    )
                    save_b = bb.form_submit_button("Save")
                    canc_b = bc.form_submit_button("✕")
                    if save_b:
                        set_budget_for_cat(cat_name, new_bgt)
                        st.session_state[budget_key] = False
                        st.toast(f"Budget for {cat_name}: ₹{int(new_bgt):,}")
                        st.rerun()
                    if canc_b:
                        st.session_state[budget_key] = False
                        st.rerun()

    # Payment modes
    st.markdown('<div class="sec-hd" style="margin-top:16px">Payment Modes</div>', unsafe_allow_html=True)
    with st.form("add_mode_form"):
        ma, mb = st.columns([4,1])
        new_mode_name = ma.text_input("new_mode", placeholder="New mode...", label_visibility="collapsed")
        if mb.form_submit_button("Add"):
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
            mc1.markdown(f'<div class="clist-row">{row["Mode"]}</div>', unsafe_allow_html=True)
            mdk = f"mdel_{i}"
            if mdk not in st.session_state: st.session_state[mdk] = False
            if not st.session_state[mdk]:
                if mc2.button("Del", key=f"mopen_{i}", use_container_width=True):
                    st.session_state[mdk] = True; st.rerun()
            else:
                my, mn = mc2.columns(2)
                if my.button("Y", key=f"mdy_{i}"):
                    save_modes(st.session_state.modes_df.drop(i).reset_index(drop=True))
                    st.session_state[mdk] = False; st.rerun()
                if mn.button("N", key=f"mdn_{i}"):
                    st.session_state[mdk] = False; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# PAGE: REVIEW
# ═══════════════════════════════════════════════════════
elif "⚠️ Review" in page:
    st.session_state.show_modal = False

    pend_all = st.session_state.pending_df.copy() if not st.session_state.pending_df.empty else pd.DataFrame()
    active_pend = pd.DataFrame()
    if not pend_all.empty and "Review_Status" in pend_all.columns:
        active_pend = pend_all[pend_all["Review_Status"].astype(str) == "pending"].copy()

    if active_pend.empty:
        st.markdown('<div class="card" style="color:#555;font-size:0.85rem;text-align:center;padding:24px">✅ All caught up — nothing pending.</div>', unsafe_allow_html=True)
    else:
        active_pend["_merchant"] = active_pend.apply(extract_merchant, axis=1)
        live_cats = sorted(st.session_state.cat_df["Category"].dropna().tolist()) if not st.session_state.cat_df.empty else []
        n_pend    = len(active_pend)

        st.markdown(f'<div class="sec-hd">{n_pend} pending transaction{"s" if n_pend!=1 else ""}</div>', unsafe_allow_html=True)

        # Bulk approve
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
            sug_cat  = "" if sug_cat.lower() in ("nan","") else sug_cat

            split_key = f"rev_split_{idx}"
            if split_key not in st.session_state:
                st.session_state[split_key] = False

            # Card header
            st.markdown(
                f'<div class="rev-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div><div class="rev-merchant">{merchant}</div>'
                f'<div class="rev-meta">{dt_str}'
                + (f'  ·  {note_val[:50]}' if note_val else '')
                + f'</div></div>'
                f'<div class="rev-amt">₹{amt:,}</div></div></div>',
                unsafe_allow_html=True
            )

            # Category selector
            cat_opts    = ["-- Select --"] + live_cats + ["+ New category"]
            default_idx = 0
            if sug_cat and sug_cat in live_cats:
                default_idx = live_cats.index(sug_cat) + 1

            sel = st.selectbox(
                f"Category for {merchant[:20]}", cat_opts,
                index=default_idx,
                key=f"rev_cat_{idx}",
                label_visibility="visible",
                help=f"Suggested: {sug_cat}" if sug_cat else "Choose category"
            )

            final_cat  = None
            is_new_cat = False
            if sel == "+ New category":
                nc_val = st.text_input(
                    "New category name", value=sug_cat,
                    key=f"rev_newcat_{idx}",
                    placeholder="Type new category..."
                )
                if nc_val.strip():
                    final_cat  = nc_val.strip()
                    is_new_cat = True
            elif sel != "-- Select --":
                final_cat = sel

            if sug_cat and default_idx == 0:
                st.caption(f"💡 Suggestion: {sug_cat}")

            # 4 action buttons
            b1, b2, b3, b4 = st.columns(4)
            if b1.button("✅ Approve", key=f"rev_app_{idx}", use_container_width=True,
                         type="primary", disabled=(not final_cat)):
                if final_cat:
                    approve_pending_row(idx, final_cat, create_new_cat=is_new_cat)
                    auto_save_import_rule(merchant, final_cat)
                    st.toast(f"Approved → {final_cat}")
                    st.rerun()

            if b2.button("⏭ Skip", key=f"rev_skip_{idx}", use_container_width=True):
                skip_pending_row(idx)
                st.toast("Skipped")
                st.rerun()

            if b3.button("✂ Split", key=f"rev_spltbtn_{idx}", use_container_width=True):
                st.session_state[split_key] = not st.session_state[split_key]
                st.rerun()

            if b4.button("🗑 Drop", key=f"rev_drop_{idx}", use_container_width=True):
                drop_pending_row(idx)
                st.toast("Dropped permanently")
                st.rerun()

            # Split panel
            if st.session_state.get(split_key, False):
                total_amt = float(row.get("Amount",0))
                with st.container(border=True):
                    st.markdown(f'<div style="font-size:0.75rem;color:#555;margin-bottom:4px">Split ₹{int(total_amt):,} into two</div>', unsafe_allow_html=True)
                    s1a, s1b = st.columns([2,3])
                    spl1_amt = s1a.number_input("Part 1 ₹", min_value=1.0, max_value=total_amt-1,
                                                 value=round(total_amt/2,0), key=f"spl1a_{idx}")
                    spl1_cat = s1b.selectbox("Category 1", live_cats, key=f"spl1c_{idx}", label_visibility="collapsed")
                    spl2_amt = total_amt - spl1_amt
                    s2a, s2b = st.columns([2,3])
                    s2a.markdown(f'<div style="font-size:0.82rem;font-weight:600;padding:8px 0;color:#111">₹{int(spl2_amt):,}</div>', unsafe_allow_html=True)
                    spl2_cat = s2b.selectbox("Category 2", live_cats, key=f"spl2c_{idx}", label_visibility="collapsed")
                    sb1, sb2 = st.columns(2)
                    if sb1.button("Save Split", key=f"dosplit_{idx}", type="primary", use_container_width=True):
                        with st.spinner("Splitting..."):
                            orig   = st.session_state.pending_df.loc[idx]
                            note_b = str(orig.get("Note","") or "").strip()
                            for s_amt, s_cat, sfx in [(spl1_amt,spl1_cat,"(split 1/2)"),(spl2_amt,spl2_cat,"(split 2/2)")]:
                                save_expense({
                                    "Date": orig.get("Date",""), "Amount": s_amt,
                                    "Category": s_cat, "Note": f"{note_b} {sfx}".strip(),
                                    "Mode": orig.get("Mode",""), "UPI_Ref": orig.get("UPI_Ref",""),
                                    "Source_Account": orig.get("Source_Account",""),
                                    "Import_Source": orig.get("Import_Source","paytm_auto"),
                                    "Review_Status": "approved"
                                })
                            upd_pend = st.session_state.pending_df.drop(idx).reset_index(drop=True)
                            conn.update(worksheet="PendingReview", data=upd_pend)
                            st.session_state.pending_df = upd_pend
                        st.session_state[split_key] = False
                        st.toast(f"Split → {spl1_cat} + {spl2_cat}")
                        st.rerun()
                    if sb2.button("Cancel", key=f"cancelsplit_{idx}", use_container_width=True):
                        st.session_state[split_key] = False
                        st.rerun()

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # Skipped section
    if not pend_all.empty and "Review_Status" in pend_all.columns:
        skipped = pend_all[pend_all["Review_Status"].astype(str) == "skipped"]
        if not skipped.empty:
            with st.expander(f"Skipped ({len(skipped)})"):
                for idx, row in skipped.iterrows():
                    m   = extract_merchant(row)
                    amt = int(row.get("Amount",0))
                    sc1, sc2 = st.columns([4,1])
                    sc1.markdown(f'<div style="font-size:0.78rem;color:#555">{m}  ₹{amt:,}</div>', unsafe_allow_html=True)
                    if sc2.button("↩", key=f"restore_{idx}"):
                        st.session_state.pending_df.at[idx, "Review_Status"] = "pending"
                        conn.update(worksheet="PendingReview", data=st.session_state.pending_df)
                        st.rerun()


# ═══════════════════════════════════════════════════════
# PAGE: MANAGE
# ═══════════════════════════════════════════════════════
elif "⚙️ Manage" in page:
    st.session_state.show_modal = False

    # Gmail Sync
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
    if not import_log_df.empty:
        last         = import_log_df.iloc[-1]
        l_stat       = "✅" if str(last.get("Status","")).strip().upper() == "OK" else "❌"
        last_run_str = f"{l_stat} {str(last.get('Run_Time','—')).strip()}  ·  {int(last.get('Imported',0) or 0)} in  ·  {int(last.get('Pending',0) or 0)} pending  ·  {int(last.get('Skipped',0) or 0)} skipped"

    st.markdown(
        f'<div class="card">'
        f'<div style="font-size:0.82rem;font-weight:600;color:#111">Auto-sync: 11am &amp; 11pm IST daily</div>'
        f'<div style="font-size:0.74rem;color:#555;margin-top:2px">Next run in {countdown} ({next_run_dt.strftime("%-I:%M %p")})</div>'
        + (f'<div style="font-size:0.72rem;color:#666;margin-top:6px">{last_run_str}</div>' if last_run_str else "")
        + '</div>', unsafe_allow_html=True
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

    # Import Log
    st.markdown('<div class="sec-hd">Import Log</div>', unsafe_allow_html=True)
    if import_log_df.empty:
        st.markdown('<div class="card" style="color:#999;font-size:0.8rem">No import runs yet.</div>', unsafe_allow_html=True)
    else:
        rows_html = ""
        for _, lr in import_log_df.tail(15).iloc[::-1].iterrows():
            ok  = str(lr.get("Status","")).strip().upper() == "OK"
            ico = "✅" if ok else "❌"
            rows_html += (
                f'<tr><td>{ico}</td>'
                f'<td style="color:#444">{str(lr.get("Run_Time","")).strip()}</td>'
                f'<td class="amt-cell" style="color:#43a047">{int(lr.get("Imported",0) or 0)}↓</td>'
                f'<td class="amt-cell" style="color:#f57c00">{int(lr.get("Pending",0) or 0)}⚠</td></tr>'
            )
        st.markdown(
            f'<div class="card" style="padding:8px 10px">'
            f'<table class="txn-table"><thead><tr>'
            f'<th></th><th>Run Time</th><th style="text-align:right">In</th><th style="text-align:right">Pend</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table></div>',
            unsafe_allow_html=True
        )

    # Import Rules
    st.markdown('<div class="sec-hd">Import Rules</div>', unsafe_allow_html=True)
    with st.form("add_rule_form"):
        ra, rb, rc = st.columns([3,2,1])
        r_kw  = ra.text_input("Keyword", placeholder="Keyword", label_visibility="visible")
        r_cat = rb.selectbox("Category", [""]+categories, label_visibility="visible")
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
            rc1.markdown(f'<div class="clist-row" style="color:#2e7d32;font-weight:600">{rr.get("Keyword","")}</div>', unsafe_allow_html=True)
            rc2.markdown(f'<div class="clist-row">→ {rr.get("Category","")}</div>', unsafe_allow_html=True)
            if rc3.button("Del", key=f"rdel_{i}", use_container_width=True):
                save_import_rules(st.session_state.import_rules.drop(i).reset_index(drop=True))
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:0.78rem;color:#999;padding:6px 0">No rules yet.</div>', unsafe_allow_html=True)

    # Change PIN
    st.markdown('<div class="sec-hd">Change PIN</div>', unsafe_allow_html=True)
    with st.form("change_pin_form"):
        pa, pb, pc = st.columns(3)
        cur_pin  = pa.text_input("Current PIN", type="password", max_chars=4, placeholder="****")
        new_pin1 = pb.text_input("New PIN",     type="password", max_chars=4, placeholder="New")
        new_pin2 = pc.text_input("Confirm PIN", type="password", max_chars=4, placeholder="Confirm")
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

    # App Settings
    st.markdown('<div class="sec-hd">App Settings</div>', unsafe_allow_html=True)
    current_income = float(get_app_setting(KEY_INCOME,"0") or 0)
    curr_thresh    = int(float(get_app_setting(KEY_ALERT_PCT,"70") or 70))
    curr_alert     = str(get_app_setting(KEY_ALERT_ON,"true")).lower() == "true"
    curr_pulse     = str(get_app_setting(KEY_PULSE_ON,"true")).lower() == "true"

    with st.form("app_settings_form"):
        new_income = st.number_input("Monthly Income (₹)", min_value=0.0, value=current_income, step=1000.0)
        new_thresh = st.slider("Budget alert threshold (%)", 50, 95, curr_thresh, 5)
        st.markdown('<div style="font-size:0.78rem;color:#555;margin-top:4px">Email alerts</div>', unsafe_allow_html=True)
        a1, a2     = st.columns(2)
        new_alert  = a1.checkbox("Budget alert (15th)", value=curr_alert)
        new_pulse  = a2.checkbox("Weekly pulse (Mon)",  value=curr_pulse)
        if st.form_submit_button("Save Settings", type="primary", use_container_width=True):
            set_app_setting(KEY_INCOME,    new_income)
            set_app_setting(KEY_ALERT_PCT, new_thresh)
            set_app_setting(KEY_ALERT_ON,  str(new_alert).lower())
            set_app_setting(KEY_PULSE_ON,  str(new_pulse).lower())
            st.toast("Settings saved!")
            st.rerun()


# ═══════════════════════════════════════════════════════
# FAB — QUICK LOG
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
    if date_choice == "Today":       log_date = today
    elif date_choice == "Yesterday": log_date = today - timedelta(days=1)
    else:                            log_date = st.date_input("Pick date", value=today, key=f"dp_{fid}")
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

if st.session_state.show_modal:
    log_modal()

# FAB ＋ button
_, fab_col, _ = st.columns([3,1,3])
with fab_col:
    if st.button("＋ Add", key="fab_open", use_container_width=True, help="Log expense"):
        st.session_state.show_modal = True
        st.rerun()
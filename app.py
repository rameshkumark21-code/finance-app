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
# PAGE CONFIG + MINIMAL CSS
# ─────────────────────────────────────────────
st.set_page_config(page_title="FinTrack", page_icon="₹", layout="centered")

st.markdown("""
<style>
html, body, * { font-family: sans-serif !important; }
.stApp { background: #f5f5f5; color: #111; }
div.block-container {
    padding-top: 0.6rem !important;
    padding-bottom: 4rem !important;
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
    max-width: 600px !important;
    margin: 0 auto !important;
}
[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }

/* Cards */
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
    color: #888;
    margin-bottom: 4px;
}
.card-amount {
    font-size: 1.6rem;
    font-weight: 700;
    color: #111;
}
.card-sub {
    font-size: 0.75rem;
    color: #666;
    margin-top: 2px;
}
.prog-track {
    background: #eee;
    border-radius: 4px;
    height: 5px;
    margin-top: 6px;
    overflow: hidden;
}
.prog-fill {
    height: 5px;
    border-radius: 4px;
}

/* Category rows */
.cat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px solid #f0f0f0;
    font-size: 0.82rem;
}
.cat-name { color: #333; flex: 1; }
.cat-amt  { font-weight: 700; color: #111; white-space: nowrap; }
.cat-pct  { font-size: 0.7rem; color: #aaa; margin-left: 8px; white-space: nowrap; }

/* Compact table */
.txn-table { width: 100%; border-collapse: collapse; font-size: 0.76rem; }
.txn-table th {
    text-align: left;
    font-size: 0.65rem;
    text-transform: uppercase;
    color: #999;
    border-bottom: 1px solid #ddd;
    padding: 4px 6px;
    font-weight: 600;
}
.txn-table td {
    padding: 5px 6px;
    border-bottom: 1px solid #f2f2f2;
    color: #333;
    vertical-align: middle;
}
.txn-table tr:last-child td { border-bottom: none; }
.amt-cell { font-weight: 600; color: #111; text-align: right; }

/* Category list */
.clist-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 5px 0;
    border-bottom: 1px solid #f2f2f2;
    font-size: 0.78rem;
}
.clist-name { color: #333; flex: 1; }

/* Review card */
.rev-card {
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 8px;
}
.rev-merchant { font-size: 0.88rem; font-weight: 700; color: #111; }
.rev-meta     { font-size: 0.7rem; color: #888; margin-top: 2px; }
.rev-amt      { font-size: 0.95rem; font-weight: 700; color: #111; }

/* Section header */
.sec-hd {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #aaa;
    margin: 14px 0 6px;
}

/* Nav dropdown area */
[data-testid="stSelectbox"] > div > div {
    background: #fff !important;
    border: 1px solid #ddd !important;
    border-radius: 8px !important;
    font-size: 0.85rem !important;
}

/* Hide default form borders */
[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

button[kind="primary"] {
    font-size: 0.75rem !important;
    padding: 4px 10px !important;
}
button[kind="secondary"] {
    font-size: 0.75rem !important;
    padding: 4px 10px !important;
}

/* Global button fix */
button, [data-testid="stButton"] button {
    color: #111 !important;
    background-color: #fff !important;
    border: 1px solid #ccc !important;
    font-weight: 600 !important;
}

/* Dropdown fix */
[data-testid="stSelectbox"] > div > div {
    color: #111 !important;
    background-color: #fff !important;
    border: 1px solid #ccc !important;
}

/* Form inputs */
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
        return (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
                pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())

def bootstrap_session():
    e, c, s, m, p, il, ir, a = load_all_data()
    if not e.empty:
        e["Date"]   = pd.to_datetime(e["Date"], errors="coerce")
        e["Amount"] = pd.to_numeric(e["Amount"], errors="coerce").fillna(0)
    if not p.empty:
        p["Date"]   = pd.to_datetime(p["Date"], errors="coerce")
        p["Amount"] = pd.to_numeric(p["Amount"], errors="coerce").fillna(0)
    if "Last_Fired" not in s.columns:
        s["Last_Fired"] = ""
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
    for k in ["bootstrapped","df","cat_df","settings_df","modes_df",
              "pending_df","import_log_df","import_rules","app_settings_df"]:
        st.session_state.pop(k, None)
    bootstrap_session()
    safe_rerun()

df            = st.session_state.df
cat_df        = st.session_state.cat_df
settings_df   = st.session_state.settings_df
modes_df      = st.session_state.modes_df
pending_df    = st.session_state.pending_df
import_log_df = st.session_state.import_log_df
import_rules  = st.session_state.import_rules

categories    = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty else []
payment_modes = modes_df["Mode"].dropna().tolist() if not modes_df.empty else DEFAULT_MODES
now           = datetime.now(TZ)
today         = now.date()
curr_ym       = now.strftime("%Y-%m")



# ─────────────────────────────────────────────
# SAVE HELPERS  (all original logic preserved)
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
        st.session_state.df = updated



# ─────────────────────────────────────────────
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
                        safe_rerun()
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
                            safe_rerun()
    st.stop()



# ─────────────────────────────────────────────
# NAVIGATION — centered dropdown
# ─────────────────────────────────────────────
pending_count = 0
if not st.session_state.pending_df.empty and "Review_Status" in st.session_state.pending_df.columns:
    pending_count = int((st.session_state.pending_df["Review_Status"].astype(str) == "pending").sum())

PAGE_OPTIONS = ["🏠 Home", "📋 Transactions", "🏷 Categories", "⚠️ Review", "⚙️ Manage"]
if pending_count > 0:
    PAGE_OPTIONS[3] = f"⚠️ Review ({pending_count})"

if "page" not in st.session_state:
    st.session_state.page = PAGE_OPTIONS[0]

# App title + lock row
h1, h2, h3 = st.columns([4,1,1])
h1.markdown("<div style='font-size:1.1rem;font-weight:700;padding:4px 0'>FinTrack</div>", unsafe_allow_html=True)
if h2.button("↻", key="refresh_top"):
    hard_refresh()
if h3.button("🔒", key="lock_top"):
    st.session_state.pin_unlocked = False
    st.session_state.pin_input    = ""
    safe_rerun()

# Center-aligned nav dropdown
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
        safe_rerun()

page = st.session_state.page
st.markdown("<hr style='margin:6px 0 10px;border:none;border-top:1px solid #e0e0e0'>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════
if "🏠 Home" in page:

    now_per    = pd.Period(curr_ym, freq="M")
    q_map      = {1:1,2:1,3:1,4:2,5:2,6:2,7:3,8:3,9:3,10:4,11:4,12:4}
    curr_q     = q_map[now.month]
    q_months   = [m for m, q in q_map.items() if q == curr_q]

    # Monthly totals
    month_df   = df[df["Date"].dt.to_period("M") == now_per].copy() if not df.empty else pd.DataFrame()
    month_total = month_df["Amount"].sum()

    # Quarterly totals
    qtr_df      = df[
        (df["Date"].dt.month.isin(q_months)) &
        (df["Date"].dt.year == now.year)
    ].copy() if not df.empty else pd.DataFrame()
    qtr_total   = qtr_df["Amount"].sum()

    # Budget limit from settings
    budgets_set = st.session_state.settings_df[
        st.session_state.settings_df["Budget"].notna() &
        (st.session_state.settings_df["Budget"].astype(str).str.strip() != "")
    ].copy() if not st.session_state.settings_df.empty else pd.DataFrame()
    total_budget = budgets_set["Budget"].apply(
        lambda v: float(v) if str(v).strip() not in ("","nan") else 0
    ).sum() if not budgets_set.empty else 0.0



    # ── Monthly card ─────────────────────────────────
    m_pct   = min(month_total / total_budget * 100, 100) if total_budget > 0 else 0
    m_color = "#e53935" if m_pct > 90 else ("#f57c00" if m_pct > 70 else "#43a047")
    budget_sub = f"Budget: ₹{total_budget:,.0f}  ·  Remaining: ₹{max(total_budget-month_total,0):,.0f}" if total_budget > 0 else "No budget set"
    st.markdown(
        f'<div class="card">'
        f'<div class="card-title">This Month — {curr_ym}</div>'
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
        top5_total_q = top5_q.sum() or 1
        html = '<div class="card">'
        for cat, amt in top5_q.items():
            pct = amt / top5_total_q * 100
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
if "📋 Transactions" in page:
    df = st.session_state.df
    if df.empty:
        st.info("No transactions.")
    else:
        st.markdown('<div class="sec-hd">All Transactions</div>', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)

# ═══════════════════════════════════════════════════════
# PAGE: CATEGORIES
# ═══════════════════════════════════════════════════════
if "🏷 Categories" in page:
    st.markdown('<div class="sec-hd">Categories</div>', unsafe_allow_html=True)
    st.dataframe(st.session_state.cat_df, use_container_width=True)

    st.markdown('<div class="sec-hd">Category Budgets</div>', unsafe_allow_html=True)
    sdf = st.session_state.settings_df.copy() if not st.session_state.settings_df.empty else pd.DataFrame(columns=["Category","Budget","Is_Recurring","Day_of_Month","Last_Fired"])
    if sdf.empty and categories:
        sdf = pd.DataFrame([{"Category": c, "Budget": "", "Is_Recurring": "", "Day_of_Month": "", "Last_Fired": ""} for c in categories])
    edited_budgets = st.data_editor(sdf, num_rows="dynamic", use_container_width=True, key="budget_editor_main")
    if st.button("💾 Save Budgets"):
        conn.update("Settings", edited_budgets)
        st.success("Budgets saved.")
        hard_refresh()

# ═══════════════════════════════════════════════════════
# PAGE: REVIEW
# ═══════════════════════════════════════════════════════
if "⚠️ Review" in page:
    df = st.session_state.pending_df
    if df.empty:
        st.info("No pending reviews.")
    else:
        st.markdown('<div class="sec-hd">Pending Review</div>', unsafe_allow_html=True)
        for idx, row in df.iterrows():
            merchant = extract_merchant(row)
            amt      = row.get("Amount",0)
            note     = str(row.get("Note",""))
            cat_sug  = str(row.get("Suggested_Category","")).strip()
            html = (
                f'<div class="rev-card">'
                f'<div class="rev-merchant">{merchant}</div>'
                f'<div class="rev-meta">{note}</div>'
                f'<div class="rev-amt">₹{int(amt):,}</div>'
                f'</div>'
            )
            st.markdown(html, unsafe_allow_html=True)
            cols = st.columns([2,2,2])
            with cols[0]:
                if st.button("Approve", key=f"approve_{idx}"):
                    approve_pending_row(idx, cat_sug if cat_sug else "Misc", create_new_cat=True)
                    safe_rerun()
            with cols[1]:
                if st.button("Skip", key=f"skip_{idx}"):
                    skip_pending_row(idx)
                    safe_rerun()
            with cols[2]:
                if st.button("Drop", key=f"drop_{idx}"):
                    drop_pending_row(idx)
                    safe_rerun()



# ═══════════════════════════════════════════════════════
# PAGE: MANAGE
# ═══════════════════════════════════════════════════════
if "⚙️ Manage" in page:
    st.markdown('<div class="sec-hd">Import Log</div>', unsafe_allow_html=True)
    st.dataframe(st.session_state.import_log_df, use_container_width=True)

    st.markdown('<div class="sec-hd">Import Rules</div>', unsafe_allow_html=True)
    rules_df = st.session_state.import_rules.copy() if not st.session_state.import_rules.empty else pd.DataFrame(columns=["Keyword","Match_In","Category"])
    rules_editor = st.data_editor(rules_df, num_rows="dynamic", use_container_width=True, key="rules_editor_main")
    if st.button("💾 Save Rules"):
        conn.update("ImportRules", rules_editor)
        st.success("Rules saved.")
        hard_refresh()

    st.markdown('<div class="sec-hd">App Settings</div>', unsafe_allow_html=True)
    app_df = st.session_state.app_settings_df.copy() if not st.session_state.app_settings_df.empty else pd.DataFrame(columns=["Key","Value"])
    app_editor = st.data_editor(app_df, num_rows="dynamic", use_container_width=True, key="app_editor_main")
    if st.button("💾 Save Settings"):
        conn.update("AppSettings", app_editor)
        st.success("Settings saved.")
        hard_refresh()

# ═══════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════
st.markdown("<hr style='margin:10px 0;border:none;border-top:1px solid #e0e0e0'>", unsafe_allow_html=True)
if st.button("Hard Refresh", key="hard_refresh_footer"):
    hard_refresh()

# ═══════════════════════════════════════════════════════
# END OF APP
# ═══════════════════════════════════════════════════════

# Ensure session state consistency
if "page" not in st.session_state:
    st.session_state.page = PAGE_OPTIONS[0]

# Final footer note
st.markdown(
    "<div style='text-align:center;color:#999;font-size:0.7rem;margin-top:20px'>"
    "FinTrack · Personal Finance Tracker · © 2026"
    "</div>",
    unsafe_allow_html=True
)

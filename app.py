import streamlit as st
import pandas as pd
import io
import requests
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta, date
import pytz
from streamlit_extras.stylable_container import stylable_container

# ==============================================================================
# 1. CONSTANTS
# ==============================================================================
RECENT_TXN_COUNT   = 10
HDFC_MILESTONE_AMT = 100_000
LARGE_AMT_WARNING  = 50_000
TZ                 = pytz.timezone('Asia/Kolkata')
DEFAULT_MODES      = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]
MAX_PIN_ATTEMPTS   = 5

# ==============================================================================
# 2. PAGE CONFIG + CSS
# ==============================================================================
st.set_page_config(page_title="FinTrack Pro", page_icon="Rs.", layout="centered")

_CSS = (
    "<link href='https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght"
    "@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&display=swap' rel='stylesheet'>"
    "<style>"
    "html,body,*{font-family:'DM Sans',sans-serif!important}"
    ".stApp{background-color:#080808;color:#e8e8e8}"
    "[data-testid='stHeader']{background:transparent}"
    "h1,h2,h3,h4{letter-spacing:-0.3px}"
    ".stTabs [data-baseweb='tab-list']{gap:2px;background:transparent;border-bottom:1px solid #1c1c1c}"
    ".stTabs [data-baseweb='tab']{height:40px;background:transparent;border-radius:8px 8px 0 0;"
    "padding:0 16px;color:#555;font-size:.85rem;font-weight:500}"
    ".stTabs [aria-selected='true']{background:transparent!important;color:#e8e8e8!important;"
    "border-bottom:2px solid #2563eb!important;font-weight:600!important}"
    # Core tiles
    ".tile{background:#101010;border:1px solid #1c1c1c;border-radius:14px;padding:16px 18px;margin-bottom:10px}"
    ".tile-accent{height:3px;border-radius:2px 2px 0 0;margin-bottom:12px}"
    ".tile-label{color:#555;font-size:.7rem;text-transform:uppercase;letter-spacing:1.4px;font-weight:600}"
    ".tile-value{font-size:1.85rem;font-weight:700;margin-top:4px;letter-spacing:-.8px;color:#f0f0f0}"
    ".tile-sub{font-size:.78rem;margin-top:4px}"
    ".trend-up{color:#f87171;font-weight:600}"
    ".trend-down{color:#34d399;font-weight:600}"
    ".trend-flat{color:#666}"
    # Progress
    ".prog-wrap{margin-top:10px}"
    ".prog-track{background:#1c1c1c;border-radius:6px;height:10px;overflow:hidden}"
    ".prog-fill{height:10px;border-radius:6px;transition:width .6s ease}"
    ".prog-meta{display:flex;justify-content:space-between;margin-top:5px;font-size:.72rem;color:#444}"
    # Section headings
    ".sec-head{font-size:.68rem;text-transform:uppercase;letter-spacing:1.6px;color:#444;font-weight:700;margin:22px 0 10px}"
    # Category rows
    ".cat-row{display:flex;align-items:center;justify-content:space-between;"
    "padding:9px 14px;border-radius:10px;margin-bottom:5px;background:#101010;border:1px solid #1c1c1c}"
    ".cat-name{font-size:.88rem;font-weight:500;color:#ddd;flex:1}"
    ".cat-bar-wrap{width:72px;height:3px;background:#1e1e1e;border-radius:2px;margin:0 12px;flex-shrink:0}"
    ".cat-bar-fill{height:3px;border-radius:2px;background:#2563eb}"
    ".cat-amt{font-size:.88rem;font-weight:600;color:#e8e8e8;white-space:nowrap}"
    # Budget rows
    ".budget-row{padding:12px 14px;border-radius:10px;background:#101010;border:1px solid #1c1c1c;margin-bottom:7px}"
    ".budget-header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px}"
    ".budget-name{font-size:.88rem;font-weight:600;color:#ddd}"
    ".budget-nums{font-size:.78rem;color:#555}"
    # Recurring cards
    ".rec-card{background:#101010;border:1px solid #1c1c1c;border-radius:12px;padding:13px 15px;margin-bottom:6px}"
    ".rec-fired{border-left:3px solid #34d399}"
    ".rec-pending{border-left:3px solid #facc15}"
    ".rec-title{font-size:.93rem;font-weight:600;color:#e0e0e0}"
    ".rec-meta{font-size:.76rem;color:#555;margin-top:3px}"
    # Category list rows
    ".catlist-row{font-size:.9rem;font-weight:500;color:#ccc;padding:9px 0;border-bottom:1px solid #141414}"
    # Empty states
    ".empty-box{text-align:center;padding:48px 20px;color:#333}"
    ".empty-box .ico{font-size:2.2rem;margin-bottom:10px}"
    ".empty-box .msg{font-size:.88rem;line-height:1.5}"
    # Category hero
    ".cat-hero{background:#101010;border:1px solid #1c1c1c;border-radius:14px;padding:16px 18px;margin-bottom:6px;cursor:pointer}"
    ".cat-hero-name{font-size:1rem;font-weight:700;color:#f0f0f0}"
    ".cat-hero-meta{font-size:.74rem;color:#555;margin-top:3px}"
    ".cat-hero-amt{font-size:1.2rem;font-weight:700;color:#2563eb;white-space:nowrap}"
    # Search cards
    ".srch-card{background:#101010;border:1px solid #1c1c1c;border-radius:12px;padding:13px 16px;margin-bottom:5px}"
    ".srch-top{display:flex;justify-content:space-between;align-items:center}"
    ".srch-cat{font-size:.9rem;font-weight:700;color:#e0e0e0}"
    ".srch-amt{font-size:.95rem;font-weight:700;color:#2563eb;white-space:nowrap}"
    ".srch-meta{font-size:.74rem;color:#555;margin-top:3px}"
    ".srch-note{font-size:.76rem;color:#777;margin-top:3px;font-style:italic}"
    # Chips / badges
    ".chip{display:inline-block;background:#1a2540;color:#6ea3ff;border-radius:6px;"
    "font-size:.68rem;font-weight:600;padding:2px 7px;margin-right:4px;letter-spacing:.4px}"
    # ── REVIEW / PENDING CARDS ───────────────────────────────
    ".review-card{background:#101010;border:1px solid #2a1f0a;border-left:3px solid #facc15;"
    "border-radius:14px;padding:16px 18px;margin-bottom:12px}"
    ".review-card-amt{font-size:1.25rem;font-weight:700;color:#f0f0f0;letter-spacing:-.5px}"
    ".review-card-txn{font-size:.9rem;font-weight:500;color:#ccc;margin-top:4px}"
    ".review-card-meta{font-size:.73rem;color:#555;margin-top:5px;line-height:1.6}"
    ".review-badge-remarks{display:inline-block;background:#1a2a1a;color:#86efac;"
    "border-radius:6px;font-size:.68rem;font-weight:600;padding:2px 8px;margin-right:4px}"
    ".review-badge-tags{display:inline-block;background:#1a1a2a;color:#93c5fd;"
    "border-radius:6px;font-size:.68rem;font-weight:600;padding:2px 8px;margin-right:4px}"
    ".review-badge-sug{display:inline-block;background:#2a2010;color:#fcd34d;"
    "border-radius:6px;font-size:.68rem;font-weight:600;padding:2px 8px}"
    ".review-bulk-bar{background:#0f0f0f;border:1px solid #1c1c1c;border-radius:12px;"
    "padding:13px 16px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between}"
    # ImportLog table
    ".log-row{display:flex;justify-content:space-between;align-items:center;"
    "padding:8px 14px;border-bottom:1px solid #141414;font-size:.8rem}"
    ".log-ok{color:#34d399;font-weight:600}"
    ".log-err{color:#f87171;font-weight:600}"
    ".log-num{color:#e8e8e8;font-weight:600}"
    ".log-dim{color:#444}"
    # Sync panel
    ".sync-card{background:#101010;border:1px solid #1c1c1c;border-radius:14px;"
    "padding:20px 20px;margin-bottom:16px}"
    ".sync-title{font-size:.95rem;font-weight:700;color:#f0f0f0;margin-bottom:6px}"
    ".sync-meta{font-size:.78rem;color:#555}"
    # Filter panel
    ".filter-panel{background:#0e0e0e;border:1px solid #1c1c1c;border-radius:14px;padding:16px 18px;margin-bottom:16px}"
    "div[data-testid='stDialog']{background:#0c0c0c!important;border:1px solid #202020!important;border-radius:22px!important}"
    "[data-testid='stTextInput'] input,[data-testid='stNumberInput'] input"
    "{background:#141414!important;border:1px solid #242424!important;border-radius:8px!important;color:#e8e8e8!important}"
    "[data-testid='stSelectbox']>div>div{background:#141414!important;border:1px solid #242424!important;border-radius:8px!important}"
    "[data-testid='stExpander']{background:#101010!important;border:1px solid #1c1c1c!important;border-radius:10px!important;margin-bottom:5px}"
    "[data-testid='stExpander'] summary{font-size:.87rem!important;font-weight:500!important;color:#ccc!important}"
    "[data-testid='stForm']{border:1px solid #1c1c1c!important;border-radius:12px!important;padding:16px!important;background:#0e0e0e!important}"
    ".stAlert{border-radius:10px!important}"
    "[data-testid='stMultiSelect'] span{background:#1a2540!important;color:#6ea3ff!important;"
    "border-radius:5px!important;font-size:.74rem!important}"
    "</style>"
)
st.markdown(_CSS, unsafe_allow_html=True)

# ==============================================================================
# 3. DATA LOAD + SESSION STATE
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
            il = pd.DataFrame(columns=[
                "Run_Time","Emails_Found","Imported","Skipped","Pending","Status","Notes"
            ])
        try:
            ir = conn.read(worksheet="ImportRules")
        except Exception:
            ir = pd.DataFrame(columns=["Keyword","Match_In","Category"])
        return e, c, s, m, p, il, ir
    except Exception as ex:
        st.error(f"Could not connect to Google Sheets: {ex}")
        return (
            pd.DataFrame(columns=["Date","Amount","Category","Note","Mode",
                                   "UPI_Ref","Source_Account","Import_Source","Review_Status"]),
            pd.DataFrame(columns=["Category"]),
            pd.DataFrame(columns=["Category","Budget","Is_Recurring","Day_of_Month","Last_Fired"]),
            pd.DataFrame({"Mode": DEFAULT_MODES}),
            pd.DataFrame(columns=["Date","Amount","Category","Note","Mode","UPI_Ref",
                                   "Source_Account","Import_Source","Review_Status",
                                   "Suggested_Category","Remarks_Raw","Tags_Raw","Transaction_Details"]),
            pd.DataFrame(columns=["Run_Time","Emails_Found","Imported","Skipped","Pending","Status","Notes"]),
            pd.DataFrame(columns=["Keyword","Match_In","Category"]),
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
    _df, _cat, _set, _modes, _pend, _log, _rules = load_all_data()
    if not _df.empty:
        _df["Date"]   = pd.to_datetime(_df["Date"], errors="coerce")
        _df["Amount"] = pd.to_numeric(_df["Amount"], errors="coerce").fillna(0)
    if not _pend.empty:
        _pend["Date"]   = pd.to_datetime(_pend["Date"], errors="coerce")
        _pend["Amount"] = pd.to_numeric(_pend["Amount"], errors="coerce").fillna(0)
    if "Last_Fired" not in _set.columns:
        _set["Last_Fired"] = ""
    st.session_state.df            = _df
    st.session_state.cat_df        = _cat
    st.session_state.settings_df   = _set
    st.session_state.modes_df      = _modes
    st.session_state.pending_df    = _pend
    st.session_state.import_log_df = _log
    st.session_state.import_rules  = _rules
    st.session_state.active_pin    = load_pin()
    st.session_state.bootstrapped  = True

if not st.session_state.get("bootstrapped"):
    bootstrap_session()

def hard_refresh():
    st.cache_data.clear()
    for k in ["bootstrapped","df","cat_df","settings_df","modes_df",
              "pending_df","import_log_df","import_rules","active_pin"]:
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
# 4. SAVE HELPERS
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

# ── Pending Review helpers ─────────────────────────────────────
def approve_pending_row(idx, chosen_category, create_new_cat=False):
    """Move a row from PendingReview → Expenses with the chosen category."""
    with st.spinner("Approving..."):
        row = st.session_state.pending_df.loc[idx]

        # Optionally create the category in Categories sheet
        if create_new_cat and chosen_category not in [
            c for c in st.session_state.cat_df["Category"].dropna().tolist()
        ]:
            new_cat_df = pd.concat([
                st.session_state.cat_df,
                pd.DataFrame([{"Category": chosen_category}])
            ], ignore_index=True)
            save_categories(new_cat_df)

        # Build expense row — carry all new columns if present
        expense_row = {
            "Date":           row.get("Date", ""),
            "Amount":         row.get("Amount", 0),
            "Category":       chosen_category,
            "Note":           row.get("Note", ""),
            "Mode":           row.get("Mode", "UPI"),
            "UPI_Ref":        row.get("UPI_Ref", ""),
            "Source_Account": row.get("Source_Account", ""),
            "Import_Source":  row.get("Import_Source", "paytm_auto"),
            "Review_Status":  "approved",
        }
        exp_new = pd.DataFrame([expense_row])
        exp_new["Date"]   = pd.to_datetime(exp_new["Date"], errors="coerce")
        exp_new["Amount"] = pd.to_numeric(exp_new["Amount"], errors="coerce").fillna(0)
        updated_exp = pd.concat([st.session_state.df, exp_new], ignore_index=True)
        conn.update(worksheet="Expenses", data=updated_exp)
        st.session_state.df = updated_exp

        # Remove from PendingReview
        updated_pend = st.session_state.pending_df.drop(idx).reset_index(drop=True)
        conn.update(worksheet="PendingReview", data=updated_pend)
        st.session_state.pending_df = updated_pend
        st.cache_data.clear()

def skip_pending_row(idx):
    """Mark a PendingReview row as skipped — stays in sheet but hidden from review UI."""
    with st.spinner("Skipping..."):
        st.session_state.pending_df.at[idx, "Review_Status"] = "skipped"
        conn.update(worksheet="PendingReview", data=st.session_state.pending_df)
        st.cache_data.clear()

def approve_all_with_suggestions():
    """Bulk approve all pending rows that have a Suggested_Category populated."""
    pend = st.session_state.pending_df
    to_approve = pend[
        (pend["Review_Status"] == "pending") &
        (pend["Suggested_Category"].astype(str).str.strip().ne("")) &
        (pend["Suggested_Category"].astype(str).str.strip().ne("nan"))
    ]
    if to_approve.empty:
        return 0
    count = 0
    for idx, row in to_approve.iterrows():
        sug = str(row["Suggested_Category"]).strip()
        if sug:
            approve_pending_row(idx, sug, create_new_cat=True)
            count += 1
    return count


# ==============================================================================
# 5. SHARED TRANSACTION ROW RENDERER
# ==============================================================================
def render_txn_row(idx, row, key_prefix="txn", show_edit=True):
    date_disp = pd.to_datetime(row["Date"]).strftime("%-d %b %Y, %H:%M") if pd.notna(row["Date"]) else "-"
    note_val  = str(row.get("Note", "") or "").strip()
    edit_key  = f"{key_prefix}_edit_{idx}"
    del_key   = f"{key_prefix}_del_{idx}"
    if edit_key not in st.session_state:
        st.session_state[edit_key] = False
    if del_key not in st.session_state:
        st.session_state[del_key] = False

    c_amt, c_info, c_btn = st.columns([2, 5, 1])
    c_amt.markdown(
        f"<div style='font-size:.95rem;font-weight:700;color:#f0f0f0;padding:10px 0'>"
        f"Rs.{float(row['Amount']):,.0f}</div>",
        unsafe_allow_html=True
    )
    mode_chip = f"<span class='chip'>{row['Mode']}</span>" if str(row.get("Mode","")).strip() else ""
    note_html = (f"<div style='font-size:.72rem;color:#555;margin-top:2px;font-style:italic'>"
                 f"{note_val}</div>") if note_val else ""
    c_info.markdown(
        f"<div style='padding:10px 0;line-height:1.35'>"
        f"<span style='font-size:.88rem;font-weight:600;color:#ccc'>{row['Category']}</span>"
        f"<br><span style='font-size:.72rem;color:#555'>{date_disp}</span> {mode_chip}"
        f"{note_html}</div>",
        unsafe_allow_html=True
    )
    if show_edit and c_btn.button("✏️", key=f"{key_prefix}_tgl_{idx}", help="Edit / Delete"):
        st.session_state[edit_key] = not st.session_state[edit_key]
        st.rerun()
    st.markdown("<hr style='border:none;border-top:1px solid #161616;margin:0'>", unsafe_allow_html=True)

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
            btn1, btn2 = st.columns(2)
            if btn1.button("Save changes", key=f"{key_prefix}_save_{idx}",
                           use_container_width=True, type="primary"):
                update_expense(idx, {"Amount": new_amt, "Category": new_cat,
                                     "Mode": new_mode, "Note": new_note.strip()})
                st.session_state[edit_key] = False
                st.rerun()
            if not st.session_state[del_key]:
                if btn2.button("Delete", key=f"{key_prefix}_delb_{idx}", use_container_width=True):
                    st.session_state[del_key] = True
                    st.rerun()
            else:
                btn2.warning("Sure?")
                y_, n_ = btn2.columns(2)
                if y_.button("Yes", key=f"{key_prefix}_ydel_{idx}"):
                    delete_expense(idx)
                    st.session_state[edit_key] = False
                    st.session_state[del_key]  = False
                    st.rerun()
                if n_.button("No", key=f"{key_prefix}_ndel_{idx}"):
                    st.session_state[del_key] = False
                    st.rerun()


# ==============================================================================
# 6. PIN GATE
# ==============================================================================
for _k, _v in [("pin_unlocked", False), ("pin_input", ""), ("pin_attempts", 0), ("pin_error", "")]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

if not st.session_state.pin_unlocked:
    locked_out = st.session_state.pin_attempts >= MAX_PIN_ATTEMPTS
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("### FinTrack Pro")
        st.markdown(
            "<p style='color:#444;font-size:.8rem;margin-bottom:24px'>Enter your 4-digit PIN to continue</p>",
            unsafe_allow_html=True
        )
        entered  = len(st.session_state.pin_input)
        is_error = bool(st.session_state.pin_error)
        dots_html = "<div style='display:flex;gap:14px;margin-bottom:24px;justify-content:center'>"
        for i in range(4):
            if is_error:
                style = "width:13px;height:13px;border-radius:50%;background:#f87171;border:1.5px solid #f87171"
            elif i < entered:
                style = "width:13px;height:13px;border-radius:50%;background:#2563eb;border:1.5px solid #2563eb"
            else:
                style = "width:13px;height:13px;border-radius:50%;background:transparent;border:1.5px solid #333"
            dots_html += f"<div style='{style}'></div>"
        dots_html += "</div>"
        st.markdown(dots_html, unsafe_allow_html=True)
        if locked_out:
            st.error("Too many incorrect attempts. Restart the app to try again.")
            st.stop()
        if st.session_state.pin_error:
            remaining = MAX_PIN_ATTEMPTS - st.session_state.pin_attempts
            st.markdown(
                f"<p style='color:#f87171;font-size:.76rem;text-align:center;margin-bottom:12px'>"
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
# 7. RECURRING AUTO-LOG
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
# 8. TABS
# ==============================================================================
# Count pending items for tab badge
pending_count = len(
    st.session_state.pending_df[
        st.session_state.pending_df.get("Review_Status", pd.Series(dtype=str)).astype(str) == "pending"
    ]
) if not st.session_state.pending_df.empty else 0

review_label = f"Review ⚠️ {pending_count}" if pending_count > 0 else "Review"

tab_home, tab_cat_view, tab_search, tab_rec, tab_review, tab_manage = st.tabs([
    "Home", "Categories", "Search", "Recurring", review_label, "Manage"
])


# ==============================================================================
# TAB 1 — HOME
# ==============================================================================
with tab_home:
    hc1, hc2, hc3 = st.columns([5, 1, 1])
    hc1.markdown("## FinTrack")
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
        sel_month   = st.selectbox("Period", all_months, index=0, label_visibility="collapsed")
        sel_period  = pd.Period(sel_month, freq="M")
        prev_period = sel_period - 1
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

        tc1, tc2 = st.columns(2)
        if sel_month == curr_ym:
            today_total = df[df["Date"].dt.date == today]["Amount"].sum()
            tc1.markdown(
                f'<div class="tile"><div class="tile-accent" style="background:#2563eb"></div>'
                f'<div class="tile-label">Spent Today</div>'
                f'<div class="tile-value">Rs.{today_total:,.0f}</div></div>',
                unsafe_allow_html=True
            )
        else:
            tc1.markdown(
                f'<div class="tile"><div class="tile-accent" style="background:#374151"></div>'
                f'<div class="tile-label">Period</div>'
                f'<div class="tile-value" style="font-size:1.1rem;padding-top:6px">{sel_month}</div></div>',
                unsafe_allow_html=True
            )
        tc2.markdown(
            f'<div class="tile"><div class="tile-accent" style="background:#7c3aed"></div>'
            f'<div class="tile-label">Total Spend</div>'
            f'<div class="tile-value">Rs.{month_total:,.0f}</div>'
            f'<div class="tile-sub">{trend_html}</div></div>',
            unsafe_allow_html=True
        )

        q_map  = {1:1,2:1,3:1,4:2,5:2,6:2,7:3,8:3,9:3,10:4,11:4,12:4}
        curr_q = q_map[now.month]
        h_spend = df[
            (df["Date"].dt.month.map(q_map) == curr_q) &
            (df["Date"].dt.year == now.year) &
            (df["Mode"] == "HDFC Credit Card")
        ]["Amount"].sum()
        h_pct     = min(h_spend / HDFC_MILESTONE_AMT * 100, 100)
        h_color   = "#2563eb" if h_pct < 75 else ("#facc15" if h_pct < 100 else "#34d399")
        remaining = max(HDFC_MILESTONE_AMT - h_spend, 0)
        st.markdown(
            f'<div class="tile" style="border-left:3px solid {h_color}">'
            f'<div class="tile-label">HDFC Q{curr_q} Milestone</div>'
            f'<div class="tile-value">Rs.{h_spend:,.0f}'
            f'<span style="font-size:.82rem;color:#444;font-weight:400"> / Rs.{HDFC_MILESTONE_AMT:,.0f}</span></div>'
            f'<div class="prog-wrap"><div class="prog-track">'
            f'<div class="prog-fill" style="width:{h_pct:.1f}%;background:{h_color}"></div>'
            f'</div><div class="prog-meta"><span>{h_pct:.1f}% reached</span>'
            f'<span>Rs.{remaining:,.0f} to go</span></div></div></div>',
            unsafe_allow_html=True
        )

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
                bcolor = "#34d399" if bpct < 75 else ("#facc15" if bpct < 100 else "#f87171")
                over   = " Over budget!" if bspent > blimit else ""
                st.markdown(
                    f'<div class="budget-row"><div class="budget-header">'
                    f'<span class="budget-name">{bcat}{over}</span>'
                    f'<span class="budget-nums">Rs.{bspent:,.0f} / Rs.{blimit:,.0f}</span></div>'
                    f'<div class="prog-track"><div class="prog-fill" style="width:{bpct:.1f}%;background:{bcolor}"></div></div></div>',
                    unsafe_allow_html=True
                )

        st.markdown('<p class="sec-head">By Category</p>', unsafe_allow_html=True)
        if not filt.empty:
            cat_sum = filt.groupby("Category")["Amount"].sum().sort_values(ascending=False).reset_index()
            max_amt = cat_sum["Amount"].max() or 1
            for _, crow in cat_sum.iterrows():
                bar_pct = crow["Amount"] / max_amt * 100
                st.markdown(
                    f'<div class="cat-row">'
                    f'<span class="cat-name">{crow["Category"]}</span>'
                    f'<div class="cat-bar-wrap"><div class="cat-bar-fill" style="width:{bar_pct:.0f}%"></div></div>'
                    f'<span class="cat-amt">Rs.{crow["Amount"]:,.0f}</span></div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<div class="empty-box"><div class="ico">📊</div>'
                        '<div class="msg">No data for this period.</div></div>', unsafe_allow_html=True)

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
    st.markdown("## Categories")

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
            f'<div class="tile"><div class="tile-accent" style="background:#2563eb"></div>'
            f'<div class="tile-label">All Time Spend</div>'
            f'<div class="tile-value" style="font-size:1.4rem">Rs.{total_all:,.0f}</div></div>',
            unsafe_allow_html=True
        )
        s2.markdown(
            f'<div class="tile"><div class="tile-accent" style="background:#7c3aed"></div>'
            f'<div class="tile-label">Transactions</div>'
            f'<div class="tile-value" style="font-size:1.4rem">{total_txns:,}</div></div>',
            unsafe_allow_html=True
        )
        s3.markdown(
            f'<div class="tile"><div class="tile-accent" style="background:#0d9488"></div>'
            f'<div class="tile-label">Daily Average</div>'
            f'<div class="tile-value" style="font-size:1.4rem">Rs.{total_all/span_days:,.0f}</div></div>',
            unsafe_allow_html=True
        )

        st.markdown('<p class="sec-head">Category Breakdown — All Time</p>', unsafe_allow_html=True)
        sort_opt = st.radio(
            "Sort by", ["Total Spend", "No. of Transactions", "Avg Transaction", "A to Z"],
            horizontal=True, label_visibility="collapsed"
        )

        cat_grp = df.groupby("Category").agg(
            Total=("Amount", "sum"),
            Count=("Amount", "count"),
            Avg=("Amount", "mean"),
            Last=("Date", "max"),
        ).reset_index()

        if sort_opt == "Total Spend":
            cat_grp = cat_grp.sort_values("Total", ascending=False)
        elif sort_opt == "No. of Transactions":
            cat_grp = cat_grp.sort_values("Count", ascending=False)
        elif sort_opt == "Avg Transaction":
            cat_grp = cat_grp.sort_values("Avg", ascending=False)
        else:
            cat_grp = cat_grp.sort_values("Category")

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
                f'<div class="cat-hero">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div><div class="cat-hero-name">{cat_name}</div>'
                f'<div class="cat-hero-meta">{cat_count} transactions &nbsp;·&nbsp; Avg Rs.{cat_avg:,.0f}'
                f' &nbsp;·&nbsp; Last {cat_last} &nbsp;·&nbsp; {share_pct:.1f}% of total</div></div>'
                f'<div class="cat-hero-amt">Rs.{cat_total:,.0f}</div></div>'
                f'<div style="margin-top:10px;background:#1e1e1e;border-radius:4px;height:4px">'
                f'<div style="width:{bar_pct:.1f}%;background:#2563eb;height:4px;border-radius:4px"></div></div>'
                f'</div>',
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
                        cat_entries["Date"].dropna().dt.to_period("M").unique().astype(str).tolist(),
                        reverse=True
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
                        f"<p style='font-size:.75rem;color:#555;margin-bottom:8px'>"
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
    st.markdown("## Search & Filter")

    if df.empty:
        st.markdown('<div class="empty-box"><div class="ico">🔍</div>'
                    '<div class="msg">No data to search yet.</div></div>', unsafe_allow_html=True)
    else:
        with st.container():
            st.markdown('<p class="sec-head">Filters</p>', unsafe_allow_html=True)
            keyword = st.text_input("Keyword", placeholder="Search across category, note, mode...",
                                    label_visibility="collapsed")
            dr1, dr2 = st.columns(2)
            min_date = df["Date"].min().date() if not df.empty else date(2020, 1, 1)
            max_date = max(df["Date"].max().date() if not df.empty else today, today)
            date_from = dr1.date_input("From", value=min_date, min_value=min_date,
                                       max_value=max_date, key="sf_from")
            date_to   = dr2.date_input("To",   value=today,   min_value=min_date,
                                       max_value=max_date, key="sf_to")
            fm1, fm2 = st.columns(2)
            sel_cats  = fm1.multiselect("Categories",
                                        options=sorted(df["Category"].dropna().unique().tolist()),
                                        placeholder="All categories")
            sel_modes = fm2.multiselect("Modes",
                                        options=sorted(df["Mode"].dropna().unique().tolist()),
                                        placeholder="All modes")
            fa1, fa2 = st.columns(2)
            amt_min = fa1.number_input("Min amount (Rs.)", min_value=0.0, value=0.0,
                                       step=100.0, key="sf_amin")
            amt_max = fa2.number_input("Max amount (Rs.)", min_value=0.0,
                                       value=float(df["Amount"].max() or 100000),
                                       step=100.0, key="sf_amax")
            fc1, fc2, fc3, fc4 = st.columns(4)
            only_noted    = fc1.checkbox("Has note",    key="sf_noted")
            only_auto     = fc2.checkbox("Auto-logged", key="sf_auto")
            only_credited = fc3.checkbox("Credit card", key="sf_cc")
            only_today    = fc4.checkbox("Today only",  key="sf_today")
            fs1, fs2 = st.columns([3, 1])
            sort_by  = fs1.selectbox(
                "Sort by",
                ["Date (newest)","Date (oldest)","Amount (highest)","Amount (lowest)","Category A-Z"],
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
        if sel_cats:
            result = result[result["Category"].isin(sel_cats)]
        if sel_modes:
            result = result[result["Mode"].isin(sel_modes)]
        result = result[(result["Amount"] >= amt_min) & (result["Amount"] <= amt_max)]
        if only_noted:
            result = result[result["Note"].astype(str).str.strip().ne("").ne("nan")]
        if only_auto:
            result = result[result["Note"].astype(str).str.contains("Auto-logged", case=False, na=False)]
        if only_credited:
            result = result[result["Mode"].astype(str).str.contains("Credit Card", case=False, na=False)]
        if only_today:
            result = result[result["Date"].dt.date == today]
        if sort_by == "Date (newest)":
            result = result.sort_values("Date", ascending=False)
        elif sort_by == "Date (oldest)":
            result = result.sort_values("Date", ascending=True)
        elif sort_by == "Amount (highest)":
            result = result.sort_values("Amount", ascending=False)
        elif sort_by == "Amount (lowest)":
            result = result.sort_values("Amount", ascending=True)
        else:
            result = result.sort_values("Category", ascending=True)

        r_count = len(result)
        r_total = result["Amount"].sum()
        r_avg   = result["Amount"].mean() if r_count > 0 else 0

        ra1, ra2, ra3 = st.columns(3)
        ra1.markdown(
            f'<div class="tile"><div class="tile-accent" style="background:#2563eb"></div>'
            f'<div class="tile-label">Results</div>'
            f'<div class="tile-value" style="font-size:1.4rem">{r_count:,}</div></div>',
            unsafe_allow_html=True
        )
        ra2.markdown(
            f'<div class="tile"><div class="tile-accent" style="background:#7c3aed"></div>'
            f'<div class="tile-label">Total</div>'
            f'<div class="tile-value" style="font-size:1.4rem">Rs.{r_total:,.0f}</div></div>',
            unsafe_allow_html=True
        )
        ra3.markdown(
            f'<div class="tile"><div class="tile-accent" style="background:#0d9488"></div>'
            f'<div class="tile-label">Avg per txn</div>'
            f'<div class="tile-value" style="font-size:1.4rem">Rs.{r_avg:,.0f}</div></div>',
            unsafe_allow_html=True
        )

        if r_count > 0 and len(sel_cats) != 1:
            r_cat_split = result.groupby("Category")["Amount"].sum().sort_values(ascending=False)
            split_str   = "  |  ".join([f"{c}: Rs.{v:,.0f}" for c, v in r_cat_split.items()])
            st.markdown(
                f"<p style='font-size:.72rem;color:#444;margin:-6px 0 12px'>{split_str}</p>",
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
            st.markdown(
                '<div class="empty-box"><div class="ico">🔍</div>'
                '<div class="msg">No transactions match these filters.<br>'
                'Try relaxing the date range or removing some filters.</div></div>',
                unsafe_allow_html=True
            )
        else:
            for idx, row in result.iterrows():
                render_txn_row(idx, row, key_prefix="srch")


# ==============================================================================
# TAB 4 — RECURRING
# ==============================================================================
with tab_rec:
    st.markdown("## Recurring Rules")
    with st.expander("Create New Rule"):
        with st.form("new_rec"):
            rc1, rc2 = st.columns(2)
            c_sel = rc1.selectbox("Category", categories)
            a_sel = rc2.number_input("Amount (Rs.)", min_value=0.0, value=None, placeholder="0.00")
            d_sel = st.slider("Auto-log on day of month", 1, 31, 1)
            if st.form_submit_button("Add Rule", type="primary"):
                if a_sel:
                    new_r   = pd.DataFrame([{"Category": c_sel, "Budget": a_sel,
                                              "Is_Recurring": True, "Day_of_Month": d_sel,
                                              "Last_Fired": ""}])
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
                    f'<div class="rec-meta">Rs.{float(row["Budget"]):,.0f}  --  {status_txt}</div></div>',
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
# TAB 5 — REVIEW (Pending Review — Paytm Imports)
# ==============================================================================
with tab_review:
    st.markdown("## Pending Review")

    pend_all = st.session_state.pending_df.copy() if not st.session_state.pending_df.empty \
               else pd.DataFrame()

    # Only show rows with status == "pending"
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
        n_pend = len(active_pend)
        n_with_sug = len(active_pend[
            active_pend.get("Suggested_Category", pd.Series(dtype=str)).astype(str).str.strip().ne("")
            & active_pend.get("Suggested_Category", pd.Series(dtype=str)).astype(str).str.strip().ne("nan")
        ]) if "Suggested_Category" in active_pend.columns else 0

        # Bulk action bar
        st.markdown(
            f'<div style="background:#0f0f0f;border:1px solid #1c1c1c;border-radius:12px;'
            f'padding:13px 16px;margin-bottom:16px;">'
            f'<span style="font-size:.9rem;font-weight:600;color:#facc15">⚠️ {n_pend} item{"s" if n_pend != 1 else ""} need review</span>'
            f'<span style="font-size:.76rem;color:#555;margin-left:10px">'
            f'{n_with_sug} have a suggested category</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        if n_with_sug > 0:
            if st.button(
                f"✅ Approve all {n_with_sug} with suggestions",
                type="primary",
                use_container_width=True,
                key="bulk_approve_btn"
            ):
                count = approve_all_with_suggestions()
                st.toast(f"Approved {count} items!")
                st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Per-card review UI
        live_categories = sorted(
            st.session_state.cat_df["Category"].dropna().tolist()
        ) if not st.session_state.cat_df.empty else []

        for idx, row in active_pend.iterrows():
            date_disp   = pd.to_datetime(row["Date"]).strftime("%-d %b %Y, %H:%M") \
                          if pd.notna(row.get("Date")) else "-"
            amount      = float(row.get("Amount", 0))
            note_val    = str(row.get("Note", "") or "").strip()
            txn_details = str(row.get("Transaction_Details", "") or "").strip()
            remarks_raw = str(row.get("Remarks_Raw", "") or "").strip()
            tags_raw    = str(row.get("Tags_Raw", "") or "").strip()
            sug_cat     = str(row.get("Suggested_Category", "") or "").strip()
            upi_ref     = str(row.get("UPI_Ref", "") or "").strip()

            # ── Build badge HTML ──────────────────────────────────
            badges = ""
            if remarks_raw and remarks_raw != "nan":
                badges += f"<span class='review-badge-remarks'>Remarks: {remarks_raw}</span>"
            if tags_raw and tags_raw != "nan":
                badges += f"<span class='review-badge-tags'>Tags: {tags_raw}</span>"
            if sug_cat and sug_cat != "nan":
                badges += f"<span class='review-badge-sug'>💡 Suggested: {sug_cat}</span>"

            st.markdown(
                f'<div class="review-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div class="review-card-amt">Rs.{amount:,.0f}</div>'
                f'<span style="font-size:.72rem;color:#555">{date_disp}</span>'
                f'</div>'
                f'<div class="review-card-txn">{txn_details or note_val}</div>'
                f'<div class="review-card-meta">'
                f'{badges}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            # Determine default index for category dropdown
            # Pre-select suggested category if it's in the list
            default_opts = ["-- New category --"] + live_categories
            if sug_cat and sug_cat != "nan" and sug_cat in live_categories:
                default_idx = live_categories.index(sug_cat) + 1  # +1 for "-- New category --"
            elif sug_cat and sug_cat != "nan":
                default_idx = 0  # "-- New category --" selected, will create it
            else:
                default_idx = 0

            sel_key   = f"rev_cat_{idx}"
            new_key   = f"rev_newcat_{idx}"
            skip_key  = f"rev_skip_{idx}"

            if skip_key not in st.session_state:
                st.session_state[skip_key] = False

            sel_cat = st.selectbox(
                "Assign category",
                options=default_opts,
                index=default_idx,
                key=sel_key,
                label_visibility="collapsed"
            )

            # If "New category" selected, show text input
            final_cat    = None
            is_new_cat   = False
            if sel_cat == "-- New category --":
                new_cat_input = st.text_input(
                    "New category name",
                    value=sug_cat if sug_cat and sug_cat != "nan" else "",
                    placeholder="e.g. Egg, Chai, Vegetables...",
                    key=new_key
                )
                if new_cat_input.strip():
                    final_cat  = new_cat_input.strip()
                    is_new_cat = True
            else:
                final_cat = sel_cat

            col_approve, col_skip = st.columns(2)
            if col_approve.button(
                "✅ Approve", key=f"rev_approve_{idx}",
                use_container_width=True, type="primary",
                disabled=(not final_cat)
            ):
                if final_cat:
                    approve_pending_row(idx, final_cat, create_new_cat=is_new_cat)
                    st.toast(f"Approved → {final_cat}")
                    st.rerun()

            if not st.session_state[skip_key]:
                if col_skip.button("⏭ Skip", key=f"rev_skip_btn_{idx}", use_container_width=True):
                    st.session_state[skip_key] = True
                    st.rerun()
            else:
                col_skip.warning("Skip this?")
                ya, na = col_skip.columns(2)
                if ya.button("Yes", key=f"rev_skip_y_{idx}"):
                    skip_pending_row(idx)
                    st.session_state[skip_key] = False
                    st.rerun()
                if na.button("No", key=f"rev_skip_n_{idx}"):
                    st.session_state[skip_key] = False
                    st.rerun()

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # Skipped items — collapsible section
    if not pend_all.empty and "Review_Status" in pend_all.columns:
        skipped = pend_all[pend_all["Review_Status"].astype(str) == "skipped"]
        if not skipped.empty:
            with st.expander(f"Skipped items ({len(skipped)}) — tap to review"):
                for idx, row in skipped.iterrows():
                    date_disp = pd.to_datetime(row["Date"]).strftime("%-d %b %Y") \
                                if pd.notna(row.get("Date")) else "-"
                    txn       = str(row.get("Transaction_Details","") or "").strip()
                    amt       = float(row.get("Amount", 0))
                    st.markdown(
                        f'<div style="padding:8px 0;border-bottom:1px solid #141414;'
                        f'display:flex;justify-content:space-between;font-size:.85rem;color:#666">'
                        f'<span>{txn}</span><span>Rs.{amt:,.0f} · {date_disp}</span></div>',
                        unsafe_allow_html=True
                    )
                    if st.button("↩ Restore to Review", key=f"restore_{idx}",
                                 use_container_width=False):
                        st.session_state.pending_df.at[idx, "Review_Status"] = "pending"
                        conn.update(worksheet="PendingReview",
                                    data=st.session_state.pending_df)
                        st.cache_data.clear()
                        st.rerun()


# ==============================================================================
# TAB 6 — MANAGE
# ==============================================================================
with tab_manage:
    st.markdown("## Manage")

    # ── GMAIL SYNC ──────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Gmail Sync</p>', unsafe_allow_html=True)

    apps_script_url = st.secrets.get("apps_script_url", "")

    # ── Schedule status tile — always visible ────────────────────────────
    # Compute next 11AM and 11PM IST from now
    now_ist      = datetime.now(TZ)
    today_11am   = now_ist.replace(hour=11, minute=0, second=0, microsecond=0)
    today_11pm   = now_ist.replace(hour=23, minute=0, second=0, microsecond=0)
    next_runs    = [t for t in [today_11am, today_11pm] if t > now_ist]
    if not next_runs:
        # Both passed today — next is tomorrow 11AM
        tomorrow    = now_ist + timedelta(days=1)
        next_run_dt = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)
    else:
        next_run_dt = next_runs[0]
    time_until   = next_run_dt - now_ist
    hours_until  = int(time_until.total_seconds() // 3600)
    mins_until   = int((time_until.total_seconds() % 3600) // 60)
    next_run_str = next_run_dt.strftime("%-I:%M %p")
    countdown    = f"{hours_until}h {mins_until}m" if hours_until > 0 else f"{mins_until}m"

    # Last run summary from ImportLog
    last_run_html = ""
    last_run_ok   = None
    if not import_log_df.empty:
        last      = import_log_df.iloc[-1]
        last_stat = str(last.get("Status","")).strip().upper()
        last_run_ok = last_stat == "OK"
        lico      = "✅" if last_run_ok else "❌"
        last_run_html = (
            f'<div style="margin-top:10px;padding-top:10px;border-top:1px solid #1c1c1c;'
            f'font-size:.76rem;color:#555">'
            f'Last run: {lico} <span style="color:#ccc">'
            f'{str(last.get("Run_Time","—")).strip()}</span>'
            f' &nbsp;·&nbsp; <span style="color:#34d399">'
            f'{int(last.get("Imported",0) or 0)} imported</span>'
            f' &nbsp;·&nbsp; <span style="color:#facc15">'
            f'{int(last.get("Pending",0) or 0)} pending</span>'
            f' &nbsp;·&nbsp; <span style="color:#555">'
            f'{int(last.get("Skipped",0) or 0)} skipped</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="sync-card">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
        f'<div>'
        f'<div class="sync-title">🕐 Auto-Sync Schedule</div>'
        f'<div class="sync-meta" style="margin-top:4px">'
        f'Runs automatically at <b style="color:#ccc">11:00 AM</b> and '
        f'<b style="color:#ccc">11:00 PM</b> IST daily via Google Apps Script.</div>'
        f'</div>'
        f'<div style="text-align:right;flex-shrink:0;margin-left:12px">'
        f'<div style="font-size:.68rem;color:#555;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:3px">Next run</div>'
        f'<div style="font-size:1rem;font-weight:700;color:#2563eb">{next_run_str}</div>'
        f'<div style="font-size:.72rem;color:#555">in {countdown}</div>'
        f'</div>'
        f'</div>'
        f'{last_run_html}'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Manual Sync button — only if URL is configured ───────────────────
    if not apps_script_url:
        st.markdown(
            '<div class="sync-card" style="border-color:#2a1f0a;border-left:3px solid #facc15">'
            '<div class="sync-title" style="color:#facc15">⚠️ Manual sync not configured</div>'
            '<div class="sync-meta" style="margin-top:4px">The auto-sync above runs on schedule '
            'without any setup. To also enable the <b>Sync Now</b> button, add '
            '<code>apps_script_url</code> to your Streamlit secrets.</div>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        if "sync_result" in st.session_state:
            r = st.session_state.sync_result
            if r.get("status") == "ok":
                res = r.get("result", {})
                st.success(
                    f"✅ Sync complete — {res.get('imported',0)} imported, "
                    f"{res.get('pending',0)} pending review, "
                    f"{res.get('skipped',0)} duplicates skipped"
                )
            else:
                st.error(f"Sync failed: {r.get('message','Unknown error')}")
            del st.session_state["sync_result"]

        if st.button("🔄 Sync Now", type="primary", use_container_width=True, key="sync_now_btn"):
            with st.spinner("Syncing Gmail... this may take 20–30 seconds"):
                try:
                    resp = requests.get(apps_script_url, timeout=60)
                    st.session_state.sync_result = resp.json()
                except requests.exceptions.Timeout:
                    st.session_state.sync_result = {
                        "status": "error",
                        "message": "Request timed out. The sync may still be running — check back in a minute."
                    }
                except Exception as e:
                    st.session_state.sync_result = {"status": "error", "message": str(e)}
                hard_refresh()

    # ── IMPORT LOG ──────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Import Log</p>', unsafe_allow_html=True)

    if import_log_df.empty:
        st.markdown('<div class="empty-box"><div class="ico">📋</div>'
                    '<div class="msg">No import runs yet. The log will appear here after the first sync.</div></div>',
                    unsafe_allow_html=True)
    else:
        show_log = import_log_df.tail(20).iloc[::-1]  # newest first, last 20 runs
        for _, lrow in show_log.iterrows():
            status     = str(lrow.get("Status", "")).strip()
            is_ok      = status.upper() == "OK"
            status_cls = "log-ok" if is_ok else "log-err"
            status_ico = "✅" if is_ok else "❌"
            imp        = int(lrow.get("Imported", 0) or 0)
            skp        = int(lrow.get("Skipped",  0) or 0)
            pnd        = int(lrow.get("Pending",  0) or 0)
            em         = int(lrow.get("Emails_Found", 0) or 0)
            run_time   = str(lrow.get("Run_Time", "")).strip()
            notes      = str(lrow.get("Notes", "")).strip()
            st.markdown(
                f'<div class="log-row">'
                f'<span class="{status_cls}">{status_ico}</span>'
                f'<span class="log-dim" style="flex:1;margin:0 12px;font-size:.75rem">{run_time}</span>'
                f'<span class="log-num" style="color:#34d399">{imp}↓</span>'
                f'<span class="log-dim" style="margin:0 8px">|</span>'
                f'<span class="log-num" style="color:#facc15">{pnd}⚠</span>'
                f'<span class="log-dim" style="margin:0 8px">|</span>'
                f'<span class="log-dim">{skp} skip</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            if not is_ok and notes:
                st.markdown(
                    f'<div style="font-size:.7rem;color:#f87171;padding:3px 14px 8px;'
                    f'background:#140a0a;border-radius:6px;margin-bottom:2px">{notes}</div>',
                    unsafe_allow_html=True
                )

    # ── IMPORT RULES ────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Import Rules (Keyword → Category)</p>', unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:.75rem;color:#555;margin-bottom:10px'>"
        "When a keyword is found in any field of a Paytm transaction, it's auto-assigned "
        "to the mapped category. Case-insensitive.</p>",
        unsafe_allow_html=True
    )

    with st.form("new_rule_form"):
        ir1, ir2, ir3 = st.columns([3, 2, 1])
        new_kw  = ir1.text_input("Keyword", placeholder="e.g. Swiggy", label_visibility="collapsed")
        new_rcat = ir2.selectbox("Category", [""] + categories,
                                  label_visibility="collapsed")
        if ir3.form_submit_button("Add", use_container_width=True):
            if new_kw.strip() and new_rcat:
                new_rule  = pd.DataFrame([{"Keyword": new_kw.strip(),
                                            "Match_In": "Any",
                                            "Category": new_rcat}])
                updated_r = pd.concat([st.session_state.import_rules, new_rule],
                                       ignore_index=True)
                save_import_rules(updated_r)
                st.rerun()
            else:
                st.warning("Both keyword and category are required.")

    if not st.session_state.import_rules.empty:
        for i, rrow in st.session_state.import_rules.iterrows():
            rc1, rc2, rc3 = st.columns([3, 3, 1])
            rc1.markdown(
                f'<div class="catlist-row" style="color:#86efac">'
                f'{rrow.get("Keyword","")}</div>',
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
            '<div class="msg">No rules yet. Add keywords above to auto-categorise imports.</div>'
            '</div>',
            unsafe_allow_html=True
        )

    # ── PAYMENT MODES ────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Payment Modes</p>', unsafe_allow_html=True)
    with st.form("new_mode"):
        nm1, nm2 = st.columns([4, 1])
        nm = nm1.text_input("New mode", label_visibility="collapsed",
                             placeholder="e.g. ICICI Credit Card")
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

    # ── CATEGORIES ───────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Categories</p>', unsafe_allow_html=True)
    with st.form("new_cat"):
        cc1, cc2 = st.columns([4, 1])
        nc = cc1.text_input("New category", label_visibility="collapsed",
                             placeholder="e.g. Dining Out")
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

    # ── CHANGE PIN ───────────────────────────────────────────────────────────
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
# 9. FAB — QUICK LOG
# ==============================================================================
if "show_modal" not in st.session_state:
    st.session_state.show_modal = False

if st.session_state.show_modal:
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

    log_modal()

with stylable_container(key="fab", css_styles="""
button {
    position: fixed; bottom: 32px; right: 24px;
    width: 60px; height: 60px; border-radius: 50%;
    background: #2563eb; color: #fff; font-size: 34px;
    z-index: 9999; border: none;
    box-shadow: 0 6px 24px rgba(37,99,235,0.45);
}
"""):
    if st.button("+", key="main_plus_btn"):
        st.session_state.show_modal = True
        st.rerun()

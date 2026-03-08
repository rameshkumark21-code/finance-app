import streamlit as st
import pandas as pd
import io
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
    ".tile{background:#101010;border:1px solid #1c1c1c;border-radius:14px;padding:16px 18px;margin-bottom:10px}"
    ".tile-accent{height:3px;border-radius:2px 2px 0 0;margin-bottom:12px}"
    ".tile-label{color:#555;font-size:.7rem;text-transform:uppercase;letter-spacing:1.4px;font-weight:600}"
    ".tile-value{font-size:1.85rem;font-weight:700;margin-top:4px;letter-spacing:-.8px;color:#f0f0f0}"
    ".tile-sub{font-size:.78rem;margin-top:4px}"
    ".trend-up{color:#f87171;font-weight:600}"
    ".trend-down{color:#34d399;font-weight:600}"
    ".trend-flat{color:#666}"
    ".prog-wrap{margin-top:10px}"
    ".prog-track{background:#1c1c1c;border-radius:6px;height:10px;overflow:hidden}"
    ".prog-fill{height:10px;border-radius:6px;transition:width .6s ease}"
    ".prog-meta{display:flex;justify-content:space-between;margin-top:5px;font-size:.72rem;color:#444}"
    ".sec-head{font-size:.68rem;text-transform:uppercase;letter-spacing:1.6px;color:#444;font-weight:700;margin:22px 0 10px}"
    ".cat-row{display:flex;align-items:center;justify-content:space-between;"
    "padding:9px 14px;border-radius:10px;margin-bottom:5px;background:#101010;border:1px solid #1c1c1c}"
    ".cat-name{font-size:.88rem;font-weight:500;color:#ddd;flex:1}"
    ".cat-bar-wrap{width:72px;height:3px;background:#1e1e1e;border-radius:2px;margin:0 12px;flex-shrink:0}"
    ".cat-bar-fill{height:3px;border-radius:2px;background:#2563eb}"
    ".cat-amt{font-size:.88rem;font-weight:600;color:#e8e8e8;white-space:nowrap}"
    ".budget-row{padding:12px 14px;border-radius:10px;background:#101010;border:1px solid #1c1c1c;margin-bottom:7px}"
    ".budget-header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px}"
    ".budget-name{font-size:.88rem;font-weight:600;color:#ddd}"
    ".budget-nums{font-size:.78rem;color:#555}"
    ".rec-card{background:#101010;border:1px solid #1c1c1c;border-radius:12px;padding:13px 15px;margin-bottom:6px}"
    ".rec-fired{border-left:3px solid #34d399}"
    ".rec-pending{border-left:3px solid #facc15}"
    ".rec-title{font-size:.93rem;font-weight:600;color:#e0e0e0}"
    ".rec-meta{font-size:.76rem;color:#555;margin-top:3px}"
    ".catlist-row{font-size:.9rem;font-weight:500;color:#ccc;padding:9px 0;border-bottom:1px solid #141414}"
    ".empty-box{text-align:center;padding:48px 20px;color:#333}"
    ".empty-box .ico{font-size:2.2rem;margin-bottom:10px}"
    ".empty-box .msg{font-size:.88rem;line-height:1.5}"
    # Category drilldown
    ".cat-hero{background:#101010;border:1px solid #1c1c1c;border-radius:14px;padding:16px 18px;margin-bottom:6px;cursor:pointer}"
    ".cat-hero-name{font-size:1rem;font-weight:700;color:#f0f0f0}"
    ".cat-hero-meta{font-size:.74rem;color:#555;margin-top:3px}"
    ".cat-hero-amt{font-size:1.2rem;font-weight:700;color:#2563eb;white-space:nowrap}"
    ".txn-sub-row{padding:9px 14px;border-bottom:1px solid #141414;display:flex;justify-content:space-between;align-items:center}"
    ".txn-sub-left{font-size:.84rem;color:#bbb}"
    ".txn-sub-right{font-size:.84rem;font-weight:600;color:#e8e8e8;white-space:nowrap}"
    ".txn-sub-note{font-size:.72rem;color:#555;margin-top:2px}"
    # Search results
    ".srch-card{background:#101010;border:1px solid #1c1c1c;border-radius:12px;padding:13px 16px;margin-bottom:5px}"
    ".srch-top{display:flex;justify-content:space-between;align-items:center}"
    ".srch-cat{font-size:.9rem;font-weight:700;color:#e0e0e0}"
    ".srch-amt{font-size:.95rem;font-weight:700;color:#2563eb;white-space:nowrap}"
    ".srch-meta{font-size:.74rem;color:#555;margin-top:3px}"
    ".srch-note{font-size:.76rem;color:#777;margin-top:3px;font-style:italic}"
    # Chips / badges
    ".chip{display:inline-block;background:#1a2540;color:#6ea3ff;border-radius:6px;"
    "font-size:.68rem;font-weight:600;padding:2px 7px;margin-right:4px;letter-spacing:.4px}"
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
    # Multiselect tags
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
        return e, c, s, m
    except Exception as ex:
        st.error(f"Could not connect to Google Sheets: {ex}")
        return (
            pd.DataFrame(columns=["Date", "Amount", "Category", "Note", "Mode"]),
            pd.DataFrame(columns=["Category"]),
            pd.DataFrame(columns=["Category", "Budget", "Is_Recurring", "Day_of_Month", "Last_Fired"]),
            pd.DataFrame({"Mode": DEFAULT_MODES}),
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
    _df, _cat, _set, _modes = load_all_data()
    if not _df.empty:
        _df["Date"]   = pd.to_datetime(_df["Date"], errors="coerce")
        _df["Amount"] = pd.to_numeric(_df["Amount"], errors="coerce").fillna(0)
    if "Last_Fired" not in _set.columns:
        _set["Last_Fired"] = ""
    st.session_state.df           = _df
    st.session_state.cat_df       = _cat
    st.session_state.settings_df  = _set
    st.session_state.modes_df     = _modes
    st.session_state.active_pin   = load_pin()
    st.session_state.bootstrapped = True

if not st.session_state.get("bootstrapped"):
    bootstrap_session()

def hard_refresh():
    st.cache_data.clear()
    for k in ["bootstrapped", "df", "cat_df", "settings_df", "modes_df", "active_pin"]:
        st.session_state.pop(k, None)
    st.rerun()

df          = st.session_state.df
cat_df      = st.session_state.cat_df
settings_df = st.session_state.settings_df
modes_df    = st.session_state.modes_df

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

# ==============================================================================
# 5. SHARED TRANSACTION ROW RENDERER (used in Home, Categories, Search)
# ==============================================================================
def render_txn_row(idx, row, key_prefix="txn", show_edit=True):
    """Renders a single transaction card row with optional inline edit/delete."""
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
    note_html = f"<div style='font-size:.72rem;color:#555;margin-top:2px;font-style:italic'>{note_val}</div>" if note_val else ""
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
            new_amt  = ea.number_input("Amount", value=float(row["Amount"]), min_value=0.0, key=f"{key_prefix}_eamt_{idx}")
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
            if btn1.button("Save changes", key=f"{key_prefix}_save_{idx}", use_container_width=True, type="primary"):
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
                        st.session_state.pin_input  = st.session_state.pin_input[:-1]
                        st.session_state.pin_error  = ""
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
            save_expense({"Date": fire_dt, "Amount": amt, "Category": row["Category
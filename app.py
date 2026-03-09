import streamlit as st
import pandas as pd
import io
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta, date
import pytz
from streamlit_extras.stylable_container import stylable_container

# ==============================================================================
# CONSTANTS
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

# ==============================================================================
# VIEW MODE
# ==============================================================================
if "view_mode"  not in st.session_state: st.session_state.view_mode  = "mobile"
if "active_tab" not in st.session_state: st.session_state.active_tab = T_DASH
is_mobile = (st.session_state.view_mode == "mobile")

# ==============================================================================
# PAGE CONFIG + CSS
# ==============================================================================
st.set_page_config(page_title="FinTrack Pro", page_icon="💰", layout="centered")

_CSS = (
    "<link href='https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght"
    "@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&display=swap' rel='stylesheet'>"
    "<style>"
    "html,body,*{font-family:'DM Sans',sans-serif!important}"
    ".stApp{background:#080808;color:#e8e8e8}"
    # Kill all Streamlit chrome
    "[data-testid='stHeader']{display:none!important}"
    "[data-testid='stToolbar']{display:none!important}"
    "[data-testid='stDecoration']{display:none!important}"
    "[data-testid='stStatusWidget']{display:none!important}"
    ".stDeployButton{display:none!important}"
    # Zero top padding
    "[data-testid='stMain']{padding-top:0!important}"
    "[data-testid='block-container']{padding-top:0!important}"
    "section[data-testid='stMain']>div:first-child{padding-top:0!important}"
    # Base components
    ".tile{background:#101010;border:1px solid #1c1c1c;border-radius:13px;padding:13px 15px;margin-bottom:8px}"
    ".tile-accent{height:2px;border-radius:2px 2px 0 0;margin-bottom:8px}"
    ".tile-label{color:#555;font-size:.64rem;text-transform:uppercase;letter-spacing:1.4px;font-weight:600}"
    ".tile-value{font-size:1.6rem;font-weight:700;margin-top:3px;letter-spacing:-.8px;color:#f0f0f0}"
    ".tile-sub{font-size:.76rem;margin-top:3px}"
    ".trend-up{color:#f87171;font-weight:600}"
    ".trend-down{color:#34d399;font-weight:600}"
    ".trend-flat{color:#555}"
    ".prog-track{background:#1c1c1c;border-radius:5px;height:7px;overflow:hidden}"
    ".prog-fill{height:7px;border-radius:5px;transition:width .5s ease}"
    ".prog-meta{display:flex;justify-content:space-between;margin-top:4px;font-size:.68rem;color:#444}"
    ".sec-head{font-size:.62rem;text-transform:uppercase;letter-spacing:1.8px;color:#3a3a3a;"
    "font-weight:700;margin:14px 0 7px}"
    ".cat-row{display:flex;align-items:center;padding:8px 12px;border-radius:9px;margin-bottom:4px;"
    "background:#101010;border:1px solid #161616}"
    ".cat-name{font-size:.84rem;font-weight:500;color:#ccc;flex:1}"
    ".cat-bar-wrap{width:54px;height:3px;background:#1a1a1a;border-radius:2px;margin:0 9px;flex-shrink:0}"
    ".cat-bar-fill{height:3px;border-radius:2px;background:#2563eb}"
    ".cat-amt{font-size:.84rem;font-weight:600;color:#e0e0e0;white-space:nowrap}"
    ".budget-row{padding:10px 13px;border-radius:9px;background:#101010;border:1px solid #161616;margin-bottom:5px}"
    ".budget-header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px}"
    ".budget-name{font-size:.84rem;font-weight:600;color:#ccc}"
    ".budget-nums{font-size:.72rem;color:#444}"
    ".rec-card{background:#101010;border:1px solid #161616;border-radius:11px;padding:11px 13px;margin-bottom:5px}"
    ".rec-fired{border-left:3px solid #34d399}"
    ".rec-pending{border-left:3px solid #facc15}"
    ".catlist-row{font-size:.86rem;font-weight:500;color:#bbb;padding:8px 0;border-bottom:1px solid #111}"
    ".empty-box{text-align:center;padding:40px 16px;color:#2a2a2a}"
    ".empty-box .ico{font-size:2rem;margin-bottom:8px}"
    ".empty-box .msg{font-size:.84rem;line-height:1.5}"
    ".cat-hero{background:#101010;border:1px solid #161616;border-radius:13px;padding:13px 15px;margin-bottom:5px}"
    ".chip{display:inline-block;background:#131f38;color:#5a8de0;border-radius:5px;"
    "font-size:.62rem;font-weight:600;padding:2px 6px;margin-right:3px}"
    # Streamlit widget overrides
    "div[data-testid='stDialog']{background:#0c0c0c!important;border:1px solid #1e1e1e!important;border-radius:20px!important}"
    "[data-testid='stTextInput'] input,[data-testid='stNumberInput'] input"
    "{background:#111!important;border:1px solid #222!important;border-radius:8px!important;color:#e0e0e0!important}"
    "[data-testid='stSelectbox']>div>div{background:#111!important;border:1px solid #222!important;border-radius:8px!important}"
    "[data-testid='stForm']{border:1px solid #1c1c1c!important;border-radius:11px!important;padding:13px!important;background:#0c0c0c!important}"
    ".stAlert{border-radius:9px!important}"
    "[data-testid='stMultiSelect'] span{background:#131f38!important;color:#5a8de0!important;border-radius:5px!important;font-size:.7rem!important}"
    # Dashboard hero
    ".dash-hero{background:linear-gradient(135deg,#0c1d3a 0%,#142040 60%,#0a1830 100%);"
    "border:1px solid #1a3060;border-radius:17px;padding:18px 16px 14px;margin-bottom:9px}"
    ".dash-hero-label{font-size:.62rem;text-transform:uppercase;letter-spacing:1.8px;color:#3d5a8a;font-weight:600}"
    ".dash-hero-amount{font-size:2.2rem;font-weight:700;color:#fff;letter-spacing:-1px;margin:3px 0 2px}"
    ".dash-hero-sub{font-size:.74rem;color:#3d5a8a}"
    ".dash-stat{background:#0c0c0c;border:1px solid #161616;border-radius:11px;padding:9px 10px;text-align:center}"
    ".dash-stat-val{font-size:.95rem;font-weight:700;color:#e8e8e8;margin-top:2px}"
    ".dash-stat-lbl{font-size:.58rem;color:#3a3a3a;text-transform:uppercase;letter-spacing:1px;font-weight:600}"
    ".dash-txn-row{display:flex;align-items:center;padding:9px 0;border-bottom:1px solid #101010}"
    ".dash-txn-icon{width:32px;height:32px;border-radius:9px;display:flex;align-items:center;"
    "justify-content:center;font-size:.85rem;margin-right:9px;flex-shrink:0}"
    ".dash-txn-cat{font-size:.82rem;font-weight:600;color:#ccc}"
    ".dash-txn-meta{font-size:.66rem;color:#3a3a3a;margin-top:1px}"
    ".dash-txn-amt{font-size:.88rem;font-weight:700;color:#f87171;white-space:nowrap;margin-left:8px}"
    ".dash-bar-col{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px}"
    ".dash-bar-fill{width:100%;border-radius:3px 3px 0 0;min-height:3px}"
    ".dash-bar-day{font-size:.56rem;color:#3a3a3a;font-weight:600}"
    "</style>"
)
st.markdown(_CSS, unsafe_allow_html=True)

# Mobile extra CSS
if is_mobile:
    st.markdown(
        "<style>"
        "[data-testid='stAppViewContainer']{max-width:430px!important;margin:0 auto!important}"
        "[data-testid='block-container']{padding:0 11px 70px!important;max-width:430px!important}"
        "button[data-testid='baseButton-secondary']{min-height:40px!important;border-radius:9px!important}"
        "button[data-testid='baseButton-primary']{min-height:42px!important;border-radius:9px!important}"
        "</style>",
        unsafe_allow_html=True
    )
else:
    st.markdown(
        "<style>"
        "[data-testid='block-container']{max-width:840px!important;padding:0 20px 80px!important}"
        "</style>",
        unsafe_allow_html=True
    )

# ==============================================================================
# DATA LOAD
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
    except Exception as ex:
        st.error(f"Could not connect to Google Sheets: {ex}")
        return (
            pd.DataFrame(columns=["Date","Amount","Category","Note","Mode"]),
            pd.DataFrame(columns=["Category"]),
            pd.DataFrame(columns=["Category","Budget","Is_Recurring","Day_of_Month","Last_Fired"]),
            pd.DataFrame({"Mode": DEFAULT_MODES}),
        )

@st.cache_data(ttl=30)
def load_pin():
    try:
        sec = conn.read(worksheet="Security", usecols=[0], nrows=1)
        raw = str(sec.iloc[0, 0]).strip()
        return raw if (raw.isdigit() and len(raw) == 4) else "1234"
    except:
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
    for k in ["bootstrapped","df","cat_df","settings_df","modes_df","active_pin"]:
        st.session_state.pop(k, None)
    st.rerun()

df            = st.session_state.df
cat_df        = st.session_state.cat_df
settings_df   = st.session_state.settings_df
modes_df      = st.session_state.modes_df
categories    = sorted(cat_df["Category"].dropna().tolist())    if not cat_df.empty   else []
payment_modes = modes_df["Mode"].dropna().tolist()              if not modes_df.empty else DEFAULT_MODES
now     = datetime.now(TZ)
today   = now.date()
curr_ym = now.strftime("%Y-%m")

# ==============================================================================
# SAVE HELPERS
# ==============================================================================
def save_expense(row_dict):
    with st.spinner("Saving..."):
        nr = pd.DataFrame([row_dict])
        nr["Date"]   = pd.to_datetime(nr["Date"], errors="coerce")
        nr["Amount"] = pd.to_numeric(nr["Amount"], errors="coerce").fillna(0)
        upd = pd.concat([st.session_state.df, nr], ignore_index=True)
        conn.update(worksheet="Expenses", data=upd)
        st.session_state.df = upd
        st.cache_data.clear()

def update_expense(idx, fields):
    with st.spinner("Updating..."):
        for k, v in fields.items():
            st.session_state.df.at[idx, k] = v
        conn.update(worksheet="Expenses", data=st.session_state.df)
        st.cache_data.clear()

def delete_expense(idx):
    with st.spinner("Deleting..."):
        upd = st.session_state.df.drop(idx).reset_index(drop=True)
        conn.update(worksheet="Expenses", data=upd)
        st.session_state.df = upd
        st.cache_data.clear()

def save_settings(ndf):
    with st.spinner("Saving..."):
        conn.update(worksheet="Settings", data=ndf)
        st.session_state.settings_df = ndf
        st.cache_data.clear()

def save_categories(ndf):
    with st.spinner("Saving..."):
        conn.update(worksheet="Categories", data=ndf)
        st.session_state.cat_df = ndf
        st.cache_data.clear()

def save_modes(ndf):
    with st.spinner("Saving..."):
        conn.update(worksheet="Modes", data=ndf)
        st.session_state.modes_df = ndf
        st.cache_data.clear()

def save_pin(new_pin):
    with st.spinner("Saving PIN..."):
        conn.update(worksheet="Security", data=pd.DataFrame({"PIN": [new_pin]}))
        st.session_state.active_pin = new_pin
        st.cache_data.clear()

# ==============================================================================
# TRANSACTION ROW RENDERER
# ==============================================================================
def render_txn_row(idx, row, key_prefix="txn"):
    date_disp = pd.to_datetime(row["Date"]).strftime("%-d %b %Y, %H:%M") if pd.notna(row["Date"]) else "-"
    note_val  = str(row.get("Note", "") or "").strip()
    edit_key  = f"{key_prefix}_edit_{idx}"
    del_key   = f"{key_prefix}_del_{idx}"
    if edit_key not in st.session_state: st.session_state[edit_key] = False
    if del_key  not in st.session_state: st.session_state[del_key]  = False

    ca, ci, cb = st.columns([2, 5, 1])
    ca.markdown(
        f"<div style='font-size:.9rem;font-weight:700;color:#f0f0f0;padding:8px 0'>"
        f"Rs.{float(row['Amount']):,.0f}</div>",
        unsafe_allow_html=True
    )
    mode_chip = f"<span class='chip'>{row['Mode']}</span>" if str(row.get("Mode","")).strip() else ""
    note_html = f"<div style='font-size:.66rem;color:#444;margin-top:1px;font-style:italic'>{note_val}</div>" if note_val else ""
    ci.markdown(
        f"<div style='padding:8px 0;line-height:1.3'>"
        f"<span style='font-size:.82rem;font-weight:600;color:#bbb'>{row['Category']}</span>"
        f"<br><span style='font-size:.66rem;color:#444'>{date_disp}</span> {mode_chip}{note_html}</div>",
        unsafe_allow_html=True
    )
    if cb.button("✏️", key=f"{key_prefix}_tgl_{idx}"):
        st.session_state[edit_key] = not st.session_state[edit_key]
        st.rerun()
    st.markdown("<hr style='border:none;border-top:1px solid #0e0e0e;margin:0'>", unsafe_allow_html=True)

    if st.session_state[edit_key]:
        with st.container(border=True):
            ea, eb = st.columns(2)
            new_amt  = ea.number_input("Amount", value=float(row["Amount"]), min_value=0.0, key=f"{key_prefix}_eamt_{idx}")
            new_cat  = eb.selectbox("Category", categories,
                index=categories.index(row["Category"]) if row["Category"] in categories else 0,
                key=f"{key_prefix}_ecat_{idx}")
            ec, ed = st.columns(2)
            new_mode = ec.selectbox("Mode", payment_modes,
                index=payment_modes.index(row["Mode"]) if row["Mode"] in payment_modes else 0,
                key=f"{key_prefix}_emode_{idx}")
            new_note = ed.text_input("Note", value=note_val, key=f"{key_prefix}_enote_{idx}")
            b1, b2 = st.columns(2)
            if b1.button("Save changes", key=f"{key_prefix}_save_{idx}", use_container_width=True, type="primary"):
                update_expense(idx, {"Amount": new_amt, "Category": new_cat, "Mode": new_mode, "Note": new_note.strip()})
                st.session_state[edit_key] = False
                st.rerun()
            if not st.session_state[del_key]:
                if b2.button("Delete", key=f"{key_prefix}_delb_{idx}", use_container_width=True):
                    st.session_state[del_key] = True
                    st.rerun()
            else:
                b2.warning("Sure?")
                y_, n_ = b2.columns(2)
                if y_.button("Yes", key=f"{key_prefix}_ydel_{idx}"):
                    delete_expense(idx)
                    st.session_state[edit_key] = False
                    st.session_state[del_key]  = False
                    st.rerun()
                if n_.button("No", key=f"{key_prefix}_ndel_{idx}"):
                    st.session_state[del_key] = False
                    st.rerun()

# ==============================================================================
# PIN GATE
# ==============================================================================
for _k, _v in [("pin_unlocked", False), ("pin_input", ""), ("pin_attempts", 0), ("pin_error", "")]:
    if _k not in st.session_state: st.session_state[_k] = _v

if not st.session_state.pin_unlocked:
    locked_out = st.session_state.pin_attempts >= MAX_PIN_ATTEMPTS
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("### 💰 FinTrack Pro")
        st.markdown("<p style='color:#444;font-size:.8rem;margin-bottom:20px'>Enter your 4-digit PIN</p>", unsafe_allow_html=True)
        entered  = len(st.session_state.pin_input)
        is_error = bool(st.session_state.pin_error)
        dots = "<div style='display:flex;gap:14px;margin-bottom:20px;justify-content:center'>"
        for i in range(4):
            if is_error:   s = "background:#f87171;border:1.5px solid #f87171"
            elif i < entered: s = "background:#2563eb;border:1.5px solid #2563eb"
            else:          s = "background:transparent;border:1.5px solid #2a2a2a"
            dots += f"<div style='width:12px;height:12px;border-radius:50%;{s}'></div>"
        dots += "</div>"
        st.markdown(dots, unsafe_allow_html=True)
        if locked_out:
            st.error("Too many incorrect attempts. Restart to try again.")
            st.stop()
        if st.session_state.pin_error:
            rem = MAX_PIN_ATTEMPTS - st.session_state.pin_attempts
            st.markdown(
                f"<p style='color:#f87171;font-size:.74rem;text-align:center;margin-bottom:10px'>"
                f"Incorrect PIN — {rem} attempt{'s' if rem != 1 else ''} left.</p>",
                unsafe_allow_html=True
            )
        for rk in [["1","2","3"], ["4","5","6"], ["7","8","9"], ["","0","del"]]:
            k1, k2, k3 = st.columns(3)
            for cw, d in zip([k1, k2, k3], rk):
                if d == "":
                    cw.markdown("")
                elif d == "del":
                    if cw.button("⌫", use_container_width=True, key="pin_del"):
                        st.session_state.pin_input = st.session_state.pin_input[:-1]
                        st.session_state.pin_error = ""
                        st.rerun()
                else:
                    if cw.button(d, use_container_width=True, key=f"pin_{d}"):
                        if len(st.session_state.pin_input) < 4:
                            st.session_state.pin_input += d
                            st.session_state.pin_error  = ""
                            if len(st.session_state.pin_input) == 4:
                                if st.session_state.pin_input == st.session_state.active_pin:
                                    st.session_state.pin_unlocked = True
                                    st.session_state.pin_input    = ""
                                    st.session_state.pin_attempts = 0
                                else:
                                    st.session_state.pin_attempts += 1
                                    st.session_state.pin_error    = "wrong"
                                    st.session_state.pin_input    = ""
                            st.rerun()
    st.stop()

# ==============================================================================
# RECURRING AUTO-LOG
# ==============================================================================
if not st.session_state.get("auto_log_checked") and not settings_df.empty:
    fired_any   = False
    updated_sdf = st.session_state.settings_df.copy()
    for i, row in st.session_state.settings_df.iterrows():
        try:
            if str(row.get("Is_Recurring","")).strip().lower() not in ("true","1","yes"):
                continue
            last_f = str(row.get("Last_Fired","")).strip()
            dom    = int(row.get("Day_of_Month", 32))
            amt    = float(row.get("Budget", 0) or 0)
            if last_f == curr_ym or today.day < dom:
                continue
            fire_dt = f"{today.strftime('%Y-%m-%d')} {now.strftime('%H:%M:%S')}"
            save_expense({"Date": fire_dt, "Amount": amt, "Category": row["Category"],
                          "Mode": "Auto", "Note": "Auto-logged (recurring)"})
            updated_sdf.at[i, "Last_Fired"] = curr_ym
            fired_any = True
            st.toast(f"Auto-logged: {row['Category']}  Rs.{amt:,.0f}")
        except:
            pass
    if fired_any:
        save_settings(updated_sdf)
    st.session_state.auto_log_checked = True

# ==============================================================================
# NAVIGATION
# The ONLY reliable way to do bottom nav in Streamlit is to wrap real
# st.buttons inside a stylable_container that has position:fixed + display:flex.
# The container element becomes the fixed bar; buttons inside it are real.
# ==============================================================================
active = st.session_state.active_tab

if is_mobile:
    # ── Thin sticky top bar ──────────────────────────────────────────────────
    st.markdown(
        f"<div style='position:sticky;top:0;z-index:300;background:#080808;"
        f"border-bottom:1px solid #141414;display:flex;align-items:center;"
        f"justify-content:space-between;padding:0 12px;height:44px;'>"
        f"<span style='font-size:.9rem;font-weight:700;color:#f0f0f0'>"
        f"{TAB_ICONS[active]} {PAGE_NAMES[active]}</span>"
        f"</div>",
        unsafe_allow_html=True
    )

    # Appbar action buttons (real, small)
    _ab = ("button{background:#111!important;border:1px solid #1a1a1a!important;"
           "color:#666!important;border-radius:7px!important;font-size:.7rem!important;"
           "min-height:28px!important;height:28px!important;padding:0 8px!important}")
    ac1, ac2, ac3, _sp = st.columns([1, 1, 1, 3])
    with ac1:
        with stylable_container(key="ac_tog", css_styles=_ab):
            if st.button("🖥️", key="view_toggle"):
                st.session_state.view_mode = "desktop"; st.rerun()
    with ac2:
        with stylable_container(key="ac_lock", css_styles=_ab):
            if st.button("🔒", key="lock_btn"):
                st.session_state.pin_unlocked = False
                st.session_state.pin_input = ""
                st.session_state.pin_error = ""
                st.rerun()
    with ac3:
        with stylable_container(key="ac_ref", css_styles=_ab):
            if st.button("↺", key="refresh_btn"):
                hard_refresh()

    # ── Bottom nav: stylable_container IS the fixed bar ─────────────────────
    # The container div itself gets position:fixed so its children (the buttons)
    # are physically inside the fixed bar and respond to clicks correctly.
    _nav_wrap_css = (
        "{"
        "position:fixed;bottom:0;left:50%;transform:translateX(-50%);"
        "width:100%;max-width:430px;background:#080808;"
        "border-top:1px solid #141414;z-index:400;"
        "display:flex;flex-direction:row;padding:0;"
        "}"
    )
    with stylable_container(key="bottom_nav_bar", css_styles=_nav_wrap_css):
        _btn_base = (
            "button{{"
            "background:{bg}!important;border:none!important;"
            "border-top:{border}!important;"
            "color:{col}!important;font-size:.52rem!important;font-weight:600!important;"
            "width:100%!important;min-height:54px!important;height:54px!important;"
            "border-radius:0!important;padding:6px 2px 4px!important;"
            "display:flex!important;flex-direction:column!important;"
            "align-items:center!important;justify-content:center!important;"
            "gap:2px!important;text-transform:uppercase;letter-spacing:.5px"
            "}}"
        )
        nav_cols = st.columns(6)
        for i in range(6):
            is_act = (i == active)
            css = _btn_base.format(
                bg     = "#080808",
                border = ("2px solid #2563eb" if is_act else "2px solid transparent"),
                col    = ("#2563eb" if is_act else "#3a3a3a"),
            )
            with nav_cols[i]:
                with stylable_container(key=f"bnav_{i}", css_styles=css):
                    if st.button(f"{TAB_ICONS[i]}\n{TAB_SHORT[i]}", key=f"nav_{i}"):
                        st.session_state.active_tab = i
                        st.rerun()

else:
    # ── Desktop: horizontal tab row ──────────────────────────────────────────
    _tnav_a = ("button{background:transparent!important;border:none!important;"
               "border-bottom:2px solid #2563eb!important;color:#e8e8e8!important;"
               "font-size:.82rem!important;font-weight:700!important;"
               "padding:10px 14px!important;border-radius:0!important;min-height:40px!important}")
    _tnav_i = ("button{background:transparent!important;border:none!important;"
               "border-bottom:1px solid #1c1c1c!important;color:#484848!important;"
               "font-size:.82rem!important;font-weight:500!important;"
               "padding:10px 14px!important;border-radius:0!important;min-height:40px!important}")

    tab_row = st.columns(6)
    for i in range(6):
        with tab_row[i]:
            with stylable_container(key=f"tnav_{i}", css_styles=(_tnav_a if i == active else _tnav_i)):
                if st.button(f"{TAB_ICONS[i]} {TABS[i]}", key=f"nav_{i}"):
                    st.session_state.active_tab = i
                    st.rerun()

    # Desktop header row
    h1, h2, h3, h4 = st.columns([4, 1, 1, 1])
    h1.markdown(f"<div style='font-size:1.4rem;font-weight:700;color:#f0f0f0;margin:10px 0 6px'>{PAGE_NAMES[active]}</div>", unsafe_allow_html=True)
    if h2.button("📱 Mobile", key="view_toggle", use_container_width=True):
        st.session_state.view_mode = "mobile"; st.rerun()
    if h3.button("🔒 Lock", key="lock_btn", use_container_width=True):
        st.session_state.pin_unlocked = False; st.session_state.pin_input = ""; st.session_state.pin_error = ""; st.rerun()
    if h4.button("↺ Refresh", key="refresh_btn", use_container_width=True):
        hard_refresh()

# ==============================================================================
# CONTENT ROUTING
# ==============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
if active == T_DASH:
    if df.empty:
        st.markdown('<div class="empty-box"><div class="ico">📊</div><div class="msg">No data yet.<br>Tap + to log your first expense.</div></div>', unsafe_allow_html=True)
    else:
        curr_filt = df[df["Date"].dt.to_period("M").astype(str) == curr_ym].copy()
        prev_ym   = (pd.Period(curr_ym, "M") - 1).strftime("%Y-%m")
        prev_filt = df[df["Date"].dt.to_period("M").astype(str) == prev_ym].copy()
        month_total = curr_filt["Amount"].sum()
        prev_total  = prev_filt["Amount"].sum()
        today_total = df[df["Date"].dt.date == today]["Amount"].sum()
        week_start  = today - timedelta(days=today.weekday())
        week_total  = df[df["Date"].dt.date >= week_start]["Amount"].sum()
        txn_count   = len(curr_filt)
        avg_txn     = (curr_filt["Amount"].mean() if txn_count > 0 else 0)

        if prev_total > 0:
            mom_pct = (month_total - prev_total) / prev_total * 100
            sign    = "+" if mom_pct > 0 else ""
            col_m   = "#f87171" if mom_pct > 0 else "#34d399"
            mom_str = f'<span style="color:{col_m};font-weight:700">{sign}{mom_pct:.0f}% vs {prev_ym}</span>'
        else:
            mom_str = '<span style="color:#3a3a3a">First month on record</span>'

        # Hero card
        st.markdown(
            f'<div class="dash-hero">'
            f'<div class="dash-hero-label">This Month — {now.strftime("%B %Y")}</div>'
            f'<div class="dash-hero-amount">Rs.{month_total:,.0f}</div>'
            f'<div class="dash-hero-sub">{mom_str}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # 3 stat chips
        s1, s2, s3 = st.columns(3)
        for col_w, lbl, val in [
            (s1, "Today",      f"Rs.{today_total:,.0f}"),
            (s2, "This Week",  f"Rs.{week_total:,.0f}"),
            (s3, "Avg / Txn",  f"Rs.{avg_txn:,.0f}"),
        ]:
            col_w.markdown(
                f'<div class="dash-stat">'
                f'<div class="dash-stat-lbl">{lbl}</div>'
                f'<div class="dash-stat-val">{val}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        # 7-day bar chart
        st.markdown('<p class="sec-head">Last 7 Days</p>', unsafe_allow_html=True)
        days7      = [today - timedelta(days=i) for i in range(6, -1, -1)]
        day_totals = [df[df["Date"].dt.date == d]["Amount"].sum() for d in days7]
        max_day    = max(day_totals) or 1
        bars = "<div style='display:flex;align-items:flex-end;gap:4px;height:56px;margin-top:4px'>"
        for d, v in zip(days7, day_totals):
            h   = max(int(v / max_day * 52), 3)
            bg  = "#2563eb" if d == today else "#1a2e50"
            bars += (
                f"<div class='dash-bar-col'>"
                f"<div class='dash-bar-fill' style='height:{h}px;background:{bg}'></div>"
                f"<span class='dash-bar-day'>{d.strftime('%a')[:2]}</span>"
                f"</div>"
            )
        bars += "</div>"
        st.markdown(bars, unsafe_allow_html=True)

        # Top 5 categories this month
        st.markdown('<p class="sec-head">Top Categories</p>', unsafe_allow_html=True)
        if not curr_filt.empty:
            cat_top   = curr_filt.groupby("Category")["Amount"].sum().sort_values(ascending=False).head(5)
            max_c     = cat_top.max() or 1
            cat_icons = {"Food":"🍔","Groceries":"🛒","Fuel":"⛽","Entertainment":"🎬",
                         "Vegetables":"🥦","Rent":"🏠","Snacks":"☕","Travel":"✈️",
                         "Shopping":"🛍️","Health":"💊","Utilities":"💡","Dining":"🍽️"}
            for cat, amt in cat_top.items():
                icon = cat_icons.get(cat, "💸")
                pct  = (amt / month_total * 100) if month_total > 0 else 0
                bar  = int(amt / max_c * 100)
                st.markdown(
                    f'<div style="display:flex;align-items:center;padding:7px 0;border-bottom:1px solid #0e0e0e">'
                    f'<div class="dash-txn-icon" style="background:#0e1a2e">{icon}</div>'
                    f'<div style="flex:1;min-width:0">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:3px">'
                    f'<span style="font-size:.82rem;font-weight:600;color:#bbb">{cat}</span>'
                    f'<span style="font-size:.82rem;font-weight:700;color:#e0e0e0">Rs.{amt:,.0f}</span></div>'
                    f'<div style="background:#151515;border-radius:3px;height:3px">'
                    f'<div style="width:{bar}%;background:#2563eb;height:3px;border-radius:3px"></div></div>'
                    f'</div>'
                    f'<span style="font-size:.64rem;color:#3a3a3a;margin-left:8px;min-width:28px;text-align:right">{pct:.0f}%</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        # Recent 8 transactions
        st.markdown('<p class="sec-head">Recent</p>', unsafe_allow_html=True)
        recent = df.sort_values("Date", ascending=False).head(8)
        ibg_pool = ["#0e1a0e","#0a0a1e","#1e0a0a","#1a140a","#0a141e","#140a1e","#101818","#181010"]
        for ix, (_, row) in enumerate(recent.iterrows()):
            icon = cat_icons.get(row["Category"], "💸") if 'cat_icons' in dir() else "💸"
            dstr = pd.to_datetime(row["Date"]).strftime("%-d %b, %H:%M") if pd.notna(row["Date"]) else "-"
            note = str(row.get("Note","") or "").strip()
            meta = f"{dstr} · {row['Mode']}" + (f" · {note}" if note else "")
            st.markdown(
                f'<div class="dash-txn-row">'
                f'<div class="dash-txn-icon" style="background:{ibg_pool[ix % 8]}">{icon}</div>'
                f'<div style="flex:1;min-width:0">'
                f'<div class="dash-txn-cat">{row["Category"]}</div>'
                f'<div class="dash-txn-meta">{meta}</div>'
                f'</div>'
                f'<div class="dash-txn-amt">−Rs.{float(row["Amount"]):,.0f}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        # HDFC Milestone
        q_map   = {1:1,2:1,3:1,4:2,5:2,6:2,7:3,8:3,9:3,10:4,11:4,12:4}
        curr_q  = q_map[now.month]
        h_spend = df[
            (df["Date"].dt.month.map(q_map) == curr_q) &
            (df["Date"].dt.year == now.year) &
            (df["Mode"] == "HDFC Credit Card")
        ]["Amount"].sum()
        h_pct = min(h_spend / HDFC_MILESTONE_AMT * 100, 100)
        h_col = "#2563eb" if h_pct < 75 else ("#facc15" if h_pct < 100 else "#34d399")
        st.markdown('<p class="sec-head">HDFC Milestone</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="tile" style="border-left:3px solid {h_col}">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
            f'<span style="font-size:.78rem;color:#bbb;font-weight:600">Q{curr_q} — HDFC Credit Card</span>'
            f'<span style="font-size:.78rem;font-weight:700;color:{h_col}">Rs.{h_spend:,.0f} / Rs.{HDFC_MILESTONE_AMT:,.0f}</span>'
            f'</div>'
            f'<div class="prog-track"><div class="prog-fill" style="width:{h_pct:.1f}%;background:{h_col}"></div></div>'
            f'<div class="prog-meta"><span>{h_pct:.1f}% reached</span>'
            f'<span>Rs.{max(HDFC_MILESTONE_AMT - h_spend, 0):,.0f} to go</span></div>'
            f'</div>',
            unsafe_allow_html=True
        )

# ─────────────────────────────────────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────────────────────────────────────
elif active == T_HOME:
    if df.empty:
        st.markdown('<div class="empty-box"><div class="ico">💸</div><div class="msg">No expenses yet.<br>Tap + to get started.</div></div>', unsafe_allow_html=True)
    else:
        all_months = sorted(df["Date"].dropna().dt.to_period("M").unique().astype(str).tolist(), reverse=True)
        sel_month  = st.selectbox("Period", all_months, index=0, label_visibility="collapsed")
        sel_period = pd.Period(sel_month, freq="M")
        prev_period = sel_period - 1
        filt = df[df["Date"].dt.to_period("M") == sel_period].copy()
        prev = df[df["Date"].dt.to_period("M") == prev_period].copy()
        month_total = filt["Amount"].sum()
        prev_total  = prev["Amount"].sum()

        if prev_total > 0:
            pct_diff = (month_total - prev_total) / prev_total * 100
            trend_html = (
                f'<span class="{"trend-up" if pct_diff > 0 else "trend-down"}">'
                f'{"+" if pct_diff > 0 else ""}{pct_diff:.0f}% vs {str(prev_period)}</span>'
            )
        else:
            trend_html = '<span class="trend-flat">First month</span>'

        if is_mobile:
            if sel_month == curr_ym:
                today_total = df[df["Date"].dt.date == today]["Amount"].sum()
                st.markdown(
                    f'<div class="tile"><div class="tile-accent" style="background:#2563eb"></div>'
                    f'<div class="tile-label">Spent Today</div>'
                    f'<div class="tile-value">Rs.{today_total:,.0f}</div></div>',
                    unsafe_allow_html=True
                )
            st.markdown(
                f'<div class="tile"><div class="tile-accent" style="background:#7c3aed"></div>'
                f'<div class="tile-label">This Month</div>'
                f'<div class="tile-value">Rs.{month_total:,.0f}</div>'
                f'<div class="tile-sub">{trend_html}</div></div>',
                unsafe_allow_html=True
            )
        else:
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
                    f'<div class="tile-value" style="font-size:1.1rem">{sel_month}</div></div>',
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
        h_pct = min(h_spend / HDFC_MILESTONE_AMT * 100, 100)
        h_col = "#2563eb" if h_pct < 75 else ("#facc15" if h_pct < 100 else "#34d399")
        remaining = max(HDFC_MILESTONE_AMT - h_spend, 0)
        st.markdown(
            f'<div class="tile" style="border-left:3px solid {h_col}">'
            f'<div class="tile-label">HDFC Q{curr_q} Milestone</div>'
            f'<div class="tile-value">Rs.{h_spend:,.0f}'
            f'<span style="font-size:.78rem;color:#3a3a3a;font-weight:400"> / Rs.{HDFC_MILESTONE_AMT:,.0f}</span></div>'
            f'<div style="margin-top:7px"><div class="prog-track">'
            f'<div class="prog-fill" style="width:{h_pct:.1f}%;background:{h_col}"></div></div>'
            f'<div class="prog-meta"><span>{h_pct:.1f}%</span><span>Rs.{remaining:,.0f} to go</span></div></div></div>',
            unsafe_allow_html=True
        )

        budgets = (
            st.session_state.settings_df[
                st.session_state.settings_df["Budget"].notna() &
                (st.session_state.settings_df["Budget"].astype(str).str.strip() != "")
            ].copy()
            if not st.session_state.settings_df.empty
            else pd.DataFrame()
        )
        if not budgets.empty:
            st.markdown('<p class="sec-head">Budget Tracker</p>', unsafe_allow_html=True)
            for _, brow in budgets.iterrows():
                blimit = float(brow.get("Budget", 0) or 0)
                if blimit <= 0: continue
                bspent = filt[filt["Category"] == brow["Category"]]["Amount"].sum()
                bpct   = min(bspent / blimit * 100, 100)
                bcol   = "#34d399" if bpct < 75 else ("#facc15" if bpct < 100 else "#f87171")
                st.markdown(
                    f'<div class="budget-row"><div class="budget-header">'
                    f'<span class="budget-name">{brow["Category"]}{"  ⚠️" if bspent > blimit else ""}</span>'
                    f'<span class="budget-nums">Rs.{bspent:,.0f} / Rs.{blimit:,.0f}</span></div>'
                    f'<div class="prog-track"><div class="prog-fill" style="width:{bpct:.1f}%;background:{bcol}"></div></div></div>',
                    unsafe_allow_html=True
                )

        st.markdown('<p class="sec-head">By Category</p>', unsafe_allow_html=True)
        if not filt.empty:
            cat_sum = filt.groupby("Category")["Amount"].sum().sort_values(ascending=False).reset_index()
            max_amt = cat_sum["Amount"].max() or 1
            for _, crow in cat_sum.iterrows():
                st.markdown(
                    f'<div class="cat-row"><span class="cat-name">{crow["Category"]}</span>'
                    f'<div class="cat-bar-wrap"><div class="cat-bar-fill" style="width:{crow["Amount"]/max_amt*100:.0f}%"></div></div>'
                    f'<span class="cat-amt">Rs.{crow["Amount"]:,.0f}</span></div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<div class="empty-box"><div class="ico">📊</div><div class="msg">No data for this period.</div></div>', unsafe_allow_html=True)

        st.markdown('<p class="sec-head">Recent Transactions</p>', unsafe_allow_html=True)
        sq = st.text_input("search_home", placeholder="Filter by category, mode or note...", label_visibility="collapsed")
        txn_df = filt.copy()
        if sq.strip():
            mask = (
                txn_df["Category"].astype(str).str.contains(sq, case=False, na=False) |
                txn_df["Note"].astype(str).str.contains(sq, case=False, na=False) |
                txn_df["Mode"].astype(str).str.contains(sq, case=False, na=False)
            )
            txn_df = txn_df[mask]
        txn_df = txn_df.sort_values("Date", ascending=False).head(RECENT_TXN_COUNT)
        if txn_df.empty:
            st.markdown('<div class="empty-box"><div class="ico">🔍</div><div class="msg">No transactions match.</div></div>', unsafe_allow_html=True)
        else:
            for idx, row in txn_df.iterrows():
                render_txn_row(idx, row, key_prefix="home")

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────
elif active == T_CATS:
    if df.empty:
        st.markdown('<div class="empty-box"><div class="ico">🏷️</div><div class="msg">No data yet.</div></div>', unsafe_allow_html=True)
    else:
        total_all  = df["Amount"].sum()
        total_txns = len(df)
        span_days  = max((df["Date"].max() - df["Date"].min()).days, 1)

        if is_mobile:
            st.markdown(
                f'<div class="tile"><div class="tile-accent" style="background:#2563eb"></div>'
                f'<div class="tile-label">All Time</div>'
                f'<div class="tile-value">Rs.{total_all:,.0f}</div>'
                f'<div class="tile-sub" style="color:#3a3a3a">{total_txns} transactions · Avg Rs.{total_all/span_days:,.0f}/day</div></div>',
                unsafe_allow_html=True
            )
        else:
            s1, s2, s3 = st.columns(3)
            for cw, lbl, clr, val in [
                (s1, "All Time",    "#2563eb", f"Rs.{total_all:,.0f}"),
                (s2, "Transactions","#7c3aed", f"{total_txns:,}"),
                (s3, "Daily Avg",   "#0d9488", f"Rs.{total_all/span_days:,.0f}"),
            ]:
                cw.markdown(
                    f'<div class="tile"><div class="tile-accent" style="background:{clr}"></div>'
                    f'<div class="tile-label">{lbl}</div>'
                    f'<div class="tile-value" style="font-size:1.35rem">{val}</div></div>',
                    unsafe_allow_html=True
                )

        st.markdown('<p class="sec-head">All Categories — All Time</p>', unsafe_allow_html=True)
        sort_opt = st.radio("Sort", ["Total Spend","No. of Transactions","Avg Transaction","A to Z"],
                            horizontal=True, label_visibility="collapsed")
        cat_grp = df.groupby("Category").agg(
            Total=("Amount","sum"), Count=("Amount","count"),
            Avg=("Amount","mean"),  Last=("Date","max"),
        ).reset_index()
        if   sort_opt == "Total Spend":         cat_grp = cat_grp.sort_values("Total", ascending=False)
        elif sort_opt == "No. of Transactions": cat_grp = cat_grp.sort_values("Count", ascending=False)
        elif sort_opt == "Avg Transaction":     cat_grp = cat_grp.sort_values("Avg",   ascending=False)
        else:                                   cat_grp = cat_grp.sort_values("Category")
        max_total = cat_grp["Total"].max() or 1

        for _, crow in cat_grp.iterrows():
            cat_name  = crow["Category"]
            cat_total = crow["Total"]
            cat_count = int(crow["Count"])
            cat_last  = pd.to_datetime(crow["Last"]).strftime("%-d %b %Y") if pd.notna(crow["Last"]) else "-"
            share_pct = cat_total / total_all * 100 if total_all > 0 else 0
            st.markdown(
                f'<div class="cat-hero">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div><div style="font-size:.92rem;font-weight:700;color:#e8e8e8">{cat_name}</div>'
                f'<div style="font-size:.68rem;color:#3a3a3a;margin-top:2px">'
                f'{cat_count} txns · Avg Rs.{crow["Avg"]:,.0f} · {share_pct:.1f}% · Last {cat_last}</div></div>'
                f'<div style="font-size:1.05rem;font-weight:700;color:#2563eb;white-space:nowrap">Rs.{cat_total:,.0f}</div></div>'
                f'<div style="margin-top:7px;background:#151515;border-radius:3px;height:3px">'
                f'<div style="width:{cat_total/max_total*100:.1f}%;background:#2563eb;height:3px;border-radius:3px"></div></div>'
                f'</div>',
                unsafe_allow_html=True
            )
            vk = f"view_cat_{cat_name}"
            if vk not in st.session_state: st.session_state[vk] = False
            if st.button(f"{'Hide' if st.session_state[vk] else f'Show all {cat_count}'} entries", key=f"btn_cat_{cat_name}"):
                st.session_state[vk] = not st.session_state[vk]; st.rerun()
            if st.session_state[vk]:
                cat_entries = df[df["Category"] == cat_name].sort_values("Date", ascending=False)
                with st.container(border=True):
                    cat_months = sorted(
                        cat_entries["Date"].dropna().dt.to_period("M").unique().astype(str).tolist(),
                        reverse=True
                    )
                    mf = st.selectbox("Filter month", ["All months"] + cat_months,
                                      key=f"mf_{cat_name}", label_visibility="collapsed")
                    if mf != "All months":
                        cat_entries = cat_entries[cat_entries["Date"].dt.to_period("M").astype(str) == mf]
                    sub_total = cat_entries["Amount"].sum()
                    st.markdown(
                        f"<p style='font-size:.7rem;color:#3a3a3a;margin-bottom:6px'>"
                        f"{len(cat_entries)} entries · Rs.{sub_total:,.0f}</p>",
                        unsafe_allow_html=True
                    )
                    for idx, erow in cat_entries.iterrows():
                        render_txn_row(idx, erow, key_prefix=f"cat_{cat_name}")
            st.markdown("<div style='height:3px'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SEARCH
# ─────────────────────────────────────────────────────────────────────────────
elif active == T_SEARCH:
    if df.empty:
        st.markdown('<div class="empty-box"><div class="ico">🔍</div><div class="msg">No data to search yet.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="sec-head">Filters</p>', unsafe_allow_html=True)
        keyword = st.text_input("Keyword", placeholder="Category, note, mode...", label_visibility="collapsed")
        dr1, dr2 = st.columns(2)
        min_date  = df["Date"].min().date() if not df.empty else date(2020, 1, 1)
        max_date  = max(df["Date"].max().date() if not df.empty else today, today)
        date_from = dr1.date_input("From", value=min_date, min_value=min_date, max_value=max_date, key="sf_from")
        date_to   = dr2.date_input("To",   value=today,    min_value=min_date, max_value=max_date, key="sf_to")
        fm1, fm2 = st.columns(2)
        sel_cats  = fm1.multiselect("Categories", options=sorted(df["Category"].dropna().unique().tolist()), placeholder="All categories")
        sel_modes = fm2.multiselect("Modes",      options=sorted(df["Mode"].dropna().unique().tolist()),     placeholder="All modes")
        fa1, fa2 = st.columns(2)
        amt_min = fa1.number_input("Min Rs.", min_value=0.0, value=0.0, step=100.0, key="sf_amin")
        amt_max = fa2.number_input("Max Rs.", min_value=0.0, value=float(df["Amount"].max() or 100000), step=100.0, key="sf_amax")
        fc1, fc2, fc3, fc4 = st.columns(4)
        only_noted = fc1.checkbox("Has note",    key="sf_noted")
        only_auto  = fc2.checkbox("Auto",        key="sf_auto")
        only_cc    = fc3.checkbox("Credit card", key="sf_cc")
        only_today_f = fc4.checkbox("Today",     key="sf_today")
        fs1, fs2 = st.columns([3, 1])
        sort_by = fs1.selectbox("Sort", ["Date (newest)","Date (oldest)","Amount (highest)","Amount (lowest)","Category A-Z"], label_visibility="collapsed")
        if fs2.button("Clear", use_container_width=True):
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
                result["Note"].astype(str).str.contains(kw, case=False, na=False) |
                result["Mode"].astype(str).str.contains(kw, case=False, na=False)
            )
            result = result[mask]
        if sel_cats:    result = result[result["Category"].isin(sel_cats)]
        if sel_modes:   result = result[result["Mode"].isin(sel_modes)]
        result = result[(result["Amount"] >= amt_min) & (result["Amount"] <= amt_max)]
        if only_noted:   result = result[result["Note"].astype(str).str.strip().ne("").ne("nan")]
        if only_auto:    result = result[result["Note"].astype(str).str.contains("Auto-logged", case=False, na=False)]
        if only_cc:      result = result[result["Mode"].astype(str).str.contains("Credit Card", case=False, na=False)]
        if only_today_f: result = result[result["Date"].dt.date == today]

        if   sort_by == "Date (newest)":      result = result.sort_values("Date",     ascending=False)
        elif sort_by == "Date (oldest)":      result = result.sort_values("Date",     ascending=True)
        elif sort_by == "Amount (highest)":   result = result.sort_values("Amount",   ascending=False)
        elif sort_by == "Amount (lowest)":    result = result.sort_values("Amount",   ascending=True)
        else:                                 result = result.sort_values("Category", ascending=True)

        r_count = len(result)
        r_total = result["Amount"].sum()
        r_avg   = result["Amount"].mean() if r_count > 0 else 0

        # Results summary tile
        st.markdown(
            f'<div class="tile" style="margin-top:8px">'
            f'<div class="tile-accent" style="background:#2563eb"></div>'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<div><div class="tile-label">Results</div>'
            f'<div class="tile-value" style="font-size:1.4rem">{r_count:,}</div></div>'
            f'<div style="text-align:right">'
            f'<div class="tile-label">Total</div>'
            f'<div style="font-size:1.05rem;font-weight:700;color:#f0f0f0">Rs.{r_total:,.0f}</div>'
            f'<div style="font-size:.68rem;color:#3a3a3a;margin-top:1px">Avg Rs.{r_avg:,.0f}</div>'
            f'</div></div></div>',
            unsafe_allow_html=True
        )

        if r_count > 0:
            csv_buf = io.StringIO()
            result[["Date","Category","Amount","Mode","Note"]].to_csv(csv_buf, index=False)
            st.download_button(
                f"Export {r_count} results as CSV",
                data=csv_buf.getvalue(),
                file_name=f"fintrack_{today}.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.markdown('<p class="sec-head">Results</p>', unsafe_allow_html=True)
        if result.empty:
            st.markdown('<div class="empty-box"><div class="ico">🔍</div><div class="msg">No transactions match.<br>Try relaxing the filters.</div></div>', unsafe_allow_html=True)
        else:
            for idx, row in result.iterrows():
                render_txn_row(idx, row, key_prefix="srch")

# ─────────────────────────────────────────────────────────────────────────────
# RECURRING
# ─────────────────────────────────────────────────────────────────────────────
elif active == T_REC:
    with st.expander("Create New Rule"):
        with st.form("new_rec"):
            rc1, rc2 = st.columns(2)
            c_sel = rc1.selectbox("Category", categories)
            a_sel = rc2.number_input("Amount (Rs.)", min_value=0.0, value=None, placeholder="0.00")
            d_sel = st.slider("Auto-log on day of month", 1, 31, 1)
            if st.form_submit_button("Add Rule", type="primary"):
                if a_sel:
                    new_row = pd.DataFrame([{"Category": c_sel, "Budget": a_sel,
                                             "Is_Recurring": True, "Day_of_Month": d_sel, "Last_Fired": ""}])
                    save_settings(pd.concat([st.session_state.settings_df, new_row], ignore_index=True))
                    st.rerun()
                else:
                    st.warning("Please enter an amount.")

    if st.session_state.settings_df.empty:
        st.markdown('<div class="empty-box"><div class="ico">🔄</div><div class="msg">No recurring rules yet.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="sec-head">Active Rules</p>', unsafe_allow_html=True)
        for i, row in st.session_state.settings_df.iterrows():
            try:
                dom        = int(row.get("Day_of_Month", 0))
                last_fired = str(row.get("Last_Fired", "")).strip()
                fired_this = (last_fired == curr_ym)
                card_cls   = "rec-fired" if fired_this else "rec-pending"
                status_txt = f"✅ Fired {curr_ym}" if fired_this else f"⏳ Due on day {dom}"
                st.markdown(
                    f'<div class="rec-card {card_cls}">'
                    f'<div style="font-size:.88rem;font-weight:600;color:#e0e0e0">{row["Category"]}</div>'
                    f'<div style="font-size:.72rem;color:#3a3a3a;margin-top:3px">Rs.{float(row["Budget"]):,.0f} · {status_txt}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                ck = f"crec_{i}"
                if ck not in st.session_state: st.session_state[ck] = False
                r1, r2 = st.columns([5, 1])
                if not st.session_state[ck]:
                    if r2.button("Delete", key=f"del_rec_{i}", use_container_width=True):
                        st.session_state[ck] = True; st.rerun()
                else:
                    r1.warning("Delete this rule?")
                    ya, na = r1.columns(2)
                    if ya.button("Yes", key=f"yrec_{i}"):
                        save_settings(st.session_state.settings_df.drop(i).reset_index(drop=True))
                        st.session_state[ck] = False; st.rerun()
                    if na.button("No", key=f"nrec_{i}"):
                        st.session_state[ck] = False; st.rerun()
            except:
                pass

# ─────────────────────────────────────────────────────────────────────────────
# MANAGE
# ─────────────────────────────────────────────────────────────────────────────
elif active == T_MANAGE:
    st.markdown('<p class="sec-head">Payment Modes</p>', unsafe_allow_html=True)
    with st.form("new_mode"):
        nm1, nm2 = st.columns([4, 1])
        nm = nm1.text_input("New mode", label_visibility="collapsed", placeholder="e.g. ICICI Credit Card")
        if nm2.form_submit_button("Add", use_container_width=True):
            if nm.strip():
                save_modes(pd.concat([st.session_state.modes_df, pd.DataFrame([{"Mode": nm.strip()}])], ignore_index=True))
                st.rerun()
            else:
                st.warning("Mode name cannot be empty.")
    for i, row in st.session_state.modes_df.iterrows():
        mc1, mc2 = st.columns([5, 1])
        mc1.markdown(f'<div class="catlist-row">{row["Mode"]}</div>', unsafe_allow_html=True)
        mck = f"cmode_{i}"
        if mck not in st.session_state: st.session_state[mck] = False
        if not st.session_state[mck]:
            if mc2.button("Del", key=f"del_mode_{i}", use_container_width=True):
                st.session_state[mck] = True; st.rerun()
        else:
            mc2.warning("Sure?")
            my_, mn_ = mc2.columns(2)
            if my_.button("Y", key=f"ymode_{i}"):
                save_modes(st.session_state.modes_df.drop(i).reset_index(drop=True))
                st.session_state[mck] = False; st.rerun()
            if mn_.button("N", key=f"nmode_{i}"):
                st.session_state[mck] = False; st.rerun()

    st.markdown('<p class="sec-head">Categories</p>', unsafe_allow_html=True)
    with st.form("new_cat"):
        cc1, cc2 = st.columns([4, 1])
        nc = cc1.text_input("New category", label_visibility="collapsed", placeholder="e.g. Dining Out")
        if cc2.form_submit_button("Add", use_container_width=True):
            if nc.strip():
                save_categories(pd.concat([st.session_state.cat_df, pd.DataFrame([{"Category": nc.strip()}])], ignore_index=True))
                st.rerun()
            else:
                st.warning("Category name cannot be empty.")
    if st.session_state.cat_df.empty:
        st.markdown('<div class="empty-box"><div class="ico">🏷️</div><div class="msg">No categories yet.</div></div>', unsafe_allow_html=True)
    else:
        for i, row in st.session_state.cat_df.iterrows():
            cc1, cc2 = st.columns([5, 1])
            cc1.markdown(f'<div class="catlist-row">{row["Category"]}</div>', unsafe_allow_html=True)
            cck = f"ccat_{i}"
            if cck not in st.session_state: st.session_state[cck] = False
            if not st.session_state[cck]:
                if cc2.button("Del", key=f"del_cat_{i}", use_container_width=True):
                    st.session_state[cck] = True; st.rerun()
            else:
                cc2.warning("Sure?")
                cy_, cn_ = cc2.columns(2)
                if cy_.button("Y", key=f"ycat_{i}"):
                    save_categories(st.session_state.cat_df.drop(i).reset_index(drop=True))
                    st.session_state[cck] = False; st.rerun()
                if cn_.button("N", key=f"ncat_{i}"):
                    st.session_state[cck] = False; st.rerun()

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
# FAB — QUICK LOG
# ==============================================================================
if "show_modal" not in st.session_state:
    st.session_state.show_modal = False

if st.session_state.show_modal:
    @st.dialog("Quick Log")
    def log_modal():
        if "form_id" not in st.session_state: st.session_state.form_id = 0
        if "last_log" in st.session_state:
            ll = st.session_state.last_log
            st.success(f"Logged: Rs.{ll['amt']:,.0f} under {ll['cat']}")
        live_cats  = sorted(st.session_state.cat_df["Category"].dropna().tolist()) if not st.session_state.cat_df.empty else []
        live_modes = st.session_state.modes_df["Mode"].dropna().tolist() if not st.session_state.modes_df.empty else DEFAULT_MODES
        fid = st.session_state.form_id
        amt = st.number_input("Amount (Rs.)", min_value=0.0, value=None, placeholder="Enter amount", key=f"amt_{fid}")
        if amt and amt > LARGE_AMT_WARNING:
            st.warning(f"Rs.{amt:,.0f} is unusually large.")
        dc = st.radio("Date", ["Today","Yesterday","Pick a date"], horizontal=True, key=f"ds_{fid}")
        if dc == "Today":     log_date = today
        elif dc == "Yesterday": log_date = today - timedelta(days=1)
        else:                   log_date = st.date_input("Pick date", value=today, key=f"date_{fid}")
        ma, mb = st.columns(2)
        cat  = ma.selectbox("Category", live_cats,  key=f"cat_{fid}")
        mode = mb.selectbox("Mode",     live_modes, key=f"mode_{fid}")
        note = st.text_input("Note (optional)", value="", placeholder="Merchant, tag...", key=f"note_{fid}")
        c1, c2 = st.columns(2)
        if c1.button("Save & Add More", type="primary", use_container_width=True):
            if not amt or amt <= 0:
                st.warning("Please enter a valid amount."); return
            now_ts = datetime.now(TZ).timestamp()
            last_ts = st.session_state.get("last_save_ts", 0)
            if ((now_ts - last_ts) < 3 and
                    st.session_state.get("last_save_amt") == amt and
                    st.session_state.get("last_save_cat") == cat):
                st.warning("Duplicate detected."); return
            final_dt = f"{log_date.strftime('%Y-%m-%d')} {datetime.now(TZ).strftime('%H:%M:%S')}"
            save_expense({"Date": final_dt, "Amount": amt, "Category": cat, "Mode": mode, "Note": note.strip()})
            st.session_state.update({
                "last_save_ts": now_ts, "last_save_amt": amt, "last_save_cat": cat,
                "last_log": {"amt": amt, "cat": cat}, "form_id": fid + 1,
            })
            st.rerun()
        if c2.button("Finish", use_container_width=True):
            st.session_state.show_modal = False
            for k in ["last_log","last_save_ts","last_save_amt","last_save_cat"]:
                st.session_state.pop(k, None)
            st.rerun()
    log_modal()

_fab_css = (
    "button{position:fixed;bottom:64px;right:16px;width:50px;height:50px;"
    "border-radius:50%;background:#2563eb;color:#fff;font-size:28px;z-index:9999;"
    "border:none;box-shadow:0 4px 18px rgba(37,99,235,.6)}"
) if is_mobile else (
    "button{position:fixed;bottom:30px;right:30px;width:56px;height:56px;"
    "border-radius:50%;background:#2563eb;color:#fff;font-size:30px;z-index:9999;"
    "border:none;box-shadow:0 6px 22px rgba(37,99,235,.5)}"
)
with stylable_container(key="fab", css_styles=_fab_css):
    if st.button("+", key="main_plus_btn"):
        st.session_state.show_modal = True
        st.rerun()

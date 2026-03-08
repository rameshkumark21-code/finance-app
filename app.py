import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import pytz
from streamlit_extras.stylable_container import stylable_container

# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
RECENT_TXN_COUNT   = 10
HDFC_MILESTONE_AMT = 100_000   # T6: Change here to reconfigure target
LARGE_AMT_WARNING  = 50_000    # T12: Soft warning threshold
TZ                 = pytz.timezone('Asia/Kolkata')
DEFAULT_MODES      = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]

# ═══════════════════════════════════════════════════════════════════════════════
# 2. PAGE CONFIG + CSS (DM Sans, unified blue accent, refined dark theme)
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="FinTrack Pro", page_icon="₹", layout="centered")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&display=swap" rel="stylesheet">
<style>
/* ── GLOBAL ── */
*, body { font-family: 'DM Sans', sans-serif !important; }
.stApp { background-color: #080808; color: #e8e8e8; }
[data-testid="stHeader"] { background: transparent; }
h1, h2, h3, h4 { font-family: 'DM Sans', sans-serif !important; letter-spacing: -0.3px; }

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px; background: transparent;
    border-bottom: 1px solid #1c1c1c; padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    height: 40px; background: transparent;
    border-radius: 8px 8px 0 0; padding: 0 16px;
    color: #555; font-size: 0.85rem; font-weight: 500;
    transition: color 0.15s;
}
.stTabs [data-baseweb="tab"]:hover { color: #999 !important; }
.stTabs [aria-selected="true"] {
    background: transparent !important; color: #e8e8e8 !important;
    border-bottom: 2px solid #2563eb !important; font-weight: 600 !important;
}

/* ── TILES ── */
.tile {
    background: #101010; border: 1px solid #1c1c1c;
    border-radius: 14px; padding: 16px 18px; margin-bottom: 10px;
    position: relative;
}
.tile-accent { height: 3px; border-radius: 2px 2px 0 0; margin-bottom: 12px; }
.tile-label {
    color: #555; font-size: 0.7rem; text-transform: uppercase;
    letter-spacing: 1.4px; font-weight: 600;
}
.tile-value {
    font-size: 1.85rem; font-weight: 700; margin-top: 4px;
    letter-spacing: -0.8px; color: #f0f0f0;
}
.tile-sub { font-size: 0.78rem; margin-top: 4px; }
.trend-up   { color: #f87171; font-weight: 600; }
.trend-down { color: #34d399; font-weight: 600; }
.trend-flat { color: #666; }

/* ── PROGRESS ── */
.prog-wrap { margin-top: 10px; }
.prog-track {
    background: #1c1c1c; border-radius: 6px; height: 10px; overflow: hidden;
}
.prog-fill  { height: 10px; border-radius: 6px; transition: width 0.6s ease; }
.prog-meta  {
    display: flex; justify-content: space-between;
    margin-top: 5px; font-size: 0.72rem; color: #444;
}

/* ── SECTION HEADER ── */
.sec-head {
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 1.6px;
    color: #444; font-weight: 700; margin: 22px 0 10px;
}

/* ── CATEGORY BAR ROWS ── */
.cat-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 9px 14px; border-radius: 10px; margin-bottom: 5px;
    background: #101010; border: 1px solid #1c1c1c;
}
.cat-name { font-size: 0.88rem; font-weight: 500; color: #ddd; flex: 1; }
.cat-bar-wrap {
    width: 72px; height: 3px; background: #1e1e1e;
    border-radius: 2px; margin: 0 12px; flex-shrink: 0;
}
.cat-bar-fill { height: 3px; border-radius: 2px; background: #2563eb; }
.cat-amt { font-size: 0.88rem; font-weight: 600; color: #e8e8e8; white-space: nowrap; }

/* ── BUDGET ROWS ── */
.budget-row {
    padding: 12px 14px; border-radius: 10px; background: #101010;
    border: 1px solid #1c1c1c; margin-bottom: 7px;
}
.budget-header {
    display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: 8px;
}
.budget-name { font-size: 0.88rem; font-weight: 600; color: #ddd; }
.budget-nums { font-size: 0.78rem; color: #555; }

/* ── RECURRING CARDS ── */
.rec-card {
    background: #101010; border: 1px solid #1c1c1c;
    border-radius: 12px; padding: 13px 15px; margin-bottom: 6px;
}
.rec-fired   { border-left: 3px solid #34d399; }
.rec-pending { border-left: 3px solid #facc15; }
.rec-title   { font-size: 0.93rem; font-weight: 600; color: #e0e0e0; }
.rec-meta    { font-size: 0.76rem; color: #555; margin-top: 3px; }

/* ── CATEGORY LIST ROWS ── */
.catlist-row {
    font-size: 0.9rem; font-weight: 500; color: #ccc;
    padding: 9px 0; border-bottom: 1px solid #141414;
}

/* ── EMPTY STATE ── */
.empty-box {
    text-align: center; padding: 48px 20px; color: #333;
}
.empty-box .ico { font-size: 2.2rem; margin-bottom: 10px; }
.empty-box .msg { font-size: 0.88rem; line-height: 1.5; }

/* ── DIALOG ── */
div[data-testid="stDialog"] {
    background: #0c0c0c !important;
    border: 1px solid #202020 !important;
    border-radius: 22px !important;
}

/* ── INPUTS ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: #141414 !important;
    border: 1px solid #242424 !important;
    border-radius: 8px !important;
    color: #e8e8e8 !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #141414 !important;
    border: 1px solid #242424 !important;
    border-radius: 8px !important;
}

/* ── EXPANDER (txn rows) ── */
[data-testid="stExpander"] {
    background: #101010 !important;
    border: 1px solid #1c1c1c !important;
    border-radius: 10px !important;
    margin-bottom: 5px;
}
[data-testid="stExpander"] summary {
    font-size: 0.87rem !important; font-weight: 500 !important; color: #ccc !important;
}

/* ── STREAMLIT OVERRIDES ── */
[data-testid="stForm"] { border: 1px solid #1c1c1c !important; border-radius: 12px !important; padding: 16px !important; background: #0e0e0e !important; }
.stAlert { border-radius: 10px !important; }

/* ── PIN LOCK SCREEN ── */
.pin-wrap {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; min-height: 70vh; gap: 8px;
}
.pin-logo {
    font-size: 2.6rem; margin-bottom: 4px;
}
.pin-title {
    font-size: 1.3rem; font-weight: 700; color: #e8e8e8;
    letter-spacing: -0.4px; margin-bottom: 2px;
}
.pin-sub {
    font-size: 0.8rem; color: #444; margin-bottom: 20px;
}
.pin-dots {
    display: flex; gap: 14px; margin-bottom: 28px;
}
.pin-dot {
    width: 14px; height: 14px; border-radius: 50%;
    border: 1.5px solid #333; background: transparent;
    transition: background 0.15s, border-color 0.15s;
}
.pin-dot.filled {
    background: #2563eb; border-color: #2563eb;
}
.pin-dot.error {
    background: #f87171; border-color: #f87171;
}
.pin-keypad {
    display: grid; grid-template-columns: repeat(3, 72px);
    gap: 12px;
}
.pin-key {
    height: 72px; border-radius: 14px;
    background: #111; border: 1px solid #1e1e1e;
    color: #e8e8e8; font-size: 1.3rem; font-weight: 600;
    cursor: pointer; transition: background 0.12s, transform 0.08s;
    font-family: 'DM Sans', sans-serif;
    display: flex; align-items: center; justify-content: center;
}
.pin-key:hover  { background: #1a1a1a; }
.pin-key:active { transform: scale(0.94); background: #222; }
.pin-key.del    { color: #555; font-size: 1rem; }
.pin-key.empty  { background: transparent; border-color: transparent; cursor: default; }
.pin-attempts   { font-size: 0.75rem; color: #f87171; margin-top: 10px; min-height: 18px; }
.pin-locked     { font-size: 0.8rem; color: #facc15; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. DATA LOAD + SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
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
        st.error(f"⚠️ Could not connect to Google Sheets: {ex}")
        return (
            pd.DataFrame(columns=["Date", "Amount", "Category", "Note", "Mode"]),
            pd.DataFrame(columns=["Category"]),
            pd.DataFrame(columns=["Category", "Budget", "Is_Recurring", "Day_of_Month", "Last_Fired"]),
            pd.DataFrame({"Mode": DEFAULT_MODES}),
        )

def bootstrap_session():
    """Seed session state from Sheets — runs once per session."""
    _df, _cat, _set, _modes = load_all_data()
    # T3: parse dates & amounts ONCE at load time
    if not _df.empty:
        _df["Date"]   = pd.to_datetime(_df["Date"], errors="coerce")
        _df["Amount"] = pd.to_numeric(_df["Amount"], errors="coerce").fillna(0)
    # Ensure Last_Fired column exists in Settings
    if "Last_Fired" not in _set.columns:
        _set["Last_Fired"] = ""
    st.session_state.df          = _df
    st.session_state.cat_df      = _cat
    st.session_state.settings_df = _set
    st.session_state.modes_df    = _modes
    st.session_state.bootstrapped = True

if not st.session_state.get("bootstrapped"):
    bootstrap_session()

def hard_refresh():
    """F8: Wipe cache + session, reload from Sheets."""
    st.cache_data.clear()
    for k in ["bootstrapped", "df", "cat_df", "settings_df", "modes_df"]:
        st.session_state.pop(k, None)
    st.rerun()


# ── Live references ──
df           = st.session_state.df
cat_df       = st.session_state.cat_df
settings_df  = st.session_state.settings_df
modes_df     = st.session_state.modes_df

categories    = sorted(cat_df["Category"].dropna().tolist())    if not cat_df.empty    else []
payment_modes = modes_df["Mode"].dropna().tolist()              if not modes_df.empty  else DEFAULT_MODES
now           = datetime.now(TZ)
today         = now.date()
curr_ym       = now.strftime("%Y-%m")   # e.g. "2026-03"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. HELPER SAVE FUNCTIONS (T10: spinners on all writes)
# ═══════════════════════════════════════════════════════════════════════════════
def _parse_new_expense_row(row_dict):
    new = pd.DataFrame([row_dict])
    new["Date"]   = pd.to_datetime(new["Date"], errors="coerce")
    new["Amount"] = pd.to_numeric(new["Amount"], errors="coerce").fillna(0)
    return new

def save_expense(row_dict):
    with st.spinner("Saving…"):
        new_row = _parse_new_expense_row(row_dict)
        updated = pd.concat([st.session_state.df, new_row], ignore_index=True)
        conn.update(worksheet="Expenses", data=updated)
        st.session_state.df = updated
        st.cache_data.clear()   # T2: only Expenses cache truly needs clearing here

def update_expense(idx, fields):
    with st.spinner("Updating…"):
        for k, v in fields.items():
            st.session_state.df.at[idx, k] = v
        conn.update(worksheet="Expenses", data=st.session_state.df)
        st.cache_data.clear()

def delete_expense(idx):
    with st.spinner("Deleting…"):
        updated = st.session_state.df.drop(idx).reset_index(drop=True)
        conn.update(worksheet="Expenses", data=updated)
        st.session_state.df = updated
        st.cache_data.clear()

def save_settings(new_df):
    with st.spinner("Saving…"):
        conn.update(worksheet="Settings", data=new_df)
        st.session_state.settings_df = new_df
        st.cache_data.clear()

def save_categories(new_df):
    with st.spinner("Saving…"):
        conn.update(worksheet="Categories", data=new_df)
        st.session_state.cat_df = new_df
        st.cache_data.clear()

def save_modes(new_df):
    with st.spinner("Saving…"):
        conn.update(worksheet="Modes", data=new_df)
        st.session_state.modes_df = new_df
        st.cache_data.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. F1 – RECURRING AUTO-LOG (runs once per session on load)
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state.get("auto_log_checked") and not settings_df.empty:
    fired_any      = False
    updated_sdf    = st.session_state.settings_df.copy()

    for i, row in st.session_state.settings_df.iterrows():
        try:
            is_rec = str(row.get("Is_Recurring", "")).strip().lower() in ("true", "1", "yes")
            if not is_rec:
                continue
            last_fired  = str(row.get("Last_Fired", "")).strip()
            day_of_mon  = int(row.get("Day_of_Month", 32))
            amt         = float(row.get("Budget", 0) or 0)

            if last_fired == curr_ym:
                continue   # Already fired this month
            if today.day < day_of_mon:
                continue   # Not due yet

            # Auto-log
            fire_dt = f"{today.strftime('%Y-%m-%d')} {now.strftime('%H:%M:%S')}"
            save_expense({
                "Date": fire_dt, "Amount": amt,
                "Category": row["Category"], "Mode": "Auto",
                "Note": "🔄 Auto-logged (recurring)",
            })
            updated_sdf.at[i, "Last_Fired"] = curr_ym
            fired_any = True
            st.toast(f"🔄 Auto-logged: {row['Category']}  ₹{amt:,.0f}", icon="✅")
        except Exception:
            pass

    if fired_any:
        save_settings(updated_sdf)

    st.session_state.auto_log_checked = True


# ═══════════════════════════════════════════════════════════════════════════════
# 6. TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_home, tab_rec, tab_cat = st.tabs(["🏠 Home", "🔄 Recurring", "🏷️ Manage"])


# ───────────────────────────────────────────────────────────────────────────────
# HOME TAB
# ───────────────────────────────────────────────────────────────────────────────
with tab_home:

    # F8: Header row with Refresh
    hc1, hc2 = st.columns([6, 1])
    hc1.markdown("## FinTrack")
    if hc2.button("↻", help="Refresh from Google Sheets", use_container_width=True):
        hard_refresh()

    # T4: correct empty check
    if df.empty:
        st.markdown("""<div class="empty-box">
            <div class="ico">💸</div>
            <div class="msg">No expenses logged yet.<br>Tap <strong>+</strong> to record your first transaction.</div>
        </div>""", unsafe_allow_html=True)

    else:
        # F3: Month selector
        all_months = sorted(
            df["Date"].dropna().dt.to_period("M").unique().astype(str).tolist(),
            reverse=True
        )
        sel_month  = st.selectbox("📅", all_months, index=0, label_visibility="collapsed")
        sel_period = pd.Period(sel_month, freq="M")
        prev_period = sel_period - 1

        filt = df[df["Date"].dt.to_period("M") == sel_period].copy()
        prev = df[df["Date"].dt.to_period("M") == prev_period].copy()

        # ── TILES ──────────────────────────────────────────────────────────────
        month_total = filt["Amount"].sum()
        prev_total  = prev["Amount"].sum()

        # T5: Month-over-month trend
        if prev_total > 0:
            pct_diff   = (month_total - prev_total) / prev_total * 100
            t_arrow    = "↑" if pct_diff > 0 else "↓"
            t_cls      = "trend-up" if pct_diff > 0 else "trend-down"
            trend_html = f'<span class="{t_cls}">{t_arrow} {abs(pct_diff):.0f}% vs {str(prev_period)}</span>'
        else:
            trend_html = '<span class="trend-flat">First month on record</span>'

        tc1, tc2 = st.columns(2)

        # Today tile (only shown when viewing current month)
        if sel_month == curr_ym:
            today_total = df[df["Date"].dt.date == today]["Amount"].sum()
            tc1.markdown(f'''<div class="tile">
                <div class="tile-accent" style="background:#2563eb;"></div>
                <div class="tile-label">Spent Today</div>
                <div class="tile-value">₹{today_total:,.0f}</div>
            </div>''', unsafe_allow_html=True)
        else:
            tc1.markdown(f'''<div class="tile">
                <div class="tile-accent" style="background:#374151;"></div>
                <div class="tile-label">Period</div>
                <div class="tile-value" style="font-size:1.1rem;padding-top:6px;">{sel_month}</div>
            </div>''', unsafe_allow_html=True)

        tc2.markdown(f'''<div class="tile">
            <div class="tile-accent" style="background:#7c3aed;"></div>
            <div class="tile-label">Total Spend</div>
            <div class="tile-value">₹{month_total:,.0f}</div>
            <div class="tile-sub">{trend_html}</div>
        </div>''', unsafe_allow_html=True)

        # HDFC Milestone tile (always current quarter, not filtered month)
        q_map   = {1:1,2:1,3:1,4:2,5:2,6:2,7:3,8:3,9:3,10:4,11:4,12:4}
        curr_q  = q_map[now.month]
        h_spend = df[
            (df["Date"].dt.month.map(q_map) == curr_q) &
            (df["Date"].dt.year == now.year) &
            (df["Mode"] == "HDFC Credit Card")
        ]["Amount"].sum()
        h_pct   = min(h_spend / HDFC_MILESTONE_AMT * 100, 100)
        h_color = "#2563eb" if h_pct < 75 else ("#facc15" if h_pct < 100 else "#34d399")
        remaining = max(HDFC_MILESTONE_AMT - h_spend, 0)

        st.markdown(f'''<div class="tile" style="border-left:3px solid {h_color};">
            <div class="tile-label">HDFC Q{curr_q} Milestone</div>
            <div class="tile-value">₹{h_spend:,.0f}
                <span style="font-size:0.82rem;color:#444;font-weight:400;"> / ₹{HDFC_MILESTONE_AMT:,.0f}</span>
            </div>
            <div class="prog-wrap">
                <div class="prog-track">
                    <div class="prog-fill" style="width:{h_pct:.1f}%;background:{h_color};"></div>
                </div>
                <div class="prog-meta">
                    <span>{h_pct:.1f}% reached</span>
                    <span>₹{remaining:,.0f} to go</span>
                </div>
            </div>
        </div>''', unsafe_allow_html=True)

        # ── F5: BUDGET TRACKER ─────────────────────────────────────────────────
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
                over   = " ⚠️ Over budget!" if bspent > blimit else ""
                st.markdown(f'''<div class="budget-row">
                    <div class="budget-header">
                        <span class="budget-name">{bcat}{over}</span>
                        <span class="budget-nums">₹{bspent:,.0f} / ₹{blimit:,.0f}</span>
                    </div>
                    <div class="prog-track">
                        <div class="prog-fill" style="width:{bpct:.1f}%;background:{bcolor};"></div>
                    </div>
                </div>''', unsafe_allow_html=True)

        # ── CATEGORY BREAKDOWN ─────────────────────────────────────────────────
        st.markdown('<p class="sec-head">By Category</p>', unsafe_allow_html=True)
        if not filt.empty:
            cat_sum = (
                filt.groupby("Category")["Amount"].sum()
                .sort_values(ascending=False)
                .reset_index()
            )
            max_amt = cat_sum["Amount"].max() or 1
            for _, crow in cat_sum.iterrows():
                bar_pct = crow["Amount"] / max_amt * 100
                st.markdown(f'''<div class="cat-row">
                    <span class="cat-name">{crow["Category"]}</span>
                    <div class="cat-bar-wrap">
                        <div class="cat-bar-fill" style="width:{bar_pct:.0f}%;"></div>
                    </div>
                    <span class="cat-amt">₹{crow["Amount"]:,.0f}</span>
                </div>''', unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty-box"><div class="ico">📊</div><div class="msg">No data for this period.</div></div>', unsafe_allow_html=True)

        # ── F6: TRANSACTIONS with SEARCH + F2: EDIT / DELETE ──────────────────
        st.markdown('<p class="sec-head">Transactions</p>', unsafe_allow_html=True)

        # F6: Search bar
        search_q = st.text_input(
            "search", placeholder="🔍  Filter by category, mode or note…",
            label_visibility="collapsed"
        )

        txn_df = filt.copy()
        if search_q.strip():
            q = search_q.strip()
            mask = (
                txn_df["Category"].astype(str).str.contains(q, case=False, na=False) |
                txn_df["Note"].astype(str).str.contains(q, case=False, na=False)     |
                txn_df["Mode"].astype(str).str.contains(q, case=False, na=False)
            )
            txn_df = txn_df[mask]

        # T13: configurable count
        txn_df = txn_df.sort_values("Date", ascending=False).head(RECENT_TXN_COUNT)

        if txn_df.empty:
            st.markdown('<div class="empty-box"><div class="ico">🔍</div><div class="msg">No transactions match.</div></div>', unsafe_allow_html=True)
        else:
            for idx, row in txn_df.iterrows():
                # T14: consistent display format
                date_disp = pd.to_datetime(row["Date"]).strftime("%-d %b, %H:%M") if pd.notna(row["Date"]) else "—"
                note_disp = f"  ·  {row['Note']}" if str(row.get("Note", "")).strip() else ""
                label     = f"₹{float(row['Amount']):,.0f}   ·   {row['Category']}   ·   {date_disp}"

                with st.expander(label):
                    ea, eb = st.columns(2)
                    new_amt  = ea.number_input("Amount", value=float(row["Amount"]), min_value=0.0, key=f"e_amt_{idx}")
                    new_cat  = eb.selectbox(
                        "Category", categories,
                        index=categories.index(row["Category"]) if row["Category"] in categories else 0,
                        key=f"e_cat_{idx}"
                    )
                    ec, ed = st.columns(2)
                    new_mode = ec.selectbox(
                        "Mode", payment_modes,
                        index=payment_modes.index(row["Mode"]) if row["Mode"] in payment_modes else 0,
                        key=f"e_mode_{idx}"
                    )
                    new_note = ed.text_input("Note", value=str(row.get("Note", "") or ""), key=f"e_note_{idx}")

                    btn1, btn2 = st.columns(2)
                    if btn1.button("💾 Save changes", key=f"save_{idx}", use_container_width=True, type="primary"):
                        update_expense(idx, {
                            "Amount": new_amt, "Category": new_cat,
                            "Mode": new_mode, "Note": new_note.strip()
                        })
                        st.rerun()

                    # Confirm delete (two-step)
                    ck = f"cdel_{idx}"
                    if ck not in st.session_state:
                        st.session_state[ck] = False

                    if not st.session_state[ck]:
                        if btn2.button("🗑️ Delete", key=f"del_{idx}", use_container_width=True):
                            st.session_state[ck] = True
                            st.rerun()
                    else:
                        btn2.warning("Sure?")
                        y_, n_ = btn2.columns(2)
                        if y_.button("✅", key=f"ydel_{idx}"):
                            delete_expense(idx)
                            st.session_state[ck] = False
                            st.rerun()
                        if n_.button("❌", key=f"ndel_{idx}"):
                            st.session_state[ck] = False
                            st.rerun()


# ───────────────────────────────────────────────────────────────────────────────
# RECURRING TAB
# ───────────────────────────────────────────────────────────────────────────────
with tab_rec:
    st.markdown("## Recurring Rules")

    with st.expander("➕  Create New Rule"):
        with st.form("new_rec"):
            rc1, rc2 = st.columns(2)
            c_sel = rc1.selectbox("Category", categories)
            a_sel = rc2.number_input("Amount (₹)", min_value=0.0, value=None, placeholder="0.00")
            d_sel = st.slider("Auto-log on day", 1, 31, 1)
            if st.form_submit_button("Add Rule", type="primary"):
                if a_sel:
                    new_r   = pd.DataFrame([{
                        "Category": c_sel, "Budget": a_sel,
                        "Is_Recurring": True, "Day_of_Month": d_sel, "Last_Fired": ""
                    }])
                    updated = pd.concat([st.session_state.settings_df, new_r], ignore_index=True)
                    save_settings(updated)
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
                fired_this = last_fired == curr_ym
                status_cls = "rec-fired" if fired_this else "rec-pending"
                status_txt = f"✅ Fired {curr_ym}" if fired_this else f"⏳ Due on day {dom}"
                next_date  = (
                    today.replace(day=min(dom, 28)).strftime("%-d %b")
                    if not fired_this else "—"
                )

                # F10: Visibility into fired vs pending
                st.markdown(f'''<div class="rec-card {status_cls}">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <div class="rec-title">{row["Category"]}</div>
                            <div class="rec-meta">₹{float(row["Budget"]):,.0f}  ·  {status_txt}</div>
                        </div>
                    </div>
                </div>''', unsafe_allow_html=True)

                # Delete with confirm
                ck = f"crec_{i}"
                if ck not in st.session_state:
                    st.session_state[ck] = False

                rcol1, rcol2, rcol3 = st.columns([5, 1, 1])
                if not st.session_state[ck]:
                    if rcol3.button("🗑️", key=f"del_rec_{i}", help="Delete rule"):
                        st.session_state[ck] = True
                        st.rerun()
                else:
                    rcol2.warning("Sure?")
                    if rcol2.button("✅", key=f"yrec_{i}"):
                        updated = st.session_state.settings_df.drop(i).reset_index(drop=True)
                        save_settings(updated)
                        st.session_state[ck] = False
                        st.rerun()
                    if rcol3.button("❌", key=f"nrec_{i}"):
                        st.session_state[ck] = False
                        st.rerun()
            except Exception:
                pass


# ───────────────────────────────────────────────────────────────────────────────
# MANAGE TAB (Categories + F4: Payment Modes)
# ───────────────────────────────────────────────────────────────────────────────
with tab_cat:
    st.markdown("## Manage")

    # ── F4: PAYMENT MODES ──────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Payment Modes</p>', unsafe_allow_html=True)
    with st.form("new_mode"):
        nm1, nm2 = st.columns([4, 1])
        nm = nm1.text_input("New mode name", label_visibility="collapsed", placeholder="e.g. ICICI Credit Card")
        if nm2.form_submit_button("Add", use_container_width=True):
            if nm.strip():
                updated = pd.concat(
                    [st.session_state.modes_df, pd.DataFrame([{"Mode": nm.strip()}])],
                    ignore_index=True
                )
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
            if mc2.button("🗑️", key=f"del_mode_{i}"):
                st.session_state[mck] = True
                st.rerun()
        else:
            mc2.warning("Sure?")
            my_, mn_ = mc2.columns(2)
            if my_.button("✅", key=f"ymode_{i}"):
                updated = st.session_state.modes_df.drop(i).reset_index(drop=True)
                save_modes(updated)
                st.session_state[mck] = False
                st.rerun()
            if mn_.button("❌", key=f"nmode_{i}"):
                st.session_state[mck] = False
                st.rerun()

    # ── CATEGORIES ─────────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">Categories</p>', unsafe_allow_html=True)
    with st.form("new_cat"):
        cc1, cc2 = st.columns([4, 1])
        nc = cc1.text_input("New category name", label_visibility="collapsed", placeholder="e.g. Dining Out")
        if cc2.form_submit_button("Add", use_container_width=True):
            if nc.strip():
                updated = pd.concat(
                    [st.session_state.cat_df, pd.DataFrame([{"Category": nc.strip()}])],
                    ignore_index=True
                )
                save_categories(updated)
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
            if cck not in st.session_state:
                st.session_state[cck] = False
            if not st.session_state[cck]:
                if cc2.button("🗑️", key=f"del_cat_{i}"):
                    st.session_state[cck] = True
                    st.rerun()
            else:
                cc2.warning("Sure?")
                cy_, cn_ = cc2.columns(2)
                if cy_.button("✅", key=f"ycat_{i}"):
                    updated = st.session_state.cat_df.drop(i).reset_index(drop=True)
                    save_categories(updated)
                    st.session_state[cck] = False
                    st.rerun()
                if cn_.button("❌", key=f"ncat_{i}"):
                    st.session_state[cck] = False
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# 7. QUICK LOG MODAL
# ═══════════════════════════════════════════════════════════════════════════════
@st.dialog("Quick Log")
def log_modal():
    if "form_id" not in st.session_state:
        st.session_state.form_id = 0

    if "last_log" in st.session_state:
        ll = st.session_state.last_log
        st.success(f"✅  ₹{ll['amt']:,.0f} logged under {ll['cat']}")

    # T9: always read live categories & modes from session state
    live_cats  = sorted(st.session_state.cat_df["Category"].dropna().tolist()) if not st.session_state.cat_df.empty else []
    live_modes = st.session_state.modes_df["Mode"].dropna().tolist()           if not st.session_state.modes_df.empty else DEFAULT_MODES

    fid = st.session_state.form_id

    amt = st.number_input("Amount (₹)", min_value=0.0, value=None,
                          placeholder="Enter amount", key=f"amt_{fid}")

    # T12: large amount soft warning
    if amt and amt > LARGE_AMT_WARNING:
        st.warning(f"⚠️  ₹{amt:,.0f} is unusually large — double-check before saving.")

    # Yesterday shortcut
    date_choice = st.radio("Date", ["Today", "Yesterday", "Pick a date"],
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

    note = st.text_input(
        "Note *(optional)*", value="",
        placeholder="Merchant, tag…", key=f"note_{fid}"
    )

    col1, col2 = st.columns(2)

    if col1.button("Save & Add More", type="primary", use_container_width=True):
        if not amt or amt <= 0:
            st.warning("Please enter a valid amount.")
            return

        # T15: duplicate guard (same amount + category within 3 seconds)
        now_ts   = datetime.now(TZ).timestamp()
        last_ts  = st.session_state.get("last_save_ts",  0)
        last_amt = st.session_state.get("last_save_amt", None)
        last_cat = st.session_state.get("last_save_cat", None)
        if (now_ts - last_ts) < 3 and last_amt == amt and last_cat == cat:
            st.warning("⚠️  Duplicate detected — same amount & category within 3 seconds.")
            return

        final_dt = f"{log_date.strftime('%Y-%m-%d')} {datetime.now(TZ).strftime('%H:%M:%S')}"
        save_expense({"Date": final_dt, "Amount": amt, "Category": cat, "Mode": mode, "Note": note.strip()})

        st.session_state.update({
            "last_save_ts":  now_ts,
            "last_save_amt": amt,
            "last_save_cat": cat,
            "last_log":      {"amt": amt, "cat": cat},
            "form_id":       fid + 1,
        })
        st.rerun()

    if col2.button("Finish", use_container_width=True):
        st.session_state.show_modal = False
        for k in ["last_log", "last_save_ts", "last_save_amt", "last_save_cat"]:
            st.session_state.pop(k, None)
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# 8. FAB
# ═══════════════════════════════════════════════════════════════════════════════
if "show_modal" not in st.session_state:
    st.session_state.show_modal = False

if st.session_state.show_modal:
    log_modal()

with stylable_container(key="fab", css_styles="""
button {
    position: fixed; bottom: 32px; right: 24px;
    width: 60px; height: 60px; border-radius: 50%;
    background: #2563eb; color: #fff; font-size: 34px;
    z-index: 9999; border: none;
    box-shadow: 0 6px 24px rgba(37,99,235,0.45);
    transition: transform 0.15s, box-shadow 0.15s;
}
button:hover {
    transform: scale(1.07);
    box-shadow: 0 8px 30px rgba(37,99,235,0.6);
}
"""):
    if st.button("+", key="main_plus_btn"):
        st.session_state.show_modal = True
        st.rerun()

import streamlit as st
import pandas as pd
import io
import requests
from datetime import datetime, timedelta, date
from streamlit_extras.stylable_container import stylable_container

from utils import (
    RECENT_TXN_COUNT, HDFC_MILESTONE_AMT, LARGE_AMT_WARNING, TZ, DEFAULT_MODES, MAX_PIN_ATTEMPTS,
    KEY_INCOME, KEY_ALERT_PCT, KEY_ALERT_ON, KEY_PULSE_ON, load_all_data, load_pin, save_expense,
    update_expense, delete_expense, save_settings, save_categories, save_modes, save_pin, save_import_rules,
    get_app_setting, set_app_setting, split_expense_row, extract_merchant, build_heatmap_html, build_dow_html,
    detect_anomalies, detect_duplicates, detect_recurring_merchants, get_merchant_trend, approve_pending_row,
    skip_pending_row, approve_all_with_suggestions, auto_save_import_rule, approve_merchant_group,
    skip_merchant_group, approve_split_group
)
from ui_components import inject_custom_css

# ==============================================================================
# CONFIG & CSS
# ==============================================================================
st.set_page_config(page_title="FinTrack Pro", page_icon="₹", layout="centered")
inject_custom_css()

if "view_mode" not in st.session_state:
    st.session_state.view_mode = "mobile"
if st.session_state.view_mode == "desktop":
    st.markdown('<style>div.block-container{max-width:820px!important;margin:0 auto!important;'
                'padding-left:1.5rem!important;padding-right:1.5rem!important}</style>',
                unsafe_allow_html=True)

# ==============================================================================
# SESSION SETUP
# ==============================================================================
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
    st.session_state.update({
        "df": _df, "cat_df": _cat, "settings_df": _set, "modes_df": _modes,
        "pending_df": _pend, "import_log_df": _log, "import_rules": _rules,
        "app_settings_df": _app, "active_pin": load_pin(), "bootstrapped": True
    })

if not st.session_state.get("bootstrapped"):
    bootstrap_session()

def hard_refresh():
    st.cache_data.clear()
    for k in ["bootstrapped","df","cat_df","settings_df","modes_df","pending_df",
              "import_log_df","import_rules","app_settings_df","active_pin"]:
        st.session_state.pop(k, None)
    st.rerun()

df             = st.session_state.df
cat_df         = st.session_state.cat_df
settings_df    = st.session_state.settings_df
modes_df       = st.session_state.modes_df
pending_df     = st.session_state.pending_df
import_log_df  = st.session_state.import_log_df
import_rules   = st.session_state.import_rules

categories    = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty else []
payment_modes = modes_df["Mode"].dropna().tolist() if not modes_df.empty else DEFAULT_MODES
now           = datetime.now(TZ)
today         = now.date()
curr_ym       = now.strftime("%Y-%m")

# ==============================================================================
# TXN RENDERER
# ==============================================================================
def render_txn_row(idx, row, key_prefix="txn", show_edit=True):
    date_disp = pd.to_datetime(row["Date"]).strftime("%-d %b, %H:%M") if pd.notna(row["Date"]) else "-"
    note_val  = str(row.get("Note", "") or "").strip()
    edit_key, del_key, split_key = f"{key_prefix}_edit_{idx}", f"{key_prefix}_del_{idx}", f"{key_prefix}_split_{idx}"
    
    for k, v in [(edit_key, False), (del_key, False), (split_key, False)]:
        if k not in st.session_state: st.session_state[k] = v

    mode_val  = str(row.get("Mode","")).strip()
    note_html = f'<span class="txn-note"> · {note_val[:28]}</span>' if note_val else ""
    mode_html = f'<span class="chip">{mode_val}</span>' if mode_val else ""

    c_info, c_amt, c_btn = st.columns([5, 3, 1])
    c_info.markdown(
        f'<div class="txn-row" style="border:none;padding:6px 0">'
        f'<div><div class="txn-cat">{row["Category"]}{note_html}</div>'
        f'<div class="txn-meta">{date_disp} {mode_html}</div>'
        f'</div></div>', unsafe_allow_html=True
    )
    c_amt.markdown(
        f'<div style="font-size:.9rem;font-weight:700;color:#e8e8f0;padding:6px 0;text-align:right;'
        f'font-family:\'JetBrains Mono\',monospace">Rs.{float(row["Amount"]):,.0f}</div>', unsafe_allow_html=True
    )
    
    if show_edit and c_btn.button("✏️", key=f"{key_prefix}_tgl_{idx}"):
        st.session_state[edit_key] = not st.session_state[edit_key]
        st.session_state[split_key] = False
        st.rerun()
    st.markdown("<hr style='border:none;border-top:1px solid #1a1a24;margin:0'>", unsafe_allow_html=True)

    if show_edit and st.session_state[edit_key]:
        with st.container(border=True):
            ea, eb = st.columns(2)
            new_amt = ea.number_input("Amount", value=float(row["Amount"]), min_value=0.0, key=f"{key_prefix}_eamt_{idx}")
            new_cat = eb.selectbox("Category", categories, index=categories.index(row["Category"]) if row["Category"] in categories else 0, key=f"{key_prefix}_ecat_{idx}")
            ec, ed = st.columns(2)
            new_mode = ec.selectbox("Mode", payment_modes, index=payment_modes.index(row["Mode"]) if row["Mode"] in payment_modes else 0, key=f"{key_prefix}_emode_{idx}")
            new_note = ed.text_input("Note", value=note_val, key=f"{key_prefix}_enote_{idx}")
            btn1, btn2, btn3 = st.columns(3)
            if btn1.button("Save", key=f"{key_prefix}_save_{idx}", use_container_width=True, type="primary"):
                update_expense(idx, {"Amount": new_amt, "Category": new_cat, "Mode": new_mode, "Note": new_note.strip()})
                st.session_state[edit_key] = False
                st.toast("Updated ✓"); st.rerun()
            if btn2.button("✂ Split", key=f"{key_prefix}_splbtn_{idx}", use_container_width=True):
                st.session_state[split_key], st.session_state[edit_key] = True, False
                st.rerun()
            if not st.session_state[del_key]:
                if btn3.button("Delete", key=f"{key_prefix}_delb_{idx}", use_container_width=True):
                    st.session_state[del_key] = True; st.rerun()
            else:
                btn3.warning("Sure?")
                y_, n_ = btn3.columns(2)
                if y_.button("Yes", key=f"{key_prefix}_ydel_{idx}"):
                    delete_expense(idx)
                    st.session_state[edit_key], st.session_state[del_key] = False, False
                    st.rerun()
                if n_.button("No", key=f"{key_prefix}_ndel_{idx}"):
                    st.session_state[del_key] = False; st.rerun()

    if show_edit and st.session_state[split_key]:
        total_amt = float(row["Amount"])
        st.markdown(f'<div class="split-row"><span style="font-size:.8rem;font-weight:700;color:#f0a500">✂ Split Rs.{total_amt:,.0f} into two</span></div>', unsafe_allow_html=True)
        with st.container(border=True):
            s1a, s1b = st.columns([1, 2])
            spl1_amt = s1a.number_input("Part 1 Rs.", min_value=1.0, max_value=total_amt-1, value=round(total_amt/2, 2), key=f"spl1a_{idx}")
            spl1_cat = s1b.selectbox("Category 1", categories, key=f"spl1c_{idx}", label_visibility="collapsed")
            spl2_amt = total_amt - spl1_amt
            s2a, s2b = st.columns([1, 2])
            s2a.markdown(f'<div style="padding:8px 0;font-size:.92rem;font-weight:600;color:#e8e8f0;font-family:\'JetBrains Mono\',monospace">Rs.{spl2_amt:,.0f}</div>', unsafe_allow_html=True)
            spl2_cat = s2b.selectbox("Category 2", categories, key=f"spl2c_{idx}", label_visibility="collapsed")
            sb1, sb2 = st.columns(2)
            if sb1.button("✂ Split & Save", key=f"do_split_{key_prefix}_{idx}", type="primary", use_container_width=True):
                split_expense_row(idx, spl1_amt, spl1_cat, spl2_amt, spl2_cat)
                st.session_state[split_key] = False
                st.toast(f"Split → {spl1_cat} + {spl2_cat} ✓"); st.rerun()
            if sb2.button("Cancel", key=f"cancel_split_{key_prefix}_{idx}", use_container_width=True):
                st.session_state[split_key] = False; st.rerun()

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
        st.markdown("<div style='text-align:center;margin-bottom:6px'><span style='font-size:1.5rem;font-weight:700;color:#e8e8f0;font-family:\"Sora\",sans-serif;letter-spacing:-.5px'>Fin<span style='color:#f0a500'>Track</span> Pro</span></div>", unsafe_allow_html=True)
        st.markdown("<p style='color:#444460;font-size:.8rem;margin-bottom:24px;text-align:center'>Enter your 4-digit PIN to continue</p>", unsafe_allow_html=True)
        entered  = len(st.session_state.pin_input)
        is_error = bool(st.session_state.pin_error)
        dots_html = "<div style='display:flex;gap:14px;margin-bottom:24px;justify-content:center'>"
        for i in range(4):
            style = "width:13px;height:13px;border-radius:50%;background:#f75676;border:1.5px solid #f75676" if is_error else ("width:13px;height:13px;border-radius:50%;background:#f0a500;border:1.5px solid #f0a500" if i < entered else "width:13px;height:13px;border-radius:50%;background:transparent;border:1.5px solid #2a2a3a")
            dots_html += f"<div style='{style}'></div>"
        dots_html += "</div>"
        st.markdown(dots_html, unsafe_allow_html=True)
        
        if locked_out:
            st.error("Too many incorrect attempts. Restart the app to try again."); st.stop()
        if st.session_state.pin_error:
            remaining = MAX_PIN_ATTEMPTS - st.session_state.pin_attempts
            st.markdown(f"<p style='color:#f75676;font-size:.76rem;text-align:center;margin-bottom:12px'>Incorrect PIN. {remaining} attempt{'s' if remaining != 1 else ''} left.</p>", unsafe_allow_html=True)
        
        keys_layout = [["1","2","3"],["4","5","6"],["7","8","9"],["","0","del"]]
        for row_keys in keys_layout:
            k1, k2, k3 = st.columns(3)
            for col_w, digit in zip([k1, k2, k3], row_keys):
                if digit == "": col_w.markdown("")
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
                                    st.session_state.update({"pin_unlocked": True, "pin_input": "", "pin_error": "", "pin_attempts": 0})
                                else:
                                    st.session_state.pin_attempts += 1
                                    st.session_state.update({"pin_error": "wrong", "pin_input": ""})
                            st.rerun()
    st.stop()

# ==============================================================================
# AUTO-LOG
# ==============================================================================
if not st.session_state.get("auto_log_checked") and not settings_df.empty:
    fired_any = False
    updated_sdf = st.session_state.settings_df.copy()
    for i, row in st.session_state.settings_df.iterrows():
        try:
            is_rec = str(row.get("Is_Recurring", "")).strip().lower() in ("true", "1", "yes")
            if not is_rec: continue
            last_fired, day_of_mon, amt = str(row.get("Last_Fired", "")).strip(), int(row.get("Day_of_Month", 32)), float(row.get("Budget", 0) or 0)
            if last_fired == curr_ym or today.day < day_of_mon: continue
            
            fire_dt = f"{today.strftime('%Y-%m-%d')} {now.strftime('%H:%M:%S')}"
            save_expense({"Date": fire_dt, "Amount": amt, "Category": row["Category"], "Mode": "Auto", "Note": "Auto-logged (recurring)"})
            updated_sdf.at[i, "Last_Fired"] = curr_ym
            fired_any = True
            st.toast(f"Auto-logged: {row['Category']}  Rs.{amt:,.0f}")
        except Exception: pass
    if fired_any: save_settings(updated_sdf)
    st.session_state.auto_log_checked = True

pending_count = int((st.session_state.pending_df["Review_Status"].astype(str) == "pending").sum()) if not st.session_state.pending_df.empty and "Review_Status" in st.session_state.pending_df.columns else 0

# ==============================================================================
# BOTTOM-NAV ROUTING
# ==============================================================================
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "records"
active_tab = st.session_state.active_tab

with stylable_container(key="topbar", css_styles="""
    button{
        background:#1a1a24!important;border:1px solid #2a2a3a!important;
        border-radius:8px!important;color:#666!important;
        font-size:.82rem!important;padding:0!important;line-height:1!important;
        height:32px!important;min-height:32px!important;max-height:32px!important;
    }
"""):
    _tb1, _tb2, _tb3, _tb4 = st.columns([5, 1, 1, 1])
    _tb1.markdown("<span style='font-size:1.4rem;font-weight:700;color:#e8e8f0;letter-spacing:-.5px'>Fin<span style='color:#f0a500'>Track</span> Pro</span>", unsafe_allow_html=True)
    _vm = st.session_state.view_mode
    if _tb2.button("🖥" if _vm == "mobile" else "📱", key="view_mode_btn"):
        st.session_state.view_mode = "desktop" if _vm == "mobile" else "mobile"
        st.rerun()
    if _tb3.button("🔒", key="lock_icon", use_container_width=True):
        st.session_state.update({"pin_unlocked": False, "pin_input": "", "pin_error": ""}); st.rerun()
    if _tb4.button("↻", key="refresh_icon", use_container_width=True): hard_refresh()

_hdr_exp  = df[df["Date"].dt.to_period("M") == pd.Period(curr_ym, freq="M")]["Amount"].sum() if not df.empty else 0.0
_hdr_inc  = float(get_app_setting(KEY_INCOME, "0") or "0")
_hdr_bal  = _hdr_inc - _hdr_exp if _hdr_inc > 0 else None
_hdr_lbl  = f"[ All Accounts &nbsp; Rs.{_hdr_bal:,.0f} balance ]" if _hdr_bal is not None else f"[ Rs.{_hdr_exp:,.0f} this month ]"
_inc_html = (f'<div class="mm-stat"><div class="mm-stat-lbl">Income so far</div><div class="mm-stat-val mm-inc">Rs.{_hdr_inc:,.0f}</div></div>') if _hdr_inc > 0 else ""

if active_tab == "records":
    st.markdown(f'<div class="mm-header"><div class="mm-balance">{_hdr_lbl}</div><div class="mm-stats"><div class="mm-stat"><div class="mm-stat-lbl">Expense so far</div><div class="mm-stat-val mm-exp">Rs.{_hdr_exp:,.0f}</div></div>{_inc_html}</div></div>', unsafe_allow_html=True)
    if df.empty:
        st.markdown("<div class='empty-box'><div class='ico'>💸</div><div class='msg'>No expenses yet. Tap + to get started.</div></div>", unsafe_allow_html=True)
    else:
        HOME_RANGES, HOME_RANGE_LBL = ["1M", "3M", "6M", "1Y"], ["This M", "3M", "6M", "1Y"]
        if "home_pill_idx" not in st.session_state: st.session_state.home_pill_idx = 0
        _hp_cols = st.columns(4)
        for _pi, (_pc, _pl) in enumerate(zip(_hp_cols, HOME_RANGE_LBL)):
            _sel = st.session_state.home_pill_idx == _pi
            with _pc:
                with stylable_container(key=f"hpill_{_pi}", css_styles=f"button{{background:{'rgba(240,165,0,.15)' if _sel else '#13131a'}!important; border:1px solid {'#f0a500' if _sel else '#2a2a3a'}!important; border-radius:20px!important; color:{'#f0a500' if _sel else '#555'}!important; font-size:.75rem!important; font-weight:{'700' if _sel else '400'}!important; padding:4px 0!important; height:30px!important; min-height:30px!important;}}"):
                    if st.button(_pl, key=f"hpill_btn_{_pi}", use_container_width=True):
                        st.session_state.home_pill_idx = _pi; st.rerun()

        _sel_range, now_per = HOME_RANGES[st.session_state.home_pill_idx], pd.Period(curr_ym, freq="M")
        
        if _sel_range == "1M":
            filt, prev, _show_today, _range_lbl = df[df["Date"].dt.to_period("M") == now_per].copy(), df[df["Date"].dt.to_period("M") == (now_per - 1)].copy(), True, curr_ym
        elif _sel_range == "3M":
            filt, prev, _show_today, _range_lbl = df[df["Date"].dt.to_period("M") > (now_per - 3)].copy(), df[df["Date"].dt.to_period("M").between(str(now_per - 6), str(now_per - 4))].copy(), False, "Last 3 months"
        elif _sel_range == "6M":
            filt, prev, _show_today, _range_lbl = df[df["Date"].dt.to_period("M") > (now_per - 6)].copy(), df[df["Date"].dt.to_period("M").between(str(now_per - 12), str(now_per - 7))].copy(), False, "Last 6 months"
        else:
            filt, prev, _show_today, _range_lbl = df[df["Date"].dt.to_period("M") > (now_per - 12)].copy(), df[df["Date"].dt.to_period("M") <= (now_per - 12)].copy(), False, "Last 12 months"

        sel_month, sel_period, month_total, prev_total = curr_ym, now_per, filt["Amount"].sum(), prev["Amount"].sum()

        if prev_total > 0:
            pct_diff = (month_total - prev_total) / prev_total * 100
            trend_html = f'<span class="{"trend-up" if pct_diff > 0 else "trend-down"}">{"+" if pct_diff > 0 else ""}{pct_diff:.0f}% vs prev</span>'
        else: trend_html = '<span class="trend-flat">First period on record</span>'

        if _show_today:
            today_total = df[df["Date"].dt.date == today]["Amount"].sum()
            today_block = f'<div><div class="hero-today-lbl">Today</div><div class="hero-today-val">Rs.{today_total:,.0f}</div></div>'
        else:
            today_block = f'<div style="text-align:right"><div class="hero-today-lbl">Period</div><div style="font-size:.8rem;font-weight:600;color:#666">{_range_lbl}</div></div>'
        
        st.markdown(f'<div class="hero-card"><div style="font-size:.68rem;text-transform:uppercase;letter-spacing:1.4px;color:#444460;font-weight:700">Total Spend</div><div class="hero-row"><div><div class="hero-amount">Rs.{month_total:,.0f}</div><div style="font-size:.78rem;margin-top:6px">{trend_html}</div></div>{today_block}</div></div>', unsafe_allow_html=True)

        monthly_income, q_map = float(get_app_setting(KEY_INCOME, "0") or "0"), {1:1,2:1,3:1,4:2,5:2,6:2,7:3,8:3,9:3,10:4,11:4,12:4}
        curr_q = q_map[now.month]
        h_spend = df[(df["Date"].dt.month.map(q_map) == curr_q) & (df["Date"].dt.year == now.year) & (df["Mode"] == "HDFC Credit Card")]["Amount"].sum()
        h_pct = min(h_spend / HDFC_MILESTONE_AMT * 100, 100)
        h_color = "#5e72e4" if h_pct < 75 else ("#f0a500" if h_pct < 100 else "#2dce89")

        mt_left, mt_right = st.columns(2)
        if monthly_income > 0 and _show_today:
            savings, savings_pct = monthly_income - month_total, (monthly_income - month_total) / monthly_income * 100
            sav_color, sav_sign, sav_fill = "#2dce89" if savings >= 0 else "#f75676", "+" if savings >= 0 else "", min(abs(savings_pct), 100)
            mt_left.markdown(f'<div class="mini-tile" style="border-left:3px solid {sav_color}"><div class="mini-tile-lbl">Savings Rate</div><div class="mini-tile-val" style="color:{sav_color}">{sav_sign}{savings_pct:.1f}%</div><div class="mini-tile-sub">Rs.{abs(savings):,.0f} {"saved" if savings>=0 else "over"}</div><div class="prog-wrap"><div class="prog-track"><div class="prog-fill" style="width:{sav_fill:.1f}%;background:{sav_color}"></div></div></div></div>', unsafe_allow_html=True)
        else: mt_left.markdown(f'<div class="mini-tile" style="border-left:3px solid #2a2a3a"><div class="mini-tile-lbl">Savings Rate</div><div class="mini-tile-val" style="color:#444460">—</div><div class="mini-tile-sub">Set income in Manage</div></div>', unsafe_allow_html=True)
        mt_right.markdown(f'<div class="mini-tile" style="border-left:3px solid {h_color}"><div class="mini-tile-lbl">HDFC Q{curr_q}</div><div class="mini-tile-val" style="color:{h_color}">Rs.{h_spend:,.0f}</div><div class="mini-tile-sub">{h_pct:.0f}% of Rs.{HDFC_MILESTONE_AMT//1000:,}k</div><div class="prog-wrap"><div class="prog-track"><div class="prog-fill" style="width:{h_pct:.1f}%;background:{h_color}"></div></div></div></div>', unsafe_allow_html=True)

        if not st.session_state.pending_df.empty:
            anomalies = detect_anomalies(st.session_state.pending_df, df)
            if anomalies:
                items_html = "".join([f'<div class="anomaly-item"><span style="color:#ccc">{info["merchant"][:30]}</span><span style="color:#f75676;font-weight:600">Rs.{info["amount"]:,.0f} <span style="color:#444460;font-weight:400;font-size:.72rem">(avg Rs.{info["avg"]:,.0f})</span></span></div>' for info in list(anomalies.values())[:5]])
                st.markdown(f'<div class="anomaly-panel"><div class="anomaly-panel-title">🚨 {len(anomalies)} Unusual Amount{"s" if len(anomalies)>1 else ""} in Pending Review</div>{items_html}</div>', unsafe_allow_html=True)

        budgets = st.session_state.settings_df[st.session_state.settings_df["Budget"].notna() & (st.session_state.settings_df["Budget"].astype(str).str.strip() != "")].copy() if not st.session_state.settings_df.empty else pd.DataFrame()
        if not budgets.empty:
            st.markdown('<p class="sec-head">Budget Tracker</p>', unsafe_allow_html=True)
            for _, brow in budgets.iterrows():
                bcat, blimit = brow["Category"], float(brow.get("Budget", 0) or 0)
                if blimit <= 0: continue
                bspent = filt[filt["Category"] == bcat]["Amount"].sum()
                bpct, bcolor = min(bspent / blimit * 100, 100), "#2dce89" if bspent/blimit < 0.75 else ("#f0a500" if bspent <= blimit else "#f75676")
                st.markdown(f'<div class="budget-row"><div class="budget-header"><span class="budget-name">{bcat}{" ⚠ Over!" if bspent > blimit else ""}</span><span class="budget-nums">Rs.{bspent:,.0f} / Rs.{blimit:,.0f}</span></div><div class="prog-track"><div class="prog-fill" style="width:{bpct:.1f}%;background:{bcolor}"></div></div></div>', unsafe_allow_html=True)

        st.markdown('<p class="sec-head">By Category</p>', unsafe_allow_html=True)
        if not filt.empty:
            cat_sum, max_amt = filt.groupby("Category")["Amount"].sum().sort_values(ascending=False).reset_index(), filt.groupby("Category")["Amount"].sum().max() or 1
            prev3 = df[(df["Date"].dt.to_period("M") > (sel_period - 3)) & (df["Date"].dt.to_period("M") < sel_period)]
            cat_3mo_avg = prev3.groupby("Category")["Amount"].mean() if not prev3.empty else pd.Series(dtype=float)
            for _, crow in cat_sum.iterrows():
                bar_pct, cat_nm, avg_3 = crow["Amount"] / max_amt * 100, crow["Category"], float(cat_3mo_avg.get(crow["Category"], 0))
                trend_arrow = f'<span style="color:{"#f75676" if ((crow["Amount"] - avg_3) / avg_3 * 100) > 10 else "#2dce89"};font-size:.7rem">{"↑" if ((crow["Amount"] - avg_3) / avg_3 * 100) > 10 else "↓"}{abs(((crow["Amount"] - avg_3) / avg_3 * 100)):.0f}%</span>' if avg_3 > 0 and abs(((crow["Amount"] - avg_3) / avg_3 * 100)) > 10 else ""
                st.markdown(f'<div class="cat-row"><span class="cat-name">{cat_nm} {trend_arrow}</span><div class="cat-bar-wrap"><div class="cat-bar-fill" style="width:{bar_pct:.0f}%"></div></div><span class="cat-amt">Rs.{crow["Amount"]:,.0f}</span></div>', unsafe_allow_html=True)
        else: st.markdown('<div class="empty-box"><div class="ico">📊</div><div class="msg">No data for this period.</div></div>', unsafe_allow_html=True)

        if pending_count > 0:
            _rv1, _rv2 = st.columns([3, 1])
            _rv1.markdown(f'<div style="background:#100a00;border:1px solid #2a1a00;border-left:3px solid #f0a500;border-radius:10px;padding:7px 12px;display:flex;align-items:center"><span style="font-size:.82rem;color:#f0a500;font-weight:600">⚠️ {pending_count} txn{"s" if pending_count>1 else ""} pending review</span></div>', unsafe_allow_html=True)
            with _rv2:
                with stylable_container(key="rev_link", css_styles="button{background:#2a1f00!important;border:1px solid #f0a500!important;border-radius:8px!important;color:#f0a500!important;font-size:.76rem!important;font-weight:700!important;height:38px!important;min-height:38px!important}"):
                    if st.button("Review →", key="review_shortcut", use_container_width=True):
                        st.session_state.active_tab = "review"; st.rerun()

        st.markdown('<p class="sec-head">Recent Transactions</p>', unsafe_allow_html=True)
        _sq1, _sq2 = st.columns([5, 1])
        search_q = _sq1.text_input("search_home", placeholder="Filter by category, note, mode...", label_visibility="collapsed")
        with _sq2:
            with stylable_container(key="go_srch_btn", css_styles="button{background:#1a1a24!important;border:1px solid #2a2a3a!important;border-radius:8px!important;color:#888!important;font-size:.78rem!important;height:38px!important;min-height:38px!important}"):
                if st.button("🔍 More", key="go_search", use_container_width=True):
                    st.session_state.active_tab = "search"; st.rerun()
        txn_df = filt[filt["Category"].astype(str).str.contains(search_q.strip(), case=False, na=False) | filt["Note"].astype(str).str.contains(search_q.strip(), case=False, na=False) | filt["Mode"].astype(str).str.contains(search_q.strip(), case=False, na=False)] if search_q.strip() else filt.copy()
        txn_df = txn_df.sort_values("Date", ascending=False).head(RECENT_TXN_COUNT)
        if txn_df.empty: st.markdown('<div class="empty-box"><div class="ico">🔍</div><div class="msg">No transactions match.</div></div>', unsafe_allow_html=True)
        else:
            for idx, row in txn_df.iterrows(): render_txn_row(idx, row, key_prefix="home")

elif active_tab == "analysis":
    st.markdown("<span style='font-size:1.2rem;font-weight:700;color:#e8e8f0'>Analysis</span>", unsafe_allow_html=True)
    if df.empty: st.markdown('<div class="empty-box"><div class="ico">🏷️</div><div class="msg">No data yet.</div></div>', unsafe_allow_html=True)
    else:
        total_all, total_txns, span_days = df["Amount"].sum(), len(df), max((df["Date"].max() - df["Date"].min()).days, 1)
        s1, s2, s3 = st.columns(3)
        s1.markdown(f'<div class="tile"><div class="tile-accent" style="background:#f0a500"></div><div class="tile-label">All Time Spend</div><div class="tile-value" style="font-size:1.4rem">Rs.{total_all:,.0f}</div></div>', unsafe_allow_html=True)
        s2.markdown(f'<div class="tile"><div class="tile-accent" style="background:#5e72e4"></div><div class="tile-label">Transactions</div><div class="tile-value" style="font-size:1.4rem">{total_txns:,}</div></div>', unsafe_allow_html=True)
        s3.markdown(f'<div class="tile"><div class="tile-accent" style="background:#2dce89"></div><div class="tile-label">Daily Average</div><div class="tile-value" style="font-size:1.4rem">Rs.{total_all/span_days:,.0f}</div></div>', unsafe_allow_html=True)
        
        st.markdown('<p class="sec-head">Analytics & Charts</p>', unsafe_allow_html=True)
        if "an_pill_idx" not in st.session_state: st.session_state.an_pill_idx = 0
        _an_cols = st.columns(4)
        for _ai, (_ac, _al) in enumerate(zip(_an_cols, ["3M",  "6M", "1Y", "All"])):
            _asel = st.session_state.an_pill_idx == _ai
            with _ac:
                with stylable_container(key=f"anpill_{_ai}", css_styles=f"button{{background:{'rgba(240,165,0,.15)' if _asel else '#13131a'}!important; border:1px solid {'#f0a500' if _asel else '#2a2a3a'}!important; border-radius:20px!important; color:{'#f0a500' if _asel else '#555'}!important; font-size:.75rem!important; font-weight:{'700' if _asel else '400'}!important; padding:4px 0!important; height:30px!important; min-height:30px!important;}}"):
                    if st.button(_al, key=f"anpill_btn_{_ai}", use_container_width=True):
                        st.session_state.an_pill_idx = _ai; st.rerun()

        an_sel, now_per = ["3M", "6M", "1Y", "All"][st.session_state.an_pill_idx], pd.Period(curr_ym, freq="M")
        an_df = df[df["Date"].dt.to_period("M") > (now_per - int(an_sel[:-1]) if an_sel != "All" else df["Date"].min().to_period("M") - 1)]

        st.markdown('<div class="analytics-card"><div class="analytics-title">Spend Heatmap — Last 52 Weeks</div>', unsafe_allow_html=True)
        st.markdown(build_heatmap_html(df), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if not an_df.empty:
            mo_totals = an_df.groupby(an_df["Date"].dt.to_period("M"))["Amount"].sum().sort_index()
            if len(mo_totals) > 1:
                bars_html = "".join([f'<div class="monthly-bar-row"><span class="monthly-bar-lbl">{str(period)[-5:]}</span><div style="flex:1;background:#1a1a24;border-radius:4px;height:14px;overflow:hidden"><div style="width:{val / (float(mo_totals.max()) or 1.0) * 100:.1f}%;height:14px;border-radius:4px;background:#f0a500"></div></div><span class="monthly-bar-amt">Rs.{val:,.0f}</span></div>' for period, val in mo_totals.items()])
                st.markdown(f'<div class="analytics-card"><div class="analytics-title">Monthly Spend</div>{bars_html}</div>', unsafe_allow_html=True)

        budgets_a = settings_df[settings_df["Budget"].notna() & (settings_df["Budget"].astype(str).str.strip() != "")].copy() if not settings_df.empty else pd.DataFrame()
        if not budgets_a.empty and an_sel not in ("3M", "6M", "1Y", "All"):
            st.markdown('<div class="analytics-card"><div class="analytics-title">Budget vs Actual</div>', unsafe_allow_html=True)
            for _, brow in budgets_a.iterrows():
                bcat, blimit = brow["Category"], float(brow.get("Budget", 0) or 0)
                if blimit <= 0: continue
                bspent, bpct = an_df[an_df["Category"] == bcat]["Amount"].sum(), an_df[an_df["Category"] == bcat]["Amount"].sum() / blimit * 100
                st.markdown(f'<div style="margin-bottom:12px"><div style="display:flex;justify-content:space-between;margin-bottom:5px"><span style="font-size:.86rem;font-weight:600;color:#ccc">{bcat}{f"<span style=\'color:#f75676;font-size:.7rem\'> +Rs.{bspent-blimit:,.0f} over</span>" if bspent > blimit else ""}</span><span style="font-size:.8rem;color:#444460;font-family:\'JetBrains Mono\',monospace">Rs.{bspent:,.0f} / Rs.{blimit:,.0f} &nbsp; {bpct:.0f}%</span></div><div class="prog-track"><div class="prog-fill" style="width:{min(bpct, 100):.1f}%;background:{"#2dce89" if bpct < 75 else ("#f0a500" if bpct < 100 else "#f75676")}"></div></div></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        an_col1, an_col2 = st.columns(2)
        with an_col1:
            st.markdown('<div class="analytics-card"><div class="analytics-title">Avg Spend by Day</div>', unsafe_allow_html=True)
            st.markdown(build_dow_html(an_df), unsafe_allow_html=True)
            st.markdown('<div style="font-size:.65rem;color:#333;margin-top:8px"><span style="color:#f0a500">■</span> Weekday &nbsp; <span style="color:#5e72e4">■</span> Weekend</div></div>', unsafe_allow_html=True)
        with an_col2:
            st.markdown('<div class="analytics-card"><div class="analytics-title">Top Merchants</div>', unsafe_allow_html=True)
            if not an_df.empty:
                an_df_m = an_df.copy()
                an_df_m["_m"] = an_df_m.apply(extract_merchant, axis=1)
                top_m = an_df_m.groupby("_m")["Amount"].sum().sort_values(ascending=False).head(10).reset_index()
                top_m.columns, mx_m = ["Merchant","Total"], float(top_m["Total"].max() if not top_m.empty else 1.0)
                for _, mr in top_m.iterrows(): st.markdown(f'<div class="merchant-rank-row"><span class="merchant-rank-name">{mr["Merchant"][:22]}</span><div class="merchant-rank-bar" style="width:{mr["Total"] / mx_m * 80:.0f}px"></div><span class="merchant-rank-amt">Rs.{mr["Total"]:,.0f}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

elif active_tab == "search":
    st.markdown("<span style='font-size:1.2rem;font-weight:700;color:#e8e8f0'>Search & Filter</span>", unsafe_allow_html=True)
    if df.empty: st.markdown('<div class="empty-box"><div class="ico">🔍</div><div class="msg">No data to search yet.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="sec-head">Filters</p>', unsafe_allow_html=True)
        keyword = st.text_input("Keyword", placeholder="Search...", label_visibility="collapsed")
        dr1, dr2 = st.columns(2)
        min_date, max_date = df["Date"].min().date() if not df.empty else date(2020, 1, 1), max(df["Date"].max().date() if not df.empty else today, today)
        date_from, date_to = dr1.date_input("From", value=min_date, min_value=min_date, max_value=max_date, key="sf_from"), dr2.date_input("To", value=today, min_value=min_date, max_value=max_date, key="sf_to")
        fm1, fm2 = st.columns(2)
        sel_cats, sel_modes = fm1.multiselect("Categories", options=sorted(df["Category"].dropna().unique().tolist()), placeholder="All categories"), fm2.multiselect("Modes", options=sorted(df["Mode"].dropna().unique().tolist()), placeholder="All modes")
        fa1, fa2 = st.columns(2)
        amt_min, amt_max = fa1.number_input("Min amount (Rs.)", min_value=0.0, value=0.0, step=100.0, key="sf_amin"), fa2.number_input("Max amount (Rs.)", min_value=0.0, value=float(df["Amount"].max() or 100000), step=100.0, key="sf_amax")
        fc1, fc2, fc3, fc4 = st.columns(4)
        only_noted, only_auto, only_credited, only_today = fc1.checkbox("Has note", key="sf_noted"), fc2.checkbox("Auto", key="sf_auto"), fc3.checkbox("Credit", key="sf_cc"), fc4.checkbox("Today", key="sf_today")
        fs1, fs2 = st.columns([3, 1])
        sort_by = fs1.selectbox("Sort by", ["Date (newest)","Date (oldest)","Amount (highest)","Amount (lowest)","Category A-Z"], label_visibility="collapsed")
        if fs2.button("Clear", use_container_width=True):
            for k in ["sf_from","sf_to","sf_amin","sf_amax","sf_noted","sf_auto","sf_cc","sf_today"]: st.session_state.pop(k, None)
            st.rerun()

        result = df[(df["Date"].dt.date >= date_from) & (df["Date"].dt.date <= date_to)].copy()
        if keyword.strip(): result = result[(result["Category"].astype(str).str.contains(keyword.strip(), case=False, na=False)) | (result["Note"].astype(str).str.contains(keyword.strip(), case=False, na=False)) | (result["Mode"].astype(str).str.contains(keyword.strip(), case=False, na=False))]
        if sel_cats: result = result[result["Category"].isin(sel_cats)]
        if sel_modes: result = result[result["Mode"].isin(sel_modes)]
        result = result[(result["Amount"] >= amt_min) & (result["Amount"] <= amt_max)]
        if only_noted: result = result[result["Note"].astype(str).str.strip().ne("").ne("nan")]
        if only_auto: result = result[result["Note"].astype(str).str.contains("Auto-logged", case=False, na=False)]
        if only_credited: result = result[result["Mode"].astype(str).str.contains("Credit Card", case=False, na=False)]
        if only_today: result = result[result["Date"].dt.date == today]

        if sort_by == "Date (newest)": result = result.sort_values("Date", ascending=False)
        elif sort_by == "Date (oldest)": result = result.sort_values("Date", ascending=True)
        elif sort_by == "Amount (highest)": result = result.sort_values("Amount", ascending=False)
        elif sort_by == "Amount (lowest)": result = result.sort_values("Amount", ascending=True)
        else: result = result.sort_values("Category", ascending=True)

        r_count, r_total, r_avg = len(result), result["Amount"].sum(), result["Amount"].mean() if len(result) > 0 else 0
        ra1, ra2, ra3 = st.columns(3)
        ra1.markdown(f'<div class="tile"><div class="tile-accent" style="background:#f0a500"></div><div class="tile-label">Results</div><div class="tile-value" style="font-size:1.4rem">{r_count:,}</div></div>', unsafe_allow_html=True)
        ra2.markdown(f'<div class="tile"><div class="tile-accent" style="background:#5e72e4"></div><div class="tile-label">Total</div><div class="tile-value" style="font-size:1.4rem">Rs.{r_total:,.0f}</div></div>', unsafe_allow_html=True)
        ra3.markdown(f'<div class="tile"><div class="tile-accent" style="background:#2dce89"></div><div class="tile-label">Avg per txn</div><div class="tile-value" style="font-size:1.4rem">Rs.{r_avg:,.0f}</div></div>', unsafe_allow_html=True)

        st.markdown('<p class="sec-head">Results</p>', unsafe_allow_html=True)
        if result.empty: st.markdown('<div class="empty-box"><div class="ico">🔍</div><div class="msg">No matches.</div></div>', unsafe_allow_html=True)
        else:
            for idx, row in result.iterrows(): render_txn_row(idx, row, key_prefix="srch")

elif active_tab == "budgets":
    st.markdown("<span style='font-size:1.2rem;font-weight:700;color:#e8e8f0'>Budgets & Recurring</span>", unsafe_allow_html=True)
    st.markdown('<p class="sec-head">Budget Planner — ' + curr_ym + '</p>', unsafe_allow_html=True)
    _bp_filt = df[df["Date"].dt.to_period("M") == pd.Period(curr_ym, freq="M")].copy() if not df.empty else pd.DataFrame()
    _bp_budgets = st.session_state.settings_df[st.session_state.settings_df["Budget"].notna() & (st.session_state.settings_df["Budget"].astype(str).str.strip() != "")].copy() if not st.session_state.settings_df.empty else pd.DataFrame()
    _bp_total, _bp_spent = _bp_budgets["Budget"].apply(lambda v: float(v) if str(v).strip() not in ("","nan") else 0).sum() if not _bp_budgets.empty else 0.0, _bp_filt["Amount"].sum() if not _bp_filt.empty else 0.0
    
    _bpc1, _bpc2 = st.columns(2)
    _bpc1.markdown(f'<div class="tile"><div class="tile-accent" style="background:#5e72e4"></div><div class="tile-label">Total Budget</div><div class="tile-value" style="font-size:1.3rem">Rs.{_bp_total:,.0f}</div></div>', unsafe_allow_html=True)
    _bpc2.markdown(f'<div class="tile"><div class="tile-accent" style="background:#f75676"></div><div class="tile-label">Total Spent</div><div class="tile-value" style="font-size:1.3rem;color:#f75676">Rs.{_bp_spent:,.0f}</div></div>', unsafe_allow_html=True)
    
    if not _bp_budgets.empty:
        st.markdown(f'<p class="sec-head">Budgeted categories: {curr_ym}</p>', unsafe_allow_html=True)
        for _, _bprow in _bp_budgets.iterrows():
            _bpcat, _bplimit = _bprow["Category"], float(_bprow.get("Budget", 0) or 0)
            if _bplimit <= 0: continue
            _bpspent = _bp_filt[_bp_filt["Category"] == _bpcat]["Amount"].sum() if not _bp_filt.empty else 0.0
            st.markdown(f'<div class="budget-row"><div class="budget-header"><span class="budget-name">{_bpcat}</span><span style="background:{"#2dce89" if _bpspent/_bplimit < 0.75 else ("#f0a500" if _bpspent <= _bplimit else "#f75676")};color:#000;font-size:.7rem;font-weight:700;padding:1px 7px;border-radius:4px">Rs.{_bplimit:,.0f}</span></div><div style="font-size:.72rem;color:#888;margin-bottom:4px">Spent: <span style="color:#f75676">Rs.{_bpspent:,.0f}</span> &nbsp;·&nbsp; Remaining: <span style="color:{"#2dce89" if _bpspent/_bplimit < 0.75 else ("#f0a500" if _bpspent <= _bplimit else "#f75676")}">Rs.{max(_bplimit - _bpspent, 0):,.0f}</span></div><div class="prog-track"><div class="prog-fill" style="width:{min(_bpspent / _bplimit * 100, 110):.1f}%;background:{"#2dce89" if _bpspent/_bplimit < 0.75 else ("#f0a500" if _bpspent <= _bplimit else "#f75676")}"></div></div>{"<span style=\'color:#f75676;font-size:.7rem\'> *Limit exceeded</span>" if _bpspent > _bplimit else ""}</div>', unsafe_allow_html=True)
        
        _all_cats_bp, _budgeted_set = sorted(st.session_state.cat_df["Category"].dropna().tolist()) if not st.session_state.cat_df.empty else [], set(_bp_budgets["Category"].tolist())
        _unbudgeted_bp = [c for c in _all_cats_bp if c not in _budgeted_set]
        if _unbudgeted_bp:
            st.markdown('<p class="sec-head">Not budgeted this month</p>', unsafe_allow_html=True)
            for _ubc in _unbudgeted_bp:
                _ubc1, _ubc2 = st.columns([3, 1])
                _ubc1.markdown(f'<div class="catlist-row">{_ubc}</div>', unsafe_allow_html=True)
                with _ubc2:
                    with stylable_container(key=f"sbtn_{_ubc[:12]}", css_styles="button{background:#0d1a0d!important;border:1px solid #2dce89!important;border-radius:6px!important;color:#2dce89!important;font-size:.65rem!important;font-weight:700!important;height:28px!important;min-height:28px!important}"):
                        if st.button("SET", key=f"sb_{_ubc[:14]}", use_container_width=True): st.session_state[f"_sbdg_{_ubc}"] = True; st.rerun()
                if st.session_state.get(f"_sbdg_{_ubc}", False):
                    with st.form(f"sbf_{_ubc[:12]}"):
                        _nba = st.number_input(f"Budget for {_ubc} (Rs.)", min_value=0.0, step=500.0)
                        if st.form_submit_button("Save", type="primary"):
                            save_settings(pd.concat([st.session_state.settings_df, pd.DataFrame([{"Category": _ubc, "Budget": _nba, "Is_Recurring": False, "Day_of_Month": "", "Last_Fired": ""}])], ignore_index=True))
                            st.session_state.pop(f"_sbdg_{_ubc}", None); st.rerun()

    st.markdown('<p class="sec-head">Recurring Rules</p>', unsafe_allow_html=True)
    with st.expander("Create New Rule"):
        with st.form("new_rec"):
            rc1, rc2 = st.columns(2)
            c_sel, a_sel, d_sel = rc1.selectbox("Category", categories), rc2.number_input("Amount (Rs.)", min_value=0.0, value=None), st.slider("Auto-log on day", 1, 31, 1)
            if st.form_submit_button("Add Rule", type="primary"):
                if a_sel:
                    save_settings(pd.concat([st.session_state.settings_df, pd.DataFrame([{"Category": c_sel, "Budget": a_sel, "Is_Recurring": True, "Day_of_Month": d_sel, "Last_Fired": ""}])], ignore_index=True))
                    st.rerun()

    if not st.session_state.settings_df.empty:
        st.markdown('<p class="sec-head">Active Rules</p>', unsafe_allow_html=True)
        for i, row in st.session_state.settings_df.iterrows():
            try:
                if str(row.get("Is_Recurring", "")).strip().lower() in ("true", "1", "yes"):
                    dom, last_fired = int(row.get("Day_of_Month", 0)), str(row.get("Last_Fired", "")).strip()
                    st.markdown(f'<div class="rec-card {"rec-fired" if last_fired == curr_ym else "rec-pending"}"><div class="rec-title">{row["Category"]}</div><div class="rec-meta">Rs.{float(row["Budget"]):,.0f}  ·  {"Fired " + curr_ym if last_fired == curr_ym else f"Due on day {dom}"}</div></div>', unsafe_allow_html=True)
                    rcol1, rcol2, rcol3 = st.columns([5, 1, 1])
                    if not st.session_state.get(f"crec_{i}", False):
                        if rcol3.button("Del", key=f"del_rec_{i}", use_container_width=True): st.session_state[f"crec_{i}"] = True; st.rerun()
                    else:
                        rcol2.warning("Sure?")
                        if rcol2.button("Y", key=f"yrec_{i}"):
                            save_settings(st.session_state.settings_df.drop(i).reset_index(drop=True))
                            st.session_state[f"crec_{i}"] = False; st.rerun()
                        if rcol3.button("N", key=f"nrec_{i}"): st.session_state[f"crec_{i}"] = False; st.rerun()
            except Exception: pass

elif active_tab == "review":
    _rb1, _rb2 = st.columns([1, 4])
    with _rb1:
        with stylable_container(key="back_rec", css_styles="button{background:#1a1a24!important;border:1px solid #2a2a3a!important;border-radius:8px!important;color:#888!important;font-size:.75rem!important;height:32px!important;min-height:32px!important}"):
            if st.button("←", key="back_to_rec"): st.session_state.active_tab = "records"; st.rerun()
    _rb2.markdown("<span style='font-size:1.2rem;font-weight:700;color:#e8e8f0'>Pending Review</span>", unsafe_allow_html=True)

    pend_all = st.session_state.pending_df.copy() if not st.session_state.pending_df.empty else pd.DataFrame()
    active_pend = pend_all[pend_all["Review_Status"].astype(str) == "pending"].copy() if not pend_all.empty and "Review_Status" in pend_all.columns else pd.DataFrame()

    if active_pend.empty: st.markdown("<div class='empty-box'><div class='ico'>✅</div><div class='msg'>All caught up! No items pending review.</div></div>", unsafe_allow_html=True)
    else:
        active_pend["_merchant"] = active_pend.apply(extract_merchant, axis=1)
        live_categories, anomaly_map, dup_set, recur_set = sorted(st.session_state.cat_df["Category"].dropna().tolist()) if not st.session_state.cat_df.empty else [], detect_anomalies(active_pend, df) if not df.empty else {}, detect_duplicates(active_pend), detect_recurring_merchants(active_pend, df) if not df.empty else set()
        merchant_list = active_pend.groupby("_merchant").agg(count=("Amount","count"), total=("Amount","sum"), sug=("Suggested_Category", lambda x: (x.astype(str).str.strip().replace("nan","").replace("","").mode().iloc[0] if not x.astype(str).str.strip().replace("nan","").replace("","").mode().empty else ""))).reset_index().sort_values("count", ascending=False)
        n_pend, n_groups, n_with_sug = len(active_pend), len(merchant_list), int((merchant_list["sug"].str.strip().ne("")).sum())

        st.markdown(f'<div style="background:#0f0f15;border:1px solid #2a2a3a;border-radius:12px;padding:13px 16px;margin-bottom:16px"><div style="display:flex;justify-content:space-between;align-items:center"><span style="font-size:.9rem;font-weight:600;color:#f0a500">⚠️ {n_pend} transaction{"s" if n_pend!=1 else ""} · {n_groups} merchants</span><span style="font-size:.76rem;color:#444460">{n_with_sug} with suggestions</span></div><div style="margin-top:6px">{f"<span class=\'badge-anomaly\'>🚨 {len(anomaly_map)} unusual</span>" if anomaly_map else ""}{f"<span class=\'badge-dup\'>⚠ {len(dup_set)} possible dups</span>" if dup_set else ""}</div></div>', unsafe_allow_html=True)

        if n_with_sug > 0 and st.button(f"✅ Approve all {n_with_sug} with suggestions", type="primary", use_container_width=True, key="bulk_appr"):
            st.toast(f"Approved {approve_all_with_suggestions()} transactions!"); st.rerun()

        for _, grp_row in merchant_list.iterrows():
            merchant, count, total, sug_cat, grp_indices = grp_row["_merchant"], int(grp_row["count"]), float(grp_row["total"]), str(grp_row["sug"]).strip() if grp_row["sug"] else "", active_pend[active_pend["_merchant"] == grp_row["_merchant"]].index.tolist()
            st.markdown(f'<div class="review-card"><div style="display:flex;justify-content:space-between;align-items:flex-start"><div style="font-size:1rem;font-weight:700;color:#e8e8f0">{merchant}</div><div style="text-align:right"><div style="font-size:1rem;font-weight:700;color:#2dce89;font-family:\'JetBrains Mono\',monospace">Rs.{total:,.0f}</div><div style="font-size:.7rem;color:#444460">{count} txn{"s" if count>1 else ""}</div></div></div><div>{"<span class=\'review-badge-sug\'>💡 " + sug_cat + "</span>" if sug_cat and sug_cat != "nan" else ""}{"<span class=\'badge-anomaly\'>🚨 Unusual</span>" if any(idx in anomaly_map for idx in grp_indices) else ""}{"<span class=\'badge-recur\'>🔄 Recurring</span>" if merchant in recur_set else ""}</div></div>', unsafe_allow_html=True)
            
            grp_key = merchant.replace(" ","_").replace(".","")[:30]
            sel_cat = st.selectbox("Category", options=["-- New category --"] + live_categories, index=(live_categories.index(sug_cat) + 1) if sug_cat in live_categories else 0, key=f"grp_cat_{grp_key}", label_visibility="collapsed")
            final_cat, is_new_cat = (st.text_input("New category name", value=sug_cat if sug_cat and sug_cat != "nan" else "", key=f"grp_newcat_{grp_key}").strip(), True) if sel_cat == "-- New category --" else (sel_cat, False)
            remember_rule = st.toggle(f"Remember rule for {merchant[:25]}", value=True, key=f"rem_{grp_key}")

            col_approve, col_skip, col_split_btn = st.columns(3)
            if col_approve.button(f"✅ Approve {count}", key=f"grp_approve_{grp_key}", use_container_width=True, type="primary", disabled=(not final_cat)):
                if final_cat: approve_merchant_group(grp_indices, final_cat, create_new_cat=is_new_cat, merchant_name=merchant if remember_rule else ""); st.toast(f"Approved {count}"); st.rerun()
            if col_skip.button(f"⏭ Skip {count}", key=f"grp_skip_{grp_key}", use_container_width=True): skip_merchant_group(grp_indices); st.rerun()

elif active_tab == "accounts":
    st.markdown("<span style='font-size:1.2rem;font-weight:700;color:#e8e8f0'>Settings</span>", unsafe_allow_html=True)
    with st.form("income_form"):
        fi1, fi2 = st.columns([3, 1])
        new_income = fi1.number_input("Monthly Income (Rs.)", min_value=0.0, value=float(get_app_setting(KEY_INCOME, "0") or 0), step=1000.0)
        if fi2.form_submit_button("Save", use_container_width=True, type="primary"): set_app_setting(KEY_INCOME, new_income); st.rerun()
    
    st.markdown('<p class="sec-head">Gmail Sync</p>', unsafe_allow_html=True)
    if st.button("🔄 Sync Now", type="primary", use_container_width=True, key="sync_now_btn"):
        with st.spinner("Syncing Gmail..."):
            try: st.session_state.sync_result = requests.get(st.secrets.get("apps_script_url", ""), timeout=120).json()
            except Exception as e: st.session_state.sync_result = {"status": "error", "message": str(e)}
            hard_refresh()
            
elif active_tab == "categories":
    st.markdown("<span style='font-size:1.2rem;font-weight:700;color:#e8e8f0'>Categories & Security</span>", unsafe_allow_html=True)
    with st.form("catpg_add"):
        _cpf1, _cpf2 = st.columns([4, 1])
        _cpnew = _cpf1.text_input("New", label_visibility="collapsed", placeholder="e.g. Dining Out")
        if _cpf2.form_submit_button("+ Add", use_container_width=True):
            if _cpnew.strip(): save_categories(pd.concat([st.session_state.cat_df, pd.DataFrame([{"Category": _cpnew.strip()}])], ignore_index=True)); st.rerun()
    for _cpi, _cprow in st.session_state.cat_df.iterrows():
        _cp1, _cp2 = st.columns([5, 1])
        _cp1.markdown(f'<div class="catlist-row">{_cprow["Category"]}</div>', unsafe_allow_html=True)
        if _cp2.button("Del", key=f"del_cat_{_cpi}"): save_categories(st.session_state.cat_df.drop(_cpi).reset_index(drop=True)); st.rerun()

# ==============================================================================
# BOTTOM NAVIGATION BAR (Visual + Overlays)
# ==============================================================================
_pend_sfx = f" ⚠{pending_count}" if pending_count > 0 else ""
_NAV_ITEMS = [("records", "📋", "Records" + _pend_sfx), ("analysis", "📊", "Analysis"), ("budgets", "💰", "Budgets"), ("accounts", "⚙️", "Settings"), ("categories", "🏷️", "Categories")]
_is_records_active = active_tab in ("records", "search", "review")

_nav_html = '<div class="bnav-wrap">'
for _ntid, _nico, _nlbl in _NAV_ITEMS:
    _nav_html += f'<div class="bnav-item{" active" if (_ntid == "records" and _is_records_active) or (_ntid == active_tab and not _is_records_active) else ""}"><span class="bnav-icon">{_nico}</span><span>{_nlbl}</span></div>'
_nav_html += '</div>'
st.markdown(_nav_html, unsafe_allow_html=True)

with stylable_container(key="bnav_overlays", css_styles=".stHorizontalBlock { display: flex !important; flex-wrap: nowrap !important; }"):
    _bnav_cols = st.columns(5)
    for _bc, (_ntid, _nico, _nlbl) in zip(_bnav_cols, _NAV_ITEMS):
        with _bc:
            with stylable_container(key=f"nav_{_ntid}", css_styles="button{background:transparent!important;border:none!important;color:transparent!important;height:60px!important;position:fixed!important;bottom:0!important;z-index:10000!important;opacity:0!important;}"):
                if st.button("nav", key=f"navbtn_{_ntid}"): st.session_state.active_tab = _ntid; st.rerun()

# ==============================================================================
# FAB — QUICK LOG
# ==============================================================================
if "show_modal" not in st.session_state: st.session_state.show_modal = False
@st.dialog("Quick Log")
def log_modal():
    if "form_id" not in st.session_state: st.session_state.form_id = 0
    fid = st.session_state.form_id
    amt = st.number_input("Amount (Rs.)", min_value=0.0, value=None, key=f"amt_{fid}")
    cat = st.selectbox("Category", categories, key=f"cat_{fid}")
    if st.button("Save", type="primary", use_container_width=True):
        if amt:
            save_expense({"Date": f"{today.strftime('%Y-%m-%d')} {now.strftime('%H:%M:%S')}", "Amount": amt, "Category": cat, "Mode": "UPI", "Note": ""})
            st.session_state.show_modal = False; st.rerun()
if st.session_state.show_modal: log_modal()

with stylable_container(key="fab", css_styles="button {position: fixed; bottom: 72px; right: 24px; width: 60px; height: 60px; border-radius: 50%; background: #f0a500; color: #000; font-size: 34px; z-index: 9999; border: none; box-shadow: 0 6px 24px rgba(240,165,0,0.45);}"):
    if st.button("+", key="main_plus_btn"): st.session_state.show_modal = True; st.rerun()

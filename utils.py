import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta, date
import pytz

# ==============================================================================
# CONSTANTS
# ==============================================================================
RECENT_TXN_COUNT    = 7
HDFC_MILESTONE_AMT  = 100_000
LARGE_AMT_WARNING   = 50_000
TZ                  = pytz.timezone('Asia/Kolkata')
DEFAULT_MODES       = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]
MAX_PIN_ATTEMPTS    = 5
ANOMALY_MULT        = 3.0
RECUR_MIN_MONTHS    = 3

KEY_INCOME          = "Monthly_Income"
KEY_ALERT_PCT       = "Budget_Alert_Threshold"
KEY_ALERT_ON        = "Budget_Alert_Enabled"
KEY_PULSE_ON        = "Weekly_Pulse_Enabled"

# ==============================================================================
# DATA LOADERS
# ==============================================================================
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=30)
def load_all_data():
    conn = get_connection()
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
            il = pd.DataFrame(columns=["Run_Time","Emails_Found","Imported","Skipped","Pending","Status","Notes"])
        try:
            ir = conn.read(worksheet="ImportRules")
        except Exception:
            ir = pd.DataFrame(columns=["Keyword","Match_In","Category"])
        try:
            a = conn.read(worksheet="AppSettings")
        except Exception:
            a = pd.DataFrame(columns=["Key","Value"])
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

@st.cache_data(ttl=30)
def load_pin():
    conn = get_connection()
    try:
        sec = conn.read(worksheet="Security", usecols=[0], nrows=1)
        raw = str(sec.iloc[0, 0]).strip()
        return raw if raw.isdigit() and len(raw) == 4 else "1234"
    except Exception:
        return "1234"

# ==============================================================================
# SAVE HELPERS
# ==============================================================================
def save_expense(row_dict):
    conn = get_connection()
    with st.spinner("Saving..."):
        new_row = pd.DataFrame([row_dict])
        new_row["Date"]   = pd.to_datetime(new_row["Date"], errors="coerce")
        new_row["Amount"] = pd.to_numeric(new_row["Amount"], errors="coerce").fillna(0)
        updated = pd.concat([st.session_state.df, new_row], ignore_index=True)
        conn.update(worksheet="Expenses", data=updated)
        st.session_state.df = updated
        st.cache_data.clear()

def update_expense(idx, fields):
    conn = get_connection()
    with st.spinner("Updating..."):
        for k, v in fields.items():
            st.session_state.df.at[idx, k] = v
        conn.update(worksheet="Expenses", data=st.session_state.df)
        st.cache_data.clear()

def delete_expense(idx):
    conn = get_connection()
    with st.spinner("Deleting..."):
        updated = st.session_state.df.drop(idx).reset_index(drop=True)
        conn.update(worksheet="Expenses", data=updated)
        st.session_state.df = updated
        st.cache_data.clear()

def save_settings(new_df):
    conn = get_connection()
    with st.spinner("Saving..."):
        conn.update(worksheet="Settings", data=new_df)
        st.session_state.settings_df = new_df
        st.cache_data.clear()

def save_categories(new_df):
    conn = get_connection()
    with st.spinner("Saving..."):
        conn.update(worksheet="Categories", data=new_df)
        st.session_state.cat_df = new_df
        st.cache_data.clear()

def save_modes(new_df):
    conn = get_connection()
    with st.spinner("Saving..."):
        conn.update(worksheet="Modes", data=new_df)
        st.session_state.modes_df = new_df
        st.cache_data.clear()

def save_pin(new_pin: str):
    conn = get_connection()
    with st.spinner("Saving PIN..."):
        pin_df = pd.DataFrame({"PIN": [new_pin]})
        conn.update(worksheet="Security", data=pin_df)
        st.session_state.active_pin = new_pin
        st.cache_data.clear()

def save_import_rules(new_df):
    conn = get_connection()
    with st.spinner("Saving rules..."):
        conn.update(worksheet="ImportRules", data=new_df)
        st.session_state.import_rules = new_df
        st.cache_data.clear()

def get_app_setting(key, default="0"):
    df_a = st.session_state.get("app_settings_df", pd.DataFrame())
    if df_a.empty or "Key" not in df_a.columns:
        return default
    mask = df_a["Key"].astype(str).str.strip() == key
    if not mask.any():
        return default
    return str(df_a.loc[mask, "Value"].iloc[0]).strip()

def set_app_setting(key, value):
    conn = get_connection()
    df_a = st.session_state.get("app_settings_df", pd.DataFrame(columns=["Key","Value"])).copy()
    mask = df_a["Key"].astype(str).str.strip() == key if not df_a.empty else pd.Series([], dtype=bool)
    if not df_a.empty and mask.any():
        df_a.loc[mask, "Value"] = str(value)
    else:
        df_a = pd.concat([df_a, pd.DataFrame([{"Key": key, "Value": str(value)}])], ignore_index=True)
    conn.update(worksheet="AppSettings", data=df_a)
    st.session_state.app_settings_df = df_a
    st.cache_data.clear()

def split_expense_row(idx, amt1, cat1, amt2, cat2):
    conn = get_connection()
    with st.spinner("Splitting..."):
        orig = st.session_state.df.loc[idx]
        note_base = str(orig.get("Note", "") or "").strip()
        row1 = {
            "Date": orig.get("Date",""), "Amount": amt1, "Category": cat1,
            "Note": f"{note_base} (split 1/2)".strip(),
            "Mode": orig.get("Mode",""), "UPI_Ref": str(orig.get("UPI_Ref","") or ""),
            "Source_Account": orig.get("Source_Account",""),
            "Import_Source": orig.get("Import_Source",""), "Review_Status": orig.get("Review_Status",""),
        }
        row2 = {
            "Date": orig.get("Date",""), "Amount": amt2, "Category": cat2,
            "Note": f"{note_base} (split 2/2)".strip(),
            "Mode": orig.get("Mode",""), "UPI_Ref": "",
            "Source_Account": orig.get("Source_Account",""),
            "Import_Source": orig.get("Import_Source",""), "Review_Status": orig.get("Review_Status",""),
        }
        base  = st.session_state.df.drop(idx).reset_index(drop=True)
        r1_df = pd.DataFrame([row1])
        r2_df = pd.DataFrame([row2])
        r1_df["Date"] = pd.to_datetime(r1_df["Date"], errors="coerce")
        r2_df["Date"] = pd.to_datetime(r2_df["Date"], errors="coerce")
        updated = pd.concat([base, r1_df, r2_df], ignore_index=True)
        conn.update(worksheet="Expenses", data=updated)
        st.session_state.df = updated
        st.cache_data.clear()

# ==============================================================================
# ANALYTICS & REVIEW FUNCTIONS
# ==============================================================================
def extract_merchant(row):
    txn  = str(row.get("Transaction_Details", "") or "").strip()
    note = str(row.get("Note", "") or "").strip()
    src  = txn or note.split("·")[0].strip()
    for prefix in ["Paid to ","paid to ","Money sent to ","money sent to "]:
        if src.lower().startswith(prefix.lower()):
            src = src[len(prefix):]
            break
    return src.strip() or "Unknown Merchant"

def build_heatmap_html(df_h):
    now_date = datetime.now(TZ).date()
    if df_h.empty:
        return "<div style='color:#444460;font-size:.82rem;padding:20px 0'>No data yet — sync transactions to see your heatmap</div>"
    dfc = df_h[df_h["Date"].notna()].copy()
    if dfc.empty: return "<div style='color:#444460;font-size:.82rem'>No dated transactions</div>"
    dfc["_day"] = dfc["Date"].dt.date
    daily = dfc.groupby("_day")["Amount"].sum()
    mx = float(daily.max()) if not daily.empty else 1.0
    if mx == 0: mx = 1.0
    start = now_date - timedelta(weeks=52)
    start = start - timedelta(days=start.weekday())
    week_starts, month_marks, last_m, wi = [], [], None, 0
    cur = start
    while cur <= now_date:
        m = cur.strftime("%b")
        if m != last_m:
            month_marks.append((wi, m))
            last_m = m
        week_starts.append(cur)
        cur += timedelta(weeks=1)
        wi += 1
    total_weeks = len(week_starts)
    mh = '<div style="display:flex;margin-bottom:4px;margin-left:18px">'
    for i, (wk, mn) in enumerate(month_marks):
        nxt = month_marks[i+1][0] if i+1 < len(month_marks) else total_weeks
        px  = (nxt - wk) * 12
        mh += f'<div style="min-width:{px}px;font-size:.6rem;color:#444460;overflow:hidden;white-space:nowrap">{mn}</div>'
    mh += '</div>'
    dlabels = ["M","","W","","F","","S"]
    lc = '<div style="display:flex;flex-direction:column;gap:2px;margin-right:4px;flex-shrink:0">'
    for d in dlabels: lc += f'<div style="width:10px;height:10px;font-size:.55rem;color:#333;line-height:10px;text-align:center">{d}</div>'
    lc += '</div>'
    gc = ""
    for ws in week_starts:
        col = '<div style="display:flex;flex-direction:column;gap:2px">'
        for d in range(7):
            day = ws + timedelta(days=d)
            if day > now_date:
                col += '<div style="width:10px;height:10px"></div>'
                continue
            amt = float(daily.get(day, 0))
            if amt == 0:
                color, tip = "#1a1a24", f"Rs.0 · {day.strftime('%d %b')}"
            else:
                inten = amt / mx
                if   inten < 0.2: color = "#2a1f05"
                elif inten < 0.4: color = "#3a2c05"
                elif inten < 0.6: color = "#5a4010"
                elif inten < 0.8: color = "#8a6200"
                else:             color = "#f0a500"
                tip = f"Rs.{amt:,.0f} · {day.strftime('%d %b')}"
            col += f'<div title="{tip}" style="width:10px;height:10px;border-radius:2px;background:{color}"></div>'
        col += '</div>'
        gc += col
    legend = (
        '<div style="display:flex;align-items:center;gap:6px;margin-top:8px;font-size:.62rem;color:#444460">'
        '<span>Less</span>' + "".join([f'<div style="width:10px;height:10px;border-radius:2px;background:{c}"></div>' for c in ["#1a1a24","#2a1f05","#5a4010","#8a6200","#f0a500"]]) + '<span>More</span></div>'
    )
    return f'<div class="heatmap-wrap">{mh}<div style="display:flex;gap:2px">{lc}{gc}</div>{legend}</div>'

def build_dow_html(df_d):
    if df_d.empty: return "<div style='color:#444460;font-size:.82rem'>No data</div>"
    dfc = df_d[df_d["Date"].notna()].copy()
    dfc["_dow"] = dfc["Date"].dt.dayofweek
    dow_avg = dfc.groupby("_dow")["Amount"].mean()
    days  = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    mx    = float(dow_avg.max()) if not dow_avg.empty else 1.0
    if mx == 0: mx = 1.0
    html = ""
    for i, day in enumerate(days):
        avg    = float(dow_avg.get(i, 0))
        pct    = avg / mx * 100
        color  = "#5e72e4" if i >= 5 else "#f0a500"
        html  += (f'<div class="dow-row"><span class="dow-label">{day}</span>'
                  f'<div style="flex:1;background:#1a1a24;border-radius:4px;height:16px;overflow:hidden">'
                  f'<div class="dow-bar-fill" style="width:{pct:.1f}%;background:{color}"></div></div>'
                  f'<span class="dow-bar-amt">Rs.{avg:,.0f}</span></div>')
    return html

def detect_anomalies(pending_df_a, expenses_df_a):
    if pending_df_a.empty or expenses_df_a.empty: return {}
    hist = expenses_df_a[expenses_df_a["Date"].notna()].copy()
    hist["_m"] = hist.apply(extract_merchant, axis=1)
    stats = hist.groupby("_m")["Amount"].agg(["mean","count"])
    stats = stats[stats["count"] >= 3]
    stats_map = stats["mean"].to_dict()
    anomalies = {}
    _rs = pending_df_a["Review_Status"].astype(str) if "Review_Status" in pending_df_a.columns else pd.Series("", index=pending_df_a.index)
    active = pending_df_a[_rs == "pending"].copy()
    if active.empty: return {}
    active["_m"] = active.apply(extract_merchant, axis=1)
    for idx, row in active.iterrows():
        m, amt = row["_m"], float(row.get("Amount", 0))
        if m in stats_map and stats_map[m] > 0 and amt > stats_map[m] * ANOMALY_MULT:
            anomalies[idx] = {"merchant": m, "amount": amt, "avg": stats_map[m]}
    return anomalies

def detect_duplicates(pending_df_d):
    if pending_df_d.empty: return set()
    _rs = pending_df_d["Review_Status"].astype(str) if "Review_Status" in pending_df_d.columns else pd.Series("", index=pending_df_d.index)
    active = pending_df_d[_rs == "pending"].copy()
    if active.empty: return set()
    active["_m"] = active.apply(extract_merchant, axis=1)
    active["_dt"] = pd.to_datetime(active["Date"], errors="coerce")
    dup_idx = set()
    rows = list(active.iterrows())
    for i, (idx1, r1) in enumerate(rows):
        for idx2, r2 in rows[i+1:]:
            if r1["_m"] == r2["_m"] and r1["Amount"] == r2["Amount"]:
                d1, d2 = r1["_dt"], r2["_dt"]
                if pd.notna(d1) and pd.notna(d2) and abs((d1-d2).total_seconds()) <= 86400:
                    dup_idx.add(idx1); dup_idx.add(idx2)
    return dup_idx

def detect_recurring_merchants(pending_df_r, expenses_df_r):
    if pending_df_r.empty or expenses_df_r.empty: return set()
    _rs = pending_df_r["Review_Status"].astype(str) if "Review_Status" in pending_df_r.columns else pd.Series("", index=pending_df_r.index)
    active = pending_df_r[_rs == "pending"].copy()
    if active.empty: return set()
    active["_m"] = active.apply(extract_merchant, axis=1)
    pending_merchants = set(active["_m"].unique())
    hist = expenses_df_r[expenses_df_r["Date"].notna()].copy()
    hist["_m"]  = hist.apply(extract_merchant, axis=1)
    hist["_mo"] = hist["Date"].dt.to_period("M").astype(str)
    mnth = hist[hist["_m"].isin(pending_merchants)].groupby("_m")["_mo"].nunique()
    return set(mnth[mnth >= RECUR_MIN_MONTHS].index)

def get_merchant_trend(merchant, expenses_df_t):
    if expenses_df_t.empty: return None
    hist = expenses_df_t[expenses_df_t["Date"].notna()].copy()
    hist["_m"] = hist.apply(extract_merchant, axis=1)
    hist["_mo"] = hist["Date"].dt.to_period("M")
    last3 = sorted(hist["_mo"].unique())[-3:]
    sub = hist[(hist["_m"] == merchant) & (hist["_mo"].isin(last3))]
    if sub.empty: return None
    return sub.groupby("_mo")["Amount"].sum().mean()

def approve_pending_row(idx, chosen_category, create_new_cat=False):
    conn = get_connection()
    with st.spinner("Approving..."):
        row = st.session_state.pending_df.loc[idx]
        if create_new_cat and chosen_category not in [c for c in st.session_state.cat_df["Category"].dropna().tolist()]:
            save_categories(pd.concat([st.session_state.cat_df, pd.DataFrame([{"Category": chosen_category}])], ignore_index=True))
        expense_row = {
            "Date": row.get("Date",""), "Amount": row.get("Amount",0), "Category": chosen_category, "Note": row.get("Note",""),
            "Mode": row.get("Mode","UPI"), "UPI_Ref": row.get("UPI_Ref",""), "Source_Account": row.get("Source_Account",""),
            "Import_Source": row.get("Import_Source","paytm_auto"), "Review_Status": "approved",
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

def skip_pending_row(idx):
    conn = get_connection()
    with st.spinner("Skipping..."):
        st.session_state.pending_df.at[idx, "Review_Status"] = "skipped"
        conn.update(worksheet="PendingReview", data=st.session_state.pending_df)
        st.cache_data.clear()

def approve_all_with_suggestions():
    pend = st.session_state.pending_df
    if pend.empty: return 0
    _rs  = pend["Review_Status"].astype(str) if "Review_Status" in pend.columns else pd.Series("", index=pend.index)
    _sug = pend["Suggested_Category"].astype(str) if "Suggested_Category" in pend.columns else pd.Series("", index=pend.index)
    to_approve = pend[(_rs == "pending") & (_sug.str.strip().ne("")) & (_sug.str.strip().ne("nan"))]
    if to_approve.empty: return 0
    count = 0
    for idx, row in to_approve.iterrows():
        sug = str(row.get("Suggested_Category","")).strip()
        if sug and sug != "nan":
            approve_pending_row(idx, sug, create_new_cat=True)
            count += 1
    return count

def auto_save_import_rule(merchant, category):
    rules = st.session_state.import_rules
    words = [w for w in merchant.split() if len(w) > 3]
    keyword = words[0] if words else merchant[:10]
    keyword = keyword.strip()
    if len(keyword) < 3: return
    existing = rules["Keyword"].astype(str).str.lower().str.strip().tolist() if not rules.empty else []
    if keyword.lower() in existing: return
    new_rule = pd.DataFrame([{"Keyword": keyword, "Match_In": "Any", "Category": category}])
    updated  = pd.concat([rules, new_rule], ignore_index=True) if not rules.empty else new_rule
    save_import_rules(updated)

def approve_merchant_group(indices, chosen_category, create_new_cat=False, merchant_name=""):
    conn = get_connection()
    with st.spinner(f"Approving {len(indices)} transactions..."):
        existing_cats = st.session_state.cat_df["Category"].dropna().tolist()
        if create_new_cat and chosen_category not in existing_cats:
            save_categories(pd.concat([st.session_state.cat_df, pd.DataFrame([{"Category": chosen_category}])], ignore_index=True))
        pend = st.session_state.pending_df
        new_expense_rows = []
        for idx in indices:
            if idx not in pend.index: continue
            row = pend.loc[idx]
            new_expense_rows.append({
                "Date": row.get("Date",""), "Amount": row.get("Amount",0), "Category": chosen_category, "Note": row.get("Note",""),
                "Mode": row.get("Mode","UPI"), "UPI_Ref": row.get("UPI_Ref",""), "Source_Account": row.get("Source_Account",""),
                "Import_Source": row.get("Import_Source","paytm_auto"), "Review_Status": "approved",
            })
        if new_expense_rows:
            exp_new = pd.DataFrame(new_expense_rows)
            exp_new["Date"]   = pd.to_datetime(exp_new["Date"], errors="coerce")
            exp_new["Amount"] = pd.to_numeric(exp_new["Amount"], errors="coerce").fillna(0)
            updated_exp = pd.concat([st.session_state.df, exp_new], ignore_index=True)
            conn.update(worksheet="Expenses", data=updated_exp)
            st.session_state.df = updated_exp
        updated_pend = pend.drop(index=indices).reset_index(drop=True)
        conn.update(worksheet="PendingReview", data=updated_pend)
        st.session_state.pending_df = updated_pend
        st.cache_data.clear()
        if merchant_name and chosen_category:
            auto_save_import_rule(merchant_name, chosen_category)

def skip_merchant_group(indices):
    conn = get_connection()
    with st.spinner("Skipping..."):
        for idx in indices:
            if idx in st.session_state.pending_df.index:
                st.session_state.pending_df.at[idx, "Review_Status"] = "skipped"
        conn.update(worksheet="PendingReview", data=st.session_state.pending_df)
        st.cache_data.clear()

def approve_split_group(split_map, create_cats=None):
    conn = get_connection()
    with st.spinner(f"Approving {len(split_map)} transactions..."):
        create_cats = create_cats or []
        existing_cats = st.session_state.cat_df["Category"].dropna().tolist()
        for cat in create_cats:
            if cat and cat not in existing_cats:
                save_categories(pd.concat([st.session_state.cat_df, pd.DataFrame([{"Category": cat}])], ignore_index=True))
                existing_cats.append(cat)
        pend = st.session_state.pending_df
        new_rows = []
        for idx, cat in split_map.items():
            if idx not in pend.index or not cat or cat == "-- New category --": continue
            row = pend.loc[idx]
            new_rows.append({
                "Date": row.get("Date",""), "Amount": row.get("Amount",0), "Category": cat, "Note": row.get("Note",""),
                "Mode": row.get("Mode","UPI"), "UPI_Ref": row.get("UPI_Ref",""), "Source_Account": row.get("Source_Account",""),
                "Import_Source": row.get("Import_Source","paytm_auto"), "Review_Status": "approved",
            })
        if new_rows:
            exp_new = pd.DataFrame(new_rows)
            exp_new["Date"]   = pd.to_datetime(exp_new["Date"], errors="coerce")
            exp_new["Amount"] = pd.to_numeric(exp_new["Amount"], errors="coerce").fillna(0)
            updated_exp = pd.concat([st.session_state.df, exp_new], ignore_index=True)
            conn.update(worksheet="Expenses", data=updated_exp)
            st.session_state.df = updated_exp
        indices = list(split_map.keys())
        updated_pend = pend.drop(index=indices).reset_index(drop=True)
        conn.update(worksheet="PendingReview", data=updated_pend)
        st.session_state.pending_df = updated_pend
        st.cache_data.clear()

import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import pytz
from streamlit_extras.stylable_container import stylable_container

# --- 1. SETTINGS & EXPERT UI ---
st.set_page_config(page_title="FinTrack Pro", page_icon="₹", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #ffffff; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }

    /* Top Tab Navigation Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #000000;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #111111;
        border-radius: 10px 10px 0px 0px;
        padding: 10px 20px;
        color: #888888;
    }
    .stTabs [aria-selected="true"] {
        background-color: #222222 !important;
        color: #ffffff !important;
        border-bottom: 2px solid #2563eb !important;
    }

    /* Tile Styling */
    .dashboard-tile {
        background-color: #111111;
        border: 1px solid #222222;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
    }
    .tile-label { color: #888888; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }
    .tile-value { font-size: 1.8rem; font-weight: 700; margin-top: 5px; }

    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: #555555;
    }
    .empty-state .icon { font-size: 3rem; margin-bottom: 12px; }
    .empty-state .msg { font-size: 1rem; }

    /* Dialog / Popup */
    div[data-testid="stDialog"] {
        background-color: #0a0a0a !important;
        border: 1px solid #333333 !important;
        border-radius: 28px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA LOAD ---
conn = st.connection("gsheets", type=GSheetsConnection)

# FIX: Reasonable TTL (30s) + no inner ttl=0 to stop hammering Sheets on every interaction
@st.cache_data(ttl=30)
def load_all_data():
    try:
        e = conn.read(worksheet="Expenses")
        c = conn.read(worksheet="Categories")
        s = conn.read(worksheet="Settings")
        return e, c, s
    except Exception as ex:
        st.error(f"⚠️ Could not load data from Google Sheets: {ex}")
        return (pd.DataFrame(columns=["Date", "Amount", "Category", "Note", "Mode"]),
                pd.DataFrame(columns=["Category"]),
                pd.DataFrame(columns=["Category", "Budget", "Is_Recurring", "Day_of_Month"]))

# FIX: Store dataframes in session state so writes update local state instantly,
#      avoiding a round-trip back to Sheets just to re-render
if "df" not in st.session_state or "cat_df" not in st.session_state or "settings_df" not in st.session_state:
    _df, _cat_df, _settings_df = load_all_data()
    st.session_state.df = _df
    st.session_state.cat_df = _cat_df
    st.session_state.settings_df = _settings_df

df         = st.session_state.df
cat_df     = st.session_state.cat_df
settings_df = st.session_state.settings_df

# Pre-process dates & amounts once
if not df.empty:
    df['Date']   = pd.to_datetime(df['Date'], errors='coerce')
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)

categories    = sorted(cat_df["Category"].dropna().tolist()) if not cat_df.empty else []
payment_modes = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]
tz            = pytz.timezone('Asia/Kolkata')
now           = datetime.now(tz)

# Helper: write expense row without full cache reload
def save_expense(new_row_dict):
    new_row = pd.DataFrame([new_row_dict])
    updated = pd.concat([st.session_state.df, new_row], ignore_index=True)
    conn.update(worksheet="Expenses", data=updated)
    st.session_state.df = updated
    st.cache_data.clear()   # Invalidate so next cold load is fresh

def save_settings(new_df):
    conn.update(worksheet="Settings", data=new_df)
    st.session_state.settings_df = new_df
    st.cache_data.clear()

def save_categories(new_df):
    conn.update(worksheet="Categories", data=new_df)
    st.session_state.cat_df = new_df
    st.cache_data.clear()

# --- 3. TOP NAVIGATION TABS ---
tab_home, tab_rec, tab_cat = st.tabs(["🏠 Home", "🔄 Recurring", "🏷️ Categories"])

# --- 4. TAB: HOME ---
with tab_home:
    st.write("## Dashboard")

    if df.empty or df['Amount'].sum() == 0:
        # FIX: Friendly empty state instead of blank screen
        st.markdown("""
            <div class="empty-state">
                <div class="icon">💸</div>
                <div class="msg">No expenses logged yet.<br>Tap <strong>+</strong> to record your first transaction.</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        # --- Tiles row ---
        col1, col2 = st.columns(2)

        # Today tile
        today_total = df[df['Date'].dt.date == now.date()]['Amount'].sum()
        col1.markdown(f'<div class="dashboard-tile"><div class="tile-label">Spent Today</div><div class="tile-value">₹{today_total:,.0f}</div></div>', unsafe_allow_html=True)

        # FIX: This Month tile
        month_total = df[(df['Date'].dt.month == now.month) & (df['Date'].dt.year == now.year)]['Amount'].sum()
        col2.markdown(f'<div class="dashboard-tile"><div class="tile-label">This Month</div><div class="tile-value">₹{month_total:,.0f}</div></div>', unsafe_allow_html=True)

        # HDFC Q Milestone tile (full width)
        q_map   = {1:1, 2:1, 3:1, 4:2, 5:2, 6:2, 7:3, 8:3, 9:3, 10:4, 11:4, 12:4}
        curr_q  = q_map[now.month]
        h_spend = df[(df['Date'].dt.month.map(q_map) == curr_q) & (df['Mode'] == 'HDFC Credit Card')]['Amount'].sum()
        color   = "#2563eb" if h_spend < 100000 else "#22c55e"
        pct     = min(h_spend / 100000 * 100, 100)
        st.markdown(f'''
            <div class="dashboard-tile" style="border-left: 4px solid {color};">
                <div class="tile-label">HDFC Q{curr_q} Milestone</div>
                <div class="tile-value">₹{h_spend:,.0f} <span style="font-size:0.9rem;color:#888">/ ₹1,00,000</span></div>
                <div style="margin-top:10px;background:#222;border-radius:8px;height:6px;">
                    <div style="width:{pct:.1f}%;background:{color};height:6px;border-radius:8px;transition:width 0.4s;"></div>
                </div>
            </div>
        ''', unsafe_allow_html=True)

        # FIX: Category breakdown for current month
        st.write("### 📊 This Month by Category")
        monthly_df = df[(df['Date'].dt.month == now.month) & (df['Date'].dt.year == now.year)]
        if not monthly_df.empty:
            cat_summary = (
                monthly_df.groupby("Category")["Amount"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
            )
            cat_summary.columns = ["Category", "Amount (₹)"]
            cat_summary["Amount (₹)"] = cat_summary["Amount (₹)"].map(lambda x: f"₹{x:,.0f}")
            st.dataframe(cat_summary, use_container_width=True, hide_index=True)

        # FIX: nlargest by Date instead of tail() to guarantee truly latest 6
        st.write("### 🕐 Latest 6 Transactions")
        latest = df.nlargest(6, 'Date')[['Date', 'Amount', 'Category', 'Mode', 'Note']].copy()
        latest['Date']   = latest['Date'].dt.strftime('%d %b, %I:%M %p')
        latest['Amount'] = latest['Amount'].map(lambda x: f"₹{x:,.0f}")
        st.dataframe(latest, use_container_width=True, hide_index=True)

# --- 5. TAB: RECURRING MAINTENANCE ---
with tab_rec:
    st.write("## Recurring Maintenance")
    with st.expander("➕ Create New Rule"):
        with st.form("new_rec"):
            c_sel = st.selectbox("Category", categories)
            a_sel = st.number_input("Amount", min_value=0.0, value=None, placeholder="₹ Enter Amount")
            d_sel = st.slider("Log Day", 1, 31, 1)
            if st.form_submit_button("Add to System"):
                if a_sel:
                    new_r   = pd.DataFrame([{"Category": c_sel, "Budget": a_sel, "Is_Recurring": True, "Day_of_Month": d_sel}])
                    updated = pd.concat([settings_df, new_r], ignore_index=True)
                    save_settings(updated)
                    st.rerun()
                else:
                    st.warning("Please enter an amount.")

    if settings_df.empty:
        st.markdown('<div class="empty-state"><div class="icon">🔄</div><div class="msg">No recurring rules yet.</div></div>', unsafe_allow_html=True)
    else:
        for i, row in st.session_state.settings_df.iterrows():
            with st.container(border=True):
                cols = st.columns([3, 1])
                cols[0].write(f"**{row['Category']}**\n₹{row['Budget']} on Day {row['Day_of_Month']}")
                # FIX: Two-step delete confirmation to prevent accidental deletion
                confirm_key = f"confirm_rec_{i}"
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False

                if not st.session_state[confirm_key]:
                    if cols[1].button("🗑️", key=f"del_rec_{i}"):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    cols[1].warning("Sure?")
                    c1, c2 = cols[1].columns(2)
                    if c1.button("✅", key=f"yes_rec_{i}"):
                        updated = st.session_state.settings_df.drop(i).reset_index(drop=True)
                        save_settings(updated)
                        st.session_state[confirm_key] = False
                        st.rerun()
                    if c2.button("❌", key=f"no_rec_{i}"):
                        st.session_state[confirm_key] = False
                        st.rerun()

# --- 6. TAB: CATEGORIES ---
with tab_cat:
    st.write("## Category List")
    with st.form("new_cat"):
        nc = st.text_input("New Category Name")
        if st.form_submit_button("Add"):
            if nc.strip():
                updated = pd.concat([st.session_state.cat_df, pd.DataFrame([{"Category": nc.strip()}])], ignore_index=True)
                save_categories(updated)
                st.rerun()
            else:
                st.warning("Category name cannot be empty.")

    if st.session_state.cat_df.empty:
        st.markdown('<div class="empty-state"><div class="icon">🏷️</div><div class="msg">No categories yet.</div></div>', unsafe_allow_html=True)
    else:
        for i, row in st.session_state.cat_df.iterrows():
            cols = st.columns([4, 1])
            cols[0].write(row['Category'])
            # FIX: Two-step delete confirmation
            confirm_key = f"confirm_cat_{i}"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = False

            if not st.session_state[confirm_key]:
                if cols[1].button("🗑️", key=f"del_cat_{i}"):
                    st.session_state[confirm_key] = True
                    st.rerun()
            else:
                cols[1].warning("Sure?")
                c1, c2 = cols[1].columns(2)
                if c1.button("✅", key=f"yes_cat_{i}"):
                    updated = st.session_state.cat_df.drop(i).reset_index(drop=True)
                    save_categories(updated)
                    st.session_state[confirm_key] = False
                    st.rerun()
                if c2.button("❌", key=f"no_cat_{i}"):
                    st.session_state[confirm_key] = False
                    st.rerun()

# --- 7. GLOBAL FLOATING QUICK LOG ---
@st.dialog("Quick Log")
def log_modal():
    if "form_id" not in st.session_state:
        st.session_state.form_id = 0

    if "last_log" in st.session_state:
        st.success(f"✅ Logged: ₹{st.session_state.last_log['amt']} for {st.session_state.last_log['cat']}")

    amt = st.number_input("Amount", min_value=0.0, value=None,
                          placeholder="₹ Enter Amount",
                          key=f"amt_{st.session_state.form_id}")

    # FIX: Yesterday shortcut + date picker together
    today     = now.date()
    yesterday = today - timedelta(days=1)
    date_shortcut = st.radio("Quick date", ["Today", "Yesterday", "Pick a date"],
                             horizontal=True, key=f"ds_{st.session_state.form_id}")
    if date_shortcut == "Today":
        log_date = today
    elif date_shortcut == "Yesterday":
        log_date = yesterday
    else:
        log_date = st.date_input("Transaction Date", value=today,
                                 key=f"date_{st.session_state.form_id}")

    cat  = st.selectbox("Category", categories, key=f"cat_{st.session_state.form_id}")
    mode = st.selectbox("Mode", payment_modes, key=f"mode_{st.session_state.form_id}")
    note = st.text_input("Note", value="", placeholder="Optional note (merchant, tag, etc.)",
                         key=f"note_{st.session_state.form_id}")

    col1, col2 = st.columns(2)

    if col1.button("Save & Add More", type="primary", use_container_width=True):
        if amt:
            now_time = datetime.now(tz).strftime("%H:%M:%S")
            final_dt = f"{log_date.strftime('%Y-%m-%d')} {now_time}"
            save_expense({"Date": final_dt, "Amount": amt, "Category": cat, "Mode": mode, "Note": note.strip()})
            st.session_state.last_log = {"amt": amt, "cat": cat}
            st.session_state.form_id += 1
            st.rerun()
        else:
            st.warning("Please enter an amount.")

    if col2.button("Finish", use_container_width=True):
        st.session_state.show_modal = False
        if "last_log" in st.session_state:
            del st.session_state.last_log
        st.rerun()

# --- 8. TRIGGER LOGIC ---
# FIX: Pre-initialise show_modal so FAB never needs two clicks
if "show_modal" not in st.session_state:
    st.session_state.show_modal = False

if st.session_state.show_modal:
    log_modal()

with stylable_container(key="fab", css_styles="button { position: fixed; bottom: 35px; right: 25px; width: 65px; height: 65px; border-radius: 50%; background-color: #2563eb; color: white; font-size: 38px; z-index: 1000; border: none; box-shadow: 0 4px 15px rgba(37,99,235,0.4); }"):
    if st.button("+", key="main_plus_btn"):
        st.session_state.show_modal = True
        st.rerun()

import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

# --- 1. SETTINGS & CUSTOM CSS ---
st.set_page_config(page_title="FinTrack India Pro", page_icon="₹", layout="centered")

st.markdown("""
    <style>
    /* Global Dark Theme Overrides */
    .stApp { background-color: #000000; color: #ffffff; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    
    /* Massive Amount Input Look */
    .amount-display {
        font-size: 72px;
        font-weight: 900;
        text-align: center;
        color: white;
        margin-bottom: 20px;
        font-family: 'Inter', sans-serif;
    }
    
    /* Custom Card Style */
    .status-card {
        background: #0a0a0a;
        border: 1px solid #1a1a1a;
        padding: 20px;
        border-radius: 24px;
        text-align: center;
        margin-bottom: 20px;
    }
    
    /* Category Button Styling */
    div.stButton > button {
        background-color: #111111;
        border: 1px solid #222222;
        border-radius: 16px;
        min-height: 80px;
        color: #9ca3af;
        transition: all 0.2s;
    }
    
    /* Highlight Selected Category (Primary Button) */
    div.stButton > button[kind="primary"] {
        background-color: #1d4ed822 !important;
        border: 2px solid #3b82f6 !important;
        color: white !important;
    }

    div.stButton > button:hover {
        border-color: #3b82f6;
        color: white;
    }
    
    /* Primary Log Button Override */
    .log-btn button {
        background-color: #2563eb !important;
        color: white !important;
        font-weight: bold !important;
        font-size: 20px !important;
        border-radius: 24px !important;
        padding: 15px !important;
        border: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA INITIALIZATION ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    try:
        e = conn.read(worksheet="Expenses", ttl=0)
        c = conn.read(worksheet="Categories", ttl=0)
        return e, c
    except:
        return pd.DataFrame(columns=["Date", "Amount", "Category", "Note"]), pd.DataFrame(columns=["Category"])

df, cat_df = load_data()
categories = cat_df["Category"].dropna().tolist() if not cat_df.empty else ["Kirana", "Milk/Veg", "Fuel", "Dining", "Staff", "Bills", "Medical", "Shopping"]

# --- 3. NAVIGATION ---
tab_log, tab_stats, tab_data = st.tabs(["💸 LOG", "📊 STATS", "💾 DATA"])

# --- 4. LOG PAGE ---
with tab_log:
    # Today's Total Header
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        
        today = datetime.now(pytz.timezone('Asia/Kolkata')).date()
        today_total = df[df['Date'].dt.date == today]['Amount'].sum()
    else:
        today_total = 0
        
    st.markdown(f"""
        <div class="status-card">
            <p style="color: #6b7280; font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 2px;">Spent Today</p>
            <h2 style="font-size: 32px; margin: 0; color: white;">₹{today_total:,.0f}</h2>
        </div>
    """, unsafe_allow_html=True)

    # Blank Amount Box
    amount = st.number_input(
        "Amount", 
        min_value=0, 
        step=1, 
        value=None, 
        label_visibility="collapsed", 
        placeholder="0"
    )

    display_amount = amount if amount is not None else 0
    st.markdown(f'<p class="amount-display"><span style="color: #4b5563;">₹</span>{display_amount}</p>', unsafe_allow_html=True)

    # --- CATEGORY GRID (FIXED HIGHLIGHT) ---
    st.write("### Select Category")
    if 'selected_cat' not in st.session_state:
        st.session_state.selected_cat = categories[0]

    cols = st.columns(3)
    for i, cat in enumerate(categories):
        with cols[i % 3]:
            # Highlight logic
            is_selected = st.session_state.selected_cat == cat
            if st.button(cat, 
                         use_container_width=True, 
                         type="primary" if is_selected else "secondary", 
                         key=f"btn_{cat}"):
                st.session_state.selected_cat = cat
                st.rerun()

    note = st.text_input("Note (Optional)", placeholder="What was this for?")

    # Log Button
    st.markdown('<div class="log-btn">', unsafe_allow_html=True)
    if st.button("Log Expense", use_container_width=True):
        if amount is not None and amount > 0:
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{"Date": now, "Amount": amount, "Category": st.session_state.selected_cat, "Note": note}])
            conn.update(worksheet="Expenses", data=pd.concat([df, new_row], ignore_index=True))
            st.success("Transaction Saved!")
            st.balloons()
            st.rerun()
        else:
            st.warning("Please enter an amount.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. STATS PAGE ---
with tab_stats:
    st.subheader("Monthly Breakdown")
    if not df.empty:
        chart_data = df.groupby("Category")["Amount"].sum().reset_index()
        st.bar_chart(chart_data, x="Category", y="Amount", color="Category")
        
        total_all = df['Amount'].sum()
        progress = min(total_all/100000, 1.0)
        st.markdown(f"""
            <div class="status-card">
                <p style="font-size: 14px;">HDFC ₹1L Milestone</p>
                <h3 style="color: #3b82f6;">{progress*100:.1f}%</h3>
            </div>
        """, unsafe_allow_html=True)
        st.progress(progress)
    else:
        st.info("No data available yet.")

# --- 6. DATA PAGE ---
with tab_data:
    st.subheader("Manage Categories")
    new_cat = st.text_input("New Category Name")
    if st.button("Add Category"):
        if new_cat:
            new_cat_row = pd.DataFrame([{"Category": new_cat}])
            conn.update(worksheet="Categories", data=pd.concat([cat_df, new_cat_row], ignore_index=True))
            st.cache_data.clear()
            st.rerun()

    st.divider()
    st.subheader("Raw History")
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)

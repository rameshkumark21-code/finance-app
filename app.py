import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from ui_components import inject_custom_css, render_nav_menu
from utils import load_all_data

# --- 1. CONFIG & SCOPE CONSTANTS ---
st.set_page_config(page_title="FinTrack Pro", page_icon="₹", layout="centered")
TZ = pytz.timezone('Asia/Kolkata')
HDFC_MILESTONE_AMT = 100_000

# Ensure the app doesn't crash if utils is missing constants
if 'MAX_PIN_ATTEMPTS' not in globals():
    MAX_PIN_ATTEMPTS = 5

# --- 2. INJECT CSS & DATA ---
inject_custom_css()

# Load real data, but use fallbacks for the preview
try:
    df, cat_df, settings_df, modes_df = load_all_data()
except:
    df = pd.DataFrame(columns=["Date", "Amount", "Category", "Mode", "Note"])
    cat_df = pd.DataFrame({"Category": ["Food", "Rent", "Travel", "Shopping"]})

# --- 3. SESSION STATE MANAGEMENT ---
if "current_page" not in st.session_state:
    st.session_state.current_page = 0
if "pin_unlocked" not in st.session_state:
    st.session_state.pin_unlocked = False

# --- 4. GLOBAL HEADER ---
st.markdown('<div class="g-title">FinTrack <span>Pro</span></div>', unsafe_allow_html=True)
render_nav_menu()

page = st.session_state.current_page

# --- 5. PAGE ROUTING & UI SECTIONS ---

# PAGE 0: DASHBOARD
if page == 0:
    st.markdown("### 🏠 Dashboard")
    
    # Hero Cards Section
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Monthly Spend", f"₹{df['Amount'].sum() if not df.empty else '0.00'}", "+5% vs last month")
    with col2:
        st.metric("Today's Spend", "₹1,240", "Flat")

    # HDFC Milestone Tracker
    st.write("---")
    st.markdown("**🎯 HDFC Millennia Milestone (₹1L)**")
    hdfc_spend = df[df['Mode'] == 'HDFC Credit Card']['Amount'].sum() if not df.empty else 0
    progress = min(hdfc_spend / HDFC_MILESTONE_AMT, 1.0)
    st.progress(progress)
    st.caption(f"₹{hdfc_spend:,.0f} spent of ₹1,00,000 target.")

    # Recent Transactions Section
    st.markdown("#### 🕒 Recent Transactions")
    if not df.empty:
        st.table(df.tail(7)[["Date", "Category", "Amount"]])
    else:
        st.info("No transactions logged yet.")

# PAGE 1: ANALYTICS
elif page == 1:
    st.markdown("### 📈 Analytics")
    st.info("Visualizing your 52-week heatmap and spending trends...")
    # Placeholder for GitHub-style heatmap
    st.image("https://via.placeholder.com/700x200.png?text=Spending+Heatmap+Grid+(52+Weeks)", use_container_width=True)
    
    col_a, col_b = st.columns(2)
    col_a.bar_chart({"Mon": 400, "Tue": 600, "Wed": 300, "Thu": 1200, "Fri": 1500})
    col_b.write("**Merchant Rankings**")
    col_b.caption("1. Amazon - ₹12,400")
    col_b.caption("2. Swiggy - ₹4,200")

# PAGE 2: LOG EXPENSE
elif page == 2:
    st.markdown("### ➕ Log Expense")
    with st.container():
        amt = st.number_input("Amount (₹)", min_value=0, step=10, key="log_amt")
        
        # Suggested Category Chips (Scope detail)
        st.markdown("<small>Suggestions: Food, Rent, Fuel, Shopping</small>", unsafe_allow_html=True)
        
        cat = st.selectbox("Category", cat_df["Category"] if not cat_df.empty else ["General"])
        mode = st.selectbox("Payment Mode", ["UPI", "Cash", "HDFC Millennia", "SBI Signature"])
        note = st.text_input("Notes (e.g. Dinner at Rameshwaram)")
        
        if st.button("Save Transaction", use_container_width=True):
            st.success("Transaction Logged Successfully!")

# PAGE 3: BUDGETS & GOALS
elif page == 3:
    st.markdown("### 🎯 Budgets & Recurring")
    st.write("**Category Budgets**")
    st.markdown("Food: ₹4,500 / ₹6,000")
    st.progress(0.75)
    st.markdown("Rent: ₹25,000 / ₹25,000")
    st.progress(1.0)
    
    st.write("---")
    st.write("**Recurring Subscriptions**")
    st.checkbox("Netflix (₹199) - Paid", value=True, disabled=True)
    st.checkbox("Gym - Clout Fit (₹2000) - Due in 3 days", value=False)

# PAGE 4: SETTINGS
elif page == 4:
    st.markdown("### ⚙️ Settings")
    st.number_input("Monthly Income Goal", value=80000)
    st.toggle("Budget Alerts (at 80%)", value=True)
    st.toggle("Weekly Pulse Report", value=True)
    if st.button("Manage Categories"):
        st.write("Redirecting to Category Editor...")

# PAGE 5: SECURITY
elif page == 5:
    st.markdown("### 🔒 Security")
    pin = st.text_input("Enter 4-Digit PIN", type="password")
    if st.button("Unlock App"):
        if pin == "1234": # Placeholder logic
            st.session_state.pin_unlocked = True
            st.success("App Unlocked")
        else:
            st.error("Incorrect PIN")

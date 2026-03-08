import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

st.set_page_config(page_title="FinTrack Pro", page_icon="₹")
st.title("₹ FinTrack Pro")

# Using the connection without the hardcoded URL in the code (it's in Secrets now)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 1. SYNC CATEGORIES ---
try:
    cat_df = conn.read(worksheet="Categories", ttl=0)
    categories = cat_df["Category"].dropna().unique().tolist()
except Exception:
    categories = ["Food", "Groceries", "Vegetables", "Rent", "Fuel", "Bike", "EB", "Home", "Clothing"]
    st.sidebar.warning("Note: Using local category list.")

# --- 2. CARD REWARDS LOGIC ---
def get_card_advice(cat):
    # SBI Signature 5X (Dining/Grocery)
    sbi_5x = ["Food", "Groceries", "Vegetables", "Dining"]
    # HDFC Millennia 5% (Amazon/Swiggy/Zomato/Uber/Clout Fit)
    hdfc_5pct = ["Amazon", "Swiggy", "Zomate", "Uber", "Clout Fit", "Flipkart"]
    
    if cat in sbi_5x:
        return "SBI Signature", "5X Reward Points"
    elif cat in hdfc_5pct:
        return "HDFC Millennia", "5% Cashback"
    elif cat in ["Fuel", "Rent", "Insurance"]:
        return "Any Card", "⚠️ Zero Rewards Category"
    else:
        return "HDFC Millennia", "1% Cashback"

# --- 3. INPUT FORM ---
with st.form("entry_form", clear_on_submit=True):
    st.subheader("Log New Expense")
    amount = st.number_input("Amount (₹)", min_value=0, step=1)
    category = st.selectbox("Category", categories)
    note = st.text_input("Note (Optional)")
    
    rec_card, benefit = get_card_advice(category)
    st.info(f"💡 Recommended: **{rec_card}** ({benefit})")
    
    if st.form_submit_button("Log Expense"):
        if amount > 0:
            try:
                tz = pytz.timezone('Asia/Kolkata')
                now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                new_row = pd.DataFrame([{"Date": now, "Amount": amount, "Category": category, "Note": note}])
                
                # Fetch and Update
                existing = conn.read(worksheet="Expenses", ttl=0)
                updated_df = pd.concat([existing, new_row], ignore_index=True) if not existing.empty else new_row
                
                conn.update(worksheet="Expenses", data=updated_df)
                st.success(f"Successfully logged ₹{amount}!")
                
                # Milestone Reminder
                if rec_card == "HDFC Millennia":
                    st.caption("This helps towards your ₹1L quarterly milestone! 🎯")
                st.balloons()
            except Exception as e:
                st.error(f"Sync Error: {e}")

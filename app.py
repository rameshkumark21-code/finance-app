import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

# Page Config
st.set_page_config(page_title="FinTrack India", page_icon="₹", layout="centered")
st.title("₹ FinTrack Pro")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1g_tT_yuO_-kN-e-3bufhZI3q0WEOVvWYerUV4bwMQQc/edit"

# --- SYNC CATEGORIES ---
try:
    # Being explicit with the URL helps avoid the 400 error
    categories_df = conn.read(spreadsheet=SHEET_URL, worksheet="Categories", ttl=0)
    categories = categories_df["Category"].dropna().unique().tolist()
except Exception as e:
    st.error(f"Sync Error: {e}")
    categories = ["Food", "Groceries", "Fuel", "Rent", "Bike", "EB", "Home", "Clothing"]

# --- CARD LOGIC HELPER ---
def get_card_advice(cat):
    # HDFC Millennia 5% partners
    millennia_5pct = ["Zomato", "Swiggy", "Uber", "Amazon", "Flipkart", "Clout Fit"]
    # SBI Signature 5X partners
    sbi_5x = ["Dining", "Food", "Groceries", "Vegetables", "Departmental"]
    # Zero reward categories
    zero_reward = ["Rent", "Fuel", "Insurance"]

    if cat in sbi_5x:
        return "SBI Signature", "5X Reward Points"
    elif cat in millennia_5pct:
        return "HDFC Millennia", "5% Cashback"
    elif cat in zero_reward:
        return "⚠️ ANY", "Zero Rewards Category"
    else:
        return "HDFC Millennia", "1% Cashback"

# --- EXPENSE FORM ---
with st.form("entry_form", clear_on_submit=True):
    st.subheader("Log New Expense")
    amount = st.number_input("Amount (₹)", min_value=0, step=1)
    category = st.selectbox("Category", categories)
    note = st.text_input("Note (Optional)")
    
    # Live Card Suggestion
    rec_card, benefit = get_card_advice(category)
    st.info(f"💡 Recommended: **{rec_card}** ({benefit})")
    
    submit = st.form_submit_button("Log Expense")

    if submit and amount > 0:
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        
        new_row = pd.DataFrame([{"Date": now, "Amount": amount, "Category": category, "Note": note}])
        
        # Save to sheet
        existing_data = conn.read(spreadsheet=SHEET_URL, worksheet="Expenses", ttl=0)
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, worksheet="Expenses", data=updated_df)
        
        st.success(f"Logged ₹{amount} for {category}!")
        if rec_card == "HDFC Millennia":
            st.write("Progressing towards your ₹1L quarterly milestone!")

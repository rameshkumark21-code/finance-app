import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

st.set_page_config(page_title="FinTrack Pro", page_icon="₹")
st.title("₹ FinTrack Pro")

# Direct Link to your sheet from image_72fc9c.png
SHEET_URL = "https://docs.google.com/spreadsheets/d/1g_tT_yuO_-kN-e-3bufhZI3q0WEOVvWYerUV4bwMQQc/edit"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 1. SYNC CATEGORIES ---
try:
    # Adding ttl=0 forces the app to ignore cached errors and fetch fresh data
    cat_df = conn.read(spreadsheet=SHEET_URL, worksheet="Categories", ttl=0)
    categories = cat_df["Category"].dropna().unique().tolist()
except Exception as e:
    # Fallback list if sync fails (includes your Vegetables and EB categories)
    categories = ["Food", "Groceries", "Vegetables", "Rent", "Fuel", "Bike", "EB", "Home", "Clothing"]
    st.sidebar.error(f"Syncing Error: {e}")

# --- 2. CARD RECOMMENDATION LOGIC ---
def suggest_card(cat):
    # SBI Signature 5X rewards logic
    sbi_5x = ["Food", "Groceries", "Vegetables", "Dining"]
    # HDFC Millennia 5% cashback logic
    hdfc_5pct = ["Amazon", "Swiggy", "Zomato", "Uber", "Clout Fit"]
    
    if cat in sbi_5x:
        return "SBI Signature", "5X Reward Points"
    elif cat in hdfc_5pct:
        return "HDFC Millennia", "5% Cashback"
    elif cat in ["Fuel", "Rent"]:
        return "Any Card", "Zero Rewards Category"
    else:
        return "HDFC Millennia", "1% Cashback"

# --- 3. INPUT FORM ---
with st.form("entry_form", clear_on_submit=True):
    st.subheader("Log New Expense")
    amount = st.number_input("Amount (₹)", min_value=0, step=1)
    category = st.selectbox("Category", categories)
    note = st.text_input("Note (Optional)")
    
    # Live advice based on selected category
    rec_card, benefit = suggest_card(category)
    st.info(f"💡 Recommended: **{rec_card}** ({benefit})")
    
    if st.form_submit_button("Log Expense"):
        if amount > 0:
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{"Date": now, "Amount": amount, "Category": category, "Note": note}])
            
            # Read and Update
            existing = conn.read(spreadsheet=SHEET_URL, worksheet="Expenses", ttl=0)
            updated = pd.concat([existing, new_row], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Expenses", data=updated)
            st.success(f"Logged ₹{amount} to {category}!")

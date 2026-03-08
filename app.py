import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

st.set_page_config(page_title="FinTrack Pro", page_icon="₹")
st.title("₹ FinTrack Pro")

# Direct Link to your sheet - using this directly often bypasses Secrets glitches
SHEET_URL = "https://docs.google.com/spreadsheets/d/1g_tT_yuO_-kN-e-3bufhZI3q0WEOVvWYerUV4bwMQQc/edit"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 1. SYNC CATEGORIES ---
try:
    # Forces a fresh fetch to avoid cached 400 errors
    cat_df = conn.read(spreadsheet=SHEET_URL, worksheet="Categories", ttl=0)
    categories = cat_df["Category"].dropna().unique().tolist()
except Exception:
    # Reliable fallback with your specific local categories
    categories = ["Food", "Groceries", "Vegetables", "Rent", "Fuel", "Bike", "EB", "Clothing", "Home"]
    st.sidebar.warning("Note: Using local category list.")

# --- 2. CARD REWARDS LOGIC ---
def get_card_advice(cat):
    # SBI Signature 5X rewards
    sbi_5x = ["Food", "Groceries", "Vegetables", "Dining"]
    # HDFC Millennia 5% cashback (Includes Clout Fit for gym)
    hdfc_5pct = ["Amazon", "Swiggy", "Zomato", "Uber", "Clout Fit", "Flipkart"]
    
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
    
    # Live advice based on selected category
    rec_card, benefit = get_card_advice(category)
    st.info(f"💡 Recommended: **{rec_card}** ({benefit})")
    
    if st.form_submit_button("Log Expense"):
        if amount > 0:
            try:
                tz = pytz.timezone('Asia/Kolkata')
                now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                new_row = pd.DataFrame([{"Date": now, "Amount": amount, "Category": category, "Note": note}])
                
                # Fetch existing to append
                existing = conn.read(spreadsheet=SHEET_URL, worksheet="Expenses", ttl=0)
                
                if existing is not None and not existing.empty:
                    updated_df = pd.concat([existing, new_row], ignore_index=True)
                else:
                    updated_df = new_row
                
                # Push back to Google Sheets
                conn.update(spreadsheet=SHEET_URL, worksheet="Expenses", data=updated_df)
                st.success(f"Successfully logged ₹{amount}!")
                st.balloons()
            except Exception as e:
                st.error(f"Error updating sheet: {e}")

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

# --- CATEGORY SYNC LOGIC ---
try:
    # Use ttl=0 to ensure it doesn't use old, broken cached data
    categories_df = conn.read(worksheet="Categories", ttl=0)
    # This grabs everything under the "Category" column in your sheet
    categories = categories_df["Category"].dropna().unique().tolist()
    
    if not categories:
        raise ValueError("Sheet is empty")
except Exception as e:
    # If it fails, we show this fallback so the app doesn't crash
    st.sidebar.warning(f"Note: Using offline categories. (Error: {str(e)})")
    categories = ["Food", "Groceries", "Fuel", "Rent", "Other"]

# Expense Input Form
with st.form("entry_form", clear_on_submit=True):
    st.subheader("Log New Expense")
    amount = st.number_input("Amount (₹)", min_value=0, step=1)
    category = st.selectbox("Category", categories)
    note = st.text_input("Note (Optional)")
    
    submit = st.form_submit_button("Log Expense")

    if submit:
        if amount > 0:
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            
            new_row = pd.DataFrame([{"Date": now, "Amount": amount, "Category": category, "Note": note}])
            
            # Read and Append (ttl=0 is key here too)
            existing_data = conn.read(worksheet="Expenses", ttl=0)
            updated_df = pd.concat([existing_data, new_row], ignore_index=True)
            
            conn.update(worksheet="Expenses", data=updated_df)
            st.success(f"Successfully logged ₹{amount} to your Google Sheet!")
            st.balloons()

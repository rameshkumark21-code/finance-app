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

# Fetch Categories from your "Categories" Tab
try:
    categories_df = conn.read(worksheet="Categories")
    categories = categories_df["Category"].dropna().tolist()
except Exception:
    # Fallback if the Categories tab isn't ready yet
    categories = ["Kirana", "Fuel", "Dining", "Bills", "Medical", "Shopping", "Other"]

# Expense Input Form
with st.form("entry_form", clear_on_submit=True):
    st.subheader("Log New Expense")
    amount = st.number_input("Amount (₹)", min_value=0, step=1)
    category = st.selectbox("Category", categories)
    note = st.text_input("Note (Optional)")
    
    submit = st.form_submit_button("Log Expense")

    if submit:
        if amount > 0:
            # Prepare the new row
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            
            new_data = pd.DataFrame([{"Date": now, "Amount": amount, "Category": category, "Note": note}])
            
            # Read existing data and append
            existing_data = conn.read(worksheet="Expenses")
            updated_df = pd.concat([existing_data, new_data], ignore_index=True)
            
            # Update the Sheet
            conn.update(worksheet="Expenses", data=updated_df)
            st.success(f"Logged ₹{amount} for {category}!")
        else:
            st.error("Please enter an amount greater than 0.")

# Dashboard Summary
st.divider()
st.subheader("Spend Analysis")
try:
    df = conn.read(worksheet="Expenses")
    if not df.empty:
        # Simple Bar Chart
        chart_data = df.groupby("Category")["Amount"].sum()
        st.bar_chart(chart_data)
        
        # Recent Transactions Table
        st.write("Recent Entries")
        st.dataframe(df.tail(5), use_container_width=True)
except:
    st.info("Log your first expense to see the chart!")

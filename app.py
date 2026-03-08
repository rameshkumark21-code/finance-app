import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

st.set_page_config(page_title="FinTrack India", page_icon="₹")
st.title("₹ FinTrack Pro")

# Connect to Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

# Fetch Categories
try:
    categories = conn.read(worksheet="Categories")["Category"].tolist()
except:
    categories = ["Food", "Transport", "Bills"]

# Input Form
with st.form("entry_form"):
    amount = st.number_input("Amount (₹)", min_value=0)
    category = st.selectbox("Category", categories)
    note = st.text_input("Note")
    if st.form_submit_button("Log Expense"):
        new_data = pd.DataFrame([{"Date": datetime.now(pytz.timezone('Asia/Kolkata')), 
                                  "Amount": amount, "Category": category, "Note": note}])
        conn.update(worksheet="Expenses", data=pd.concat([conn.read(worksheet="Expenses"), new_data]))
        st.success("Logged!")

st.bar_chart(conn.read(worksheet="Expenses").groupby('Category')['Amount'].sum())

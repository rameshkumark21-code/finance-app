import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

TZ = pytz.timezone('Asia/Kolkata')
DEFAULT_MODES = ["UPI", "Cash", "HDFC Credit Card", "SBI Credit Card"]

def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=30)
def load_all_data():
    conn = get_connection()
    try:
        e = conn.read(worksheet="Expenses")
        c = conn.read(worksheet="Categories")
        s = conn.read(worksheet="Settings")
        m = conn.read(worksheet="Modes")
        return e, c, s, m
    except Exception:
        # Return empty structures if sheet read fails
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame({"Mode": DEFAULT_MODES})

def save_expense(row_dict):
    conn = get_connection()
    new_row = pd.DataFrame([row_dict])
    # Logic to append and update GSheets
    st.cache_data.clear()

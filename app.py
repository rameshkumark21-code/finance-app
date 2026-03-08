import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

st.set_page_config(page_title="FinTrack Pro", page_icon="₹", layout="wide")

# --- 1. VIEW TOGGLE ---
view_mode = st.sidebar.radio("View Mode", ["Mobile", "Laptop"], index=0)
st.title("₹ FinTrack Pro")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. DATA SYNC ---
@st.cache_data(ttl=60)
def get_data():
    try:
        return conn.read(worksheet="Expenses", ttl=0)
    except:
        return pd.DataFrame(columns=["Date", "Amount", "Category", "Note"])

df = get_data()

# --- 3. SESSION STATE FOR BUTTON SELECTION ---
if 'selected_cat' not in st.session_state:
    st.session_state.selected_cat = "Food" # Default

# --- 4. CATEGORY BUTTON GRID ---
st.subheader("1. Select Category")
categories = ["Food", "Groceries", "Veg", "Rent", "Fuel", "Bike", "EB", "Home", "Clothes", "Clout Fit"]

# Display buttons in a grid (3 columns for Mobile, 5 for Laptop)
cols_count = 3 if view_mode == "Mobile" else 5
cat_cols = st.columns(cols_count)

for i, cat in enumerate(categories):
    with cat_cols[i % cols_count]:
        if st.button(cat, use_container_width=True, 
                     type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat = cat

# --- 5. LOGGING AREA ---
st.markdown(f"Selected: **{st.session_state.selected_cat}**")

with st.container(border=True):
    amount = st.number_input("2. Enter Amount (₹)", min_value=0, step=1, value=0)
    note = st.text_input("3. Note (Optional)")
    
    # Card Logic based on selected category
    sbi_5x = ["Food", "Groceries", "Veg", "Dining"]
    hdfc_5pct = ["Amazon", "Swiggy", "Zomato", "Uber", "Clout Fit", "Flipkart"]
    
    rec = "SBI Signature" if st.session_state.selected_cat in sbi_5x else "HDFC Millennia"
    ben = "5X Points" if st.session_state.selected_cat in sbi_5x else ("5% Cashback" if st.session_state.selected_cat in hdfc_5pct else "1% Cashback")
    
    st.info(f"💡 Use: **{rec}** ({ben})")

    if st.button("🚀 Log Expense", use_container_width=True, type="primary"):
        if amount > 0:
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{"Date": now, "Amount": amount, "Category": st.session_state.selected_cat, "Note": note}])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="Expenses", data=updated_df)
            st.success(f"Logged ₹{amount} to {st.session_state.selected_cat}!")
            st.balloons()
            st.rerun()

# --- 6. HISTORY ---
st.divider()
st.subheader("Recent Spends")
st.dataframe(df.tail(3 if view_mode == "Mobile" else 10), use_container_width=True)

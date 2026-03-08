import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

st.set_page_config(page_title="FinTrack Pro", page_icon="₹", layout="wide")

# --- 1. VIEW TOGGLE (Mobile Default) ---
view_mode = st.sidebar.radio("View Mode", ["Mobile", "Laptop"], index=0)

st.title("₹ FinTrack Pro")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. DATA SYNC ---
@st.cache_data(ttl=60)
def get_data():
    try:
        df = conn.read(worksheet="Expenses", ttl=0)
        return df
    except Exception:
        return pd.DataFrame(columns=["Date", "Amount", "Category", "Note"])

df = get_data()

# --- 3. DYNAMIC LAYOUT BASED ON TOGGLE ---
if view_mode == "Mobile":
    # Stacked View: Metrics -> Form -> Minimal History
    if not df.empty:
        df['Amount'] = pd.to_numeric(df['Amount'])
        total = df['Amount'].sum()
        st.metric("Total (Monthly)", f"₹{total:,.0f}")
        st.progress(min(total/100000, 1.0))
        st.caption("HDFC ₹1L Milestone Progress")

    st.subheader("Quick Log")
else:
    # Wide View: Metrics and Charts at the top
    col1, col2 = st.columns(2)
    if not df.empty:
        df['Amount'] = pd.to_numeric(df['Amount'])
        total = df['Amount'].sum()
        with col1:
            st.metric("Total Spend", f"₹{total:,.0f}")
        with col2:
            st.subheader("Category Breakdown")
            st.bar_chart(df.groupby("Category")["Amount"].sum())
    st.divider()

# --- 4. THE LOGGING FORM (Always visible) ---
# Using columns for the form to keep it tidy on Laptop
form_col = st.columns([1, 1, 1])[0] if view_mode == "Laptop" else st.container()

with form_col:
    with st.form("entry_form", clear_on_submit=True):
        amount = st.number_input("Amount (₹)", min_value=0, step=1)
        # Using your local fallback categories if sheet sync fails
        categories = ["Food", "Groceries", "Vegetables", "Rent", "Fuel", "Bike", "EB", "Home", "Clothing", "Clout Fit"]
        category = st.selectbox("Category", categories)
        note = st.text_input("Note")
        
        # Card Logic
        sbi_5x = ["Food", "Groceries", "Vegetables", "Dining"]
        hdfc_5pct = ["Amazon", "Swiggy", "Zomato", "Uber", "Clout Fit", "Flipkart"]
        
        rec = "SBI Signature" if category in sbi_5x else "HDFC Millennia"
        ben = "5X Points" if category in sbi_5x else ("5% Cashback" if category in hdfc_5pct else "1% Cashback")
        
        st.info(f"💡 Use: **{rec}** ({ben})")

        if st.form_submit_button("Submit"):
            if amount > 0:
                tz = pytz.timezone('Asia/Kolkata')
                now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                new_row = pd.DataFrame([{"Date": now, "Amount": amount, "Category": category, "Note": note}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Expenses", data=updated_df)
                st.success("Success!")
                st.rerun()

# --- 5. HISTORY ---
st.subheader("Recent Spends")
st.dataframe(df.tail(3 if view_mode == "Mobile" else 10), use_container_width=True)

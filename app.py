import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

st.set_page_config(page_title="FinTrack Pro", page_icon="₹", layout="wide")
st.title("₹ FinTrack Pro")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 1. DATA SYNC ---
@st.cache_data(ttl=60) # Cache for 1 min to stay fast
def get_data():
    df = conn.read(worksheet="Expenses", ttl=0)
    return df

try:
    df = get_data()
    cat_df = conn.read(worksheet="Categories", ttl=0)
    categories = cat_df["Category"].dropna().unique().tolist()
except Exception:
    df = pd.DataFrame(columns=["Date", "Amount", "Category", "Note"])
    categories = ["Food", "Groceries", "Vegetables", "Rent", "Fuel", "Bike", "EB", "Home", "Clothing"]

# --- 2. TOP METRICS DASHBOARD ---
if not df.empty:
    df['Amount'] = pd.to_numeric(df['Amount'])
    total_spend = df['Amount'].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Spend (Monthly)", f"₹{total_spend:,.0f}")
    
    # HDFC Milestone Logic (Quarterly)
    progress = (total_spend / 100000) * 100
    col2.metric("HDFC Milestone", f"{progress:.1f}%", help="Target: ₹1,00,000 for quarterly rewards")
    
    # Simple Progress Bar for the milestone
    st.progress(min(progress/100, 1.0))

st.divider()

# --- 3. INPUT & VISUALS SIDE-BY-SIDE ---
left_col, right_col = st.columns([1, 1.5])

with left_col:
    with st.form("entry_form", clear_on_submit=True):
        st.subheader("Log New Expense")
        amount = st.number_input("Amount (₹)", min_value=0, step=1)
        category = st.selectbox("Category", categories)
        note = st.text_input("Note (Optional)")
        
        # Card Advice
        sbi_5x = ["Food", "Groceries", "Vegetables", "Dining"]
        hdfc_5pct = ["Amazon", "Swiggy", "Zomato", "Uber", "Clout Fit", "Flipkart"]
        
        if category in sbi_5x:
            rec, ben = "SBI Signature", "5X Points"
        elif category in hdfc_5pct:
            rec, ben = "HDFC Millennia", "5% Cashback"
        else:
            rec, ben = "HDFC Millennia", "1% Cashback"
            
        st.info(f"💡 Use **{rec}** ({ben})")

        if st.form_submit_button("Submit"):
            if amount > 0:
                tz = pytz.timezone('Asia/Kolkata')
                now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                new_row = pd.DataFrame([{"Date": now, "Amount": amount, "Category": category, "Note": note}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Expenses", data=updated_df)
                st.success("Logged!")
                st.rerun()

with right_col:
    st.subheader("Spending by Category")
    if not df.empty:
        chart_data = df.groupby("Category")["Amount"].sum()
        st.bar_chart(chart_data)
    else:
        st.info("No data logged yet for this month.")

# --- 4. RECENT HISTORY ---
st.divider()
st.subheader("Recent Entries")
st.dataframe(df.tail(5).sort_index(ascending=False), use_container_width=True)

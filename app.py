import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

st.set_page_config(page_title="FinTrack Pro", page_icon="₹", layout="wide")

# --- 1. TOP ICON TOGGLE ---
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "Mobile"

# Create two small columns at the very top for icons
t1, t2, _ = st.columns([0.1, 0.1, 0.8])
with t1:
    if st.button("📱"):
        st.session_state.view_mode = "Mobile"
with t2:
    if st.button("💻"):
        st.session_state.view_mode = "Laptop"

st.caption(f"Current View: **{st.session_state.view_mode}**")
st.title("₹ FinTrack Pro")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. DATA SYNC ---
@st.cache_data(ttl=10)
def get_all_data():
    try:
        exp_df = conn.read(worksheet="Expenses", ttl=0)
        cat_df = conn.read(worksheet="Categories", ttl=0)
        return exp_df, cat_df
    except:
        return pd.DataFrame(columns=["Date", "Amount", "Category", "Note"]), pd.DataFrame(columns=["Category"])

df, cat_master = get_all_data()
categories = cat_master["Category"].dropna().tolist() if not cat_master.empty else ["Food", "Groceries", "Veg", "Rent", "Fuel", "Bike", "EB", "Home", "Clothes", "Clout Fit"]

# --- 3. MANAGE CATEGORIES ---
with st.expander("⚙️ Manage Categories"):
    c1, c2 = st.columns(2)
    with c1:
        new_cat = st.text_input("Add Category")
        if st.button("Add"):
            if new_cat and new_cat not in categories:
                new_row = pd.DataFrame([{"Category": new_cat}])
                conn.update(worksheet="Categories", data=pd.concat([cat_master, new_row], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
    with c2:
        del_cat = st.selectbox("Delete Category", categories)
        if st.button("Remove"):
            updated_cats = cat_master[cat_master["Category"] != del_cat]
            conn.update(worksheet="Categories", data=updated_cats)
            st.cache_data.clear()
            st.rerun()

# --- 4. BUTTON GRID ---
if 'selected_cat' not in st.session_state:
    st.session_state.selected_cat = categories[0]

st.subheader("1. Select Category")
cols_count = 3 if st.session_state.view_mode == "Mobile" else 6
cat_cols = st.columns(cols_count)

for i, cat in enumerate(categories):
    with cat_cols[i % cols_count]:
        if st.button(cat, use_container_width=True, 
                     type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat = cat

# --- 5. LOGGING AREA ---
with st.container(border=True):
    amount = st.number_input(f"Logging: {st.session_state.selected_cat} (₹)", min_value=0, step=1)
    note = st.text_input("Note (Optional)")
    
    # Reward Logic
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
            conn.update(worksheet="Expenses", data=pd.concat([df, new_row], ignore_index=True))
            st.success("Logged!")
            st.rerun()

# --- 6. HISTORY & MILESTONE ---
if not df.empty:
    total = pd.to_numeric(df['Amount']).sum()
    st.progress(min(total/100000, 1.0), text=f"Quarterly Milestone: ₹{total:,.0f} / ₹1L")

st.subheader("Recent Spends")
st.dataframe(df.tail(3 if st.session_state.view_mode == "Mobile" else 10), use_container_width=True)

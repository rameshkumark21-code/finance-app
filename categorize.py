import streamlit as st
import pandas as pd

def show_bulk_review(conn):
    st.header("🔍 Merchant Review Hub")
    
    # Fetch Pending Data
    df_pending = conn.read(worksheet="PendingReview", ttl=0)
    
    if df_pending.empty:
        st.success("🎉 All caught up! No merchants left to review.")
        return

    # Get unique list of merchants
    merchants = df_pending["Note"].unique()
    
    # Track which merchant we are on
    if 'm_idx' not in st.session_state:
        st.session_state.m_idx = 0

    # Safety check if list shrunk
    if st.session_state.m_idx >= len(merchants):
        st.session_state.m_idx = 0

    current_m = merchants[st.session_state.m_idx]
    m_data = df_pending[df_pending["Note"] == current_m]

    # --- THE MERCHANT CARD ---
    with st.container(border=True):
        st.subheader(f"📍 {current_m}")
        c1, c2 = st.columns(2)
        c1.metric("Total Spends", f"₹{m_data['Amount'].sum():,.2f}")
        c2.metric("Entries", len(m_data))

        st.dataframe(m_data[["Date", "Amount"]], hide_index=True, use_container_width=True)

        # CATEGORIZATION FORM
        cat_df = conn.read(worksheet="Categories")
        cats = cat_df["Category"].tolist()
        
        with st.form(key=f"form_{current_m}"):
            sel_cat = st.selectbox("Assign Category", options=["Select..."] + cats)
            note = st.text_input("Optional Bulk Note")
            
            if st.form_submit_button("Approve & Next ➡️", type="primary", use_container_width=True):
                if sel_cat == "Select...":
                    st.error("Pick a category!")
                else:
                    # 1. Update logic (Append to Expenses / ImportRules)
                    # 2. Delete current_m from PendingReview
                    
                    st.toast(f"Categorized {current_m} as {sel_cat}")
                    # Move to next
                    st.session_state.m_idx = (st.session_state.m_idx + 1) % len(merchants)
                    st.rerun()

    st.write(f"Merchant {st.session_state.m_idx + 1} of {len(merchants)}")

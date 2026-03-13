import streamlit as st
import pandas as pd

def show_bulk_review(conn):
    st.header("🔍 Focused Merchant Review")
    
    # 1. Fetch Fresh Data
    df_pending = conn.read(worksheet="PendingReview", ttl=0)
    if df_pending.empty:
        st.success("🎉 All caught up! No merchants left to review.")
        return

    # 2. Get Unique Merchants
    unique_merchants = df_pending["Note"].unique()
    total_merchants = len(unique_merchants)
    
    # Use session_state to track which merchant we are currently looking at
    if 'merchant_index' not in st.session_state:
        st.session_state.merchant_index = 0

    # Ensure index is within bounds (if data was deleted)
    if st.session_state.merchant_index >= total_merchants:
        st.session_state.merchant_index = 0

    current_merchant = unique_merchants[st.session_state.merchant_index]
    merchant_txns = df_pending[df_pending["Note"] == current_merchant]
    total_amt = merchant_txns["Amount"].sum()

    # --- THE MERCHANT BOX (UI) ---
    with st.container(border=True):
        st.subheader(f"Merchant: {current_merchant}")
        col1, col2 = st.columns(2)
        col1.metric("Total Spends", f"₹{total_amt:,.2f}")
        col2.metric("Total Entries", len(merchant_txns))

        # Show individual entries in a small table inside the box
        st.write("**Transactions:**")
        st.dataframe(merchant_txns[["Date", "Amount"]], hide_index=True, use_container_width=True)

        # --- CATEGORIZATION FORM ---
        cat_df = conn.read(worksheet="Categories")
        available_cats = cat_df["Category"].tolist()
        
        with st.form(key=f"form_{current_merchant}"):
            selected_cat = st.selectbox("Assign Category", options=["Select..."] + available_cats)
            bulk_note = st.text_input("Optional: Add note for these entries")
            
            submit = st.form_submit_button("Approve & Next ➡️", type="primary", use_container_width=True)

            if submit:
                if selected_cat == "Select...":
                    st.error("Please select a category first!")
                else:
                    # PROCESS DATA:
                    # 1. Prepare Rows for Expenses
                    matches = merchant_txns.copy()
                    matches["Category"] = selected_cat
                    if bulk_note:
                        matches["Note"] = matches["Note"] + f" ({bulk_note})"
                    matches["Status"] = "approved"

                    # 2. Add to Expenses & ImportRules
                    # (Append matches to Expenses sheet)
                    # (Append [Merchant, "Keyword", Category] to ImportRules)
                    
                    # 3. Remove from Pending and Refresh
                    st.toast(f"Saved {current_merchant} to {selected_cat}!")
                    
                    # Move to next or reset
                    if st.session_state.merchant_index < total_merchants - 1:
                        st.session_state.merchant_index += 1
                    else:
                        st.session_state.merchant_index = 0
                    
                    st.rerun()

    # Progress indicator
    st.write(f"Merchant {st.session_state.merchant_index + 1} of {total_merchants}")
    st.progress((st.session_state.merchant_index + 1) / total_merchants)
    
    if st.button("Skip for now ⏭️"):
        st.session_state.merchant_index = (st.session_state.merchant_index + 1) % total_merchants
        st.rerun()

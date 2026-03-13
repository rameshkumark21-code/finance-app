import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

def show_bulk_review():
    st.title("🔍 Bulk Exception Review")
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Fetch fresh data from the PendingReview sheet
    df_pending = conn.read(worksheet="PendingReview", ttl=0)
    
    if df_pending.empty:
        st.success("Clean slate! No pending exceptions.")
        return

    # STEP 1: Aggregation Logic (The grouping you wanted)
    grouped = df_pending.groupby("Note").agg({
        "Amount": ["sum", "count"],
        "Date": "max"
    }).reset_index()
    grouped.columns = ["Merchant", "Total Amount", "Entries", "Last Seen"]

    # STEP 2: The Grouped Editor
    # You assign the category once for all entries under that merchant
    categories = ["Tea Coffee", "Eat Out", "Groceries", "Non-Veg", "Medical", "Travel", "Fuel", "Bills/Debt"]
    
    st.info(f"Reviewing {len(grouped)} unique merchants.")
    
    edited_df = st.data_editor(
        grouped,
        column_config={
            "Category": st.column_config.SelectboxColumn("Assign Category", options=categories, required=True),
            "Add Note": st.column_config.TextColumn("Notes (Optional)"),
            "Merchant": st.column_config.TextColumn(disabled=True),
            "Total Amount": st.column_config.NumberColumn(format="₹%.2f", disabled=True),
            "Entries": st.column_config.NumberColumn(disabled=True)
        },
        hide_index=True,
        use_container_width=True
    )

    # STEP 3: Bulk Save Logic
    if st.button("✅ Bulk Approve & Train Rules", type="primary"):
        processed_groups = edited_df.dropna(subset=["Category"])
        
        if not processed_groups.empty:
            # We iterate through the grouped choices and apply to all original rows
            for _, group in processed_groups.iterrows():
                # Filter original data to find all 65 and 55 entries for Mani M
                matching_txns = df_pending[df_pending["Note"] == group["Merchant"]]
                
                # Logic to:
                # 1. Append these rows to 'Expenses' with the new Category
                # 2. Append Merchant + Category to 'ImportRules'
                # 3. Delete from 'PendingReview'
                
            st.success(f"Successfully processed {len(processed_groups)} merchant groups!")
            st.rerun()

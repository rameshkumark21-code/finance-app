# categorize.py
import streamlit as st
import pandas as pd

def show_bulk_review(conn):
    st.header("🔍 Grouped Exception Review")
    
    # 1. Fetch Fresh Data (ttl=0 to avoid cache issues)
    df_pending = conn.read(worksheet="PendingReview", ttl=0)
    df_expenses = conn.read(worksheet="Expenses", ttl=0)
    df_rules = conn.read(worksheet="ImportRules", ttl=0)
    
    if df_pending.empty:
        st.success("No pending transactions! Everything is categorized.")
        return

    # 2. Aggregation: The "Mani M" Grouping
    grouped = df_pending.groupby("Note").agg({
        "Amount": ["sum", "count"],
        "Date": "max"
    }).reset_index()
    grouped.columns = ["Merchant", "Total Amount", "Entries", "Latest Date"]

    # 3. Categorization Editor
    cat_df = conn.read(worksheet="Categories")
    available_cats = cat_df["Category"].tolist()

    st.write(f"Found {len(grouped)} unique merchants to review.")

    edited_df = st.data_editor(
        grouped,
        column_config={
            "Category": st.column_config.SelectboxColumn("Final Category", options=available_cats, required=True),
            "Add Note": st.column_config.TextColumn("Notes (Applies to all)"),
        },
        hide_index=True,
        use_container_width=True
    )

    # 4. Bulk Action Logic
    if st.button("🚀 Approve & Train AI", type="primary"):
        processed_groups = edited_df.dropna(subset=["Category"])
        
        if not processed_groups.empty:
            new_expenses = []
            new_rules = []
            processed_merchants = []

            for _, group in processed_groups.iterrows():
                # Get all sub-transactions for this merchant (e.g., the 65 and 55)
                matches = df_pending[df_pending["Note"] == group["Merchant"]].copy()
                
                # Update them with user choices
                matches["Category"] = group["Category"]
                if group["Add Note"]:
                    matches["Note"] = matches["Note"] + " (" + group["Add Note"] + ")"
                
                new_expenses.append(matches)
                
                # Create a new rule (Clean "Paid to " prefix)
                clean_name = group["Merchant"].replace("Paid to ", "").replace("Money sent to ", "").strip()
                new_rules.append({"Keyword": clean_name, "Type": "Keyword", "Category": group["Category"]})
                
                processed_merchants.append(group["Merchant"])

            # UPDATE GOOGLE SHEETS
            # A. Update Expenses
            updated_expenses = pd.concat([df_expenses] + new_expenses, ignore_index=True)
            conn.update(worksheet="Expenses", data=updated_expenses)

            # B. Update Rules
            updated_rules = pd.concat([df_rules, pd.DataFrame(new_rules)], ignore_index=True)
            conn.update(worksheet="ImportRules", data=updated_rules)

            # C. Clear Pending (Remove the merchants we just processed)
            remaining_pending = df_pending[~df_pending["Note"].isin(processed_merchants)]
            conn.update(worksheet="PendingReview", data=remaining_pending)

            st.balloons()
            st.success(f"Success! {len(processed_groups)} merchants moved to Expenses.")
            st.rerun()

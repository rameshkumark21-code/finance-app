import streamlit as st
from utils import load_all_data, TZ
from ui_components import inject_custom_css, render_nav_menu

# Initial Setup
st.set_page_config(page_title="FinTrack Pro", page_icon="₹", layout="centered")
inject_custom_css()

# Load Data
df, cat_df, settings_df, modes_df = load_all_data()

# Render Header & Navigation
st.markdown('<div class="g-title">FinTrack <span>Pro</span></div>', unsafe_allow_html=True)
render_nav_menu()

# Page Routing
if "current_page" not in st.session_state:
    st.session_state.current_page = 0

page = st.session_state.current_page

if page == 0:
    st.subheader("Dashboard")
    # Add your specific dashboard cards here
elif page == 1:
    st.subheader("Analytics")
    # Add your heatmap/graphs here

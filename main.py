import streamlit as st
from utils import load_all_data, TZ, MAX_PIN_ATTEMPTS
from ui_components import inject_custom_css, render_nav_menu, show_pin_gate

# 1. Page Configuration
st.set_page_config(page_title="FinTrack Pro", page_icon="₹", layout="centered")
inject_custom_css()

# 2. Session State Init
if "current_page" not in st.session_state: st.session_state.current_page = 0
if "pin_unlocked" not in st.session_state: st.session_state.pin_unlocked = False

# 3. Security (The Gate)
if not st.session_state.pin_unlocked:
    show_pin_gate(MAX_PIN_ATTEMPTS)
    st.stop()

# 4. App Content
st.title("FinTrack Pro")
render_nav_menu()

df, cat_df, settings_df, modes_df = load_all_data()
page = st.session_state.current_page

if page == 0:
    # Build your Home screen using functions from utils and ui_components
    st.subheader("Summary")

import streamlit as st
from streamlit_extras.stylable_container import stylable_container

def inject_custom_css():
    st.markdown("""
    <style>
        .stApp { max-width: 100vw; overflow-x: hidden; }
        /* Stacking fix for mobile */
        @media (max-width: 768px) {
            [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; }
        }
    </style>
    """, unsafe_allow_html=True)

def render_nav_menu():
    _PAGES = ["🏠", "📈", "📅", "💳", "🎯", "⚙️"]
    _LABELS = ["Home", "Analytics", "Logs", "Cards", "Goals", "Admin"]
    
    with stylable_container(
        key="nav_bar",
        css_styles="{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-start; }"
    ):
        for i, icon in enumerate(_PAGES):
            label = f"{icon} {_LABELS[i]}"
            is_active = st.session_state.get("current_page", 0) == i
            if st.button(label, key=f"nav_{i}", type="primary" if is_active else "secondary"):
                st.session_state.current_page = i
                st.rerun()

def show_pin_gate(max_attempts):
    # Move your PIN entry UI logic here
    pass

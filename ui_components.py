import streamlit as st
from streamlit_extras.stylable_container import stylable_container

def inject_custom_css():
    _CSS = """
    <style>
        /* Mobile-First layout fix */
        .stApp { max-width: 100vw; overflow-x: hidden; background: #080810; }
        
        /* Force columns to stack on mobile */
        @media (max-width: 768px) {
            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
            }
        }
        
        /* Custom card styling */
        .card {
            background: linear-gradient(145deg, #0f0f1a, #0c0c17);
            border: 1px solid #1e1e2e;
            border-radius: 16px;
            padding: 14px;
            margin-bottom: 8px;
        }
    </style>
    """
    st.markdown(_CSS, unsafe_allow_html=True)

def render_nav_menu():
    # Use a stylable container for a wrap-around horizontal menu
    with stylable_container(
        key="nav_container",
        css_styles="""
            { 
                display: flex; 
                flex-wrap: wrap; 
                gap: 5px; 
                justify-content: center; 
            }
        """
    ):
        cols = st.columns(6)
        icons = ["🏠", "📈", "📅", "💳", "🎯", "⚙️"]
        for i, icon in enumerate(icons):
            if cols[i].button(icon, key=f"btn_{i}", use_container_width=True):
                st.session_state.current_page = i
                st.rerun()

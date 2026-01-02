import streamlit as st
import textwrap

def section_header(title, icon=""):
    """Renders a standard section header (Native approach)."""
    # Using markdown for simple header with icon
    st.markdown(f"## {icon} {title}")
    st.divider()

def render_html(html_string):
    """
    Renders HTML correctly using st.html.
    Kept for legacy or specific minor HTML needs, but discouraged for main layout.
    """
    if html_string.startswith("\n"):
        html_string = html_string[1:]
    clean_html = textwrap.dedent(html_string)
    st.html(clean_html)

def load_css(file_path="style.css"):
    """Loads CSS from a file and injects it into the app."""
    # Removed load_tailwind() call
    try:
        with open(file_path, "r") as f:
            css = f.read()
            st.html(f"<style>{css}</style>")
    except FileNotFoundError:
        st.error(f"Error loading style: {file_path} not found.")

# The following functions (dashboard_kpis, modern_table_*, card_*) have been deprecated
# and replaced by native Streamlit implementations in views.py and project_manager.py.
# They are removed to prevent confusion.

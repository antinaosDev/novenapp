import bcrypt
import streamlit as st
import pandas as pd
import base64
import os
from modules import data

def hash_password(password):
    """Hashes a password for storage."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    """Checks a password against a hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_user(username, password, full_name, role, email=None):
    """Creates a new user in the database."""
    hashed = hash_password(password)
    # Using raw SQL via data module (we need to add this function to data.py actually, or use run_query)
    try:
        data.create_user_record(username, hashed, full_name, role, email)
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False

def login_user(username, password):
    """Verifies credentials and logs the user in."""
    users = data.get_user_by_username(username)
    if not users.empty:
        user_row = users.iloc[0]
        if check_password(password, user_row['password_hash']):
            st.session_state['authenticated'] = True
            st.session_state['user_role'] = user_row['role']
            st.session_state['real_role'] = user_row['role'] # Store original role for impersonation
            st.session_state['username'] = user_row['username']
            st.session_state['full_name'] = user_row['full_name']
            st.session_state['user_id'] = int(user_row['id']) # Ensure int for DB refs
            # Capture Email for Notifications
            st.session_state['email'] = user_row.get('email', '')
            return True
    return False

def logout_user():
    """Clears session state."""
    st.session_state['authenticated'] = False
    st.session_state['user_role'] = None
    st.session_state['username'] = None
    st.rerun()

def render_login():
    """Renders the Premium Login UI."""
    
    # 1. Base CSS - Reset and Fonts (Minimal invasion)


    # Load Logo
    logo_b64 = ""
    try:
        if os.path.exists("logo_nov.png"):
            with open("logo_nov.png", "rb") as f:
                logo_b64 = base64.b64encode(f.read()).decode()
    except Exception as e:
        print(f"Error loading logo: {e}")

    # 2. Main Layout - Two Columns
    # We use a standard st.columns but we'll try to put the hero in the left
    col1, col2 = st.columns([1, 1], gap="medium")

    with col1:
        # Left: Immersive Hero
        # We use a trick to escape the column padding: negative margins or pure HTML
        # For simplicity and robustness, we just render a nice block
        st.html(f"""
        <div style="
            background-color: #112117; 
            border-radius: 24px; 
            padding: 3rem; 
            height: 90vh; 
            display: flex; 
            flex-direction: column; 
            justify-content: space-between;
            position: relative;
            overflow: hidden;
            border: 1px solid #1f3b2a;
        ">
            <!-- BG Image Layer -->
            <div style="position: absolute; inset: 0; z-index: 0; opacity: 0.4; mix-blend-mode: overlay;">
                <img src="https://images.unsplash.com/photo-1541888946425-d81bb19240f5?q=80&w=2070&auto=format&fit=crop" 
                     style="width: 100%; height: 100%; object-fit: cover; filter: grayscale(50%);">
            </div>
            
            <!-- Content -->
            <div style="position: relative; z-index: 10;">
                <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 3rem;">
                    <img src="data:image/png;base64,{logo_b64}" style="height: 3rem; width: auto;" />
                    <span style="color: white; font-weight: 700; font-size: 1.5rem;">Novenapp</span>
                </div>
                
                <h1 style="color: white; font-size: 3.5rem; font-weight: 800; line-height: 1.1; margin-bottom: 1.5rem;">
                    Construyendo el <br>
                    <span style="color: var(--primary);">futuro, hoy.</span>
                </h1>
                <p style="color: #cbd5e1; font-size: 1.125rem; max-width: 400px;">
                    Plataforma integral para gestión de obras y control financiero.
                </p>
            </div>
            
            <!-- Footer Stats -->
             <div style="position: relative; z-index: 10; display: flex; gap: 2rem; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 2rem;">
                <div>
                     <div style="font-weight: 800; color: white; font-size: 1.5rem;">100%</div>
                     <div style="color: var(--primary); font-size: 0.875rem;">Control</div>
                </div>
                <div>
                     <div style="font-weight: 800; color: white; font-size: 1.5rem;">24/7</div>
                     <div style="color: var(--primary); font-size: 0.875rem;">Monitoreo</div>
                </div>
             </div>
        </div>
        """)

    with col2:
        # Right: Login Form
        # Spacer to push down
        st.html('<div style="height: 10vh;"></div>')
        
        with st.container():
            # Centered Card within Column
            st.html(f"""
            <div style="max-width: 400px; margin: 0 auto;">
                <div style="margin-bottom: 2rem;">
                    <span style="background: var(--primary-light); color: var(--primary-focus); padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; text-transform: uppercase;">
                        Portal Corporativo
                    </span>
                </div>
                <!-- Logo Mobile/Form -->
                <div style="margin-bottom: 2rem;">
                    <img src="data:image/png;base64,{logo_b64}" style="height: 3.5rem; width: auto; margin-bottom: 1.5rem; display: block;">
                    <h2 style="font-size: 2rem; font-weight: 700; color: #0f172a; margin-bottom: 0.5rem;">Bienvenido</h2>
                    <p style="color: #64748b;">Ingresa tus credenciales para continuar.</p>
                </div>
            </div>
            """)
            
            # CSS Hack to constrain form width
            st.html("""
            <style>
                div[data-testid="stForm"] {
                    max-width: 400px;
                    margin: 0 auto;
                }
            </style>
            """)

            with st.form("login_form", border=False):
                st.markdown("<strong>Usuario</strong>", unsafe_allow_html=True)
                username = st.text_input("Username", placeholder="usuario.1", label_visibility="collapsed")
                
                st.html('<div style="height:10px"></div>')
                
                st.markdown("<strong>Contraseña</strong>", unsafe_allow_html=True)
                password = st.text_input("Password", type="password", placeholder="••••••••", label_visibility="collapsed")
                
                st.html('<div style="height:20px"></div>')
                
                if st.form_submit_button("Iniciar Sesión"):
                    if login_user(username, password):
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Credenciales Incorrectas")
            


def init_admin_if_none():
    """Creates a default admin if no users exist."""
    users = data.get_all_users()
    if users.empty:
        create_user("admin", "admin123", "Administrador Principal", "Admin")

import streamlit as st
st.set_page_config(layout="wide", page_title="Gestión de Obras", page_icon="logo_nov.png", initial_sidebar_state="expanded")
IMG_LOGO_ALAIN = "logo_alain.png"
from modules import data, ui, views, auth, views_tenders, views_finance, views_lean, views_compliance, views_quality, project_manager as projects

# Initialize DB
data.init_db()
auth.init_admin_if_none()

# Load Styles
ui.load_css("style.css")

# --- Authentication Flow ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    auth.render_login()
else:
    # --- Trigger Daily Automation ---
    # Checks if alerts need to be sent today (run once per day globally)
    try:
        from modules import notifications
        notifications.run_daily_automation()
    except Exception as e:
        print(f"Auto-Notification Error: {e}")

    # --- Sidebar Navigation (Professional) ---
    with st.sidebar:
        # App Logo / Title
        # App Logo / Title
        try:
             st.image("logo_nov.png", width=180)
        except:
             st.title("🏗️ NovApp")
             
        st.markdown("**Sistema Integrado de Gestión**")
        st.divider()

        # Navigation
        # Base Options for Full Access Roles
        full_access_roles = ['Administrador', 'Programador', 'Residente de Obra']
        role = st.session_state.get('user_role', 'Invitado')
        
        options = {}
        
        if role in full_access_roles:
            # Standard Suite
            options = {
                "Dashboard": ":material/dashboard:", 
                "Proyectos": ":material/apartment:", 
                "Licitaciones": ":material/history_edu:", 
                "Finanzas": ":material/payments:", 
                "Lean Plan": ":material/view_kanban:", 
                "Subcontratos": ":material/engineering:", 
                "Calidad": ":material/checklist:",
                "Equipos": ":material/map:", 
            }
            
            # Extensions for Admin/Programmer/Resident (User Mgmt)
            if role in ['Programador', 'Administrador', 'Residente de Obra']:
                options["Usuarios"] = ":material/people:"
            
            # Extensions for Admin/Programmer (AI)
            if role in ['Programador', 'Administrador']:
                options["Analista IA"] = ":material/neurology:"
                
            # Extensions for Programmer
            if role == 'Programador':
                options["Administración"] = ":material/admin_panel_settings:"
                
        else:
            # Restricted Roles (Capataz, Bodeguero, etc.)
            # "Solo pestaña equipos y la pestaña principal mapa de proyectos y generar el reporte pdf"
            # Equipos view contains the Map and the Report Generator.
            options = {
                "Equipos": ":material/map:"
            }
        
        selection = st.radio(
            "Navegación", 
            options.keys(),
            format_func=lambda x: f"{options[x]}  {x}",
            label_visibility="collapsed"
        )

        st.divider()
        
         # User Profile (Native)
        with st.container(border=True):
             c_av, c_info = st.columns([1, 3])
             with c_av:
                 st.write("👤")
             with c_info:
                 st.caption(f"**{st.session_state.get('full_name', 'Usuario')}**")
                 st.caption(st.session_state.get('user_role', 'Rol'))
        
        # --- NotificationAPI Client Injection (Web Push) ---
        # This script initializes the frontend SDK to enable Push/In-App
        user_email = st.session_state.get('username') # Now this is mapped to email if we used email as username, but...
        # Wait, st.session_state['username'] is the LOGIN. We need the EMAIL. 
        # We didn't store email in session_state yet. We only verified it exists in DB.
        # We need to fetch email or assume login=email? 
        # User said: "Separate Username from Email". So we need to store 'email' in session.
        # FIX: I will update auth.py to store email in session_state first.
        # For now, I'll use a placeholder or safe get.
        user_notif_email = st.session_state.get('email', '') 
        
        if user_notif_email and "@" in user_notif_email:
             # Just a small indicator or nothing
             pass
        else:
             if 'authenticated' in st.session_state and st.session_state['authenticated']:
                 st.warning("⚠️ Configura tu Email en 'Usuarios' para activar notificaciones.")

        # Impersonation (Programador Only)
        if st.session_state.get('real_role') == 'Programador':
             st.divider()
             st.caption("🕵️ Nivel Dios")
             roles = ["Programador", "Administrador", "Residente de Obra", "Capataz", "Bodeguero", "Prevencionista"]
             
             curr = st.session_state.get('user_role', 'Programador')
             if curr not in roles: roles.append(curr)
             
             new_role = st.selectbox("Simular Rol", roles, index=roles.index(curr), key="role_impersonator")
             if new_role != curr:
                 st.session_state['user_role'] = new_role
                 st.rerun()

        if st.button("Cerrar Sesión", width='stretch', icon=":material/logout:"):
             auth.logout_user()

    # --- Router Safeguard ---
    # Ensure restricted roles NEVER access other views even if state persists
    if st.session_state.get('user_role') not in full_access_roles and selection != "Equipos":
        selection = "Equipos"

    # --- Router ---
    if selection == "Dashboard":
        views.render_dashboard()
    elif selection == "Proyectos":
        # Check if we are in detail view mode
        if st.session_state.get('view_mode') == 'details' and st.session_state.get('selected_project_id'):
            # Show "Back" button
            if st.button("⬅️ Volver al Listado de Proyectos"):
                st.session_state['view_mode'] = 'overview'
                st.session_state['selected_project_id'] = None
                st.rerun()
            
            # Render Details
            projects.render_project_details(st.session_state['selected_project_id'])
        else:
            # Default: Show Overview/CRUD
            projects.render_projects_overview()
            
    elif selection == "Licitaciones":
        views_tenders.render_tenders()

    elif selection == "Finanzas":
        views_finance.render_finance()
        
    elif selection == "Lean Plan":
        views_lean.render_lean()

    elif selection == "Subcontratos":
        views_compliance.render_compliance()

    elif selection == "Calidad":
        views_quality.render_quality()
        
    elif selection == "Equipos":
        from modules import views_maps
        views_maps.render_maps()

    elif selection == "Usuarios":
        views.render_user_management()
        
    elif selection == "Analista IA":
        from modules import views_ai
        views_ai.render_ai_view()

    elif selection == "Administración":
        from modules import views_admin
        views_admin.render_admin_panel()

    # --- Footer ---
    st.divider()
    with st.container():
        col1, col2, col3, col4 = st.columns([3,1,5,1])
        with col2:
            if IMG_LOGO_ALAIN:
                try:
                    st.image(IMG_LOGO_ALAIN, width=120)
                except Exception:
                    st.caption("NovApp Dev")
            else:
                st.caption("NovApp Dev")
                
        with col3:
            st.caption("Aplicación desarrollada por **Alain Antinao Sepúlveda** | v1.2.5")
            st.caption("📧 alain.antinao.s@gmail.com")

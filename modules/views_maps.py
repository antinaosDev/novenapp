import streamlit as st
import pandas as pd
from modules import teams, data

def render_maps():
    p_col, _ = st.columns([1, 2]) # Keeping layout consistency if needed, but here we modify the header directly.
    
    # Header with Export
    c_title, c_exp = st.columns([3, 1])
    with c_title:
        st.caption("Geolocalización de proyectos y gestión de personal")
        st.title("Equipos y Cartografía")
    
    with c_exp:
        with st.popover("📄 Reportes de Dotación"):
            st.write("**Informe de Personal**")
            if st.button("Generar Reporte PDF"):
                from modules import reports_gen
                import matplotlib.pyplot as plt
                
                # Fetch Data
                all_assigns = teams.get_all_assignments()
                stats = teams.get_stats()
                
                sections = []
                
                # 1. Executive Summary & KPIs
                total_p = stats['total_personnel']
                active_projects =  all_assigns['project_name'].nunique() if not all_assigns.empty else 0
                top_role = stats['roles_df'].iloc[0]['role'] if not stats['roles_df'].empty else "N/A"
                
                # Manual KPI Row for PDF
                sections.append({
                    "type": "kpi_row",
                    "content": [
                        {"label": "Fuerza Laboral", "value": str(total_p), "sub": "Total Asignados"},
                        {"label": "Proyectos Activos", "value": str(active_projects), "sub": "En ejecución"},
                        {"label": "Cargo Principal", "value": top_role, "sub": "Mayoría"}
                    ]
                })

                sections.append({
                    "type": "text", 
                    "title": "Resumen de Dotación", 
                    "content": f"El equipo actual se compone de {total_p} colaboradores distribuidos en {active_projects} proyectos activos. La mayor concentración de roles corresponde a '{top_role}'."
                })
                
                # 2. Global Charts (Smaller Size)
                if 'roles_df' in stats and not stats['roles_df'].empty:
                    # Side by side charts using subplots if possible, or just smaller individual ones
                    # Chart 1: Roles
                    fig1, ax1 = plt.subplots(figsize=(6, 3)) # Smaller height
                    roles_df = stats['roles_df'].head(5) # Top 5 only to save space
                    ax1.barh(roles_df['role'], roles_df['count'], color='#10b981')
                    ax1.set_title("Top 5 Cargos")
                    ax1.set_xlabel("Cantidad")
                    plt.tight_layout()
                    
                    sections.append({"type": "plot", "title": "Distribución de Cargos", "content": fig1})
                
                # 3. Tables per Project
                if not all_assigns.empty:
                    # Group by Project
                    grouped = all_assigns.groupby('project_name')
                    
                    for proj_name, group in grouped:
                         # Prepare table for this project
                         disp_df = group[['full_name', 'username', 'role', 'assigned_at']].copy()
                         disp_df.columns = ['Colaborador', 'Usuario', 'Cargo / Rol', 'Fecha Ingreso']
                         disp_df['Fecha Ingreso'] = pd.to_datetime(disp_df['Fecha Ingreso']).dt.strftime('%d/%m/%Y')
                         disp_df['Usuario'] = disp_df['Usuario'].apply(lambda x: f"@{x}")
                         
                         sections.append({
                             "type": "table",
                             "title": f"Dotación: {proj_name}",
                             "content": disp_df
                         })
                
                # 4. Resources
                units = data.get_units()
                if not units.empty:
                    sections.append({
                        "type": "table",
                        "title": "Inventario de Recursos y Maquinaria",
                        "content": units[['name', 'type', 'details']]
                    })

                pdf_bytes = reports_gen.generate_pdf_report("Reporte de Dotación y Proyectos", sections)
                st.session_state['last_team_pdf'] = pdf_bytes

            if 'last_team_pdf' in st.session_state:
                st.download_button("📥 Descargar PDF", st.session_state['last_team_pdf'], file_name="dotacion_reporte.pdf", mime="application/pdf")

    # Permissions Check
    user_role = st.session_state.get('user_role', 'Invitado')
    full_access = user_role in ['Administrador', 'Programador', 'Residente de Obra']

    if full_access:
        # Global Roster Expander
        with st.expander("🌍 Nómina Global de Personal", expanded=False):
            all_assigns = teams.get_all_assignments()
            if not all_assigns.empty:
                st.dataframe(
                    all_assigns[['full_name', 'username', 'project_name', 'role', 'assigned_at']],
                    column_config={
                        "full_name": "Nombre",
                        "username": "Usuario",
                        "project_name": "Proyecto",
                        "role": "Cargo",
                        "assigned_at": st.column_config.DatetimeColumn("Fecha Asignación", format="DD/MM/YYYY")
                    },
                    hide_index=True,
                    width='stretch'
                )
            else:
                st.info("No hay personal asignado actualmente.")
    
    # Tabs Logic
    if full_access:
        tab1, tab2, tab3 = st.tabs(["🌍 Mapa de Proyectos", "👷 Gestión de Equipos", "🛠️ Inventario de Recursos"])
        
        with tab1:
            render_project_map()
            
        with tab2:
            render_team_management()
    
        with tab3:
            st.subheader("Gestión de Activos y Recursos")
            
            # New Unit Form
            with st.container(border=True):
                with st.form("new_unit_map"):
                    st.write("➕ Nuevo Recurso")
                    c_u1, c_u2 = st.columns(2)
                    u_name = c_u1.text_input("Nombre (ej. Camión Placa X)")
                    u_type = c_u2.selectbox("Tipo", ["Maquinaria", "Vehículo", "Herramienta", "Tecnología"])
                    u_det = st.text_input("Detalles / Estado")
                    
                    if st.form_submit_button("Guardar Recurso"):
                        data.add_unit(u_name, u_type, u_det)
                        st.success("Recurso agregado al inventario.")
                        st.rerun()
            
            # List Units & Management
            units_df = data.get_units()
            if not units_df.empty:
                st.divider()
                st.subheader("Inventario Actual")
                
                st.dataframe(
                    units_df,
                    column_config={
                         "name": "Recurso",
                         "type": "Categoría",
                         "details": "Detalle / Estado"
                    },
                    hide_index=True,
                    width='stretch'
                )
                
                # Management Area
                st.markdown("### 🛠️ Gestionar Recurso")
                
                # Selector
                unit_options = units_df['id'].tolist()
                sel_unit_id = st.selectbox(
                    "Seleccionar Recurso para Editar/Eliminar:", 
                    unit_options, 
                    format_func=lambda x: f"{units_df[units_df['id']==x]['name'].values[0]} ({units_df[units_df['id']==x]['type'].values[0]})"
                )
                
                if sel_unit_id:
                    u_row = units_df[units_df['id'] == sel_unit_id].iloc[0]
                    
                    with st.container(border=True):
                        st.write(f"**Editando: {u_row['name']}**")
                        
                        with st.form(f"edit_unit_{sel_unit_id}"):
                            c_e1, c_e2 = st.columns(2)
                            new_u_name = c_e1.text_input("Nombre", value=u_row['name'])
                            curr_type = u_row['type']
                            type_opts = ["Maquinaria", "Vehículo", "Herramienta", "Tecnología"]
                            new_u_type = c_e2.selectbox("Tipo", type_opts, index=type_opts.index(curr_type) if curr_type in type_opts else 0)
                            
                            new_u_det = st.text_input("Detalles / Estado", value=u_row['details'])
                            
                            if st.form_submit_button("💾 Actualizar Recurso"):
                                data.update_unit(sel_unit_id, new_u_name, new_u_type, new_u_det)
                                st.toast("Recurso actualizado", icon="✅")
                                st.rerun()
                        
                        st.markdown("")
                        if st.button("🗑️ Eliminar Recurso", key=f"del_unit_{sel_unit_id}", type="primary"):
                             data.delete_unit(sel_unit_id)
                             st.toast("Recurso eliminado", icon="🗑️")
                             st.rerun()

            else:
                st.info("No hay recursos en inventario.")
    else:
        # Restricted View: ONLY Map
        st.divider()
        render_project_map()

def render_project_map():
    df_projects = teams.get_project_locations()
    stats = teams.get_stats()
    
    if df_projects.empty:
        st.info("No hay proyectos con georreferencia activos.")
        return

    # Stats (Cards)
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.metric("Proyectos Activos", len(df_projects), help="Obras con ubicación definida")
    with c2:
        with st.container(border=True):
            st.metric("Personal en Terreno", stats['total_personnel'], help="Total de trabajadores (Asignaciones activas)")

    # --- Analytics Section ---
    st.subheader("Análisis de Dotación")
    c_chart1, c_chart2 = st.columns(2)
    
    with c_chart1:
         # Role Distribution Pie
         import plotly.express as px
         roles_df = stats['roles_df']
         
         if not roles_df.empty:
             fig_roles = px.pie(roles_df, values='count', names='role', hole=0.6, title="Distribución por Roles")
             fig_roles.update_layout(height=300, margin=dict(t=30, l=10, r=10, b=10))
             st.plotly_chart(fig_roles, width='stretch')
         else:
             st.info("Sin datos de roles.")
         
    with c_chart2:
        # Personnel per Project Bar
        projs_df = stats['projects_df']
        
        if not projs_df.empty:
            fig_bar = px.bar(projs_df, x='project_name', y='count', title="Personal por Obra", color='project_name')
            fig_bar.update_layout(height=300, margin=dict(t=30, l=10, r=10, b=10), showlegend=False)
            st.plotly_chart(fig_bar, width='stretch')
        else:
            st.info("Sin asignaciones de personal.")

    # Map Container
    with st.container(border=True):
        st.subheader("Mapa Global")
        st.map(df_projects, size=20, color='#10b981')
    
    with st.expander("📍 Detalle de Coordenadas", expanded=False):
        st.dataframe(
            df_projects[['name', 'latitude', 'longitude']], 
            hide_index=True, 
            width='stretch',
            column_config={
                "name": "Proyecto",
                "latitude": "Latitud",
                "longitude": "Longitud"
            }
        )

def render_team_management():
    # Select Project Card
    with st.container(border=True):
        st.subheader("Selección de Proyecto")
        projects = data.get_projects()
        if projects.empty:
            st.warning("Crea un proyecto primero.")
            return
            
        selected_pid = st.selectbox("Proyecto", projects['id'], format_func=lambda x: projects[projects['id']==x]['name'].values[0])
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        with st.container(border=True):
            st.subheader("Cuadrilla Asignada")
            members = teams.get_team_members(selected_pid)
            
            if members.empty:
                st.info("No hay personal asignado a este proyecto.")
            else:
                st.dataframe(
                    members[['full_name', 'role', 'assigned_at']], 
                    hide_index=True, 
                    width='stretch',
                    column_config={
                        "full_name": "Nombre",
                        "role": "Rol",
                        "assigned_at": st.column_config.DatetimeColumn("Fecha Asignación", format="DD/MM/YYYY, HH:mm")
                    }
                )
                
                st.divider()
                # Enhanced format: Name (Role)
                member_options = members['id'].tolist()
                member_to_remove = st.selectbox(
                    "Eliminar Miembro:", 
                    member_options, 
                    format_func=lambda x: f"{members[members['id']==x]['full_name'].values[0]} ({members[members['id']==x]['role'].values[0]})" if not members.empty else "", 
                    key="rem_sel"
                )
                
                if member_to_remove:
                     if st.button("❌ Eliminar Asignación", type="primary"):
                         teams.remove_team_member(member_to_remove)
                         st.toast("Miembro eliminado del equipo", icon="👋")
                         st.rerun()

    with c2:
        with st.container(border=True):
            st.subheader("Asignar Personal")
            with st.form("assign_form"):
                all_users = teams.get_all_users()
                
                if not all_users.empty:
                    # Enhanced format: Name | Username (Role)
                    user_id = st.selectbox(
                        "Seleccionar Usuario", 
                        all_users['id'], 
                        format_func=lambda x: f"{all_users[all_users['id']==x]['full_name'].values[0]} | @{all_users[all_users['id']==x]['username'].values[0]} ({all_users[all_users['id']==x]['role'].values[0]})"
                    )
                else:
                    st.warning("No hay usuarios registrados.")
                    user_id = None
                
                # Dynamic Roles
                roles_df = data.get_roles()
                available_roles = roles_df['name'].tolist() if not roles_df.empty else ["Capataz", "Bodeguero", "Prevencionista"]
                
                role = st.selectbox("Rol", available_roles)
                
                from datetime import datetime
                assign_date = st.date_input("Fecha Ingreso", value=datetime.today())

                if st.form_submit_button("Asignar"):
                    teams.assign_user_to_project(selected_pid, user_id, role, assign_date)
                    st.toast(f"Asignado como {role} desde {assign_date.strftime('%d/%m/%Y')}", icon="✅")
                    st.rerun()

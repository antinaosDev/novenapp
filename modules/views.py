import streamlit as st
import pandas as pd
from modules import data, ui
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import textwrap

def render_dashboard():
    # --- Data Fetching ---
    kpis = data.get_kpis()
    projects_df = data.get_projects()
    expenses_df = data.get_expenses_df()
    alerts_data = data.get_dashboard_alerts()
    
    # --- Pre-processing for Advanced Analytics ---
    
    # 1. Project Deadlines & Timeline
    if not projects_df.empty:
        projects_df['start_date'] = pd.to_datetime(projects_df['start_date'])
        projects_df['end_date'] = pd.to_datetime(projects_df['end_date'])
        projects_df['days_left'] = (projects_df['end_date'] - datetime.now()).dt.days
        
        # Risk flags
        projects_df['risk_deadline'] = projects_df['days_left'] < 30
    
    # 2. Budget vs Real (Merge)
    if not projects_df.empty and not expenses_df.empty:
        exp_by_proj = expenses_df.groupby('project_id')['amount'].sum().reset_index()
        budget_analysis = pd.merge(
            projects_df[['id', 'name', 'budget_total', 'status']], 
            exp_by_proj, 
            left_on='id', 
            right_on='project_id', 
            how='left'
        )
        budget_analysis['amount'] = budget_analysis['amount'].fillna(0)
        budget_analysis['utilization'] = (budget_analysis['amount'] / budget_analysis['budget_total']) * 100
    else:
        budget_analysis = projects_df.copy() if not projects_df.empty else pd.DataFrame()
        if not budget_analysis.empty:
             budget_analysis['amount'] = 0
             budget_analysis['utilization'] = 0

    # --- Header ---
    c_title, c_date = st.columns([4, 1])
    with c_title:
        st.title("Tablero de Mando Integral")
        st.caption("Visión 360° de Operaciones, Finanzas y Cumplimiento")
    with c_date:
        st.caption(f"📅 {datetime.now().strftime('%d/%m/%Y')}")
    
    # --- Top KPIs (High Level) ---
    c1, c2, c3, c4, c5 = st.columns(5)
    
    # Active Projects
    active_count = len(projects_df[projects_df['status'] == 'Activo']) if not projects_df.empty else 0
    c1.metric("Proyectos Activos", active_count, delta="En ejecución", delta_color="normal")
    
    # Budget Health
    total_budget = kpis['total_budget']
    total_spent = kpis['total_spent']
    global_utilization = (total_spent / total_budget * 100) if total_budget > 0 else 0
    c2.metric("Ejecución Presupuestal", f"{global_utilization:.1f}%", delta=f"${total_spent:,.0f} gastado", delta_color="inverse")
    
    # Pending POs
    c3.metric("Órdenes Pendientes", f"${kpis.get('pending_po_amount', 0):,.0f}", delta=f"{alerts_data[0]['message'] if alerts_data else 'Sin atrasos'}", delta_color="off")

    # Quality
    lab_df = data.get_lab_tests(None)
    pass_rate = 0
    if not lab_df.empty:
         pass_count = len(lab_df[lab_df['result'] == 'Aprobado'])
         pass_rate = int((pass_count/len(lab_df))*100)
    c4.metric("Calidad Global", f"{pass_rate}%", delta="Tasa Aprobación")
    
    # Team
    t_stats = data.get_global_team_stats() # Assuming enhanced data function or reusing existing
    # Fallback if get_global_team_stats isn't ready, use placeholder or kpis
    c5.metric("Fuerza Laboral", t_stats.get('total_personnel', 0), delta="En terreno")

    st.divider()

    # --- SECTION 1: CRITICAL TIMELINE & DEADLINES ---
    st.subheader("⏳ Cronograma Crítico y Plazos")
    
    c_gantt, c_deadlines = st.columns([2, 1])
    
    with c_gantt:
        with st.container(border=True):
            st.markdown("##### 📅 Gantt de Proyectos Activos")
            if not projects_df.empty:
                # Gantt Chart
                fig_gantt = px.timeline(
                    projects_df, 
                    x_start="start_date", 
                    x_end="end_date", 
                    y="name", 
                    color="status",
                    hover_data=["days_left", "budget_total"],
                    color_discrete_map={"Activo": "#10b981", "Completado": "#64748b", "Pausado": "#f59e0b"}
                )
                fig_gantt.update_yaxes(autorange="reversed") # Top to bottom
                fig_gantt.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_gantt, use_container_width=True)
            else:
                st.info("No hay proyectos para visualizar.")

    with c_deadlines:
        with st.container(border=True):
            st.markdown("##### 🚨 Próximos Vencimientos (< 60 días)")
            if not projects_df.empty:
                # Filter risks
                risks = projects_df[projects_df['days_left'] < 60].sort_values('days_left')
                if not risks.empty:
                    st.dataframe(
                        risks[['name', 'end_date', 'days_left']],
                        column_config={
                            "name": "Proyecto",
                            "end_date": st.column_config.DateColumn("Fecha Término", format="DD/MM/YYYY"),
                            "days_left": st.column_config.NumberColumn("Días Restantes", format="%d ⏳")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.success("🎉 Sin vencimientos críticos próximos.")
            else:
                st.caption("Sin datos.")

    st.divider()

    # --- SECTION 2: BUDGET CONTROL & ANALYTICS ---
    st.subheader("💰 Control Financiero de Proyectos")
    
    c_chart_bud, c_pie_status = st.columns([2, 1])
    
    with c_chart_bud:
         with st.container(border=True):
            st.markdown("##### 📊 Presupuesto vs. Gasto Real")
            if not budget_analysis.empty:
                # Grouped Bar Chart
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(
                    x=budget_analysis['name'],
                    y=budget_analysis['budget_total'],
                    name='Presupuesto',
                    marker_color='#cbd5e1'
                ))
                fig_bar.add_trace(go.Bar(
                    x=budget_analysis['name'],
                    y=budget_analysis['amount'],
                    name='Gasto Real',
                    marker_color='#10b981'
                ))
                fig_bar.update_layout(barmode='group', height=300, margin=dict(t=10, b=10))
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Faltan datos de presupuesto.")

    with c_pie_status:
        with st.container(border=True):
            st.markdown("##### 🏗️ Distribución de Cartera")
            if not projects_df.empty:
                status_counts = projects_df['status'].value_counts().reset_index()
                status_counts.columns = ['status', 'count']
                fig_pie = px.pie(
                    status_counts, 
                    values='count', 
                    names='status', 
                    hole=0.6,
                    color_discrete_sequence=['#10b981', '#f59e0b', '#64748b']
                )
                fig_pie.update_layout(height=300, margin=dict(t=10, b=10), showlegend=True)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.caption("Sin proyectos.")

    # --- SECTION 3: OPERATIONAL DETAILED STATS ---
    
    # Recent Activity Row
    c_exp, c_alert_list = st.columns([1, 1])
    
    with c_exp:
        st.subheader("📉 Últimos Movimientos")
        recent_exp = data.get_recent_expenses(5)
        if not recent_exp.empty:
            st.dataframe(
                recent_exp[['date', 'category', 'amount', 'description']],
                column_config={
                    "date": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"), 
                    "category": "Cat.", 
                    "amount": st.column_config.NumberColumn("Monto", format="$%d"),
                    "description": "Detalle"
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.caption("No hay gastos recientes.")
            
    with c_alert_list:
        st.subheader("🔔 Notificaciones del Sistema")
        if alerts_data:
            for alert in alerts_data[:3]:
                with st.expander(f"{alert['message']}", expanded=False):
                    st.caption(f"**Área**: {alert['scope']}")
                    st.write(alert['detail'])
        else:
            st.info("Todo en orden. Sin notificaciones.")
            
    
    # --- EXPORT TOOLS (Retained/Condensed) ---
    with st.expander("🛠️ Herramientas de Reportabilidad Avanzada"):
         c_xp1, c_xp2 = st.columns(2)
         with c_xp1:
             st.write("**Descargar Métricas (Excel)**")
             # Reuse Excel generation logic
             from modules import reports_gen
             
             # Fetch and Translate Data
             p = data.get_projects()
             e = data.get_expenses_df()
             s = data.get_subcontractors(None)
             
             # Rename Columns for Excel
             if not p.empty:
                 p = p.rename(columns={
                     'name': 'Nombre Proyecto', 'description': 'Descripción', 
                     'budget_total': 'Presupuesto Total', 'start_date': 'Fecha Inicio',
                     'end_date': 'Fecha Fin', 'status': 'Estado', 'days_left': 'Días Restantes'
                 })
             
             if not e.empty:
                 e = e.rename(columns={
                     'date': 'Fecha', 'amount': 'Monto', 'category': 'Categoría',
                     'description': 'Detalle', 'project': 'Proyecto', 'faena': 'Faena', 'unit': 'Unidad'
                 })
                 
             if not s.empty:
                 s = s.rename(columns={
                     'name': 'Razón Social', 'rut': 'RUT', 'contact_email': 'Email',
                     'contact_phone': 'Teléfono', 'specialty': 'Especialidad', 'status': 'Estado'
                 })

             xls = reports_gen.generate_excel({"Proyectos": p, "Gastos": e, "Subcontratos": s})
             st.download_button("📊 Descargar Excel", xls, file_name=f"Data_Export_{datetime.now().date()}.xlsx")
         
         with c_xp2:
             st.write("**Reporte Gerencial PDF**")
             if st.button("Generar Reporte Completo"):
                 with st.spinner("Generando Reporte de Directorio..."):
                     import matplotlib.pyplot as plt
                     import matplotlib.ticker as ticker
                     from modules import reports_gen
                     
                     # --- Data Prep ---
                     rp_kpis = data.get_kpis()
                     rp_exp = data.get_expenses_df()
                     rp_projs = data.get_projects()
                     rp_alerts = data.get_dashboard_alerts()
                     
                     # Fetch POs for Chart Data consistency
                     rp_pos = data.get_purchase_orders(None)
                     
                     # Calculate derived stats
                     exec_pct = (rp_kpis['total_spent']/rp_kpis['total_budget']*100) if rp_kpis['total_budget']>0 else 0
                     
                     # Prep projects data for report
                     if not rp_projs.empty:
                         rp_projs['end_date'] = pd.to_datetime(rp_projs['end_date'])
                         rp_projs['days_left'] = (rp_projs['end_date'] - datetime.now()).dt.days
                     
                     sections = []
                     
                     # --- PAGE 1: EXECUTIVE SUMMARY ---
                     
                     # KPI Row 1: Finance & Ops
                     sections.append({
                         "type": "kpi_row",
                         "content": [
                             {"label": "Presupuesto Total", "value": f"${rp_kpis['total_budget']:,.0f}", "sub": "Inversión Aprobada"},
                             {"label": "Gasto Ejecutado", "value": f"${rp_kpis['total_spent']:,.0f}", "sub": f"{exec_pct:.1f}% Ejecución"},
                             {"label": "Cartera Activa", "value": str(len(rp_projs[rp_projs['status']=='Activo'])), "sub": "Proyectos en Curso"}
                         ]
                     })
                     
                     # KPI Row 2: Performance
                     sections.append({
                         "type": "kpi_row",
                         "content": [
                             {"label": "PPC Global (Lean)", "value": f"{rp_kpis['global_ppc']}%", "sub": "Cumplimiento Plan"},
                             {"label": "Subcontratos", "value": str(rp_kpis['active_subs']), "sub": "Empresas Activas"},
                             {"label": "Postulaciones", "value": str(rp_kpis['open_tenders']), "sub": "En Proceso"}
                         ]
                     })
                     
                     sections.append({"type": "text", "content": " "}) # Spacer

                     # Chart 1: Project Budget vs Limit (Horizontal Bar for Readability)
                     if not rp_projs.empty:
                          # Aggregate POs by Project
                          if not rp_pos.empty:
                               # Filter non-rejected
                               valid_pos = rp_pos[rp_pos['status'] != 'Rechazada']
                               exp_by_proj = valid_pos.groupby('project_id')['total_amount'].sum().reset_index()
                               exp_by_proj.columns = ['project_id', 'amount']
                          else:
                               exp_by_proj = pd.DataFrame(columns=['project_id', 'amount'])
                               
                          merged = pd.merge(rp_projs, exp_by_proj, left_on='id', right_on='project_id', how='left').fillna(0)
                          merged = merged.sort_values('budget_total', ascending=True).tail(8) # Top 8
                          
                          fig1, ax1 = plt.subplots(figsize=(10, 5))
                          y_pos = range(len(merged))
                          
                          ax1.barh(y_pos, merged['budget_total'],  color='#cbd5e1', label='Presupuesto')
                          ax1.barh(y_pos, merged['amount'], color='#10b981', label='Ejecutado', height=0.5)
                          
                          ax1.set_yticks(y_pos)
                          ax1.set_yticklabels(merged['name'], fontsize=9)
                          ax1.set_xlabel("Monto ($)", fontsize=8)
                          ax1.legend()
                          ax1.set_title("Estado Financiero Top Proyectos", fontweight='bold')
                          ax1.grid(axis='x', linestyle='--', alpha=0.3)
                          
                          # Format X axis to full numbers
                          ax1.xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
                          
                          # Add labels on bars (Full amounts)
                          for i, v in enumerate(merged['amount']):
                              ax1.text(v, i - 0.1, f"${v:,.0f}", color='#065f46', fontweight='bold', fontsize=8, ha='left')

                          sections.append({"type": "plot", "content": fig1, "title": "Control Presupuestario (Top 8)"})
                     
                     sections.append({"type": "new_page"})

                     # --- PAGE 2: FINANCIAL EVOLUTION & RISKS ---

                     # Chart 2: Time Series
                     if not rp_exp.empty:
                         rp_exp['date'] = pd.to_datetime(rp_exp['date'])
                         m_exp = rp_exp.groupby(pd.Grouper(key='date', freq='ME'))['amount'].sum().reset_index()
                         
                         fig2, ax2 = plt.subplots(figsize=(10, 4))
                         ax2.plot(m_exp['date'], m_exp['amount'], color='#3b82f6', marker='o', linewidth=2)
                         ax2.fill_between(m_exp['date'], m_exp['amount'], color='#dbeafe', alpha=0.5)
                         
                         ax2.yaxis.set_major_formatter(ticker.StrMethodFormatter('${x:,.0f}'))
                         ax2.set_title("Evolución de Gasto Mensual", fontweight='bold')
                         ax2.grid(True, linestyle='--', alpha=0.3)
                         
                         # Parse dates to avoid overlap
                         fig2.autofmt_xdate(rotation=45)
                         
                         sections.append({"type": "plot", "content": fig2, "title": "Tendencia Financiera"})
                     
                     # Risk Table
                     risks = rp_projs[rp_projs['days_left'] < 60].sort_values('days_left')
                     if not risks.empty:
                         # Prepare table logic
                         risk_dis = risks[['name', 'end_date', 'days_left']].copy()
                         risk_dis['end_date'] = risk_dis['end_date'].dt.strftime('%d/%m/%Y')
                         risk_dis.columns = ['Proyecto', 'Fecha Término', 'Días Rest.']
                         sections.append({"type": "table", "content": risk_dis, "title": "ALERTAS: Cronograma Crítico (< 60 días)"})
                     else:
                         sections.append({"type": "text", "content": "No existen riesgos de cronograma críticos para los próximos 60 días.", "title": "Estado de Plazos"})

                     # Alerts section
                     if rp_alerts:
                         alert_txt = "\n".join([f"- [{a['severity'].upper()}] {a['scope']}: {a['message']}" for a in rp_alerts[:5]])
                         sections.append({"type": "text", "title": "Notificaciones del Sistema", "content": alert_txt})
                     
                     # Top Expenses Table
                     top_exp = rp_exp.sort_values("amount", ascending=False).head(7)
                     if not top_exp.empty:
                          top_exp_dis = top_exp[['date', 'category', 'amount', 'project']].copy()
                          top_exp_dis['date'] = top_exp_dis['date'].dt.strftime('%d/%m')
                          top_exp_dis.columns = ['Fecha', 'Ítem', 'Monto', 'Proyecto']
                          sections.append({"type": "table", "content": top_exp_dis, "title": "Desembolsos Mayores Recientes"})

                     # Generate
                     pdf_bytes = reports_gen.generate_pdf_report("Reporte de Gestión Ejecutiva", sections)
                     st.session_state['last_dash_pdf'] = pdf_bytes
                     st.rerun()

             if 'last_dash_pdf' in st.session_state:
                 st.download_button("📥 Descargar Reporte PDF", st.session_state['last_dash_pdf'], file_name="Reporte_Directorio.pdf", mime="application/pdf")



def render_config():
    st.title("Configuración & Presupuestos")
    
    tabs = st.tabs(["Proyectos", "Faenas", "Unidades"])
    
    with tabs[0]:
        st.subheader("Crear Nuevo Proyecto")
        
        with st.container(border=True):
            with st.form("new_project"):
                name = st.text_input("Nombre del Proyecto")
                budget = st.number_input("Presupuesto Total", min_value=0.0)
                desc = st.text_area("Descripción")
                c1, c2 = st.columns(2)
                start = c1.date_input("Inicio")
                end = c2.date_input("Fin")
                
                if st.form_submit_button("Guardar Proyecto"):
                    data.add_project(name, desc, budget, start, end)
                    st.success(f"Proyecto {name} creado.")
                    st.rerun()
        
        st.divider()
        st.subheader("Proyectos Existentes")
        st.dataframe(
            data.get_projects(), 
            width='stretch',
            column_config={
                "id": st.column_config.NumberColumn("ID", format="%d"),
                "name": "Nombre Proyecto",
                "description": "Descripción",
                "budget_total": st.column_config.NumberColumn("Presupuesto", format="$%d"),
                "start_date": st.column_config.DateColumn("Fecha Inicio"),
                "end_date": st.column_config.DateColumn("Fecha Fin"),
                "status": "Estado",
                "latitude": "Latitud",
                "longitude": "Longitud"
            }
        )

    with tabs[1]:
        st.subheader("Crear Nueva Faena")
        projects = data.get_projects()
        if not projects.empty:
             with st.container(border=True):
                with st.form("new_faena"):
                    p_name = st.selectbox("Proyecto Asociado", projects['name'].tolist())
                    p_id = projects[projects['name'] == p_name]['id'].values[0]
                    name = st.text_input("Nombre de Faena (ej. Excavación)")
                    sup = st.text_input("Supervisor")
                    
                    if st.form_submit_button("Guardar Faena"):
                        data.add_faena(p_id, name, sup)
                        st.success("Faena creada.")
                        st.rerun()
        else:
            st.warning("Crea proyectos primero.")
            
    with tabs[2]:
        st.subheader("Inventario de Recursos")
        with st.container(border=True):
            with st.form("new_unit"):
                name = st.text_input("Nombre (ej. Camión Placa X)")
                type_ = st.selectbox("Tipo", ["Maquinaria", "Vehículo", "Personal", "Herramienta"])
                details = st.text_input("Detalles")
                
                if st.form_submit_button("Guardar Unidad"):
                    data.add_unit(name, type_, details)
                    st.success("Unidad creada.")
                    st.rerun()

def render_user_management():
    from modules import auth  
    st.title("Gestión de Usuarios y Roles")
    
    # Check permissions
    current_role = st.session_state.get('user_role')
    
    # Fetch Roles
    roles_df = data.get_roles()
    available_roles = roles_df['name'].tolist() if not roles_df.empty else ["Programador", "Administrador", "Residente de Obra", "Capataz", "Bodeguero", "Prevencionista"]

    # --- Security Restriction ---
    # Only Programador can see/assign Programador role
    if current_role != 'Programador':
        if "Programador" in available_roles:
            available_roles.remove("Programador")

    # Tabs if Programador
    if current_role == 'Programador':
        tab_users, tab_roles = st.tabs(["👥 Usuarios", "🛡️ Roles"])
    else:
        tab_users = st.container()
        tab_roles = None

    # --- Users Tab ---
    with tab_users:
        st.subheader("Directorio de Usuarios")
        
        # Form for new user
        with st.expander("➕ Crear Nuevo Usuario", expanded=False):
            with st.container(border=True):
                with st.form("create_user"):
                    c1, c2 = st.columns(2)
                    uname = c1.text_input("Usuario (Login Sistema)")
                    email = c2.text_input("Email (Notificaciones)")
                    pwd = st.text_input("Clave", type="password")
                    fname = st.text_input("Nombre Completo")
                    # Role selection filtered
                    role = st.selectbox("Rol", available_roles) 
                    
                    if st.form_submit_button("Crear Usuario"):
                         if uname and pwd and fname:
                             auth.create_user(uname, pwd, fname, role, email)
                             st.success("Usuario creado.")
                             st.rerun()
                         else:
                             st.error("Faltan datos.")
    
        # List
        users = data.get_users_full()
        
        # Filter users list: Admin cannot see Programmers
        if current_role != 'Programador':
            users = users[users['role'] != 'Programador']
            
        with st.container(border=True):
            st.dataframe(
                users[['id', 'username', 'full_name', 'role']],
                column_config={
                    "id": "ID", "username": "Login", "full_name": "Nombre", "role": "Rol"
                },
                hide_index=True,
                width='stretch'
            )
            
        st.divider()
        
        # Edit/Delete
        st.subheader("Administrar Usuario")
        if not users.empty:
             uid = st.selectbox("Seleccionar Usuario", users['id'], format_func=lambda x: users[users['id']==x]['username'].values[0])
             user_row = users[users['id']==uid].iloc[0]
             
             with st.form("edit_user"):
                 c1, c2 = st.columns(2)
                 # Login might be editable or not. Let's allow edit but label clearly.
                 e_login = c1.text_input("Usuario (Login)", value=user_row['username'])
                 e_email = c2.text_input("Email (Notificaciones)", value=user_row.get('email', '')) # Handle missing email col gracefully first time
                 
                 e_name = st.text_input("Nombre", value=user_row['full_name'])

                 # Determine index safely
                 try:
                     r_idx = available_roles.index(user_row['role'])
                 except ValueError:
                     r_idx = 0
                     
                 e_role = st.selectbox("Rol", available_roles, index=r_idx)
                 e_pwd = st.text_input("Nueva Clave (Dejar en blanco para mantener)", type="password")
                 
                 col_save, col_del = st.columns([1, 1])
                 if col_save.form_submit_button("💾 Actualizar"):
                      new_hash = auth.hash_password(e_pwd) if e_pwd else None
                      data.update_user(uid, e_login, e_name, e_role, new_hash, e_email)
                      st.success("Usuario actualizado.")
                      st.rerun()
    
                 if col_del.form_submit_button("🗑️ Eliminar Usuario", type="primary"):
                      data.delete_user(uid)
                      st.warning("Usuario eliminado.")
                      st.rerun()

    # --- Roles Tab (Programmer Only) ---
    if tab_roles:
        with tab_roles:
            st.subheader("Gestión de Perfiles y Permisos")
            
            with st.expander("➕ Crear Nuevo Rol"):
                with st.form("new_role"):
                    r_name = st.text_input("Nombre del Rol")
                    r_desc = st.text_input("Descripción")
                    if st.form_submit_button("Crear Rol"):
                        if r_name:
                            data.add_role(r_name, r_desc)
                            st.success(f"Rol {r_name} creado.")
                            st.rerun()
            
            if not roles_df.empty:
                 st.dataframe(
                     roles_df, 
                     hide_index=True, 
                     width='stretch',
                     column_config={
                         "name": "Nombre Rol",
                         "description": "Descripción",
                         "permissions": "Permisos"
                     }
                 )
                 
                 # Delete Role
                 r_del = st.selectbox("Eliminar Rol", roles_df['id'].tolist(), format_func=lambda x: roles_df[roles_df['id']==x]['name'].values[0])
                 if st.button("🗑️ Eliminar Rol Seleccionado"):
                     data.delete_role(r_del)
                     st.rerun()

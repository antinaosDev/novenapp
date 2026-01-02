from modules import data, ui
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import textwrap

def render_projects_overview():
    st.title("Gestión de Proyectos")
    
    # Permissions
    role = st.session_state.get('user_role')
    can_edit = role in ['Administrador', 'Programador', 'Residente de Obra']
    can_delete = role in ['Administrador', 'Residente de Obra', 'Programador']

    # --- Actions: Create New ---
    if can_edit:
        with st.expander("➕ Crear Nuevo Proyecto", expanded=False):
            with st.container(border=True):
                with st.form("new_project"):
                    st.write("Registrar Nueva Obra")
                    name = st.text_input("Nombre del Proyecto")
                    budget = st.number_input("Presupuesto Total", min_value=0.0)
                    desc = st.text_area("Descripción")
                    c1, c2 = st.columns(2)
                    start = c1.date_input("Inicio")
                    end = c2.date_input("Fin")
                    
                    if st.form_submit_button("Guardar Proyecto", type="primary"):
                        data.add_project(name, desc, budget, start, end)
                        st.success(f"Proyecto {name} creado.")
                        st.rerun()

    # --- Projects List ---
    projects = data.get_projects()
    
    if projects.empty:
        st.info("No hay proyectos registrados.")
    else:
        st.subheader(f"Proyectos Activos ({len(projects)})")
        
        # Display as cards or table with actions
        for _, row in projects.iterrows():
            with st.container(border=True):
                c_info, c_actions = st.columns([3, 1])
                
                with c_info:
                    st.subheader(f"🏗️ {row['name']}")
                    st.caption(f"Estado: {row.get('status', 'N/A')} | Presupuesto: ${row['budget_total']:,.0f}")
                    st.write(row.get('description', ''))
                
                with c_actions:
                    # View Details Button (Primary Action)
                    if st.button("📂 Gestionar", key=f"view_{row['id']}", type="secondary", width='stretch'):
                        st.session_state['selected_project_id'] = row['id']
                        st.session_state['view_mode'] = 'details'
                        st.rerun()

                    # Edit (Admin/Prog)
                    if can_edit:
                        with st.popover("✏️ Editar", width='stretch'):
                             with st.form(f"edit_proj_{row['id']}"):
                                 e_name = st.text_input("Nombre", value=row['name'])
                                 e_budg = st.number_input("Presupuesto", value=float(row['budget_total']))
                                 e_desc = st.text_area("Descripción", value=row['description'])
                                 
                                 # Fechas - Handle parsing safely
                                 try:
                                     d_start = datetime.strptime(row['start_date'], '%Y-%m-%d').date()
                                     d_end = datetime.strptime(row['end_date'], '%Y-%m-%d').date()
                                 except: 
                                     d_start = datetime.now().date()
                                     d_end = datetime.now().date()

                                 c1, c2 = st.columns(2)
                                 e_start = c1.date_input("Inicio", value=d_start)
                                 e_end = c2.date_input("Fin", value=d_end)
                                 
                                 if st.form_submit_button("Guardar Cambios"):
                                     data.update_project(row['id'], e_name, e_desc, e_budg, e_start, e_end)
                                     st.rerun()

                    # Delete (Prog Only)
                    if can_delete:
                        if st.button("🗑️ Eliminar", key=f"del_proj_{row['id']}", type="primary", width='stretch'):
                            data.delete_project(row['id'])
                            st.rerun()

    """Returns plotly figure for the Gantt chart."""
def get_timeline_html(project_id):
    phases = data.get_phases(project_id)
    
    if not phases.empty:
        # Convert to datetime
        phases['start_date'] = pd.to_datetime(phases['start_date'])
        phases['end_date'] = pd.to_datetime(phases['end_date'])
        
        fig = px.timeline(phases, x_start="start_date", x_end="end_date", y="name", color="status",
                          title=None)
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            margin=dict(t=10, l=10, r=10, b=10), height=300,
            font=dict(family="sans-serif", color="#64748b")
        )
        return fig
    else:
        return None

def render_project_details(project_id):
    """Detailed view for a specific project."""
    projects = data.get_projects()
    project = projects[projects['id'] == project_id].iloc[0]
    
    # Permissions
    role = st.session_state.get('user_role')
    can_delete = role in ['Administrador', 'Residente de Obra', 'Programador']
    
    budget_str = f"${project['budget_total']:,.0f}"

    # --- Header Section (Native) ---
    st.caption("Proyectos / Detalle")
    c_title, c_stats = st.columns([2, 1])
    
    with c_title:
        st.title(project['name'])
        st.caption("Panel de control y seguimiento de obra")
        
    with c_stats:
        c_stat1, c_stat2 = st.columns(2)
        c_stat1.metric("Presupuesto", budget_str)
        c_stat2.metric("Estado", project['status'])
    
    # Export Button (New Project Fiche)
    if st.button("📄 Generar Ficha de Proyecto", key="btn_export_pdf", help="Generar informe ejecutivo del proyecto"):
        with st.spinner("Generando Ficha de Proyecto..."):
            import matplotlib.pyplot as plt
            import matplotlib.ticker as ticker
            import matplotlib.dates as mdates
            from modules import reports_gen
            
            # --- Data Gathering ---
            # Budget
            budget_items = data.get_budget_items(project_id)
            total_budget = budget_items['estimated_amount'].sum() if not budget_items.empty else project['budget_total']
            
            # Expenses
            orders = data.get_purchase_orders(project_id)
            if not orders.empty and 'status' in orders.columns:
                valid_orders = orders[orders['status']!='Rechazada']
                total_spent = valid_orders['total_amount'].sum()
            else:
                valid_orders = pd.DataFrame()
                total_spent = 0
            
            # Phases
            phases = data.get_phases(project_id)
            
            # KPIs
            exec_pct = (total_spent / total_budget * 100) if total_budget > 0 else 0
            days_left = (pd.to_datetime(project['end_date']) - datetime.now()).days
            
            sections = []
            
            # 1. Header / KPIs
            sections.append({
                "type": "kpi_row",
                "content": [
                    {"label": "Presupuesto", "value": f"${total_budget:,.0f}", "sub": "Total Estimado"},
                    {"label": "Ejecutado", "value": f"${total_spent:,.0f}", "sub": f"{exec_pct:.1f}% del Presupuesto"},
                    {"label": "Estado", "value": project['status'], "sub": f"{days_left} días restantes"}
                ]
            })
            
            sections.append({"type": "text", "title": "Descripción del Proyecto", "content": project.get('description', 'Sin descripción.')})
            
            sections.append({"type": "new_page"})
            
            # 2. Financial Breakdown (Chart)
            if not budget_items.empty:
                cat_sum = budget_items.groupby('category')['estimated_amount'].sum().reset_index()
                
                fig1, ax1 = plt.subplots(figsize=(10, 5))
                bars = ax1.bar(cat_sum['category'], cat_sum['estimated_amount'], color='#10b981')
                
                ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter('${x:,.0f}'))
                ax1.set_title("Composición del Presupuesto por Categoría", fontweight='bold')
                ax1.grid(axis='y', linestyle='--', alpha=0.3)
                
                # Labels
                for bar in bars:
                    height = bar.get_height()
                    ax1.text(bar.get_x() + bar.get_width()/2., height,
                            f'${height:,.0f}',
                            ha='center', va='bottom', fontsize=9)
                
                sections.append({"type": "plot", "content": fig1, "title": "Desglose Presupuestario"})
            
            # 3. Timeline (Chart)
            if not phases.empty:
                phases['start'] = pd.to_datetime(phases['start_date'])
                phases['end'] = pd.to_datetime(phases['end_date'])
                phases = phases.sort_values('start')
                
                fig2, ax2 = plt.subplots(figsize=(10, len(phases)*0.8 + 2))
                
                # Create Bars
                for i, row in phases.iterrows():
                    start_num = mdates.date2num(row['start'])
                    end_num = mdates.date2num(row['end'])
                    duration = end_num - start_num
                    
                    color = '#3b82f6' if row['status'] == 'En Progreso' else '#cbd5e1'
                    if row['status'] == 'Completada': color = '#10b981'
                    
                    ax2.barh(row['name'], duration, left=start_num, height=0.5, color=color)
                
                ax2.xaxis_date()
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
                ax2.set_title("Cronograma de Fases", fontweight='bold')
                ax2.grid(axis='x', linestyle='--', alpha=0.3)
                
                sections.append({"type": "plot", "content": fig2, "title": "Planificación"})
            
            # 4. Recent Expenses (Table)
            if not valid_orders.empty:
                 last_orders = valid_orders.sort_values('date', ascending=False).head(10)[['date', 'provider_name', 'description', 'total_amount']]
                 last_orders['date'] = pd.to_datetime(last_orders['date']).dt.strftime('%d/%m/%Y')
                 last_orders.columns = ['Fecha', 'Proveedor', 'Detalle', 'Monto']
                 sections.append({"type": "table", "content": last_orders, "title": "Últimos Gastos Registrados"})

            # 5. Faenas
            faenas_pdf = data.get_faenas(project_id)
            if not faenas_pdf.empty:
                sections.append({
                    "type": "table",
                    "content": faenas_pdf[['name', 'supervisor']],
                    "title": "Faenas y Frentes de Trabajo"
                })

            # Generate
            pdf_bytes = reports_gen.generate_pdf_report(f"Ficha: {project['name']}", sections)
            
            st.download_button(
                 label="⬇️ Descargar Ficha PDF",
                 data=pdf_bytes,
                 file_name=f"Ficha_{project['name']}.pdf",
                 mime="application/pdf",
                 type="primary"
            )

    # --- Tabs Content ---
    tabs = st.tabs(["📊 Cronograma", "💰 Gastos", "💬 Bitácora", "🏗️ Faenas", "⚙️ Configuración"])
    
    with tabs[0]:
        st.subheader("Línea de Tiempo")
        
        # Refresh phases
        phases = data.get_phases(project_id)
        
        if not phases.empty:
            # --- Chart Logic (Fixed) ---
            phases['start_date'] = pd.to_datetime(phases['start_date'])
            phases['end_date'] = pd.to_datetime(phases['end_date'])
            
            fig = px.timeline(phases, x_start="start_date", x_end="end_date", y="name", color="status", title=None)
            fig.update_yaxes(autorange="reversed")
            fig.update_xaxes(tickformat="%Y-%m-%d") # Fix axis labels
            fig.update_layout(
                margin=dict(t=10, l=10, r=10, b=10), height=350,
                font=dict(family="sans-serif", color="#64748b")
            )
            st.plotly_chart(fig, width='stretch')
            
            # --- CRUD Management (Table + Edit/Delete) ---
            st.divider()
            st.write("📋 Gestión de Fases")
            
            st.dataframe(
                phases[['name', 'start_date', 'end_date', 'status']],
                column_config={
                    "name": "Fase",
                    "start_date": st.column_config.DateColumn("Fecha Inicio", format="DD/MM/YYYY"),
                    "end_date": st.column_config.DateColumn("Fecha Fin", format="DD/MM/YYYY"),
                    "status": "Estado"
                },
                hide_index=True,
                width='stretch'
            )
            
            # Select for Action
            phase_to_edit = st.selectbox("Gestionar Fase:", phases['id'].tolist(), format_func=lambda x: phases[phases['id']==x]['name'].values[0], key="ph_sel")
            
            if phase_to_edit:
                row_ph = phases[phases['id']==phase_to_edit].iloc[0]
                
                with st.popover("✏️ Editar Fase"):
                    with st.form(f"edit_ph_{phase_to_edit}"):
                        u_name = st.text_input("Nombre", value=row_ph['name'])
                        c1, c2 = st.columns(2)
                        
                        # Safe date parsing
                        try:
                            d_s = row_ph['start_date'].date()
                            d_e = row_ph['end_date'].date()
                        except:
                            d_s = datetime.now().date()
                            d_e = datetime.now().date()
                            
                        u_start = c1.date_input("Inicio", value=d_s)
                        u_end = c2.date_input("Fin", value=d_e)
                        
                        if st.form_submit_button("Guardar Cambios"):
                            data.update_phase(phase_to_edit, u_name, u_start, u_end)
                            st.success("Fase actualizada")
                            st.rerun()
                            
                if st.button("🗑️ Eliminar Fase", key=f"del_ph_{phase_to_edit}"):
                    if can_delete:
                        data.delete_phase(phase_to_edit)
                        st.warning("Fase eliminada.")
                        st.rerun()
                    else:
                        st.error("Permiso denegado.")

        else:
            st.info("No hay fases definidas para este proyecto.")

        # Add Phase Form
        st.divider()
        with st.expander("➕ Agregar Nueva Fase", expanded=False):
            with st.form("add_phase"):
                st.markdown("**Nueva Fase**")
                p_name = st.text_input("Nombre de Fase", placeholder="Ej: Obra Gruesa")
                c1, c2 = st.columns(2)
                start = c1.date_input("Inicio")
                end = c2.date_input("Fin")
                if st.form_submit_button("Guardar Fase", type="primary"):
                    data.add_phase(project_id, p_name, start, end)
                    st.success("Fase agregada exitosamente.")
                    st.rerun()

    with tabs[1]:
        # --- GASTOS (REAL - OC) ---
        st.subheader("Registro de Gastos (Ordenes de Compra)")
        orders = data.get_purchase_orders(project_id)
        
        if not orders.empty:
            # Stats
            total_spent = orders[orders['status'] != 'Rechazada']['total_amount'].sum()
            st.metric("Total Gastado (OC Aprob/Pend)", f"${total_spent:,.0f}")
            
            st.dataframe(
                orders[['date', 'provider_name', 'total_amount', 'status', 'description']],
                column_config={
                    "date": st.column_config.DateColumn("Fecha Emisión", format="DD/MM/YYYY"),
                    "provider_name": "Proveedor",
                    "total_amount": st.column_config.NumberColumn("Monto Total", format="$%d"),
                    "status": "Estado",
                    "description": "Detalle / Ítem"
                },
                width='stretch',
                hide_index=True
            )
        else:
            st.info("No hay ordenes de compra registradas.")
            
        st.divider()
        st.subheader("Solicitud de Compra")
        st.caption("Crea una orden pendiente para validación en Finanzas.")
        
        with st.container(border=True):
            with st.form("project_po_request"):
                c1, c2 = st.columns(2)
                provider = c1.text_input("Proveedor Sugerido")
                item_desc = c2.text_input("Ítem / Material", placeholder="Ej: 50 sacos de cemento")
                
                c3, c4 = st.columns(2)
                est_amount = c3.number_input("Monto Estimado ($)", min_value=0.0, step=1000.0)
                # Date default today
                
                if st.form_submit_button("Enviar Solicitud", type="primary"):
                     if item_desc:
                         import time
                         temp_order_num = f"REQ-{int(time.time())}"
                         # Fix: Cast types
                         data.create_purchase_order(int(project_id), provider if provider else "Por definir", datetime.now(), float(est_amount), temp_order_num, description=item_desc)
                         st.toast("Solicitud enviada a Finanzas", icon="📨")
                         st.rerun()
                     else:
                         st.error("Descripción es obligatoria.")

    with tabs[2]:
        # Comments Section
        comments = data.get_comments(project_id)
        
        st.subheader("Bitácora de Obra")
        
        if not comments.empty:
            current_user_id = st.session_state.get('user_id')
            current_role = st.session_state.get('user_role')
            
            for _, c in comments.iterrows():
                with st.chat_message("user", avatar=None): 
                    c1, c2 = st.columns([8, 1])
                    with c1:
                         st.write(f"**{c['username']}** - {c['timestamp']}")
                         st.write(c['content'])
                    
                    # Actions (Only for owner or Admin/Programmer)
                    is_owner = (str(c['user_id']) == str(current_user_id)) if current_user_id else False
                    is_owner = (str(c['user_id']) == str(current_user_id)) if current_user_id else False
                    is_admin = current_role in ['Administrador', 'Programador', 'Residente de Obra']
                    
                    if is_owner or is_admin:
                        with c2:
                            with st.popover("⚙️"):
                                st.caption("Gestionar Comentario")
                                with st.form(f"edit_comm_{c['id']}"):
                                    new_content = st.text_area("Editar", value=c['content'])
                                    if st.form_submit_button("Actualizar"):
                                        data.update_comment(c['id'], new_content)
                                        st.rerun()
                                
                                if st.button("Eliminar", key=f"del_comm_{c['id']}", type="primary"):
                                    data.delete_comment(c['id'])
                                    st.rerun()
        else:
             st.info("No hay comentarios aún.")
             
        with st.form("new_comment", clear_on_submit=True):
            txt = st.text_area("Nuevo Comentario", placeholder="Escribe aquí...")
            if st.form_submit_button("Publicar 🚀", type="primary"):
                user_id = st.session_state.get('user_id')
                if user_id: 
                    data.add_comment(project_id, user_id, txt)
                    st.rerun()
                else:
                    st.error("Error de sesión.")

    with tabs[3]:
        st.subheader("Gestión de Faenas")
        
        # New Faena Form
        with st.container(border=True):
            st.write("➕ Nueva Faena")
            with st.form("new_faena_pm"):
                f_name = st.text_input("Nombre de Faena (ej. Excavación)")
                f_sup = st.text_input("Supervisor")
                if st.form_submit_button("Crear Faena"):
                    data.add_faena(project_id, f_name, f_sup)
                    st.success("Faena creada")
                    st.rerun()

        # List Faenas
        faenas_df = data.get_faenas(project_id)
        if not faenas_df.empty:
            st.divider()
            st.write("📋 Faenas Registradas")
            
            for _, f in faenas_df.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.write(f"**{f['name']}**")
                        st.caption(f"Supervisor: {f['supervisor']}")
                    
                    with c2:
                        with st.popover("⚙️"):
                            st.write("**Gestionar Faena**")
                            with st.form(f"edit_faena_{f['id']}"):
                                u_name = st.text_input("Nombre", value=f['name'])
                                u_sup = st.text_input("Supervisor", value=f['supervisor'])
                                if st.form_submit_button("Actualizar"):
                                    data.update_faena(f['id'], u_name, u_sup)
                                    st.success("Actualizado")
                                    st.rerun()
                            
                            if st.button("Eliminar", key=f"del_faena_{f['id']}", type="primary"):
                                if can_delete:
                                    data.delete_faena(f['id'])
                                    st.warning("Faena eliminada.")
                                    st.rerun()
                                else:
                                    st.error("Solo administradores.")
        else:
            st.info("No hay faenas registradas.")

    with tabs[4]:
        # --- CONFIG & BUDGET ---
        st.subheader("Configuración y Presupuestos")
        
        c_conf, c_budg = st.columns([1, 2])
        
        with c_conf:
            with st.container(border=True):
                st.write("**Datos Generales del Proyecto**")
                
                with st.form("edit_project_config"):
                    # Core Fields
                    u_name = st.text_input("Nombre del Proyecto", value=project['name'])
                    u_desc = st.text_area("Descripción", value=project.get('description', ''))
                    
                    # Dates & Status
                    c1, c2, c3 = st.columns(3)
                    
                    try:
                         # Safe date parsing
                         d_start = pd.to_datetime(project['start_date']).date() if project.get('start_date') else datetime.now().date()
                         d_end = pd.to_datetime(project['end_date']).date() if project.get('end_date') else datetime.now().date()
                    except:
                         d_start = datetime.now().date()
                         d_end = datetime.now().date()

                    u_start = c1.date_input("Fecha Inicio", value=d_start)
                    u_end = c2.date_input("Fecha Termino", value=d_end)
                    
                    current_status = project['status'] if project['status'] in ["Activo", "Pausado", "Completado", "En Cierre"] else "Activo"
                    u_status = c3.selectbox("Estado", ["Activo", "Pausado", "Completado", "En Cierre"], index=["Activo", "Pausado", "Completado", "En Cierre"].index(current_status))
                    
                    # Budget & Geo
                    c4, c5, c6 = st.columns(3)
                    u_budget = c4.number_input("Presupuesto Oficial ($)", value=float(project.get('budget_total', 0)), step=1000000.0, format="%.0f")
                    u_lat = c5.number_input("Latitud", value=float(project.get('latitude', -33.4489)), format="%.6f")
                    u_lon = c6.number_input("Longitud", value=float(project.get('longitude', -70.6693)), format="%.6f")
                    
                    if st.form_submit_button("💾 Guardar Cambios Globales", type="primary"):
                        data.update_project(project_id, u_name, u_desc, u_budget, u_start, u_end, u_status, u_lat, u_lon)
                        st.success("Proyecto actualizado exitosamente.")
                        st.rerun()
        
        with c_budg:
             with st.container(border=True):
                 st.write("**Control Presupuestario**")
                 
                 # Fetch Budget Items
                 budget_items = data.get_budget_items(project_id)
                 
                 # Calc Totals
                 # Calc Totals
                 global_budget = float(project.get('budget_total', 0))
                 itemized_budget = budget_items['estimated_amount'].sum() if not budget_items.empty else 0
                 
                 # Calc Actuals
                 actual_expenses = data.get_purchase_orders(project_id)
                 total_actual = actual_expenses[actual_expenses['status']!='Rechazada']['total_amount'].sum() if not actual_expenses.empty else 0
                 
                 # Metrics
                 st.markdown("##### 💵 Ejecución Financiera (Caja)")
                 m1, m2, m3 = st.columns(3)
                 m1.metric("Presupuesto Oficial", f"${global_budget:,.0f}", help="Presupuesto Global definido en la creación del proyecto")
                 m2.metric("Gasto Real (OC)", f"${total_actual:,.0f}", help="Suma de Órdenes de Compra (No Rechazadas)")
                 
                 diff_cash = global_budget - total_actual
                 m3.metric("Saldo Disponible", f"${diff_cash:,.0f}", delta_color="normal" if diff_cash >= 0 else "inverse", help="Presupuesto Oficial - Gasto Real")
                 
                 st.progress(min(total_actual / global_budget, 1.0) if global_budget > 0 else 0)
                 
                 st.divider()
                 st.markdown("##### 🧩 Planificación (Asignación)")
                 
                 c_plan1, c_plan2, c_plan3 = st.columns(3)
                 c_plan1.metric("Asignado en Ítems", f"${itemized_budget:,.0f}", help="Suma de los ítems creados abajo")
                 
                 diff_alloc = global_budget - itemized_budget
                 c_plan2.metric("Por Asignar", f"${diff_alloc:,.0f}", help="Presupuesto Oficial - Asignado en Ítems", delta_color="off")
                 
                 alloc_pct = (itemized_budget / global_budget * 100) if global_budget > 0 else 0
                 c_plan3.metric("% Asignado", f"{alloc_pct:.1f}%")

                 if diff_alloc < 0:
                     st.warning(f"⚠️ Has asignado ${abs(diff_alloc):,.0f} más que el presupuesto oficial.")
                 
                 st.divider()
                 st.write("📋 Ítems de Presupuesto")
                 
                 if not budget_items.empty:
                     # Row-based Management
                     st.dataframe(
                         budget_items[['item_name', 'category', 'estimated_amount']],
                         column_config={
                             "item_name": "Ítem",
                             "category": "Categoría",
                             "estimated_amount": st.column_config.NumberColumn("Estimado", format="$%d")
                         },
                         width='stretch',
                         hide_index=True
                     )
                     
                     st.divider()
                     st.write("🛠️ Gestión de Ítems")
                     
                     for _, row in budget_items.iterrows():
                        with st.container(border=True):
                            c1, c2 = st.columns([4, 1])
                            with c1:
                                st.write(f"**{row['item_name']}** ({row['category']})")
                                st.caption(f"Monto: ${row['estimated_amount']:,.0f}")
                            
                            with c2:
                                with st.popover("⚙️"):
                                    st.write("Editar Ítem")
                                    with st.form(f"ed_bud_{row['id']}"):
                                         u_name = st.text_input("Nombre", value=row['item_name'])
                                         u_cat = st.selectbox("Categoría", ["Materiales", "Mano de Obra", "Subcontratos", "Equipos", "General"], index=["Materiales", "Mano de Obra", "Subcontratos", "Equipos", "General"].index(row['category']) if row['category'] in ["Materiales", "Mano de Obra", "Subcontratos", "Equipos", "General"] else 0)
                                         u_amt = st.number_input("Monto", value=float(row['estimated_amount']))
                                         
                                         if st.form_submit_button("Actualizar"):
                                             data.update_budget_item(row['id'], u_name, u_cat, u_amt)
                                             st.rerun()
                                             
                                    if st.button("Eliminar", key=f"del_b_{row['id']}", type="primary"):
                                        if can_delete:
                                            data.delete_budget_item(row['id'])
                                            st.rerun()
                                        else:
                                            st.error("No tienes permisos.")
                 else:
                     st.info("No hay presupuesto definido.")

                 with st.expander("➕ Agregar Ítem Presupuestario"):
                     with st.form("new_budget_item"):
                         c1, c2 = st.columns(2)
                         b_name = c1.text_input("Nombre Ítem")
                         b_cat = c2.selectbox("Categoría", ["Materiales", "Mano de Obra", "Subcontratos", "Equipos", "General"])
                         b_amt = st.number_input("Monto Estimado ($)", min_value=0)
                         
                         if st.form_submit_button("Agregar"):
                             if b_name and b_amt > 0:
                                 data.create_budget_item(project_id, b_name, b_cat, b_amt)
                                 st.success("Agregado")
                                 st.rerun()

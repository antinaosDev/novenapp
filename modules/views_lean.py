import streamlit as st
from modules import ui
import textwrap

def render_lean():
    # --- Backend & Imports ---
    from modules import lean, data
    import pandas as pd
    from datetime import datetime
    import plotly.express as px

    st.caption("Planificación y Control de Producción")
    st.title("Lean Construction Plan")
    
    # --- Reports Header ---
    c_head, c_rep = st.columns([2, 1])
    with c_rep:
       with st.popover("📄 Exportar Reportes"):
           st.write("**Planificación Semanal**")
           if st.button("Generar Reporte de Planificación"):
               import matplotlib.pyplot as plt
               from modules import reports_gen, lean
               
               # Fetch Data (re-fetch inside to ensure clean context if needed, though we have tasks_df outside scope?)
               # Accessing tasks_df from outer scope might be risky if not defined yet.
               # Let's rely on session state project ID
               pid = st.session_state.get('lean_project_id')
               tasks = lean.get_tasks(pid)
               
               if not tasks.empty:
                   # Calculate PPC
                   from datetime import datetime
                   now = datetime.now()
                   active = tasks[~((tasks['status'] == 'Completado') & ( pd.to_datetime(tasks['end_date']) < pd.to_datetime(f"{now.year}-{now.month}-01") ))]
                   ppc_val = lean.get_ppc(active)
                   
                   sections = []
                   sections.append({
                       "type": "text",
                       "title": "Estado del Plan",
                       "content": f"El Porcentaje de Plan Completado (PPC) actual es de {ppc_val}%. Se tienen {len(active)} actividades en el tablero de gestión."
                   })
                   
                   # Chart: Kanban Status
                   status_counts = active['status'].value_counts()
                   fig1, ax1 = plt.subplots(figsize=(6, 4))
                   status_counts.plot(kind='bar', color=['#9ca3af', '#3b82f6', '#ef4444', '#22c55e'], ax=ax1)
                   ax1.set_title("Estado de Tareas Activas")
                   plt.tight_layout()
                   sections.append({"type": "plot", "content": fig1, "title": "Tablero Kanban"})
                   
                   # Table
                   sections.append({
                       "type": "table",
                       "title": "Tareas Activas",
                       "content": active[['name', 'status', 'start_date', 'end_date']]
                   })
                   
                   pdf_bytes = reports_gen.generate_pdf_report("Reporte Lean Construction", sections)
                   st.session_state['last_lean_pdf'] = pdf_bytes
               else:
                   st.warning("Sin datos para generar reporte.")
               
           if 'last_lean_pdf' in st.session_state:
               st.download_button("📥 Descargar PDF", st.session_state['last_lean_pdf'], file_name="lean_report.pdf", mime="application/pdf")
               
           # Excel
           st.write("**Plan de Trabajo**")
           pid = st.session_state.get('lean_project_id')
           tasks_all = lean.get_tasks(pid)
           if not tasks_all.empty:
                from modules import reports_gen
                xls = reports_gen.generate_excel({"Plan de Trabajo": tasks_all})
                st.download_button("📊 Descargar Excel", xls, file_name="plan_lean.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # 1. Project Selector
    projects = data.get_projects()
    if projects.empty:
        st.warning("No hay proyectos activos. Cree uno en 'Proyectos' para comenzar.")
        return

    # Helper to format project names
    proj_map = dict(zip(projects['id'], projects['name']))
    
    # Use session state to remember selection
    if 'lean_project_id' not in st.session_state:
        st.session_state['lean_project_id'] = projects['id'].iloc[0]

    p_col, _ = st.columns([1, 2])
    with p_col:
        project_id = st.selectbox(
            "Seleccionar Proyecto", 
            projects['id'], 
            format_func=lambda x: proj_map.get(x, x),
            key='lean_project_sel'
        )

    st.divider()

    # 2. Fetch Data
    tasks_df = lean.get_tasks(project_id)
    
    # 3. Filtering Logic
    if not tasks_df.empty:
        # Ensure date columns are datetime
        tasks_df['end_date'] = pd.to_datetime(tasks_df['end_date'])
        tasks_df['start_date'] = pd.to_datetime(tasks_df['start_date'])
        
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        
        # ACTIVE: Not Done OR (Done AND Finished in Current Month)
        # Using boolean indexing
        is_done = tasks_df['status'] == 'Completado'
        in_current_month = (tasks_df['end_date'].dt.month == current_month) & (tasks_df['end_date'].dt.year == current_year)
        
        active_df = tasks_df[(~is_done) | (is_done & in_current_month)].copy()
        
        # HISTORICAL: Done AND Finished BEFORE Current Month
        history_df = tasks_df[is_done & ~in_current_month].copy()
    else:
        active_df = pd.DataFrame()
        history_df = pd.DataFrame()

    # 4. KPI Calculation (Based on Active Plan)
    ppc = lean.get_ppc(active_df)
    
    # --- UI Layout ---
    tabs = st.tabs(["🚀 Planificación Activa", "📜 Historial & Métricas"])

    # --- TAB 1: ACTIVE PLAN ---
    with tabs[0]:
        # Header Metrics
        c_ppc, c_total = st.columns(2)
        with c_ppc:
            with st.container(border=True):
                st.metric("PPC Semanal (Proyectado)", f"{ppc}%", delta="Meta: 85%")
                st.progress(ppc / 100 if ppc <= 100 else 1.0)
        with c_total:
             with st.container(border=True):
                st.metric("Tareas Activas", len(active_df), help="Pendientes + Terminadas este mes")

        # Create Task Form
        with st.expander("➕ Nueva Tarea de Planificación", expanded=False):
            with st.form("new_task_form"):
                st.write("**Agregar actvidad al plan**")
                c1, c2 = st.columns(2)
                name = c1.text_input("Nombre de la Tarea / Partida")
                status = c2.selectbox("Estado Inicial", ["Por Hacer", "En Curso", "Bloqueado", "Completado"])
                start = c1.date_input("Inicio")
                end = c2.date_input("Fin")
                
                if st.form_submit_button("Crear Tarea", type="primary"):
                    if name:
                        lean.create_task(project_id, name, start, end, status)
                        st.toast("Tarea creada.", icon="📌")
                        st.rerun()
                    else:
                        st.warning("El nombre es obligatorio.")

        st.markdown("### Tablero Kanban")
        c_todo, c_prog, c_block, c_done = st.columns(4)
        
        stat_cols = {
            "Por Hacer": (c_todo, "gray"),
            "En Curso": (c_prog, "blue"),
            "Bloqueado": (c_block, "red"),
            "Completado": (c_done, "green")
        }

        if not active_df.empty:
            for s_key, (col, color) in stat_cols.items():
                with col:
                    st.markdown(f":{color}[**{s_key}**]")
                    filtered = active_df[active_df['status'] == s_key]
                    
                    for _, row in filtered.iterrows():
                        with st.container(border=True):
                            st.write(f"**{row['name']}**")
                            # Format date nicely
                            d_str = row['end_date'].strftime('%d/%m')
                            st.caption(f"🏁 {d_str}")
                            
                            # Move Logic
                            curr_idx = ["Por Hacer", "En Curso", "Bloqueado", "Completado"].index(s_key)
                            new_st = st.selectbox(
                                "Mover", 
                                ["Por Hacer", "En Curso", "Bloqueado", "Completado"],
                                key=f"mv_{row['id']}",
                                index=curr_idx,
                                label_visibility="collapsed"
                            )
                            
                            if new_st != row['status']:
                                lean.update_task_status(row['id'], new_st)
                                st.rerun()
                                
                            with st.popover("⚙️"):
                                with st.form(f"ed_{row['id']}"):
                                    n_name = st.text_input("Editar Nombre", value=row['name'])
                                    if st.form_submit_button("Guardar"):
                                        lean.update_task_details(row['id'], n_name)
                                        st.rerun()
                                if st.button("Eliminar", key=f"dl_{row['id']}"):
                                    lean.delete_task(row['id'])
                                    st.rerun()
                                    
        else:
            st.info("No hay tareas activas en este periodo.")

    # --- TAB 2: HISTORY ---
    with tabs[1]:
        st.subheader("Registro Histórico")
        st.caption(f"Tareas completadas anteriores al mes actual ({len(history_df)})")
        
        if not history_df.empty:
            # Table
            st.dataframe(
                history_df[['name', 'start_date', 'end_date', 'status']],
                column_config={
                    "name": "Tarea",
                    "start_date": st.column_config.DateColumn("Fecha Inicio", format="DD/MM/YYYY"),
                    "end_date": st.column_config.DateColumn("Fecha Fin", format="DD/MM/YYYY"),
                    "status": "Estado Final"
                },
                width='stretch',
                hide_index=True
            )
            
            # Simple Chart: Tasks per Month
            # Chart: Tasks per Month
            # Convert to period for better sorting/filling if needed, but string YYYY-MM is usually fine.
            history_df['month_year'] = history_df['end_date'].dt.strftime('%Y-%m')
            counts = history_df.groupby('month_year').size().reset_index(name='count')
            
            fig = px.bar(
                counts, 
                x='month_year', 
                y='count', 
                text='count',
                title="Evolución de Tareas Completadas", 
                labels={'month_year': 'Mes', 'count': 'Tareas'},
                color_discrete_sequence=['#2E86C1']
            )
            
            fig.update_layout(
                xaxis_title="Mes",
                yaxis_title="Cantidad de Tareas",
                xaxis=dict(type='category'), # Force categorical to avoid weird time scaling
                showlegend=False
            )
            fig.update_traces(textposition='outside')
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay historial de tareas antiguas.")

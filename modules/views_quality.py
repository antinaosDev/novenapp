import streamlit as st
import textwrap

def render_quality():
    # --- Backend & Imports ---
    from modules import quality, data
    import pandas as pd
    from datetime import datetime

    st.caption("Gestión de Calidad & Laboratorio")
    st.title("Autocontrol y Bitácora")
    
    # 1. Project Selector
    # Permissions
    can_delete = st.session_state.get('user_role') in ['Administrador', 'Residente de Obra', 'Programador']
    
    projects = data.get_projects()
    if projects.empty:
        st.warning("No hay proyectos activos.")
        return

    if 'qual_project_id' not in st.session_state:
        st.session_state['qual_project_id'] = projects['id'].iloc[0]

    p_col, _ = st.columns([1, 2])
    with p_col:
        project_id = st.selectbox(
            "Seleccionar Proyecto", 
            projects['id'], 
            format_func=lambda x: projects[projects['id']==x]['name'].values[0],
            key='qual_project_sel'
        )
    
    # --- Reports Header ---
    c_head, c_rep = st.columns([2, 1])
    with c_rep:
       with st.popover("📄 Exportar Reportes"):
           st.write("**Informe de Calidad**")
           if st.button("Generar Reporte PDF"):
               import matplotlib.pyplot as plt
               from modules import reports_gen
               
               # Fetch Data
               logs_pdf = quality.get_logs(project_id)
               lab_pdf = quality.get_lab_tests(project_id)
               
               # Calculate KPIs
               total_logs = len(logs_pdf)
               total_tests = len(lab_pdf)
               pass_rate = 0
               if total_tests > 0:
                   pass_count = len(lab_pdf[lab_pdf['result'] == 'Aprobado'])
                   pass_rate = (pass_count / total_tests) * 100
               
               sections = []
               
               # 1. Executive Summary
               sections.append({
                   "type": "text",
                   "title": "Resumen Ejecutivo",
                   "content": f"A la fecha ({datetime.now().strftime('%d/%m/%Y')}), se registran {total_logs} entradas en el libro de obra y {total_tests} ensayos de laboratorio controlados. La tasa de aprobación global de ensayos es del {pass_rate:.1f}%."
               })
               
               # 2. Charts
               if not lab_pdf.empty:
                   # Pie: Approval Rate
                   res_counts = lab_pdf['result'].value_counts()
                   fig1, ax1 = plt.subplots(figsize=(6, 4))
                   colors = {'Aprobado':'#10b981', 'Rechazado':'#ef4444', 'Pendiente':'#f59e0b'}
                   c_list = [colors.get(x, '#9ca3af') for x in res_counts.index]
                   ax1.pie(res_counts, labels=res_counts.index, autopct='%1.1f%%', colors=c_list)
                   ax1.set_title("Resultados de Ensayos")
                   sections.append({"type": "plot", "title": "Calidad de Materiales", "content": fig1})
                   
                   # Bar: Tests by Type
                   type_counts = lab_pdf['test_type'].value_counts()
                   fig2, ax2 = plt.subplots(figsize=(7, 4))
                   type_counts.plot(kind='bar', color='#3b82f6', ax=ax2)
                   ax2.set_title("Distribución por Tipo de Ensayo")
                   plt.tight_layout()
                   sections.append({"type": "plot", "title": "Tipología de Control", "content": fig2})

               # 3. Tables
               if not logs_pdf.empty:
                   logs_disp = logs_pdf[['date', 'title', 'inspector_name']].head(15).copy()
                   logs_disp.columns = ['Fecha', 'Asunto', 'Inspector']
                   # Format date if string or datetime
                   sections.append({
                       "type": "table",
                       "title": "Últimos Registros Bitácora",
                       "content": logs_disp
                   })
                   
               if not lab_pdf.empty:
                   lab_disp = lab_pdf[['test_date', 'test_type', 'result', 'observation']].head(15).copy()
                   lab_disp.columns = ['Fecha Muestreo', 'Ensayo', 'Resultado', 'Obs.']
                   # Ensure date format
                   lab_disp['Fecha Muestreo'] = pd.to_datetime(lab_disp['Fecha Muestreo']).dt.strftime('%d/%m/%Y')
                   sections.append({
                       "type": "table",
                       "title": "Últimos Ensayos",
                       "content": lab_disp
                   })
               
               pdf_bytes = reports_gen.generate_pdf_report("Reporte de Calidad y Bitácora", sections)
               st.session_state['last_qual_pdf'] = pdf_bytes
               
           if 'last_qual_pdf' in st.session_state:
               st.download_button("📥 Descargar PDF", st.session_state['last_qual_pdf'], file_name="calidad_reporte.pdf", mime="application/pdf")
    
    st.divider()

    # --- TABS ---
    tab_book, tab_lab = st.tabs(["📖 Libro de Obra", "🧪 Laboratorio & Ensayos"])

    # --- TAB 1: BOOK (BITACORA) ---
    with tab_book:
        st.subheader("Registro de Bitácora")
        
        # Helper: Display Informal Comments (Bitácora Simple from Projects)
        try:
            comments = data.get_comments(project_id)
            if not comments.empty:
                with st.expander("💬 Notas y Comentarios (Vista Proyectos)", expanded=True):
                    st.caption("Estos registros provienen de la pestaña 'Bitácora' en la sección de Proyectos.")
                    for _, c in comments.iterrows():
                        with st.chat_message("user"): 
                            st.write(f"**{c['username']}** - {c['timestamp']}")
                            st.write(c['content'])
            else:
                # Only show info if strict quality logs are also empty later, or just keep it clean
                pass
        except Exception as e:
            st.error(f"Error cargando comentarios de proyecto: {e}")

        st.divider()

        # New Log Form
        with st.expander("➕ Nueva Entrada Bitácora Técnica (Formal)", expanded=False):
            with st.container(border=True):
                with st.form("new_log_form"):
                    st.markdown("**Registrar en Libro de Obras**")
                    c1, c2 = st.columns(2)
                    title = c1.text_input("Título / Asunto")
                    
                    c3, c4 = st.columns(2)
                    role_opts = ["Residente de Obra", "Inspector Técnico (ITO)", "Jefe de Terreno", "Prevencionista de Riesgos", "Topografía"]
                    inspector = c3.selectbox("Rol / Firma", role_opts)
                    signer = c4.text_input("Nombre del Firmante")
                    
                    desc = st.text_area("Detalle / Observaciones", height=100)
                    
                    if st.form_submit_button("Firmar y Guardar", type="primary"):
                        if title and desc and signer:
                            quality.create_log(project_id, title, desc, inspector, signer)
                            st.toast("Entrada registrada.", icon="✍️")
                            st.rerun()
                        else:
                            st.warning("Título, Detalle y Nombre son obligatorios.")

        # Fetch Logs
        logs_df = quality.get_logs(project_id)
        
        if logs_df.empty:
            if not comments.empty:
                 st.caption("No hay registros formales, pero existen notas informales visualizadas arriba.")
            else:
                 st.info("No hay registros en bitácora para este proyecto.")
        else:
            for idx, row in logs_df.iterrows():
                is_ito = "ITO" in row['inspector_name']
                role_icon = "📋" if is_ito else "👷‍♂️"
                
                with st.container(border=True):
                    c_head, c_act = st.columns([0.9, 0.1])
                    with c_head:
                        st.markdown(f"**{row['title']}**")
                        signer_display = f"{row['signer_name']} ({row['inspector_name']})" if row.get('signer_name') else row['inspector_name']
                        st.caption(f"{role_icon} {signer_display} • Folio #{row['id']} • {row['date']}")
                    with c_act:
                        # Actions Popover
                        with st.popover("⚙️"):
                            with st.form(f"edit_log_{row['id']}"):
                                n_title = st.text_input("Título", value=row['title'])
                                n_desc = st.text_area("Detalle", value=row['description'])
                                n_role = st.selectbox("Rol", role_opts, index=role_opts.index(row['inspector_name']) if row['inspector_name'] in role_opts else 0)
                                n_signer = st.text_input("Nombre Firmante", value=row.get('signer_name', ''))
                                
                                if st.form_submit_button("Actualizar"):
                                    quality.update_log(row['id'], n_title, n_desc, n_role, n_signer)
                                    st.toast("Entrada actualizada")
                                    st.rerun()
                            
                            if st.button("Eliminar", key=f"del_log_{row['id']}"):
                                if can_delete:
                                    quality.delete_log(row['id'])
                                    st.rerun()
                                else:
                                    st.error("No autorizado.")
                                
                    st.write(row['description'])

    # --- TAB 2: LAB TESTS ---
    with tab_lab:
        st.subheader("Control de Ensayos")
        
        # Stats
        lab_df = quality.get_lab_tests(project_id)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Ensayos", len(lab_df))
        with c2:
            ok_count = len(lab_df[lab_df['result'] == 'Aprobado']) if not lab_df.empty else 0
            st.metric("Aprobados", ok_count)
        with c3:
            pend_count = len(lab_df[lab_df['result'] == 'Pendiente']) if not lab_df.empty else 0
            st.metric("Pendientes", pend_count)
            
        st.divider()

        # --- Analytics ---
        st.subheader("Indicadores de Calidad")
        c_chart1, c_chart2 = st.columns(2)
        
        with c_chart1:
            # Pass Rate
            import plotly.express as px
            if not lab_df.empty:
                res_counts = lab_df['result'].value_counts().reset_index()
                res_counts.columns = ['Result', 'Count']
                fig_res = px.pie(res_counts, values='Count', names='Result', hole=0.5, title="Tasa de Aprobación", color='Result', color_discrete_map={'Aprobado':'#10b981', 'Rechazado':'#ef4444', 'Pendiente':'#f59e0b'})
                fig_res.update_layout(height=300, margin=dict(t=30, l=10, r=10, b=10))
                st.plotly_chart(fig_res, width='stretch')
            else:
                 st.info("Sin datos de ensayos.")
                 
        with c_chart2:
            # Tests by Type
            if not lab_df.empty:
                type_counts = lab_df['test_type'].value_counts().reset_index()
                fig_types = px.bar(type_counts, x='test_type', y='count', title="Ensayos por Tipo", color='test_type')
                fig_types.update_layout(height=300, margin=dict(t=30, l=10, r=10, b=10), showlegend=False)
                st.plotly_chart(fig_types, width='stretch')
            else:
                 st.info("Sin datos para distribución.")
        
        st.divider()
        
        # New Test Form
        with st.expander("🧪 Registrar Nuevo Ensayo"):
            with st.form("new_test_form"):
                 c1, c2 = st.columns(2)
                 t_type = c1.selectbox("Tipo de Ensayo", ["Hormigón (Compresión)", "Mecánica de Suelos", "Acero (Tracción)", "Asfalto", "Topografía", "Otro"])
                 t_date = c2.date_input("Fecha de Muestreo")
                 
                 c3, c4 = st.columns(2)
                 t_res = c3.selectbox("Resultado", ["Pendiente", "Aprobado", "Rechazado"])
                 t_obs = c4.text_input("Observación / ID Muestra")
                 
                 if st.form_submit_button("Guardar Ensayo"):
                     quality.create_lab_test(project_id, t_type, t_date, t_res, t_obs)
                     st.toast("Ensayo registrado", icon="🧪")
                     st.rerun()

        # Lab Table with Actions
        if lab_df.empty:
             st.info("No hay ensayos registrados.")
        else:
             st.dataframe(
                 lab_df,
                 column_config={
                     "test_type": "Ensayo",
                     "test_date": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                     "result": st.column_config.SelectboxColumn("Resultado", options=["Pendiente", "Aprobado", "Rechazado"], required=True),
                     "observation": "Observación"
                 },
                 hide_index=True,
                 width='stretch'
             )
             
             # Manage Tests
             st.caption("Gestionar Ensayos Existentes")
             sel_test = st.selectbox("Seleccionar Ensayo ID", lab_df['id'].tolist(), format_func=lambda x: f"#{x} - {lab_df[lab_df['id']==x]['test_type'].values[0]}")
             if sel_test:
                 lab_filtered = lab_df[lab_df['id'] == sel_test]
                 if lab_filtered.empty:
                     st.error("Ensayo no encontrado.")
                 else:
                     row = lab_filtered.iloc[0]
                     with st.form(f"edit_test_{sel_test}"):
                          c1, c2 = st.columns(2)
                          u_type = c1.selectbox("Tipo", ["Hormigón (Compresión)", "Mecánica de Suelos", "Acero (Tracción)", "Asfalto", "Topografía", "Otro"], index=["Hormigón (Compresión)", "Mecánica de Suelos", "Acero (Tracción)", "Asfalto", "Topografía", "Otro"].index(row['test_type']) if row['test_type'] in ["Hormigón (Compresión)", "Mecánica de Suelos", "Acero (Tracción)", "Asfalto", "Topografía", "Otro"] else 0)
                          u_res = c2.selectbox("Resultado", ["Pendiente", "Aprobado", "Rechazado"], index=["Pendiente", "Aprobado", "Rechazado"].index(row['result']))
                          u_obs = st.text_input("Observación", value=row.get('observation', ''))
                          if st.form_submit_button("Actualizar Ensayo"):
                              quality.update_lab_test(sel_test, u_type, pd.to_datetime(row['test_date']), u_res, u_obs)
                              st.rerun()
                   
                     if st.button("Eliminar Ensayo", key=f"del_test_{sel_test}"):
                         quality.delete_lab_test(sel_test)
                         st.rerun()

import streamlit as st
import textwrap

def render_compliance():
    # --- Backend & Imports ---
    from modules import compliance, data
    import pandas as pd
    from datetime import datetime
    
    st.caption("Control Laboral y Documental")
    st.title("Subcontratos y Compliance")
    
    # Permissions
    can_delete = st.session_state.get('user_role') in ['Administrador', 'Residente de Obra', 'Programador']
    
    # --- Reports Header ---
    c_head, c_rep = st.columns([2, 1])
    with c_rep:
       with st.popover("📄 Exportar Reportes"):
           st.write("**Empresas Colaboradoras**")
           if st.button("Generar Reporte PDF"):
               import matplotlib.pyplot as plt
               from modules import reports_gen, compliance
               
               # Fetch Current Data
               pid = st.session_state.get('comp_project_id')
               subs_data = compliance.get_subcontractors(pid)
               stats_data = compliance.get_compliance_stats(pid)
               
               sections = []
               
               # 1. Summary
               sections.append({
                   "type": "text", 
                   "title": "Control de Subcontratos", 
                   "content": f"Se registran {len(subs_data)} empresas colaboradoras. Existen {stats_data['blocked']} empresas bloqueadas y {stats_data['pending_f30']} documentos pendientes de regularización."
               })
               
               # 2. Charts
               if not subs_data.empty:
                    # Status Pie
                    status_counts = subs_data['status'].value_counts()
                    fig1, ax1 = plt.subplots(figsize=(6, 4))
                    ax1.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', colors=['#34d399', '#ef4444', '#fbbf24'])
                    ax1.set_title("Estado de Empresas")
                    sections.append({"type": "plot", "content": fig1, "title": "Distribución Contratistas"})
                    
                    # Docs Bar
                    fig2, ax2 = plt.subplots(figsize=(6, 4))
                    cats = ['Vigente', 'Por Vencer', 'Vencido']
                    vals = [stats_data.get('chart_vigente',0), stats_data.get('chart_por_vencer',0), stats_data.get('chart_vencido',0)]
                    ax2.bar(cats, vals, color='#10b981')
                    ax2.set_title("Estado Documentación")
                    sections.append({"type": "plot", "content": fig2, "title": "Cumplimiento Documental"})

               # 3. Table
               sections.append({
                   "type": "table",
                   "title": "Listado de Empresas",
                   "content": subs_data[['name', 'rut', 'specialty', 'status']]
               })
               
               pdf_bytes = reports_gen.generate_pdf_report("Informe de Compliance", sections)
               st.session_state['last_comp_pdf'] = pdf_bytes
               
           if 'last_comp_pdf' in st.session_state:
               st.download_button("📥 Descargar PDF", st.session_state['last_comp_pdf'], file_name="compliance_report.pdf", mime="application/pdf")

           # Excel
           st.write("**Datos Compliance**")
           pid = st.session_state.get('comp_project_id')
           subs_ex = compliance.get_subcontractors(pid)
           if not subs_ex.empty:
               from modules import reports_gen
               xls = reports_gen.generate_excel({"Subcontratos": subs_ex})
               st.download_button("📊 Descargar Excel", xls, file_name="compliance_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # 1. Project Selector
    projects = data.get_projects()
    if projects.empty:
        st.warning("No hay proyectos activos.")
        return

    # Use session state to remember selection
    if 'comp_project_id' not in st.session_state:
        st.session_state['comp_project_id'] = projects['id'].iloc[0]

    p_col, _ = st.columns([1, 2])
    with p_col:
        project_id = st.selectbox(
            "Seleccionar Proyecto", 
            projects['id'], 
            format_func=lambda x: projects[projects['id']==x]['name'].values[0],
            key='comp_project_sel'
        )
    
    st.divider()

    # New Subcontractor Form
    with st.expander("➕ Nuevo Subcontratista", expanded=False):
        with st.container(border=True):
            with st.form("new_sub_form"):
                st.write("**Registrar Empresa**")
                c1, c2, c3 = st.columns(3)
                name = c1.text_input("Razón Social")
                rut = c2.text_input("RUT")
                specialty = c3.text_input("Especialidad (Ej: Estucturas)")
                
                c4, c5, c6 = st.columns(3)
                rep = c4.text_input("Representante Legal")
                email = c5.text_input("Email Contacto")
                phone = c6.text_input("Teléfono")
                
                if st.form_submit_button("Registrar Empresa", type="primary"):
                    if name and rut:
                        compliance.create_subcontractor(project_id, name, rut, email, phone, specialty, rep)
                        st.toast("Subcontratista registrado.", icon="✅")
                        st.rerun()
                    else:
                        st.warning("Razón Social y RUT son obligatorios.")

    # Fetch Data
    subs_df = compliance.get_subcontractors(project_id)
    stats = compliance.get_compliance_stats(project_id)

    # Stats (Cards)
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.metric("Subcontratistas", len(subs_df), help="Total de empresas en este proyecto")
    with c2:
        with st.container(border=True):
            st.metric("Docs Pendientes", stats['pending_f30'], delta_color="inverse", help="Documentos vencidos o faltantes")
    with c3:
        with st.container(border=True):
            st.metric("Pagos Bloqueados", len(subs_df[subs_df['status'] == 'Bloqueado']) if not subs_df.empty else 0, delta_color="inverse", help="Empresas con prohibición de pago")
    st.divider()

    # --- Analytics & Charts ---
    st.subheader("Estado de Cumplimiento")
    c_chart1, c_chart2 = st.columns(2)
    
    with c_chart1:
        # Status Pie
        import plotly.express as px
        if not subs_df.empty:
             status_counts = subs_df['status'].value_counts().reset_index()
             status_counts.columns = ['status', 'count']
             fig_status = px.pie(status_counts, values='count', names='status', hole=0.6, title="Estado de Empresas", color_discrete_sequence=px.colors.qualitative.Set2)
             fig_status.update_layout(height=300, margin=dict(t=30, l=10, r=10, b=10))
             st.plotly_chart(fig_status, width='stretch')
        else:
             st.info("No hay datos para gráfico de estado.")

    with c_chart2:
        # Document Stats (Real)
        doc_stats = pd.DataFrame({
            'Estado': ['Vigente', 'Por Vencer (<30 días)', 'Vencido/Pendiente'],
            'Cantidad': [stats.get('chart_vigente', 0), stats.get('chart_por_vencer', 0), stats.get('chart_vencido', 0)]
        })
        
        # Only show if there is data
        total_docs = stats['chart_vigente'] + stats['chart_por_vencer'] + stats['chart_vencido']
        
        if total_docs > 0:
            fig_docs = px.bar(doc_stats, x='Estado', y='Cantidad', color='Estado', title="Estado Documentación (Global)", 
                              color_discrete_map={'Vencido/Pendiente':'#ef4444', 'Vigente':'#10b981', 'Por Vencer (<30 días)':'#f59e0b'})
            fig_docs.update_layout(height=300, margin=dict(t=30, l=10, r=10, b=10), showlegend=False)
            st.plotly_chart(fig_docs, width='stretch')
        else:
            st.info("No hay documentos registrados para analizar.")
        
    st.divider()

    # --- List & Management ---
    with st.container(border=True):
        st.subheader(f"Listado de Empresas ({len(subs_df)})")

        if subs_df.empty:
            st.info("No hay subcontratistas registrados en este proyecto.")
        else:
            st.dataframe(
                subs_df[['name', 'rut', 'specialty', 'contact_email', 'status']],
                column_config={
                    "name": "Razón Social",
                    "rut": "RUT",
                    "specialty": "Especialidad",
                    "contact_email": "Email",
                    "status": st.column_config.SelectboxColumn(
                        "Estado Global",
                        options=["Activo", "Bloqueado", "Pago Autorizado"],
                        required=True,
                        width="medium"
                    )
                },
                hide_index=True,
                width='stretch'
            )
            
            st.markdown("### Gestión de Empresa")
            
            # Selector
            sub_id = st.selectbox(
                "Seleccionar para gestionar:", 
                subs_df['id'].tolist(), 
                format_func=lambda x: f"{subs_df[subs_df['id']==x]['rut'].values[0]} | {subs_df[subs_df['id']==x]['name'].values[0]}"
            )
            
            if sub_id:
                sel_row = subs_df[subs_df['id'] == sub_id].iloc[0]
                
                st.info(f"Gestionando: **{sel_row['name']}**")
                
                t_info, t_docs = st.tabs(["📝 Datos Generales", "📂 Documentación Compliance"])
                
                # TAB 1: General Info
                with t_info:
                    with st.form(f"edit_sub_{sub_id}"):
                         c1, c2 = st.columns(2)
                         e_name = c1.text_input("Razón Social", value=sel_row['name'])
                         e_rut = c2.text_input("RUT", value=sel_row['rut'])
                         
                         c3, c4 = st.columns(2)
                         e_spec = c3.text_input("Especialidad", value=sel_row.get('specialty', ''))
                         e_rep = c4.text_input("Representante", value=sel_row.get('representative', ''))
                         
                         c5, c6 = st.columns(2)
                         e_email = c5.text_input("Email", value=sel_row.get('contact_email', ''))
                         e_phone = c6.text_input("Teléfono", value=sel_row.get('contact_phone', ''))
                         
                         st.divider()
                         curr_status = sel_row['status']
                         st_opts = ["Activo", "Bloqueado", "Pago Autorizado"]
                         e_status = st.selectbox("Estado Operativo", st_opts, index=st_opts.index(curr_status) if curr_status in st_opts else 0)
                         
                         if st.form_submit_button("Guardar Cambios"):
                             compliance.update_subcontractor(sub_id, e_name, e_rut, e_email, e_phone, e_spec, e_rep)
                             if e_status != curr_status:
                                 compliance.update_sub_status(sub_id, e_status)
                             st.toast("Datos actualizados", icon="💾")
                             st.rerun()

                    if st.button("🗑️ Eliminar Empresa", key=f"del_sub_{sub_id}"):
                        if can_delete:
                            compliance.delete_subcontractor(sub_id)
                            st.toast("Empresa eliminada", icon="🗑️")
                            st.rerun()
                        else:
                            st.error("No autorizado.")

                # TAB 2: Documents
                with t_docs:
                    st.write("**Registro de Documentos de La Empresa**")
                    
                    docs_df = compliance.get_documents(sub_id)
                    if not docs_df.empty:
                        # Ensure columns are datetime
                        docs_df['expiration_date'] = pd.to_datetime(docs_df['expiration_date'])
                        if 'last_updated' in docs_df.columns:
                            docs_df['last_updated'] = pd.to_datetime(docs_df['last_updated'])
                            disp_cols = ['document_type', 'expiration_date', 'status', 'last_updated']
                            col_conf = {
                                "document_type": "Tipo Doc",
                                "expiration_date": st.column_config.DateColumn("Vencimiento", format="DD/MM/YYYY"),
                                "status": st.column_config.SelectboxColumn("Estado", options=["Vigente", "Vencido", "Pendiente"], required=True),
                                "last_updated": st.column_config.DateColumn("Fecha Carga", format="DD/MM/YYYY")
                            }
                        else:
                            disp_cols = ['document_type', 'expiration_date', 'status']
                            col_conf = {
                                "document_type": "Tipo Doc",
                                "expiration_date": st.column_config.DateColumn("Vencimiento", format="DD/MM/YYYY"),
                                "status": st.column_config.SelectboxColumn("Estado", options=["Vigente", "Vencido", "Pendiente"], required=True)
                            }

                        st.dataframe(
                            docs_df[disp_cols],
                            column_config=col_conf,
                            hide_index=True,
                            width='stretch'
                        )
                        # Delete Doc Button (Simplification: just ID deletion)
                        d_del = st.selectbox("Eliminar Doc ID:", docs_df['id'].tolist())
                        if st.button("Borrar Documento"):
                             compliance.delete_document(d_del)
                             st.rerun()
                    else:
                        st.info("No hay documentos registrados.")
                    
                    st.divider()
                    st.write("Subir Nuevo Registro")
                    with st.form(f"add_doc_{sub_id}"):
                        c1, c2 = st.columns(2)
                        d_type = c1.selectbox("Tipo Documento", ["Cert. Antecedentes", "Cert. Cumplimiento", "Carpeta de Arranque", "Contrato Firmado", "Garantía"])
                        d_exp = c2.date_input("Fecha Vencimiento (Si aplica)")
                        d_stat = st.selectbox("Estado Documento", ["Vigente", "Pendiente", "Vencido"])
                        
                        if st.form_submit_button("Registrar Documento"):
                            compliance.create_document(sub_id, d_type, d_stat, d_exp)
                            st.toast("Documento Agregado", icon="📎")
                            st.rerun()

import streamlit as st
import pandas as pd
from modules import licitaciones, data

def render_tenders():
    # --- Backend Integration ---
    tenders_df = licitaciones.get_tenders()
    
    # Permissions
    can_delete = st.session_state.get('user_role') in ['Administrador', 'Residente de Obra', 'Programador']
    
    # Calculate Stats
    # Calculate Stats
    if not tenders_df.empty and 'status' in tenders_df.columns:
        total_active = len(tenders_df[tenders_df['status'] != 'Desierta'])
        pending_ssd = len(tenders_df[tenders_df['status'] == 'Borrador']) 
        no_resolution = len(tenders_df[tenders_df['status'] == 'Evaluacion'])
    else:
        total_active = 0
        pending_ssd = 0
        no_resolution = 0
 

    # --- Header & Stats UI (Native) ---
    c_title, c_actions = st.columns([2, 2])
    with c_title:
        st.title("Gestión de Licitaciones")
        st.caption("Administración de procesos de compra y contratos.")
        
    with c_actions:
        c_add, c_pdf = st.columns(2)
        with c_add:
            pass # Creating the column structure for the button below (form is complex, keep separate)
            
        with c_pdf:
             if st.button("📄 Generar Reporte PDF", key="btn_tenders_pdf"):
                 with st.spinner("Generando Reporte de Licitaciones..."):
                     from modules import reports_gen
                     import matplotlib.pyplot as plt
                     
                     sections = []
                     
                     # 1. KPIs
                     sections.append({
                         "type": "kpi_row",
                         "content": [
                             {"label": "Postuladas", "value": str(total_active), "sub": "En Concurso"},
                             {"label": "En Estudio", "value": str(pending_ssd), "sub": "Borradores"},
                             {"label": "Sin Resolución", "value": str(no_resolution), "sub": "Evaluación"}
                         ]
                     })
                     
                     sections.append({"type": "text", "content": " "})

                     # 2. Charts (Funnel & Donut)
                     if not tenders_df.empty:
                         # Funnel Data
                         val_counts = tenders_df['status'].value_counts().reset_index()
                         fig1, ax1 = plt.subplots(figsize=(8, 4))
                         ax1.barh(val_counts['status'], val_counts['count'], color='#3b82f6')
                         ax1.set_title("Estado de Postulaciones")
                         ax1.grid(axis='x', linestyle='--', alpha=0.3)
                         sections.append({"type": "plot", "content": fig1, "title": "Embudo de Gestión"})
                         
                         sections.append({"type": "new_page"})
                     
                     # 3. List
                     if not tenders_df.empty:
                         display_df = tenders_df[['title', 'budget_estimated', 'type', 'status']].copy()
                         display_df.columns = ['Título', 'Presupuesto', 'Tipo', 'Estado']
                         display_df['Presupuesto'] = display_df['Presupuesto'].apply(lambda x: f"${x:,.0f}".replace(',', '.'))
                         sections.append({"type": "table", "content": display_df, "title": "Detalle de Licitaciones"})
                         
                     pdf_bytes = reports_gen.generate_pdf_report("Reporte de Gestión de Licitaciones", sections)
                     
                     st.download_button("⬇️ Descargar", pdf_bytes, "Reporte_Licitaciones.pdf", "application/pdf", key="dl_ten_pdf")

    with c_actions: # Re-using for the expander to keep layout
        with c_add:
            with st.expander("➕ Crear Nueva", expanded=False):
                with st.container(border=True):
                    with st.form("new_tender_form"):
                        st.markdown("**Nueva Licitación**")
                        title = st.text_input("Título de la Licitación")
                        mp_id = st.text_input("ID Mercado Público (Opcional)", placeholder="Ej: 1234-56-LP25")
                        
                        c1, c2 = st.columns(2)
                        budget = c1.number_input("Presupuesto Estimado ($)", min_value=0, step=100000)
                        
                        # Tipo con descripción
                        tipos = ["L1 (Menor <100 UTM)", "LE (Menor >100 UTM)", "LP (Pública >1000 UTM)", "LQ (Larga)", "LR (Mayor)", "LS (Servicios)"]
                        tipo_sel = c2.selectbox("Clasificación", tipos)
                        tender_type = tipo_sel.split(" ")[0] # Extract Code like L1
    
                        projects = data.get_projects()
                        if not projects.empty:
                            project_id = st.selectbox("Proyecto Asociado", projects['id'], format_func=lambda x: projects[projects['id']==x]['name'].values[0])
                        else:
                            st.warning("No hay proyectos activos.")
                            project_id = None 
                        
                        if st.form_submit_button("Crear Licitación", type="primary"):
                            if title and project_id:
                                licitaciones.create_tender(project_id, title, budget, tender_type, mp_id)
                                st.toast("Licitación creada exitosamente!", icon="🚀")
                                st.rerun()
                            else:
                                st.error("Título y Proyecto son obligatorios.")

    # Native Metrics (Cards)
    # Native Metrics (Cards)
    m1, m2, m3 = st.columns(3)
    with m1:
        with st.container(border=True):
            st.metric("Postuladas", total_active, delta="+12%", help="Licitaciones en curso")
    with m2:
        with st.container(border=True):
            st.metric("En Estudio", pending_ssd, delta="Por Enviar", delta_color="off", help="Propuestas en preparación")
    with m3:
        with st.container(border=True):
            st.metric("Sin Resolución", no_resolution, delta="En trámite", delta_color="off", help="En proceso de evaluación")
    
    # --- Analytics Section ---
    st.subheader("Análisis de Procesos")
    c_chart1, c_chart2 = st.columns(2)
    
    with c_chart1:
         # Status Funnel
         import plotly.express as px
         if not tenders_df.empty:
             val_counts = tenders_df['status'].value_counts().reset_index()
             val_counts.columns = ['status', 'count']
             # Order logic
             order_map = {"Borrador": 1, "Activa": 2, "Evaluacion": 3, "Adjudicada": 4, "Desierta": 5}
             val_counts['order'] = val_counts['status'].map(order_map).fillna(6)
             val_counts = val_counts.sort_values('order')
             
             fig_funnel = px.funnel(val_counts, x='count', y='status', title="Embudo de Licitaciones", color='status')
             fig_funnel.update_layout(height=300, margin=dict(t=30, l=10, r=10, b=10), showlegend=False)
             st.plotly_chart(fig_funnel, width='stretch')
         else:
             st.info("Sin datos para embudo.")
             
    with c_chart2:
         # Type Distribution
         if not tenders_df.empty:
             type_counts = tenders_df['type'].value_counts().reset_index()
             fig_donut = px.pie(type_counts, values='count', names='type', hole=0.7, title="Distribución por Tipo")
             fig_donut.update_layout(height=300, margin=dict(t=30, l=10, r=10, b=10))
             st.plotly_chart(fig_donut, width='stretch')
         else:
             st.info("Sin datos para distribución.")

    st.divider()

    # --- List (Card) ---
    with st.container(border=True):
        st.subheader(f"Listado de Licitaciones ({len(tenders_df)})")
        
        if tenders_df.empty:
            st.info("No hay licitaciones registradas.")
        else:
            st.dataframe(
                tenders_df[['id', 'mercado_publico_id', 'title', 'budget_estimated', 'type', 'status', 'project_id']],
                column_config={
                    "id": st.column_config.NumberColumn("Sistema ID", format="LIC-%d", width="small"),
                    "mercado_publico_id": st.column_config.TextColumn("ID MP", width="medium"),
                    "title": "Título",
                    "budget_estimated": st.column_config.NumberColumn("Presupuesto", format="$%d"),
                    "type": st.column_config.SelectboxColumn("Tipo", width="small", options=["L1", "LE", "LP", "LQ", "LR", "LS"]),
                    "status": st.column_config.SelectboxColumn(
                        "Estado",
                        options=["Borrador", "Activa", "Evaluación", "Adjudicada", "Desierta"],
                        required=True,
                    ),
                    "project_id": "Proyecto ID"
                },
                hide_index=True,
                width='stretch'
            )

            st.caption("Selecciona una licitación para gestionar:")
            
            # Actions (Card Style)
            col_sel, col_act = st.columns([2, 2])
            with col_sel:
                selected_tender_id = st.selectbox("Licitación:", tenders_df['id'].tolist(), format_func=lambda x: f"LIC-{x:04d} - {tenders_df[tenders_df['id']==x]['title'].values[0]}", label_visibility="collapsed")
                
            with col_act:
                 pass # Layout spacer
            
            if selected_tender_id:
                 tender_filtered = tenders_df[tenders_df['id'] == selected_tender_id]
                 if tender_filtered.empty:
                     st.error("Licitación no encontrada.")
                 else:
                     tender_row = tender_filtered.iloc[0]
                     st.markdown("---")
                     
                      # Management Form inside container
                     with st.container(border=False):
                         st.write(f"**Gestionando: {tender_row['title']}**")
                     
                         with st.form(f"manage_{selected_tender_id}"):
                             c1, c2 = st.columns(2)
                             new_title = c1.text_input("Editar Título", value=tender_row['title'])
                             new_budget = c2.number_input("Editar Presupuesto", value=float(tender_row['budget_estimated']))
                             
                             c3, c4 = st.columns(2)
                             new_mp_id = c3.text_input("ID Mercado Público", value=tender_row.get('mercado_publico_id', ''))
                             
                             # Tipo (Handle existing)
                             curr_type = tender_row['type'] if tender_row['type'] in ["L1", "LE", "LP", "LQ", "LR", "LS"] else "LP"
                             tipos_opts = ["L1", "LE", "LP", "LQ", "LR", "LS"]
                             new_type = c4.selectbox("Tipo", tipos_opts, index=tipos_opts.index(curr_type) if curr_type in tipos_opts else 0)
                             
                             c5, c6 = st.columns(2)
                             # Status Management
                             curr_status = tender_row['status']
                             status_opts = ["Borrador", "Activa", "Evaluación", "Adjudicada", "Desierta"]
                             new_status = c5.selectbox("Estado Actual", status_opts, index=status_opts.index(curr_status) if curr_status in status_opts else 0)
                             
                             btn_save = st.form_submit_button("💾 Guardar Cambios", type="primary")
                             
                             if btn_save:
                                  # Save all fields including status
                                  licitaciones.update_tender(selected_tender_id, new_title, new_budget, new_mp_id, new_type)
                                  if new_status != curr_status:
                                      licitaciones.update_tender_status(selected_tender_id, new_status)
                                  
                                  st.toast("Licitación actualizada", icon="💾")
                                  st.rerun()
                         
                         st.markdown("")
                         if st.button("🗑️ Eliminar Licitación", key=f"del_ten_{selected_tender_id}", type="primary"):
                              if can_delete:
                                  licitaciones.delete_tender(selected_tender_id)
                                  st.toast("Eliminado", icon="🗑️")
                                  st.rerun()
                              else:
                                  st.error("Permiso denegado.")
                     
                         st.divider()
                         st.subheader("📜 Gestión Contractual")
                     
                     # --- CONTRACTS SECTION ---
                     contracts_df = licitaciones.get_contracts(selected_tender_id)
                     
                     # 1. New Contract Form
                     with st.expander("➕ Nuevo Contrato", expanded=False):
                         with st.form(f"new_contract_{selected_tender_id}"):
                             c1, c2 = st.columns(2)
                             k_rut = c1.text_input("RUT Contratista")
                             k_name = c2.text_input("Razón Social")
                             
                             c3, c4 = st.columns(2)
                             k_amount = c3.number_input("Monto Contrato ($)", min_value=0, step=100000)
                             k_start = c4.date_input("Fecha Inicio", key=f"k_s_{selected_tender_id}")
                             
                             c5, c6 = st.columns(2)
                             k_end = c5.date_input("Fecha Término", key=f"k_e_{selected_tender_id}")
                             
                             if st.form_submit_button("Crear Contrato"):
                                 if k_rut and k_name and k_amount > 0:
                                     licitaciones.create_contract(selected_tender_id, k_name, k_rut, k_amount, k_start, k_end)
                                     st.toast("Contrato creado", icon="✅")
                                     st.rerun()
                                 else:
                                     st.warning("Datos incompletos.")

                     # 2. List & Manage Contracts
                     if contracts_df.empty:
                         st.info("No hay contratos asociados.")
                     else:
                         st.dataframe(
                             contracts_df[['contractor_name', 'rut_contractor', 'amount', 'status']],
                             column_config={
                                 "contractor_name": "Contratista",
                                 "rut_contractor": "RUT",
                                 "amount": st.column_config.NumberColumn("Monto", format="$%d"),
                                 "status": "Estado"
                             },
                             hide_index=True,
                             width='stretch'
                         )
                         
                         # Selector for Management
                         sel_contract = st.selectbox("Seleccionar Contrato para Gestionar:", contracts_df['id'].tolist(), format_func=lambda x: f"CTR-{x} | {contracts_df[contracts_df['id']==x]['contractor_name'].values[0]}")
                         
                         if sel_contract:
                             k_filtered = contracts_df[contracts_df['id'] == sel_contract]
                             if k_filtered.empty:
                                 st.error("Contrato no encontrado.")
                             else:
                                 k_row = k_filtered.iloc[0]
                                 with st.container(border=True):
                                     st.markdown(f"**Editando Contrato: {k_row['contractor_name']}**")
                                     
                                     with st.form(f"edit_ctr_{sel_contract}"):
                                         ec1, ec2 = st.columns(2)
                                         ec_name = ec1.text_input("Razón Social", value=k_row['contractor_name'])
                                         ec_rut = ec2.text_input("RUT", value=k_row['rut_contractor'])
                                         
                                         ec3, ec4 = st.columns(2)
                                         ec_amount = ec3.number_input("Monto ($)", value=float(k_row['amount']))
                                         try:
                                             curr_start = pd.to_datetime(k_row['start_date']).date()
                                             curr_end = pd.to_datetime(k_row['end_date']).date()
                                         except:
                                             from datetime import datetime
                                             curr_start = datetime.now().date()
                                             curr_end = datetime.now().date()
                                             
                                         ec_start = ec4.date_input("Inicio", value=curr_start)
                                         
                                         ec5, ec6 = st.columns(2)
                                         ec_end = ec5.date_input("Término", value=curr_end)
                                         
                                         curr_st = k_row.get('status', 'Activo')
                                         st_opts = ["Activo", "Finalizado", "Rescindido"]
                                         ec_status = ec6.selectbox("Estado", st_opts, index=st_opts.index(curr_st) if curr_st in st_opts else 0)
                                         
                                         if st.form_submit_button("Actualizar Contrato"):
                                             licitaciones.update_contract(sel_contract, ec_name, ec_rut, ec_amount, ec_start, ec_end, ec_status)
                                             st.toast("Contrato Actualizado")
                                             st.rerun()
                                     
                                     c_del_k, _ = st.columns([1, 2])
                                     with c_del_k:
                                         if st.button("🗑️ Borrar Contrato", key=f"del_ctr_{sel_contract}"):
                                             if can_delete:
                                                 licitaciones.delete_contract(sel_contract)
                                                 st.rerun()
                                             else:
                                                 st.error("No autorizado.")
                                        
                                # --- GUARANTEES SECTION REMOVED ---
                                # (User requested removal of Boletas de Garantía view)

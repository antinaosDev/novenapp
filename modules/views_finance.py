import streamlit as st
import pandas as pd
from datetime import datetime
from modules import finance, data

def render_finance():
    # --- Header (Native) ---
    st.caption("ERP / Tesorería")
    st.title("Control Financiero & EDP")
    st.markdown("**Gestión de Ordenes de Compra y Estados de Pago.**")
    
    # --- Reports Header ---
    c_head, c_rep = st.columns([2, 1])
    with c_rep:
       with st.popover("📄 Exportar Reportes"):
           st.write("**Opciones de Exportación**")
           if st.button("Generar Reporte PDF (Ejecutivo)"):
               import matplotlib.pyplot as plt
               from modules import reports_gen
               
               # 1. Fetch Data
               stats = finance.get_financial_summary()
               orders_df = finance.get_purchase_orders()
               
               sections = []
               
               # Section 1: Visual KPIs
               sections.append({
                   "type": "kpi_row",
                   "content": [
                       {"label": "Monto Pendiente", "value": f"${stats['total_pending_amount']:,.0f}", "sub": f"{stats['pending']} Órdenes por Aprobar"},
                       {"label": "Pagos Ejecutados", "value": str(stats['paid']), "sub": "Órdenes Cerradas"},
                       {"label": "Total Aprobado", "value": str(stats['approved']), "sub": "En proceso de pago"}
                   ]
               })

               # Section 2: Executive Summary Text
               sections.append({
                   "type": "text", 
                   "title": "Resumen Ejecutivo", 
                   "content": f"A la fecha de emisión ({datetime.now().strftime('%d/%m/%Y')}), el estado financiero presenta {stats['pending']} órdenes en estado pendiente, totalizando un monto de ${stats['total_pending_amount']:,.0f}. La gestión de pagos muestra un avance con {stats['paid']} órdenes liquidadas y {stats['approved']} aprobadas listas para tesorería."
               })
               
               # Section 3: Charts (Generated dynamically via Matplotlib)
               if not orders_df.empty:
                    # Chart 1: Status Distribution (Donut)
                    status_counts = orders_df['status'].value_counts()
                    fig1, ax1 = plt.subplots(figsize=(7, 4))
                    colors = {'Pendiente': '#f59e0b', 'Aprobada': '#10b981', 'Pagada': '#3b82f6'}
                    c_list = [colors.get(x, '#9ca3af') for x in status_counts.index]
                    
                    wedges, texts, autotexts = ax1.pie(status_counts, autopct='%1.1f%%', colors=c_list, pctdistance=0.75)
                    # Use legend instead of labels on slices for cleaner rendering
                    ax1.legend(wedges, status_counts.index, title="Estados", loc="center left", bbox_to_anchor=(1, 0.5))
                    
                    # Draw Circle
                    centre_circle = plt.Circle((0,0),0.70,fc='white')
                    fig1.gca().add_artist(centre_circle)
                    
                    ax1.set_title("Distribución de Órdenes por Estado")
                    plt.setp(autotexts, size=10, weight="bold", color="#1e293b")
                    sections.append({"type": "plot", "title": "Estado de la Cartera", "content": fig1})
                    
                    # Chart 2: Amounts by Project
                    if 'project_name' in orders_df.columns:
                        proj_amts = orders_df.groupby('project_name')['total_amount'].sum().sort_values(ascending=True)
                        fig2, ax2 = plt.subplots(figsize=(8, 4))
                        proj_amts.plot(kind='barh', color='#10b981', ax=ax2)
                        ax2.set_title("Gasto Acumulado por Proyecto")
                        ax2.set_xlabel("Monto Total ($)")
                        ax2.grid(axis='x', linestyle='--', alpha=0.3)
                        # Format X axis currency list with M/K suffixes to avoid overlapping
                        def compact_money(x, p):
                            if x >= 1_000_000: return f'${x/1e6:.1f}M'
                            if x >= 1_000: return f'${x/1e3:.0f}K'
                            return f'${x:,.0f}'
                        ax2.xaxis.set_major_formatter(plt.FuncFormatter(compact_money))
                        plt.tight_layout()
                        sections.append({"type": "plot", "title": "Análisis de Gasto", "content": fig2})
               
               # Section 4: Data Table
               if not orders_df.empty:
                   cols_rep = ['order_number', 'provider_name', 'category', 'total_amount', 'status', 'date'] if 'category' in orders_df.columns else ['order_number', 'provider_name', 'total_amount', 'status', 'date']
                   col_names = ['N° Orden', 'Proveedor', 'Categoría', 'Monto', 'Estado', 'Fecha'] if 'category' in orders_df.columns else ['N° Orden', 'Proveedor', 'Monto', 'Estado', 'Fecha']
                   disp_df = orders_df[cols_rep].head(20).copy()
                   disp_df.columns = col_names
                   disp_df['Monto'] = disp_df['Monto'].apply(lambda x: f"${x:,.0f}".replace(',', '.'))
                   disp_df['Fecha'] = pd.to_datetime(disp_df['Fecha']).dt.strftime('%d/%m/%Y')
                   
                   sections.append({
                       "type": "table",
                       "title": "Últimas Órdenes Registradas",
                       "content": disp_df
                   })
               
               pdf_bytes = reports_gen.generate_pdf_report("Reporte Financiero de Obras", sections)
               st.session_state['last_fin_pdf'] = pdf_bytes
               
           if 'last_fin_pdf' in st.session_state:
               st.download_button("📥 Descargar PDF", st.session_state['last_fin_pdf'], file_name="reporte_financiero.pdf", mime="application/pdf")
               
           # Excel
           st.write("**Datos Financieros**")
           orders_all = finance.get_purchase_orders()
           if not orders_all.empty:
               from modules import reports_gen
               xls_data = reports_gen.generate_excel({"Ordenes de Compra": orders_all})
               st.download_button("📊 Descargar Excel", xls_data, file_name="data_financiera.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.divider()

    # --- Actions (Card) ---
    with st.expander("➕ Registrar Orden de Compra (OC)", expanded=False):
        with st.container(border=True): # Card Wrapper for Form
            with st.form("new_po_form"):
                st.write("Nueva Orden de Compra")
                
                # Project Selector
                projects = data.get_projects()
                if not projects.empty:
                    project_id = st.selectbox("Proyecto Asociado", projects['id'], format_func=lambda x: projects[projects['id']==x]['name'].values[0])
                else:
                    st.warning("No hay proyectos activos.")
                    project_id = None
                
                c1, c2 = st.columns(2)
                order_num = c1.text_input("N° Orden (Interno/Externo)")
                provider = c2.text_input("Nombre Proveedor")
                
                c3, c4 = st.columns(2)
                amount = c3.number_input("Monto Total ($)", min_value=0, step=100000)
                date_val = c4.date_input("Fecha Emisión")
                
                cats = ["Materiales", "Subcontratos", "Gastos Generales", "Mano de Obra", "Equipos", "Otros"]
                category = st.selectbox("Categoría", cats)
                desc = st.text_area("Descripción / Detalle")
                
                if st.form_submit_button("Registrar OC", type="primary"):
                    if provider and amount > 0 and project_id and order_num:
                        finance.create_purchase_order(project_id, provider, date_val, amount, order_num, desc, category)
                        st.toast("Orden de Compra registrada.", icon="✅") 
                        st.rerun()
                    else:
                        st.error("Datos incompletos. Revisa Proyecto, N° Orden, Proveedor y Monto.")

    # Fetch Data
    stats = finance.get_financial_summary()
    orders_df = finance.get_purchase_orders()

    # --- Stats Dashboard (Cards) ---
    st.subheader("Resumen del Periodo")
    pending_str = f"${stats['total_pending_amount']:,.0f}"

    m1, m2, m3 = st.columns(3)
    
    with m1:
        with st.container(border=True):
            st.metric("Pendientes", stats["pending"], delta=f"Total: {pending_str}", delta_color="off", help="OCs esperando aprobación")
    with m2:
        with st.container(border=True):
            st.metric("Aprobadas", stats["approved"], delta="Listo para pago", help="OCs validadas técnicamente")
    with m3:
        with st.container(border=True):
            st.metric("Pagadas", stats["paid"], delta="Cerrado", help="Pagos ejecutados")

    st.divider()
    
    # --- Purchase Orders Table (Card) ---
    with st.container(border=True):
        st.subheader(f"Registro de Ordenes de Compra ({len(orders_df)})")
        
        # --- FILTRO POR PROYECTO ---
        projects_df = data.get_projects()
        if not projects_df.empty:
            proj_options = ["Todos"] + projects_df['id'].tolist()
            def format_proj(x):
                if x == "Todos": return "Todos los Proyectos"
                match = projects_df[projects_df['id'] == x]
                return match['name'].values[0] if not match.empty else f"Proyecto {x}"
            
            selected_proj_filter = st.selectbox("Filtrar por Proyecto:", proj_options, format_func=format_proj)
            
            # Aplicar filtro
            if selected_proj_filter != "Todos":
                orders_df = orders_df[orders_df['project_id'] == selected_proj_filter]
        # ---------------------------

        if orders_df.empty:
            st.info("No hay ordenes de compra registradas para esta selección.")
        else:
            # Seleccionar solo columnas esenciales para mostrar
            disp_cols = ['id', 'order_number', 'project_name', 'provider_name', 'date', 'total_amount', 'status']
            if 'category' in orders_df.columns:
                disp_cols.insert(3, 'category') # Insertar despues de Proyecto
                
            col_cfg = {
                "id": st.column_config.NumberColumn("ID", format="OC-%d", width="small"),
                "order_number": st.column_config.TextColumn("N° Orden", width="medium"),
                "project_name": st.column_config.TextColumn("Proyecto", width="medium"),
                "provider_name": "Proveedor",
                "date": st.column_config.DateColumn("Fecha Emisión", format="DD/MM/YYYY"),
                "total_amount": st.column_config.NumberColumn("Monto", format="$%d"),
                "status": st.column_config.SelectboxColumn(
                    "Estado Actual",
                    options=["Pendiente", "Aprobada", "Pagada"],
                    required=True
                )
            }
            if 'category' in orders_df.columns:
                col_cfg["category"] = "Categoría"

            st.dataframe(
                orders_df[disp_cols],
                column_config=col_cfg,
                hide_index=True,
                width='stretch'
            )

        if not orders_df.empty:
            st.caption("Gestión detallada de Órdenes")
            
            # Selection
            col_sel, col_sp = st.columns([3, 1])
            with col_sel:
                def format_po_sel(x):
                    po_row = orders_df[orders_df['id'] == x]
                    if not po_row.empty:
                        return f"OC-{int(x):04d} | {po_row['order_number'].values[0]} - {po_row['provider_name'].values[0]}"
                    return f"OC-{int(x):04d}"

                po_id = st.selectbox("Seleccionar OC para gestionar:", orders_df['id'].tolist(), format_func=format_po_sel)
        else:
            po_id = None
             
        if po_id:
             po_filtered = orders_df[orders_df['id'] == po_id]
             if po_filtered.empty:
                 st.error("Orden de Compra no encontrada.")
             else:
                 row = po_filtered.iloc[0]
                 
                 with st.container(border=True):
                     st.markdown(f"**Editando OC-{row['id']}** ({row['order_number']})")
                 
                 with st.form(f"edit_po_{po_id}"):
                     # Edit Fields
                     projects = data.get_projects()
                     p_idx = 0
                     if not projects.empty and row['project_id']:
                         # Find index of current project
                         matching = projects.index[projects['id'] == row['project_id']].tolist()
                         if matching:
                             p_idx = matching[0]

                     new_proj_id = st.selectbox("Proyecto", projects['id'], format_func=lambda x: projects[projects['id']==x]['name'].values[0], index=p_idx if not projects.empty else 0)
                     
                     c1, c2 = st.columns(2)
                     new_order_num = c1.text_input("N° Orden", value=row['order_number'])
                     new_provider = c2.text_input("Proveedor", value=row['provider_name'])
                     
                     c3, c4 = st.columns(2)
                     new_amount = c3.number_input("Monto", value=float(row['total_amount']), step=10000.0)
                     
                     # Safe date parsing
                     try:
                        d_val = pd.to_datetime(row['date']).date()
                     except:
                        d_val = pd.to_datetime('today').date()
                        
                     new_date = c4.date_input("Fecha", value=d_val)
                     # Cats
                     cats = ["Materiales", "Subcontratos", "Gastos Generales", "Mano de Obra", "Equipos", "Otros"]
                     curr_cat = row.get('category', 'Otros')
                     new_cat = st.selectbox("Categoría", cats, index=cats.index(curr_cat) if curr_cat in cats else 0)
                     new_desc = st.text_area("Descripción", value=row.get('description', ''))
                     
                     st.divider()
                     c5, c6 = st.columns(2)
                     
                     curr_status = row['status']
                     st_opts = ["Pendiente", "Aprobada", "Pagada"]
                     new_status = c5.selectbox("Estado", st_opts, index=st_opts.index(curr_status) if curr_status in st_opts else 0)
                     
                     if st.form_submit_button("💾 Guardar Cambios", type="primary"):
                         finance.update_purchase_order(po_id, new_proj_id, new_provider, new_amount, new_date, new_order_num, new_desc, new_cat)
                         if new_status != curr_status:
                             data.update_po_status(po_id, new_status)
                         st.toast("Orden actualizada", icon="💾")
                         st.rerun()

                 if st.button("🗑️ Eliminar Orden", key=f"del_po_{po_id}"):
                     finance.delete_purchase_order(po_id)
                     st.toast("Orden eliminada", icon="🗑️")
                     st.rerun()

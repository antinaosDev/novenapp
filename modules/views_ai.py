import streamlit as st
import json
import os
import re
from datetime import datetime
from modules import ai_analysis, data
# Import shared PDF class for consistency (Logo, Footer, etc.)
from modules.reports_gen import NovAPP_PDF

# --- Usage Logic ---
# --- Usage Logic (Delegated to Data Module) ---
def get_usage():
    limit = data.get_ai_call_limit()
    current = data.get_daily_ai_usage_count()
    return {"count": current, "limit": limit}

def increment_usage():
    # Increment in DB
    new_count = data.increment_daily_ai_usage()
    limit = data.get_ai_call_limit()
    return {"count": new_count, "limit": limit}

# --- Helper: Text Cleaning ---
def clean_markdown(text):
    """
    Strips common markdown symbols for PDF generation.
    """
    # Remove bold/italic markers
    text = text.replace('**', '').replace('__', '').replace('*', '')
    # Remove headers logic if embedded in text lines
    text = text.replace('### ', '').replace('## ', '').replace('# ', '')
    return text

def parse_report_sections(full_text):
    """
    Splits the AI report into a dictionary of sections.
    """
    sections = {
        "resumen": "",
        "alertas": "",
        "recomendaciones": "",
        "extra": "" 
    }
    
    # Normalize text
    text = full_text.strip()
    
    # Simple keyword splitting (case insensitive)
    # We look for the main headers requested in the prompt
    
    # Finds "1. **Resumen Ejecutivo**" or "Resumen Ejecutivo"
    # We will split by known headers
    
    # Strategy: Find indices of the headers
    headers = [
        ("Resumen Ejecutivo", "resumen"),
        ("Alertas y Riesgos", "alertas"),
        ("Recomendaciones", "recomendaciones"),
        ("Análisis Adicional", "extra") # In case it appears
    ]
    
    current_key = "intro" # Text before first header
    lines = text.split('\n')
    
    buffer = []
    
    for line in lines:
        # Check if line contains a header
        found_header = False
        lower_line = line.lower()
        
        for header_title, header_key in headers:
            if header_title.lower() in lower_line:
                # Save current buffer to current_key
                if buffer:
                    # Append to existing content if any (handling nested logic)
                     if current_key in sections:
                         sections[current_key] += "\n".join(buffer)
                     elif current_key == "intro":
                         pass # discard intro or keep it
                         
                # Switch context
                current_key = header_key
                buffer = []
                found_header = True
                break
        
        if not found_header:
            buffer.append(line)
            
    # Flush last buffer
    if buffer and current_key in sections:
        sections[current_key] += "\n".join(buffer)
        
    return sections

# --- PDF Generation ---
def create_pdf_report_v2(report_text, stats):
    """
    Uses NovAPP_PDF to generate a clean, professional PDF.
    """
    pdf = NovAPP_PDF("Reporte Ejecutivo - Análisis IA")
    pdf.add_page()
    
    # 1. KPIs Summary Table
    pdf.chapter_title("Resumen de Indicadores")
    
    # Create valid DataFrame or dictionary for the table listing
    # pdf.chapter_body doesn't take columns easily, but we can list them.
    # NovAPP_PDF.add_table expects a DataFrame. Let's make a small one.
    import pandas as pd
    
    data_kpi = {
        "Indicador": [
            "Proyectos Activos", 
            "Presupuesto Cartera",
            "Deuda Flotante",
            "Órdenes Pendientes", 
            "Calidad (Aprobación)",
            "Subcontratos Bloqueados"
        ],
        "Valor": [
            str(stats.get('active_projects', 0)),
            f"${stats.get('total_budget', 0):,.0f}",
            f"${stats.get('finance_debt', 0):,.0f}",
            str(stats.get('finance_pending', 0)),
            f"{stats.get('quality_pass_rate', 0)}%",
            str(stats.get('subs_blocked', 0))
        ]
    }
    df_kpi = pd.DataFrame(data_kpi)
    pdf.add_table(df_kpi)
    pdf.ln(5)
    
    # 2. Parse Text Content
    sections = parse_report_sections(report_text)
    
    # Helper to add section if exists
    def add_section_to_pdf(title, content):
        if content and len(content.strip()) > 5:
            pdf.chapter_title(title)
            # Clean markdown for PDF
            clean_content = clean_markdown(content)
            pdf.chapter_body(clean_content)
            pdf.ln(2)

    add_section_to_pdf("Resumen Ejecutivo", sections['resumen'])
    add_section_to_pdf("Alertas y Riesgos", sections['alertas'])
    add_section_to_pdf("Recomendaciones Estratégicas", sections['recomendaciones'])
    
    if sections.get('extra'):
         add_section_to_pdf("Análisis Adicional AI", sections['extra'])
    
    return pdf.output(dest='S').encode('latin-1')

# --- Main View ---
def render_ai_view():
    st.caption("Inteligencia Artificial")
    col_head, col_logo = st.columns([4, 1])
    with col_head:
        st.title("Analista Operativo Virtual 🧠")
    
    # Get API Key from Secrets
    try:
        default_key = st.secrets["GROQ"]["API_KEY"]
    except:
        default_key = None
        st.error("⚠️ Groq API Key no configurada. Contacte al administrador.")
        return
    
    st.session_state['groq_api_key'] = default_key
    api_key = default_key 
    
    # Usage Check
    usage = get_usage()
    limit_val = usage['limit']
    remaining = limit_val - usage['count']
    
    # Top Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Consultas Hoy", f"{usage['count']}/{limit_val}")
    c2.metric("Motor AI", "Llama 3 70B")
    c3.metric("Estado", "En Línea", delta="OK", delta_color="normal")
    
    st.divider()
    
    # Layout
    col_input, col_output = st.columns([1, 2])
    
    with col_input:
        st.subheader("Generar Nuevo Reporte")
        st.info("""
            El Analista Virtual examinará:
            - 📊 Estado de Proyectos
            - 💰 Flujo Financiero
            - 🏗️ Subcontratos y Calidad
            - 📅 Planificación (Lean)
        """)
        
        btn_disabled = remaining <= 0
        if btn_disabled:
            st.error("🚫 Límite diario alcanzado.")
        
        if st.button("✨ Generar Análisis Ejecutivo", type="primary", disabled=btn_disabled, use_container_width=True):
            with st.spinner("🤖 Analizando millones de datos..."):
                try:
                    stats = ai_analysis.gather_global_stats()
                    report = ai_analysis.generate_executive_report(api_key, stats)
                    increment_usage()
                    
                    st.session_state['ai_last_report'] = report
                    st.session_state['ai_last_stats'] = stats
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    with col_output:
        if 'ai_last_report' in st.session_state:
            report_content = st.session_state['ai_last_report']
            stats_content = st.session_state.get('ai_last_stats', {})
            
            st.subheader("📝 Reporte Ejecutivo")
            
            # --- Parsed UI Rendering ---
            sections = parse_report_sections(report_content)
            
            # 1. Resumen -> Info/Standard
            with st.container(border=True):
                st.markdown("### 📌 Resumen Ejecutivo")
                # Fix LaTeX issue: Replace $ with USD or escaped
                safe_resumen = sections['resumen'].replace('$', '\\$')
                st.markdown(safe_resumen)
            
            # 2. Alertas -> Warning
            if sections['alertas'].strip():
                with st.expander("⚠️ Alertas y Riesgos Detectados", expanded=True):
                    st.warning(sections['alertas'].replace('**', '').replace('$', '\\$'))
            
            # 3. Recomendaciones -> Success
            if sections['recomendaciones'].strip():
                 with st.expander("✅ Recomendaciones Estratégicas", expanded=True):
                    st.info(sections['recomendaciones'].replace('$', '\\$'))
                    
            # 4. Extra -> Gray
            if sections.get('extra') and sections['extra'].strip():
                with st.expander("🔍 Análisis Profundo (Debug)", expanded=False):
                    st.caption(sections['extra'])
            
            st.divider()
            
            # PDF Download
            pdf_bytes = create_pdf_report_v2(report_content, stats_content)
            
            st.download_button(
                label="📥 Descargar Reporte PDF Oficial",
                data=pdf_bytes,
                file_name=f"Reporte_Ejecutivo_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            
        else:
            st.empty()
            with st.container(border=True):
                 st.markdown("""
                 <div style='text-align: center; color: gray; padding: 40px;'>
                    <h3>👈 Genera tu primer reporte</h3>
                    <p>Obtén insights estratégicos en segundos.</p>
                 </div>
                 """, unsafe_allow_html=True)

import streamlit as st
import pandas as pd
from datetime import datetime
from groq import Groq
from modules import data, finance, compliance, licitaciones, quality, lean, teams

def gather_global_stats():
    """
    Aggregates key metrics from all modules to feed the AI context.
    """
    stats = {}
    
    # 1. Projects
    projects = data.get_projects()
    stats['total_projects'] = len(projects)
    stats['active_projects'] = len(projects[projects['status'].isin(['En Ejecución', 'Activo'])]) if not projects.empty else 0
    stats['total_budget'] = projects['budget_total'].sum() if not projects.empty else 0
    
    # 1.5 Internal/Allocated Budget (Mano de Obra)
    # New logic to see Labor Costs
    budget_items = data.get_all_budget_items()
    stats['allocated_budget_items'] = budget_items['estimated_amount'].sum() if not budget_items.empty else 0
    
    # 2. Finance
    fin_stats = finance.get_financial_summary()
    stats['finance_pending'] = fin_stats['pending']
    stats['finance_paid'] = fin_stats['paid']
    stats['finance_debt'] = fin_stats['total_pending_amount']
    
    # 3. Compliance
    # Aggregated compliance is tricky without project context, we'll confirm general status
    # We can fetch all subs and check how many are blocked
    all_subs = data.get_subcontractors(None)
    stats['subs_total'] = len(all_subs)
    stats['subs_blocked'] = len(all_subs[all_subs['status'] == 'Bloqueado']) if not all_subs.empty else 0
    
    # 4. Tenders
    tenders = licitaciones.get_tenders()
    stats['tenders_active'] = len(tenders[tenders['status'].isin(['Activa', 'Publicada', 'En Licitación'])]) if not tenders.empty else 0
    stats['tenders_awarded'] = len(tenders[tenders['status'] == 'Adjudicada']) if not tenders.empty else 0
    
    # 5. Quality
    lab_tests = quality.get_lab_tests(None)
    all_comments = data.get_all_comments()
    
    if not lab_tests.empty:
        passed = len(lab_tests[lab_tests['result'] == 'Aprobado'])
        stats['quality_pass_rate'] = f"{int((passed / len(lab_tests)) * 100)}% (Ensayos Lab)"
    elif not all_comments.empty:
        # Fallback to activity level
        stats['quality_pass_rate'] = "N/A (Solo Bitácora Activa)"
    else:
        stats['quality_pass_rate'] = "N/A"
        
    stats['bitacora_entries'] = len(all_comments)
        
    # 6. Lean
    # We'll take a generic PPC average if possible, or just task volume
    # Since PPC is per plan, let's just count total active tasks
    # We can iterate projects to get average PPC (expensive but useful)
    ppc_values = []
    if not projects.empty:
        # 7. Resources & Faenas (Consolidated)
        # Faenas are per project, but we can count total active fronts
        # We need a way to get all faenas, or iterating projects. 
        # For efficiency, let's assume data.get_faenas(None) isn't available, so we check general capacity if possible or skip.
        # However, Units are global.
        units = data.get_units()
        stats['resources_total'] = len(units)
        stats['resources_machinery'] = len(units[units['type'] == 'Maquinaria']) if not units.empty else 0
        
        # 8. Team Structure
        team_stats = teams.get_stats()
        stats['total_personnel'] = team_stats['total_personnel']
        
        for pid in projects['id']:
            tasks = lean.get_tasks(pid)
            if not tasks.empty:
                # Calculate active PPC
                # Simplified logic similar to lean.get_ppc but quick
                ppc_val = lean.get_ppc(tasks)
                ppc_values.append(ppc_val)
    
    if ppc_values:
        stats['avg_ppc'] = int(sum(ppc_values) / len(ppc_values))
    else:
        stats['avg_ppc'] = 0
        
    return stats

def generate_executive_report(api_key, stats):
    """
    Calls Groq API to generate an executive summary.
    """
    if not api_key:
        return "⚠️ Error: Falta la API Key de Groq. Configúrala en la barra lateral."
        
    client = Groq(api_key=api_key)
    
    prompt = f"""
    Actúa como Gerente de Operaciones y Analista de Datos Senior en una empresa constructora. Tu objetivo es generar un "Reporte Ejecutivo de Estado" basado en los datos en tiempo real proporcionados por la plataforma ERP de la empresa.

    [DATOS GENERALES]
    - Proyectos Totales: {stats.get('total_projects')}
    - Proyectos Activos (En Ejecución): {stats.get('active_projects')}
    - Presupuesto Total Cartera: ${stats.get('total_budget'):,.0f}
    - Presupuesto Asignado Interno (Mano de Obra/Ítems): ${stats.get('allocated_budget_items'):,.0f} (Adicional a contratos)

    [FINANZAS]
    - Órdenes de Compra Pendientes: {stats.get('finance_pending')}
    - Órdenes Pagadas: {stats.get('finance_paid')}
    - Deuda Flotante (Pendiente): ${stats.get('finance_debt'):,.0f}

    [COMPLIANCE & SUBCONTRATOS]
    - Total Subcontratistas: {stats.get('subs_total')}
    - Subcontratistas Bloqueados (Riesgo): {stats.get('subs_blocked')}

    [LICITACIONES]
    - Licitaciones Activas: {stats.get('tenders_active')}
    - Adjudicadas Recientes: {stats.get('tenders_awarded')}

    [CALIDAD & OPERACIONES]
    - Tasa Aprobación Ensayos (Laboratorio): {stats.get('quality_pass_rate')}
    - Actividad en Bitácora (Notas/Libro de Obra): {stats.get('bitacora_entries')} entradas
    - Personal en Terreno (Dotación): {stats.get('total_personnel')}
    - Recursos Totales: {stats.get('resources_total')} (Maquinaria: {stats.get('resources_machinery')})
    - PPC Promedio (Lean Construction): {stats.get('avg_ppc')}%

    INSTRUCCIONES:
    Genera un análisis narrativo que sea técnico, claro y directo. El reporte debe ser conciso, pero detallado (máximo 400 palabras).

    Estructura el reporte en 3 secciones claras:

    1. **Resumen Ejecutivo**: Presenta el estado general de salud de la empresa. Integra el análisis del presupuesto oficial vs el asignado internamente (Mano de Obra). Menciona la actividad en Bitácora como señal de fiscalización en terreno, incluso si no hay ensayos de laboratorio recientes.

    2. **Alertas y Riesgos**: Resalta las áreas críticas que requieren atención urgente. Ejemplos:
       - Subcontratistas bloqueados.
       - PPC bajo (<70%).
       - Deuda flotante alta.
       - Baja actividad en bitácora si hay proyectos activos.

    3. **Recomendaciones**: Proporciona 3 acciones estratégicas para el Gerente General.

    Utiliza formato Markdown con negritas y listas para destacar información importante.
    El tono debe ser formal, técnico pero accesible.
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error al conectar con IA: {str(e)}"

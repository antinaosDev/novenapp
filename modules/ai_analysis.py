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
    stats['active_projects'] = len(projects[projects['status'] == 'En Ejecución']) if not projects.empty else 0
    stats['total_budget'] = projects['budget_total'].sum() if not projects.empty else 0
    
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
    stats['tenders_active'] = len(tenders[tenders['status'] == 'Activa']) if not tenders.empty else 0
    stats['tenders_awarded'] = len(tenders[tenders['status'] == 'Adjudicada']) if not tenders.empty else 0
    
    # 5. Quality
    lab_tests = quality.get_lab_tests(None)
    if not lab_tests.empty:
        passed = len(lab_tests[lab_tests['result'] == 'Aprobado'])
        stats['quality_pass_rate'] = int((passed / len(lab_tests)) * 100)
    else:
        stats['quality_pass_rate'] = "N/A"
        
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
    - Tasa Aprobación Ensayos (Laboratorio): {stats.get('quality_pass_rate')}%
    - Personal en Terreno (Dotación): {stats.get('total_personnel')}
    - Recursos Totales: {stats.get('resources_total')} (Maquinaria: {stats.get('resources_machinery')})
    - PPC Promedio (Lean Construction): {stats.get('avg_ppc')}%

    INSTRUCCIONES:
    Genera un análisis narrativo que sea técnico, claro y directo. El reporte debe ser conciso, pero detallado (máximo 400 palabras).

    Estructura el reporte en 3 secciones claras:

    1. **Resumen Ejecutivo**: Presenta el estado general de salud de la empresa, destacando la eficiencia en la ejecución de proyectos y la situación financiera. Menciona si la empresa está cumpliendo con sus expectativas operativas y financieras. Haz un análisis sobre la relación entre los proyectos activos, el presupuesto total y las ordenes de compra pendientes, y cómo estos indicadores impactan la rentabilidad.

    2. **Alertas y Riesgos**: Resalta las áreas críticas que requieren atención urgente. Ejemplos incluyen:
       - Si hay subcontratistas bloqueados debido a riesgos contractuales o problemas de cumplimiento.
       - Si el PPC (Planificación por Compleción) es bajo (<70%), lo cual podría indicar problemas de eficiencia operativa o retrasos en el cronograma.
       - Si la deuda flotante es alta o si existen pagos pendientes que podrían afectar la liquidez de la empresa.
       - La cantidad de órdenes de compra pendientes podría reflejar posibles demoras o deficiencias en la gestión de compras y suministros.

    3. **Recomendaciones**: Proporciona 3 acciones estratégicas para el Gerente General:
       - Implementar un plan de revisión financiera semanal para reducir la deuda flotante y asegurar que las órdenes de compra sean procesadas a tiempo.
       - Establecer medidas para mejorar la tasa de aprobación de ensayos en el laboratorio y asegurar que todos los proyectos cumplan con los estándares de calidad desde el inicio.
       - Iniciar un programa de optimización en el manejo de subcontratistas, con especial énfasis en los subcontratistas bloqueados, para mitigar los riesgos contractuales y garantizar la continuidad de las operaciones.

    Utiliza formato Markdown con negritas y listas para destacar información importante.
    El tono debe ser formal, técnico pero accesible, con enfoque en claridad, efectividad y acción inmediata.
    El reporte debe ser redactado en español, de forma que sea fácilmente comprensible para los altos directivos de la empresa.

    **Análisis Adicional para guiar tu respuesta:**
    - **Presupuesto vs. Proyectos Activos**: Analiza la relación entre el presupuesto total y el número de proyectos activos. Si el presupuesto es elevado pero hay pocos proyectos activos, podría indicar una falta de ejecución eficiente. Si, por el contrario, hay una gran cantidad de proyectos en ejecución con un presupuesto ajustado, se debe evaluar si la empresa está operando dentro de sus márgenes de rentabilidad.
    - **PPC Promedio**: Si el PPC promedio es bajo, esto sugiere que los proyectos no están cumpliendo con las metas de productividad establecidas. Un PPC inferior al 70% indica una desviación importante en la ejecución de los proyectos, lo que podría derivar en sobrecostos o retrasos. Debería sugerirse una revisión de los procesos operativos y una mejora en la planificación y control de los proyectos.
    - **Riesgo Financiero y Subcontratistas**: La deuda flotante y las órdenes de compra pendientes pueden tener un impacto directo en la operatividad de la empresa. Si estas cifras son altas, podría haber problemas de liquidez que podrían afectar la capacidad de la empresa para cumplir con sus compromisos financieros. A su vez, los subcontratistas bloqueados por riesgo pueden ser una señal de que la empresa está enfrentando dificultades contractuales o de cumplimiento, lo cual debe resolverse con urgencia.
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

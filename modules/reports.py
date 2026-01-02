from fpdf import FPDF
import pandas as pd
from modules import data
import tempfile
import os

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Reporte de Proyecto - ConstruManager', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generate_project_report(project_id):
    pdf = PDF()
    pdf.add_page()
    
    # Fetch Data
    projects = data.get_projects()
    project = projects[projects['id'] == project_id].iloc[0] if not projects.empty else None
    
    if project is None:
        return None

    # Title
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"Proyecto: {project['name']}", 0, 1, 'L')
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f"Estado: {project['status']}", 0, 1)
    pdf.cell(0, 8, f"Presupuesto: ${project['budget_total']:,.2f}", 0, 1)
    pdf.ln(10)
    
    # Financial Summary
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "Resumen Financiero", 0, 1)
    
    # Use newly updated get_expenses_df with filtering
    df_expenses = data.get_expenses_df(project_id=project_id)
    total_spent = df_expenses['amount'].sum() if not df_expenses.empty else 0
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f"Total Gastado: ${total_spent:,.2f}", 0, 1)
    pdf.cell(0, 8, f"Disponible: ${project['budget_total'] - total_spent:,.2f}", 0, 1)
    pdf.ln(10)
    
    # Phases
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "Fases del Proyecto", 0, 1)
    
    phases = data.get_phases(project_id)
    
    pdf.set_font('Arial', '', 10)
    if not phases.empty:
        # Table Header
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(60, 8, "Nombre", 1, 0, 'C', 1)
        pdf.cell(40, 8, "Inicio", 1, 0, 'C', 1)
        pdf.cell(40, 8, "Fin", 1, 0, 'C', 1)
        pdf.cell(40, 8, "Estado", 1, 1, 'C', 1)
        
        for _, row in phases.iterrows():
            pdf.cell(60, 8, str(row['name']), 1)
            pdf.cell(40, 8, str(row['start_date']), 1)
            pdf.cell(40, 8, str(row['end_date']), 1)
            # Handle missing status col if old schema, else use it
            status = row.get('status', 'N/A')
            pdf.cell(40, 8, str(status), 1, 1)
    else:
        pdf.cell(0, 8, "No hay fases registradas.", 0, 1)
        
    pdf.ln(10)
    
    # Recent Expenses
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "Ultimos Gastos (Top 10)", 0, 1)
    
    if not df_expenses.empty:
        # Sort and take top 10
        # df is already ordered by date desc from API usually, but safe to sort
        if 'id' in df_expenses.columns:
             df_expenses.sort_values(by="id", ascending=False, inplace=True)
        top_expenses = df_expenses.head(10)
        
        pdf.set_font('Arial', '', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(30, 8, "Fecha", 1, 0, 'C', 1)
        pdf.cell(80, 8, "Descripcion", 1, 0, 'C', 1)
        pdf.cell(40, 8, "Monto", 1, 0, 'C', 1)
        pdf.cell(40, 8, "Categoria", 1, 1, 'C', 1)
        
        for _, row in top_expenses.iterrows():
            pdf.cell(30, 8, str(row['date']), 1)
            pdf.cell(80, 8, str(row['description'])[:35], 1)
            pdf.cell(40, 8, f"${row['amount']:,.2f}", 1)
            pdf.cell(40, 8, str(row['category']), 1, 1)
    else:
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 8, "No hay gastos registrados.", 0, 1)

    # Output
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name

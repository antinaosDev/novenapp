import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import matplotlib.pyplot as plt
import io
import tempfile

LOGO_PATH = os.path.join(os.getcwd(), "logo_nov.png")

# Palette
COLOR_PRIMARY = (16, 185, 129) # Emerald Green
COLOR_DARK = (15, 23, 42)      # Slate 900
COLOR_GRAY = (100, 116, 139)   # Slate 500
COLOR_BG_LIGHT = (241, 245, 249) # Slate 100

class NovAPP_PDF(FPDF):
    def __init__(self, title_report):
        super().__init__()
        self.title_report = title_report
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        # Top Bar
        self.set_fill_color(*COLOR_DARK)
        self.rect(0, 0, 210, 5, 'F')
        
        # Logo
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, 10, 12, 25)
            except:
                pass
        
        # Title
        self.set_xy(0, 15)
        self.set_font('Arial', 'B', 18)
        self.set_text_color(*COLOR_DARK)
        self.cell(0, 10, self.title_report, 0, 1, 'R')
        
        # Subtitle / Date
        self.set_font('Arial', '', 10)
        self.set_text_color(*COLOR_GRAY)
        self.cell(0, 5, f"Fecha de Emisión: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
        
        # Divider
        self.ln(10)
        self.set_draw_color(*COLOR_PRIMARY)
        self.set_line_width(0.5)
        self.line(10, 35, 200, 35)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Novenapp | {datetime.now().year} | Pág. {self.page_no()}', 0, 0, 'C')

    def sanitize_text(self, text):
        try:
            return text.encode('latin-1', 'replace').decode('latin-1')
        except:
            return text

    def chapter_title(self, label, icon=""):
        label = self.sanitize_text(label)
        self.set_font('Arial', 'B', 14)
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(0, 10, f"{icon} {label}", 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, text):
        self.set_font('Arial', '', 10)
        self.set_text_color(50, 50, 50)
        txt = self.sanitize_text(text)
        self.multi_cell(0, 5, txt)
        self.ln(3)

    def add_kpi_row(self, kpis):
        """
        Draws a row of 3 or 4 KPI boxes.
        kpis = [ {"label": "Presupuesto", "value": "$25M", "delta": "+5%"}, ... ]
        """
        self.ln(5)
        count = len(kpis)
        w = 190 / count
        h = 25
        
        y_start = self.get_y()
        
        for i, k in enumerate(kpis):
            x = 10 + (i * w)
            self.set_xy(x + 2, y_start)
            
            # Box Background
            self.set_fill_color(*COLOR_BG_LIGHT)
            self.set_draw_color(220, 220, 220)
            self.rect(x + 2, y_start, w - 4, h, 'FD')
            
            # Label
            self.set_xy(x + 5, y_start + 3)
            self.set_font('Arial', 'B', 8)
            self.set_text_color(*COLOR_GRAY)
            self.cell(w-10, 5, k['label'].encode('latin-1','replace').decode('latin-1'), 0, 1, 'L')
            
            # Value
            self.set_xy(x + 5, y_start + 10)
            self.set_font('Arial', 'B', 14)
            self.set_text_color(*COLOR_DARK)
            self.cell(w-10, 7, str(k['value']), 0, 1, 'L')
            
            # Delta/Sub
            if 'sub' in k and k['sub']:
                self.set_xy(x + 5, y_start + 18)
                self.set_font('Arial', '', 7)
                self.set_text_color(*COLOR_PRIMARY)
                self.cell(w-10, 4, k['sub'].encode('latin-1','replace').decode('latin-1'), 0, 1, 'L')

        self.set_y(y_start + h + 5)

    def add_table(self, df):
        if df.empty: return
        
        # Format
        self.set_font('Arial', 'B', 9)
        self.set_fill_color(230, 240, 235)
        self.set_text_color(0, 0, 0)
        
        col_width = 190 / len(df.columns)
        
        # Header
        for col in df.columns:
            sanitized = str(col).encode('latin-1', 'replace').decode('latin-1')
            self.cell(col_width, 8, sanitized, 1, 0, 'C', True)
        self.ln()
        
        # Body
        self.set_font('Arial', '', 8)
        self.set_text_color(50, 50, 50)
        
        for _, row in df.iterrows():
            for val in row:
                txt = str(val)
                try: txt = txt.encode('latin-1', 'replace').decode('latin-1')
                except: pass
                # Truncate
                if len(txt) > 28: txt = txt[:25] + "..."
                self.cell(col_width, 7, txt, 1, 0, 'L')
            self.ln()
        self.ln(5)

    def add_plot(self, fig, title=None):
        """Renders matplotlib figure"""
        if title:
            self.set_font('Arial', 'B', 11)
            self.set_text_color(*COLOR_DARK)
            self.cell(0, 8, title, 0, 1, 'L')
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            fig.savefig(tmp.name, bbox_inches='tight', dpi=130)
            path = tmp.name
        
        # Centered, max width
        self.image(path, x=15, w=180)
        self.ln(5)
        try: os.remove(path)
        except: pass

def generate_pdf_report(title, sections):
    pdf = NovAPP_PDF(title)
    pdf.alias_nb_pages()
    pdf.add_page()
    
    for sect in sections:
        stype = sect.get('type')
        if stype == 'kpi_row':
            pdf.add_kpi_row(sect['content'])
        elif stype == 'text':
             if sect.get('title'): pdf.chapter_title(sect['title'])
             pdf.chapter_body(sect['content'])
        elif stype == 'table':
             if sect.get('title'): pdf.chapter_title(sect['title'])
             pdf.add_table(sect['content'])
        elif stype == 'plot':
             pdf.add_plot(sect['content'], title=sect.get('title'))
        elif stype == 'new_page':
             pdf.add_page()
             
    return pdf.output()  # fpdf2 returns bytes directly with default dest or dest='S' depending on version, usually bytes is preferred for streamlit

def generate_excel(sheets_dict):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in sheets_dict.items():
            safe_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)
            # Column resizing removed to avoid xlsxwriter dependency
    output.seek(0)
    return output.getvalue()

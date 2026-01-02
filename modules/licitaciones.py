from modules import data
import pandas as pd
from datetime import datetime

# --- TENDERS (Licitaciones) ---

def create_tender(project_id, title, estimated_budget, tender_type, mercado_publico_id=""):
    """
    Creates a new Tender with specific type and ID.
    Types: L1, LE, LP, LQ, LR, LS
    """
    # Official UTM Values 2025
    utm_2025 = {
        1: 67429, 2: 67294, 3: 68034, 4: 68306, 5: 68648, 6: 68785,
        7: 68923, 8: 68647, 9: 69265, 10: 69265, 11: 69542, 12: 69542
    }
    
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Use 2025 table if current year is 2025, else fallback to Dec 2025 or hardcoded
    if current_year == 2025:
        UTM_VALUE = utm_2025.get(current_month, 69542)
    else:
        # Fallback for other years (or update as needed)
        UTM_VALUE = 69542 if current_year > 2025 else 67429
        
    status = 'Borrador'
    ssd_code = "" # Placeholder for future logic
    
    data.create_tender(project_id, title, estimated_budget, tender_type, UTM_VALUE, status, ssd_code, mercado_publico_id)

def get_tenders(project_id=None):
    return data.get_tenders(project_id)

def update_tender_status(tender_id, new_status):
    data.update_tender_status(tender_id, new_status)

def update_tender(tender_id, title, budget, mercado_publico_id, tender_type):
    data.update_tender(tender_id, title, budget, mercado_publico_id, tender_type)

def delete_tender(tender_id):
    data.delete_tender(tender_id)

# --- CONTRACTS ---

def create_contract(tender_id, contractor_name, rut, amount, start, end):
    data.create_contract(tender_id, contractor_name, rut, amount, start, end)

def get_contracts(tender_id=None):
    return data.get_contracts(tender_id)

# --- GUARANTEES ---

def create_guarantee(contract_id, g_type, amount, expiration):
    data.create_guarantee(contract_id, g_type, amount, expiration)

def update_guarantee(guarantee_id, g_type, amount, expiration, status):
    data.update_guarantee(guarantee_id, g_type, amount, expiration, status)

def delete_guarantee(guarantee_id):
    data.delete_guarantee(guarantee_id)

def update_contract(contract_id, contractor_name, rut, amount, start, end, status):
    data.update_contract(contract_id, contractor_name, rut, amount, start, end, status)

def delete_contract(contract_id):
    data.delete_contract(contract_id)

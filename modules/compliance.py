from modules import data
import pandas as pd

def get_subcontractors(project_id=None):
    return data.get_subcontractors(project_id)

def create_subcontractor(project_id, name, rut, email, phone, specialty, rep):
    data.create_subcontractor(project_id, name, rut, email, phone, specialty, rep)

def update_subcontractor(sub_id, name, rut, email, phone, specialty, rep):
    data.update_subcontractor_full(sub_id, name, rut, email, phone, specialty, rep)

def update_sub_status(sub_id, status):
    data.update_sub_status(sub_id, status)

def delete_subcontractor(sub_id):
    data.delete_subcontractor(sub_id)

def get_documents(sub_id):
    return data.get_compliance_documents(sub_id)

def create_document(sub_id, doc_type, status, expiration):
    data.create_compliance_document(sub_id, doc_type, status, expiration)

def delete_document(doc_id):
    data.delete_compliance_document(doc_id)

def get_compliance_stats(project_id=None):
    # Real calculation
    subs = data.get_subcontractors(project_id)
    if subs.empty:
        return {
            "active": 0, "pending_f30": 0, "blocked": 0,
            "chart_vigente": 0, "chart_por_vencer": 0, "chart_vencido": 0
        }
    
    # 1. Count Docs
    # We need to check docs for each sub. Ideally we'd have a join query.
    # For now, let's iterate (MVP optimization) or add a func in data.py
    # Iteration is okay for small n.
    
    pending_docs = 0
    blocked_subs = len(subs[subs['status'] == 'Bloqueado'])
    active_subs = len(subs[subs['status'] == 'Activo'])
    
    # Detailed counts for Chart
    c_vigente = 0
    c_vencido = 0
    c_por_vencer = 0
    
    from datetime import datetime
    today = datetime.now().date()
    
    for _, sub in subs.iterrows():
        docs = data.get_compliance_documents(sub['id'])
        if not docs.empty:
            for _, d in docs.iterrows():
                 # Status Check
                 is_vencido = False
                 is_por_vencer = False
                 
                 if d['status'] == 'Vencido':
                     is_vencido = True
                 elif d['status'] == 'Vigente':
                     # Check date
                     if d['expiration_date']:
                         try:
                             exp = datetime.strptime(d['expiration_date'], '%Y-%m-%d').date()
                             days = (exp - today).days
                             if days < 0:
                                 is_vencido = True
                             elif days < 30:
                                 is_por_vencer = True
                                 c_vigente += 1 # Still counted as Vigente technically? Or separate? 
                                 # Let's count properly for chart categories
                         except:
                             pass
                             
                 # Final Tally for Chart
                 if d['status'] == 'Pendiente':
                      c_vencido += 1 # Group pending with attention needed? Or separate? Let's treat as Vencido for 'Pending attention' metric but keep chart clean.
                      # Actually let's count strictly based on status for simplicity + date check
                 
                 # Recalculate strictly for the 3 buckets
                 if d['status'] == 'Vencido':
                     c_vencido += 1
                 elif d['status'] == 'Pendiente':
                     c_vencido += 1 # Treat simplified
                 elif d['status'] == 'Vigente':
                     if is_vencido: # Date override
                         c_vencido += 1
                     elif is_por_vencer:
                         c_por_vencer += 1
                     else:
                         c_vigente += 1
                         
                 # Update the simplistic pending_docs metric (Alerts)
                 if is_vencido or d['status'] == 'Pendiente' or is_por_vencer:
                     pending_docs += 1

    return {
        "active": active_subs, 
        "pending_f30": pending_docs, 
        "blocked": blocked_subs,
        "chart_vigente": c_vigente,
        "chart_por_vencer": c_por_vencer,
        "chart_vencido": c_vencido
    }

from modules import data
import pandas as pd

# --- PURCHASE ORDERS (Ordenes de Compra) ---

def create_purchase_order(project_id, provider_name, date, total_amount, order_number, description=""):
    """
    Creates a new Purchase Order (OC).
    """
    data.create_purchase_order(project_id, provider_name, date, total_amount, order_number, description)

def update_purchase_order(po_id, project_id, provider, amount, date, order_number, desc):
    data.update_purchase_order_full(po_id, project_id, provider, amount, date, order_number, desc)

def get_purchase_orders(project_id=None):
    return data.get_purchase_orders(project_id)

def approve_purchase_order(po_id):
    data.update_po_status(po_id, 'Aprobada')

def mark_as_paid(po_id):
    data.update_po_status(po_id, 'Pagada')

def delete_purchase_order(po_id):
    data.delete_purchase_order(po_id)

def get_financial_summary():
    """
    Returns KPIs for the finance dashboard.
    """
    df = get_purchase_orders()
    # Ensure columns exist (if empty df)
    if df.empty:
        return {"pending": 0, "approved": 0, "paid": 0, "total_pending_amount": 0}
        
    # Check if 'status' and 'total_amount' exist
    if 'status' not in df.columns:
        return {"pending": 0, "approved": 0, "paid": 0, "total_pending_amount": 0}

    pending = df[df['status'] == 'Pendiente']
    approved = df[df['status'] == 'Aprobada']
    paid = df[df['status'] == 'Pagada']
    
    return {
        "pending": len(pending),
        "approved": len(approved),
        "paid": len(paid),
        "total_pending_amount": pending['total_amount'].sum() if 'total_amount' in pending.columns else 0
    }

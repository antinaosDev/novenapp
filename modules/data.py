import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import time
import httpx
import httpcore

# Initialize Supabase Client
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["URL"]
    key = st.secrets["supabase"]["KEY"]
    return create_client(url, key)

supabase: Client = init_supabase()

def retry_db(func):
    """Decorator to retry Supabase queries on connection error."""
    def wrapper(*args, **kwargs):
        retries = 5
        base_delay = 2
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Check for ReadError, Resource unavailable, or Network errors
                error_msg = str(e)
                # Catch specific network related errors or string matches
                is_network_error = (
                    "Resource temporarily unavailable" in error_msg or 
                    "ReadError" in error_msg or 
                    "ConnectError" in error_msg or
                    isinstance(e, (httpx.ReadError, httpx.ConnectError, httpcore.ReadError, httpcore.ConnectError))
                )
                
                if is_network_error:
                    if attempt < retries - 1:
                        sleep_time = base_delay * (attempt + 1)
                        print(f"Database connection error: {e}. Retrying in {sleep_time}s... (Attempt {attempt+1}/{retries})")
                        time.sleep(sleep_time)
                        continue
                raise e
        return func(*args, **kwargs)
    return wrapper

def init_db():
    """Checks if connection works. Logic moved to Supabase Management via SQL Editor."""
    pass

# --- CRUD Functions ---

# Projects
def add_project(name, description, budget, start_date, end_date):
    data = {
        "name": name,
        "description": description,
        "budget_total": budget,
        "start_date": str(start_date),
        "end_date": str(end_date)
    }
    supabase.table("projects").insert(data).execute()

@retry_db
def get_projects():
    response = supabase.table("projects").select("*").execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        # Return with expected columns to prevent KeyError in views
        return pd.DataFrame(columns=[
            'id', 'name', 'description', 'budget_total', 
            'start_date', 'end_date', 'status', 'latitude', 'longitude'
        ])
    return df

def update_project(project_id, name, description, budget, start_date, end_date, status="Activo", lat=-33.4489, lon=-70.6693):
    data = {
        "name": name, 
        "description": description, 
        "budget_total": budget,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "status": status,
        "latitude": lat,
        "longitude": lon
    }
    supabase.table("projects").update(data).eq("id", project_id).execute()

def delete_project(project_id):
    # Manual Cascade Deletion to handle Foreign Keys
    try:
        # 1. Assignments
        supabase.table("project_assignments").delete().eq("project_id", project_id).execute()
        
        # 2. Operational Data (Tasks, Quality)
        supabase.table("tasks").delete().eq("project_id", project_id).execute()
        supabase.table("quality_logs").delete().eq("project_id", project_id).execute()
        supabase.table("phases").delete().eq("project_id", project_id).execute()
        
        # 2a. More Ops Data (Subcontractors & Lab Tests)
        # Handle Compliance Docs before Subcontractors
        try:
             subs_res = supabase.table("subcontractors").select("id").eq("project_id", project_id).execute()
             sub_ids = [s['id'] for s in subs_res.data]
             if sub_ids:
                 # Try to delete documents if table exists
                 try: supabase.table("compliance_documents").delete().in_("subcontractor_id", sub_ids).execute()
                 except: pass
        except:
             pass
        
        # Always attempt to delete subcontractors
        supabase.table("subcontractors").delete().eq("project_id", project_id).execute() 
             
        try:
             supabase.table("lab_tests").delete().eq("project_id", project_id).execute()
        except:
             pass # Lab tests might not exist or schema diff
        
        # 3. Resources/Expenses (Delete Expenses first as they link to Faenas)
        supabase.table("expenses").delete().eq("project_id", project_id).execute()
        supabase.table("faenas").delete().eq("project_id", project_id).execute()
        
        # 4. Purchase Orders
        supabase.table("purchase_orders").delete().eq("project_id", project_id).execute()
        
        # 5. Tenders, Contracts & Guarantees (Deep Clean)
        tenders_res = supabase.table("tenders").select("id").eq("project_id", project_id).execute()
        for tender in tenders_res.data:
            # Delete Contracts for this tender
            contracts_res = supabase.table("contracts").select("id").eq("tender_id", tender['id']).execute()
            for contract in contracts_res.data:
                # Delete Guarantees
                supabase.table("guarantees").delete().eq("contract_id", contract['id']).execute()
                # Delete Contract
                supabase.table("contracts").delete().eq("id", contract['id']).execute()
            
            # Delete Tender
            supabase.table("tenders").delete().eq("id", tender['id']).execute()
            
        # 6. Budget Items & Comments (New)
        supabase.table("budget_items").delete().eq("project_id", project_id).execute()
        supabase.table("comments").delete().eq("project_id", project_id).execute()
        
        # Finally delete Project
        supabase.table("projects").delete().eq("id", project_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting project: {e}")
        return False

@retry_db
def get_projects_expiring_soon(days_threshold):
    """Returns active projects ending within the next X days."""
    try:
        from datetime import datetime, timedelta
        now = datetime.now()
        target_date = now + timedelta(days=days_threshold)
        
        # Filter: end_date >= today AND end_date <= target_date AND status != 'Completado'
        today_str = now.strftime('%Y-%m-%d')
        target_str = target_date.strftime('%Y-%m-%d')
        
        # Note: Supabase-py simple filter might need chaining
        # .gte("end_date", today_str).lte("end_date", target_str)
        
        response = supabase.table("projects").select("*")\
            .neq("status", "Completado")\
            .neq("status", "En Cierre")\
            .gte("end_date", today_str)\
            .lte("end_date", target_str)\
            .execute()
            
        return pd.DataFrame(response.data)
    except Exception as e:
        print(f"Error checking project deadlines: {e}")
        return pd.DataFrame()

# Contracts & Guarantees Expiration
@retry_db
def get_contracts_expiring_soon(days_threshold):
    try:
        from datetime import datetime, timedelta
        now = datetime.now()
        target_date = now + timedelta(days=days_threshold)
        today_str = now.strftime('%Y-%m-%d')
        target_str = target_date.strftime('%Y-%m-%d')
        
        response = supabase.table("contracts").select("*")\
            .neq("status", "Terminado")\
            .gte("end_date", today_str)\
            .lte("end_date", target_str)\
            .execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        print(f"Error checking contracts: {e}")
        return pd.DataFrame()

@retry_db
def get_guarantees_expiring_soon(days_threshold):
    try:
        from datetime import datetime, timedelta
        now = datetime.now()
        target_date = now + timedelta(days=days_threshold)
        today_str = now.strftime('%Y-%m-%d')
        target_str = target_date.strftime('%Y-%m-%d')
        
        response = supabase.table("guarantees").select("*")\
            .eq("status", "Vigente")\
            .gte("expiration_date", today_str)\
            .lte("expiration_date", target_str)\
            .execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        print(f"Error checking guarantees: {e}")
        return pd.DataFrame()

# Faenas
def add_faena(project_id, name, supervisor):
    data = {
        "project_id": project_id,
        "name": name,
        "supervisor": supervisor
    }
    supabase.table("faenas").insert(data).execute()

def get_faenas(project_id=None):
    query = supabase.table("faenas").select("*")
    if project_id:
        query = query.eq("project_id", project_id)
    response = query.execute()
    return pd.DataFrame(response.data)

def update_faena(faena_id, name, supervisor):
    data = {"name": name, "supervisor": supervisor}
    supabase.table("faenas").update(data).eq("id", faena_id).execute()

def delete_faena(faena_id):
    # Unlink expenses first to preserve financial record but remove faena tag
    # or Delete them? User deleted project implies deleting expenses, but deleting only Faena 
    # usually means just removing the operational front. We'll set to NULL to keep the expense in the project.
    try:
        supabase.table("expenses").update({"faena_id": None}).eq("faena_id", faena_id).execute()
        supabase.table("faenas").delete().eq("id", faena_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting faena: {e}")
        return False

# Units
def add_unit(name, type, details):
    data = {
        "name": name,
        "type": type,
        "details": details
    }
    supabase.table("units").insert(data).execute()

def get_units():
    response = supabase.table("units").select("*").execute()
    return pd.DataFrame(response.data)

# Expenses
def add_expense(date, project_id, faena_id, unit_id, category, amount, description):
    data = {
        "date": str(date),
        "project_id": project_id,
        "faena_id": faena_id,
        "unit_id": unit_id,
        "category": category,
        "amount": amount,
        "description": description
    }
    supabase.table("expenses").insert(data).execute()

@retry_db
def get_expenses_df(project_id=None):
    # Supabase join syntax is: "col, relation(col)"
    query = supabase.table("expenses").select(
        "id, date, amount, category, description, project_id, project:projects(name), faena:faenas(name), unit:units(name)"
    ).order("date", desc=True)
    
    if project_id:
        query = query.eq("project_id", project_id)
        
    response = query.execute()
    data = response.data
    
    # Flatten JSON structure for DataFrame
    flat_data = []
    for row in data:
        new_row = row.copy()
        new_row['project'] = row['project']['name'] if row.get('project') else None
        new_row['faena'] = row['faena']['name'] if row.get('faena') else None
        new_row['unit'] = row['unit']['name'] if row.get('unit') else None
        flat_data.append(new_row)
        
    if not flat_data:
        return pd.DataFrame(columns=[
            'id', 'date', 'amount', 'category', 'description', 
            'project_id', 'project', 'faena', 'unit'
        ])
        
    return pd.DataFrame(flat_data)

@retry_db
def get_kpis():
    # --- 1. Finance ---
    projs = get_projects()
    total_budget = projs['budget_total'].sum() if not projs.empty else 0
    
    # Calculate Total Spent using Purchase Orders (OC) for consistency
    po_res = supabase.table("purchase_orders").select("total_amount, status").execute()
    po_df = pd.DataFrame(po_res.data)
    if not po_df.empty:
        # Filter out Rejected
        total_spent = po_df[po_df['status'] != 'Rechazada']['total_amount'].sum()
        # Also sum 'Pendiente'? Yes, usually 'Ejecutado' includes pending commitments in construction (Comprometido).
        # Or strictly 'Aprobada'? The Project Manager view used: status != 'Rechazada' (meaning Pending + Approved).
        # We will match that logic.
    else:
        total_spent = 0

    # --- 2. Lean (Global Average PPC) ---
    # Fetch all tasks to calc global PPC (Week-based approximation)
    tasks_res = supabase.table("tasks").select("status").execute()
    tasks_df = pd.DataFrame(tasks_res.data)
    if not tasks_df.empty:
        total_tasks = len(tasks_df)
        completed_tasks = len(tasks_df[tasks_df['status'] == 'Completado'])
        global_ppc = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
    else:
        global_ppc = 0

    # --- 3. Compliance (Subcontractors) ---
    subs_res = supabase.table("subcontractors").select("status").execute()
    subs_df = pd.DataFrame(subs_res.data)
    active_subs = len(subs_df[subs_df['status'] == 'Activo']) if not subs_df.empty else 0
    total_subs = len(subs_df) if not subs_df.empty else 0

    # --- 4. Tenders (Open) ---
    tenders_res = supabase.table("tenders").select("status").eq("status", "Publicada").execute()
    open_tenders = len(tenders_res.data)

    return {
        "total_spent": total_spent,
        "total_budget": total_budget,
        "global_ppc": global_ppc,
        "active_subs": active_subs,
        "total_subs": total_subs,
        "open_tenders": open_tenders
    }

@retry_db
def get_dashboard_alerts():
    alerts = []
    
    # 1. Pending Purchase Orders (Approvals)
    pending_pos_res = supabase.table("purchase_orders").select("id, order_number, provider_name, total_amount").eq("status", "Pendiente").execute()
    for po in pending_pos_res.data:
        identifier = po.get('order_number') or po['id']
        alerts.append({
            "scope": "Finanzas",
            "message": f"OC #{identifier} pendiente de aprobación",
            "detail": f"Proveedor: {po['provider_name']} - ${po['total_amount']:,.0f}",
            "severity": "warning"
        })
        
    # 2. Expiring/Expired Documents (Compliance)
    # Simple check on all docs, ideally filtered by date. Fetching all for now as dataset is small-ish
    docs_res = supabase.table("compliance_documents").select("document_type, expiration_date, subcontractor:subcontractors(name)").execute()
    today = datetime.now().date()
    for doc in docs_res.data:
        if doc['expiration_date']:
            exp_date = datetime.strptime(doc['expiration_date'], '%Y-%m-%d').date()
            days_left = (exp_date - today).days
            
            sub_name = doc['subcontractor']['name'] if doc.get('subcontractor') else "Desconocido"
            
            if days_left < 0:
                alerts.append({
                    "scope": "Subcontratos",
                    "message": f"Documento Vencido: {sub_name}",
                    "detail": f"{doc['document_type']} venció el {exp_date}",
                    "severity": "error"
                })
            elif days_left <= 7:
                 alerts.append({
                    "scope": "Subcontratos",
                    "message": f"Por Vencer: {sub_name}",
                    "detail": f"{doc['document_type']} vence en {days_left} días",
                    "severity": "warning"
                })

    # 3. Budget Overrun (Simple check: Spent > Budget per project)
    # Requires fetching both. We reuse get_kpis logic partly
    projs = get_projects()
    for _, prow in projs.iterrows():
         # Get expenses for this project
         # This is expensive in loop, but OK for small app. Optimization: aggregate in SQL/KPIs function
         # We'll skip complex one for now or do a quick check if we had expense metrics
         pass 

    return alerts

def get_recent_expenses(limit=5):
    # Select relations 
    response = supabase.table("expenses").select("date,description,category,amount").order("date", desc=True).limit(limit).execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        return pd.DataFrame(columns=['date', 'description', 'category', 'amount'])
    return df

# --- Generic Helper to replace old run_query for complex selects ---
def run_query(query_str, params=None, return_df=True):
    """
    DEPRECATED: Compatibility layer. 
    It is extremely hard to parse generic SQL to Supabase API calls.
    We will now log a warning and try to return empty or handle specific known queries.
    """
    print(f"WARNING: RAW SQL ATTEMPTED: {query_str}")
    
    # Naive handlers for specific known queries used in other modules
    # 1. Users login
    if "SELECT * FROM users WHERE username" in query_str:
        user = params[0]
        res = supabase.table("users").select("*").eq("username", user).execute()
        return pd.DataFrame(res.data)
    
    # 2. Insert User (Auth)
    if "INSERT INTO users" in query_str:
        # Params: username, password_hash, full_name, role
        # We need to extract them from params, usually passed as tuple
        data = {
            "username": params[0],
            "password_hash": params[1],
            "full_name": params[2],
            "role": params[3]
        }
        supabase.table("users").insert(data).execute()
        return True

    # 3. Teams / Project Assignments
    # We'll need to refactor teams.py likely, but let's try
    if "SELECT * FROM project_assignments" in query_str:
         res = supabase.table("project_assignments").select("*").execute()
         return pd.DataFrame(res.data)

    # Fallback for simple selects
    if query_str.startswith("SELECT * FROM"):
        # Extract table name
        parts = query_str.split()
        if len(parts) >= 4:
             table = parts[3]
             res = supabase.table(table).select("*").execute()
             return pd.DataFrame(res.data)

    return pd.DataFrame() # Return empty to avoid crash

# --- Auth & Users Support ---
def get_user_by_username(username):
    response = supabase.table("users").select("*").eq("username", username).execute()
    return pd.DataFrame(response.data)

def create_user_record(username, password_hash, full_name, role, email=None):
    data = {
        "username": username,
        "password_hash": password_hash,
        "full_name": full_name,
        "role": role,
        "email": email
    }
    supabase.table("users").insert(data).execute()

# --- Teams / Utils ---
def get_all_users():
    try:
        response = supabase.table("users").select("id, full_name, role, username, email").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        # Fallback if email column missing (SQL not run yet)
        response = supabase.table("users").select("id, full_name, role, username").execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['email'] = None
        return df

def get_users_full():
    response = supabase.table("users").select("*").order("id").execute()
    return pd.DataFrame(response.data)

def update_user(user_id, username, full_name, role, password_hash=None, email=None):
    data = {"username": username, "full_name": full_name, "role": role, "email": email}
    if password_hash:
        data["password_hash"] = password_hash
    supabase.table("users").update(data).eq("id", user_id).execute()

def delete_user(user_id):
    supabase.table("users").delete().eq("id", user_id).execute()

# --- Roles Management ---
def get_roles():
    try:
        response = supabase.table("roles").select("*").order("id").execute()
        return pd.DataFrame(response.data)
    except Exception:
        # Fallback if table doesn't exist yet
        return pd.DataFrame({
            'id': range(1, 7),
            'name': ["Programador", "Administrador", "Residente de Obra", "Capataz", "Bodeguero", "Prevencionista"],
            'description': ["Acceso Total", "Gestión", "Proyectos", "Cuadrillas", "Recursos", "Seguridad"]
        })

def add_role(name, description=""):
    data = {"name": name, "description": description}
    supabase.table("roles").insert(data).execute()

def delete_role(role_id):
    supabase.table("roles").delete().eq("id", role_id).execute()

def get_project_assignments(project_id):
    # Join with users to get names
    # select *, users(full_name)
    response = supabase.table("project_assignments").select("id, role, assigned_at, user:users(full_name)").eq("project_id", project_id).execute()
    data = response.data
    flat = []
    for row in data:
         new = row.copy()
         new['full_name'] = row['user']['full_name'] if row.get('user') else 'Unknown'
         flat.append(new)
    return pd.DataFrame(flat)

def get_all_project_assignments():
    response = supabase.table("project_assignments").select("id, role, assigned_at, user:users(full_name, username), project:projects(name)").execute()
    data = response.data
    flat = []
    for row in data:
         user_data = row.get('user') or {}
         new = {
             'id': row['id'],
             'role': row['role'],
             'assigned_at': row['assigned_at'],
             'full_name': user_data.get('full_name', 'Unknown'),
             'username': user_data.get('username', ''),
             'project_name': row['project']['name'] if row.get('project') else 'Unknown'
         }
         flat.append(new)
    return pd.DataFrame(flat)

def assign_user_to_project(project_id, user_id, role, assigned_at=None):
    data = {"project_id": project_id, "user_id": user_id, "role": role}
    if assigned_at:
        data['assigned_at'] = str(assigned_at)
        
    # Check if exists (Upsert logic or Check then insert)
    # Supabase upsert: Need unique constraint on project_id, user_id
    # Or just select first
    existing = supabase.table("project_assignments").select("id").eq("project_id", project_id).eq("user_id", user_id).execute()
    if existing.data:
         # Update
         update_payload = {"role": role}
         if assigned_at:
             update_payload['assigned_at'] = str(assigned_at)
         supabase.table("project_assignments").update(update_payload).eq("id", existing.data[0]['id']).execute()
    else:
         supabase.table("project_assignments").insert(data).execute()

def remove_project_assignment(assignment_id):
    supabase.table("project_assignments").delete().eq("id", assignment_id).execute()

# --- Budget ---
def get_budget_items(project_id):
    response = supabase.table("budget_items").select("*").eq("project_id", project_id).execute()
    return pd.DataFrame(response.data)

def create_budget_item(project_id, name, category, amount):
    data = {
        "project_id": project_id,
        "item_name": name,
        "category": category,
        "estimated_amount": amount
    }
    supabase.table("budget_items").insert(data).execute()

def update_budget_item(item_id, name, category, amount):
    supabase.table("budget_items").update({
        "item_name": name,
        "category": category,
        "estimated_amount": amount
    }).eq("id", item_id).execute()

def delete_budget_item(item_id):
    supabase.table("budget_items").delete().eq("id", item_id).execute()

# --- Finance Support ---
def create_purchase_order(project_id, provider_name, date, total_amount, order_number, description=""):
    data = {
        "project_id": int(project_id), 
        "provider_name": provider_name, 
        "date": str(date), 
        "total_amount": float(total_amount), 
        "description": description,
        "status": 'Pendiente',
        "order_number": order_number
    }
    supabase.table("purchase_orders").insert(data).execute()

def get_purchase_orders(project_id=None):
    # Select with project name
    query = supabase.table("purchase_orders").select("*, projects(name)").order("date", desc=True)
    if project_id:
        query = query.eq("project_id", project_id)
    response = query.execute()
    
    data = response.data
    # Flatten
    for row in data:
        if row.get('projects'):
            row['project_name'] = row['projects']['name']
        else:
            row['project_name'] = 'N/A'
            
    return pd.DataFrame(data)

def update_purchase_order_full(po_id, project_id, provider, amount, date, order_number, desc):
     supabase.table("purchase_orders").update({
         "project_id": project_id,
         "provider_name": provider,
         "total_amount": amount,
         "date": str(date),
         "order_number": order_number,
         "description": desc
     }).eq("id", po_id).execute()

def update_po_status(po_id, status):
    supabase.table("purchase_orders").update({"status": status}).eq("id", po_id).execute()


def delete_purchase_order(po_id):
    supabase.table("purchase_orders").delete().eq("id", po_id).execute()

# --- Compliance (Subcontractors) ---
@retry_db
def get_subcontractors(project_id=None):
    query = supabase.table("subcontractors").select("*")
    if project_id:
        query = query.eq("project_id", project_id)
    response = query.execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        return pd.DataFrame(columns=['id', 'project_id', 'name', 'rut', 'contact_email', 'contact_phone', 'specialty', 'representative', 'status'])
    return df

def create_subcontractor(project_id, name, rut, email, phone, specialty, rep):
    data = {
        "project_id": project_id,
        "name": name, 
        "rut": rut, 
        "contact_email": email,
        "contact_phone": phone,
        "specialty": specialty,
        "representative": rep,
        "status": "Activo"
    }
    supabase.table("subcontractors").insert(data).execute()

def update_subcontractor_full(sub_id, name, rut, email, phone, specialty, rep):
    supabase.table("subcontractors").update({
        "name": name, 
        "rut": rut, 
        "contact_email": email,
        "contact_phone": phone,
        "specialty": specialty,
        "representative": rep
    }).eq("id", sub_id).execute()

def update_sub_status(sub_id, status):
    supabase.table("subcontractors").update({"status": status}).eq("id", sub_id).execute()

def delete_subcontractor(sub_id):
    supabase.table("subcontractors").delete().eq("id", sub_id).execute()

# --- Compliance Documents ---
@retry_db
def get_compliance_documents(sub_id):
    response = supabase.table("compliance_documents").select("*").eq("subcontractor_id", sub_id).order("last_updated", desc=True).execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        return pd.DataFrame(columns=['id', 'subcontractor_id', 'document_type', 'status', 'expiration_date', 'last_updated'])
    return df

def create_compliance_document(sub_id, doc_type, status, expiration):
    data = {
        "subcontractor_id": sub_id,
        "document_type": doc_type,
        "status": status,
        "expiration_date": str(expiration)
    }
    supabase.table("compliance_documents").insert(data).execute()

def delete_compliance_document(doc_id):
    supabase.table("compliance_documents").delete().eq("id", doc_id).execute()

# --- Quality ---
@retry_db
def get_quality_logs(project_id=None):
    query = supabase.table("quality_logs").select("*").order("date", desc=True)
    if project_id:
        query = query.eq("project_id", project_id)
    response = query.execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        return pd.DataFrame(columns=['id', 'project_id', 'title', 'description', 'inspector_name', 'signer_name', 'date'])
    return df

def create_quality_log(project_id, title, description, inspector, signer_name):
    data = {
        "project_id": project_id, 
        "title": title, 
        "description": description, 
        "inspector_name": inspector,
        "signer_name": signer_name
    }
    supabase.table("quality_logs").insert(data).execute()

def update_quality_log(log_id, title, description, inspector, signer_name):
    supabase.table("quality_logs").update({
        "title": title, 
        "description": description, 
        "inspector_name": inspector,
        "signer_name": signer_name
    }).eq("id", log_id).execute()

def delete_quality_log(log_id):
    supabase.table("quality_logs").delete().eq("id", log_id).execute()

# --- Lab Tests ---
@retry_db
def get_lab_tests(project_id=None):
    query = supabase.table("lab_tests").select("*").order("test_date", desc=True)
    if project_id:
        query = query.eq("project_id", project_id)
    response = query.execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        return pd.DataFrame(columns=['id', 'project_id', 'test_type', 'test_date', 'result', 'observation'])
    return df

def create_lab_test(project_id, test_type, date, result, obs):
    data = {
        "project_id": project_id,
        "test_type": test_type,
        "test_date": str(date),
        "result": result,
        "observation": obs
    }
    supabase.table("lab_tests").insert(data).execute()

def update_lab_test(test_id, test_type, date, result, obs):
    supabase.table("lab_tests").update({
        "test_type": test_type,
        "test_date": str(date),
        "result": result,
        "observation": obs
    }).eq("id", test_id).execute()

def delete_lab_test(test_id):
    supabase.table("lab_tests").delete().eq("id", test_id).execute()

# --- Lean (Tasks) ---
@retry_db
def get_tasks(project_id=None):
    query = supabase.table("tasks").select("*").order("start_date")
    if project_id:
        query = query.eq("project_id", project_id)
    response = query.execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        return pd.DataFrame(columns=['id', 'project_id', 'name', 'start_date', 'end_date', 'status'])
    return df

def create_task(project_id, name, start, end, status="Por Hacer"):
    data = {
        "project_id": project_id, 
        "name": name, 
        "start_date": str(start), 
        "end_date": str(end), 
        "status": status
    }
    supabase.table("tasks").insert(data).execute()

def update_task_status(task_id, new_status):
    supabase.table("tasks").update({"status": new_status}).eq("id", task_id).execute()

def update_task_details(task_id, name):
    supabase.table("tasks").update({"name": name}).eq("id", task_id).execute()

def delete_task(task_id):
    supabase.table("tasks").delete().eq("id", task_id).execute()

# --- Tenders ---
def create_tender(project_id, title, estimated_budget, tender_type, utm_value, status, ssd_code, mercado_publico_id=""):
    data = {
         "project_id": project_id, "title": title, "type": tender_type, 
         "budget_estimated": estimated_budget, "utm_value_at_creation": utm_value,
         "status": status, "ssd_code": ssd_code, "mercado_publico_id": mercado_publico_id
    }
    supabase.table("tenders").insert(data).execute()

@retry_db
def get_tenders(project_id=None):
    query = supabase.table("tenders").select("*")
    if project_id:
        query = query.eq("project_id", project_id)
    response = query.execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        return pd.DataFrame(columns=[
            'id', 'project_id', 'title', 'type', 'budget_estimated', 
            'utm_value_at_creation', 'status', 'ssd_code', 'mercado_publico_id'
        ])
    return df

def update_tender_status(tender_id, new_status):
    supabase.table("tenders").update({"status": new_status}).eq("id", tender_id).execute()

def update_tender(tender_id, title, budget, mercado_publico_id, tender_type):
    supabase.table("tenders").update({
        "title": title, 
        "budget_estimated": budget,
        "mercado_publico_id": mercado_publico_id,
        "type": tender_type
    }).eq("id", tender_id).execute()

def delete_tender(tender_id):
    supabase.table("tenders").delete().eq("id", tender_id).execute()

# --- Contracts ---
def create_contract(tender_id, contractor_name, rut, amount, start, end):
    data = {
        "tender_id": tender_id, "contractor_name": contractor_name, "rut_contractor": rut,
        "amount": amount, "start_date": str(start), "end_date": str(end)
    }
    supabase.table("contracts").insert(data).execute()

@retry_db
def get_contracts(tender_id=None):
     query = supabase.table("contracts").select("*")
     if tender_id:
         query = query.eq("tender_id", tender_id)
     res = query.execute()
     df = pd.DataFrame(res.data)
     if df.empty:
         return pd.DataFrame(columns=[
             'id', 'tender_id', 'contractor_name', 'rut_contractor', 
             'amount', 'start_date', 'end_date', 'status'
         ])
     return df

def create_guarantee(contract_id, g_type, amount, expiration):
    data = {"contract_id": contract_id, "type": g_type, "amount": amount, "expiration_date": str(expiration)}
    supabase.table("guarantees").insert(data).execute()

def update_guarantee(guarantee_id, g_type, amount, expiration, status):
    data = {"type": g_type, "amount": amount, "expiration_date": str(expiration), "status": status}
    supabase.table("guarantees").update(data).eq("id", guarantee_id).execute()

def delete_guarantee(guarantee_id):
    supabase.table("guarantees").delete().eq("id", guarantee_id).execute()

def update_contract(contract_id, contractor_name, rut, amount, start, end, status):
    data = {
        "contractor_name": contractor_name, "rut_contractor": rut,
        "amount": amount, "start_date": str(start), "end_date": str(end),
        "status": status
    }
    supabase.table("contracts").update(data).eq("id", contract_id).execute()

def delete_contract(contract_id):
    # Cascade delete guarantees first
    supabase.table("guarantees").delete().eq("contract_id", contract_id).execute()
    supabase.table("contracts").delete().eq("id", contract_id).execute()

# --- Phases ---
@retry_db
def get_phases(project_id):
    res = supabase.table("phases").select("*").eq("project_id", project_id).execute()
    return pd.DataFrame(res.data)

def add_phase(project_id, name, start, end):
    data = {"project_id": project_id, "name": name, "start_date": str(start), "end_date": str(end)}
    supabase.table("phases").insert(data).execute()

def update_phase(phase_id, name, start, end):
    data = {"name": name, "start_date": str(start), "end_date": str(end)}
    supabase.table("phases").update(data).eq("id", phase_id).execute()

def delete_phase(phase_id):
    supabase.table("phases").delete().eq("id", phase_id).execute()

# --- Comments ---
# --- Comments ---
@retry_db
def get_comments(project_id):
    # Select all fields including ID and user_id for permissions
    res = supabase.table("comments").select("id, content, timestamp, user_id, user:users(username)").eq("project_id", project_id).order("timestamp", desc=True).execute()
    data = res.data
    flat = []
    for row in data:
        new = row.copy()
        new['username'] = row['user']['username'] if row.get('user') else 'Unknown'
        flat.append(new)
    return pd.DataFrame(flat)

def add_comment(project_id, user_id, content):
    data = {"project_id": project_id, "user_id": user_id, "content": content}
    supabase.table("comments").insert(data).execute()

def update_comment(comment_id, content):
    supabase.table("comments").update({"content": content}).eq("id", comment_id).execute()

def delete_comment(comment_id):
    supabase.table("comments").delete().eq("id", comment_id).execute()

def update_project_config(project_id, status, lat, lon):
     supabase.table("projects").update({
         "status": status, "latitude": lat, "longitude": lon
     }).eq("id", project_id).execute()

# --- Teams & Stats ---
@retry_db
def get_global_team_stats():
    # Fetch all assignments with project names
    # Table: project_assignments (id, project_id, user_id, role)
    # Join projects to get name
    res = supabase.table("project_assignments").select("role, project_id, projects(name, status)").execute()
    data = res.data
    
    # Filter only active projects if needed, or keeping all
    # Let's keep Active only
    active_data = [d for d in data if d.get('projects') and d['projects']['status'] == 'Activo']
    
    if not active_data:
        return {
            "total_personnel": 0,
            "roles_df": pd.DataFrame(columns=['role', 'count']),
            "projects_df": pd.DataFrame(columns=['project_name', 'count'])
        }

    df = pd.DataFrame(active_data)
    df['project_name'] = df['projects'].apply(lambda x: x['name'])
    
    # 1. Total Personnel
    total = len(df)
    
    # 2. Roles Distribution
    roles_df = df['role'].value_counts().reset_index()
    roles_df.columns = ['role', 'count']
    
    # 3. Personnel per Project
    projs_df = df['project_name'].value_counts().reset_index()
    projs_df.columns = ['project_name', 'count']
    
    return {
        "total_personnel": total,
        "roles_df": roles_df,
        "projects_df": projs_df
    }

# --- Finance (Purchase Orders) ---
@retry_db
def get_purchase_orders(project_id=None):
    """Fetches all POs with Project Names."""
    try:
        # Join with Projects table to get names
        query = supabase.table("purchase_orders").select("*, projects(name)").order("date", desc=True)
        if project_id:
             query = query.eq("project_id", project_id)
             
        response = query.execute()
        if response.data:
            df = pd.DataFrame(response.data)
            # Flatten project name
            if 'projects' in df.columns:
                 df['project_name'] = df['projects'].apply(lambda x: x['name'] if x else 'Sin Proyecto')
            else:
                 df['project_name'] = "Desconocido"
            return df
        return pd.DataFrame(columns=[
            'id', 'project_id', 'provider_name', 'date', 
            'total_amount', 'description', 'status', 'order_number', 
            'projects', 'project_name'
        ])
    except Exception as e:
        print(f"Error fetching POs: {e}")
        return pd.DataFrame(columns=[
            'id', 'project_id', 'provider_name', 'date', 
            'total_amount', 'description', 'status', 'order_number', 
            'projects', 'project_name'
        ])

# --- Admin / Config ---
def get_config(key, default=None):
    try:
        response = supabase.table("system_config").select("value").eq("key", key).execute()
        if response.data:
            return response.data[0]['value']
        return default
    except Exception as e:
        # print(f"Error getting config {key}: {e}") # Silent fail default
        return default

def set_config(key, value):
    try:
        data = {"key": key, "value": str(value)}
        supabase.table("system_config").upsert(data).execute()
        return True, "Success"
    except Exception as e:
        print(f"Error setting config {key}: {e}")
        return False, str(e)

# --- AI Usage ---
def log_ai_usage(user_id, tokens):
    try:
        supabase.table("ai_usage_logs").insert({
            "user_id": user_id,
            "tokens_used": tokens
        }).execute()
    except Exception as e:
         print(f"Error logging AI usage: {e}")

# --- AI Usage (Global Daily Counter) ---
def get_daily_ai_usage_count():
    """Returns the total AI calls made today globally."""
    try:
        from datetime import datetime
        today_key = f"ai_usage_{datetime.now().strftime('%Y-%m-%d')}"
        val = get_config(today_key, "0")
        return int(val)
    except:
        return 0

def increment_daily_ai_usage():
    """Increments the global counter for today."""
    try:
        from datetime import datetime
        today_key = f"ai_usage_{datetime.now().strftime('%Y-%m-%d')}"
        current = get_daily_ai_usage_count()
        set_config(today_key, current + 1)
        return current + 1
    except Exception as e:
        print(f"Error incrementing AI usage: {e}")
        return 999

def reset_ai_usage():
    try:
        from datetime import datetime
        today_key = f"ai_usage_{datetime.now().strftime('%Y-%m-%d')}"
        set_config(today_key, 0)
        return True
    except Exception as e:
        print(f"Error resetting: {e}")
        return False

# --- Notification Usage (Monthly) ---
def get_monthly_notif_count():
    try:
        from datetime import datetime
        month_key = f"notif_usage_{datetime.now().strftime('%Y-%m')}"
        val = get_config(month_key, "0")
        return int(val)
    except:
        return 0

def increment_monthly_notif():
    try:
        from datetime import datetime
        month_key = f"notif_usage_{datetime.now().strftime('%Y-%m')}"
        current = get_monthly_notif_count()
        set_config(month_key, current + 1)
        return current + 1
    except:
        return 999

def get_notif_limit():
    val = get_config("notif_monthly_limit", "100")
    try:
        return int(val)
    except:
        return 100

def get_ai_call_limit():
    val = get_config("ai_daily_limit", "3") # Default to 3 as requested
    try:
        return int(val)
    except:
        return 3





from modules import data, licitaciones, finance, lean, compliance, quality
from datetime import datetime, timedelta
import random
import pandas as pd
from supabase import create_client

# Direct Supabase access for specific population needs not covered by module functions
supabase = data.supabase

print("Starting Supabase Population...")

# --- USERS ---
print("Populating Users...")
dummy_users = [
    ("Juan Pérez", "jefe_obra", "Jefe de Cuadrilla", "jperez@nov.cl"),
    ("Maria González", "prevencion", "Prevencionista", "mgonzalez@nov.cl"),
    ("Carlos Ruiz", "capataz", "Capataz", "cruiz@nov.cl"),
    ("Ana López", "admin_obra", "Administrador de Obra", "alopez@nov.cl"),
    ("Admin User", "admin", "Administrador Principal", "admin@nov.cl")
]

user_ids = []

for name, role, full_name, email in dummy_users:
    # Check if exists
    res = supabase.table("users").select("id").eq("username", email).execute()
    if not res.data:
        # Create user
        # Hash for "123": $2b$12$eX/././././././././././.e (fake) or real one if needed.
        # Let's use a simple hash that bcrypt accepts. 
        # $2b$12$123456789012345678901uXyZ is invalid format potentially.
        # Let's use the one from auth.py or a valid bcrypt hash
        # Use a known valid hash for "123" or similar:
        # $2b$12$e.g./... is hard to fake without lib.
        # But for mock data we can just put a placeholder if we don't login, 
        # OR we use the auth.hash_password if we import it.
        # Let's import auth to be nice.
        from modules import auth
        pw_hash = auth.hash_password("123")
        
        user_data = {
            "username": email,
            "password_hash": pw_hash,
            "full_name": full_name,
            "role": role
        }
        r = supabase.table("users").insert(user_data).execute()
        uid = r.data[0]['id']
        print(f"Created User: {full_name}")
    else:
        uid = res.data[0]['id']
    
    user_ids.append(uid)

# --- PROJECTS ---
print("Populating Projects...")
projects_data = [
    ("Torre Central", "Rascacielos de 45 pisos en el centro financiero.", 12000000000, "2024-01-15", "2026-12-30", -33.4372, -70.6506),
    ("Residencial Los Álamos", "Conjunto habitacional de 5 torres.", 4500000000, "2024-03-01", "2025-11-20", -33.4169, -70.6067),
    ("Centro Comercial Norte", "Mall de 3 niveles con estacionamiento subterráneo.", 8500000000, "2024-05-10", "2026-06-15", -33.3662, -70.6970)
]

project_ids = []
for p_data in projects_data:
    # Check if exists
    res = supabase.table("projects").select("id").eq("name", p_data[0]).execute()
    if not res.data:
        new_proj = {
            "name": p_data[0],
            "description": p_data[1],
            "budget_total": p_data[2],
            "start_date": p_data[3],
            "end_date": p_data[4],
            "latitude": p_data[5],
            "longitude": p_data[6],
            "status": "Activo"
        }
        r = supabase.table("projects").insert(new_proj).execute()
        pid = r.data[0]['id']
        print(f"Created Project: {p_data[0]}")
    else:
        pid = res.data[0]['id']
    project_ids.append(pid)

active_pid = project_ids[0]

# --- TEAMS ---
print("Assigning Teams...")
for uid in user_ids:
    # Check
    res = supabase.table("project_assignments").select("*").eq("project_id", active_pid).eq("user_id", uid).execute()
    if not res.data:
        data.assign_user_to_project(active_pid, uid, "Staff")
        print(f"Assigned user {uid} to project {active_pid}")

# --- TENDERS ---
print("Populating Tenders...")
tender_titles = [
    "Instalación de Faenas y Cierros",
    "Movimiento de Tierras Masivo",
    "Obra Gruesa - Hormigonado Torre A",
    "Instalación Eléctrica e Iluminación"
]
df_t = licitaciones.get_tenders(active_pid)
if df_t.empty:
    for title in tender_titles:
        budget = random.randint(10000000, 500000000)
        licitaciones.create_tender(active_pid, title, budget, f"SSD-{random.randint(1000,9999)}")
        print(f"Created Tender: {title}")

# --- FINANCE ---
print("Populating Finance (Purchase Orders)...")
df_p = finance.get_purchase_orders(active_pid)
if df_p.empty or len(df_p) < 5:
    providers = ["Construmart Pro", "Sodimac Industrial", "Cementos Melón"]
    for _ in range(10):
        prov = random.choice(providers)
        date = datetime.now() - timedelta(days=random.randint(0, 60))
        amount = random.randint(500000, 15000000)
        finance.create_purchase_order(active_pid, prov, date.date(), amount, "Materiales Varios")
    print("Created Purchase Orders")

# Also insert some Expenses (direct table) since finance module uses purchase_orders but views.py uses expenses
print("Populating Direct Expenses...")
res = supabase.table("expenses").select("id").eq("project_id", active_pid).limit(1).execute()
if not res.data:
    # Need dummy faena and unit
    f_res = supabase.table("faenas").insert({"project_id": active_pid, "name": "Faena General", "supervisor": "Jefe"}).execute()
    u_res = supabase.table("units").insert({"name": "Unidad 1", "type": "General"}).execute()
    fid = f_res.data[0]['id']
    uid_unit = u_res.data[0]['id']
    
    for _ in range(20):
        e_data = {
            "date": str((datetime.now() - timedelta(days=random.randint(0,30))).date()),
            "project_id": active_pid,
            "faena_id": fid,
            "unit_id": uid_unit,
            "category": random.choice(["Materiales", "Mano de Obra", "Equipos"]),
            "amount": random.randint(100000, 5000000),
            "description": "Gasto vario de obra"
        }
        supabase.table("expenses").insert(e_data).execute()
    print("Created Expenses")

# --- LEAN ---
print("Populating Lean Tasks...")
check_tasks = lean.get_tasks(active_pid)
if check_tasks.empty:
    lean_tasks = [("Armado de Enfierradura", "Done"), ("Hormigonado", "To Do")]
    for name, status in lean_tasks:
        start = datetime.now()
        end = start + timedelta(days=5)
        lean.create_task(active_pid, name, start.date(), end.date(), status)
    print("Created Lean Tasks")

# --- COMPLIANCE ---
print("Populating Subcontractors...")
check_subs = compliance.get_subcontractors()
if check_subs.empty:
    compliance.create_subcontractor("Ingeniería Sur", "77.111.222-3", "contact@sur.cl")
    print("Created Subcontractor")

print("--------------------------------------------------")
print("POPULATION COMPLETE")

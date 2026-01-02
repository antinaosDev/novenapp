from modules import data, licitaciones, finance, lean, compliance, quality, schema
from datetime import datetime, timedelta
import random
import pandas as pd

# Initialize DB and Schema
data.init_db()

print("Initializing Schema...")
schema.init_schema()

print("Populating Projects & Core Data...")
# --- PROJECTS ---
# --- PROJECTS ---
# Projects with Santiago, Chile Coordinates
projects_data = [
    ("Torre Central", "Rascacielos de 45 pisos en el centro financiero.", 12000000000, "2024-01-15", "2026-12-30", -33.4372, -70.6506), # Santiago Centro
    ("Residencial Los Álamos", "Conjunto habitacional de 5 torres.", 4500000000, "2024-03-01", "2025-11-20", -33.4169, -70.6067), # Providencia/Las Condes
    ("Centro Comercial Norte", "Mall de 3 niveles con estacionamiento subterráneo.", 8500000000, "2024-05-10", "2026-06-15", -33.3662, -70.6970) # Quilicura/Norte
]

project_ids = []
current_legacy_projects = data.get_projects()
# If columns missing in dataframe (old read), re-read or assume simple update
if current_legacy_projects.empty:
    for p in projects_data:
        # data.add_project now needs to handle the extra args or we direct insert
        # To avoid changing modules/data.py signature, let's direct insert here for populate script
        pid = data.run_query("INSERT INTO projects (name, description, budget_total, start_date, end_date, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?)", p)
        project_ids.append(pid)
        print(f"Added Project: {p[0]}")
else:
    # Attempt to update coordinates if they are default
    print("Updating existing projects with coordinates...")
    for idx, p in enumerate(projects_data):
        # We assume order matches for simplicity in this demo script
        try:
            current_id = current_legacy_projects.iloc[idx]['id']
            data.run_query("UPDATE projects SET latitude = ?, longitude = ? WHERE id = ?", (p[5], p[6], int(current_id)))
        except IndexError:
            pass
    project_ids = current_legacy_projects['id'].tolist()

# Use the first project for most demos
active_pid = project_ids[0] if project_ids else 1

# --- MODULE 7: TEAMS (ASSIGNMENTS) ---
print("Populating Project Assignments...")
# Create some dummy users if they don't exist
dummy_users = [
    ("Juan Pérez", "Jefe de Cuadrilla", "jperez"),
    ("Maria González", "Prevencionista", "mgonzalez"),
    ("Carlos Ruiz", "Capataz", "cruiz"),
    ("Ana López", "Administrador de Obra", "alopez")
]

for name, role, username in dummy_users:
    # Check if user exists
    res = data.run_query("SELECT id FROM users WHERE username = ?", (username,), return_df=True)
    if res.empty:
        # Simple hash for '123' used in auth.py
        # We'll rely on auth.py's register logic or direct insert for seed
        # Direct insert for speed
        pw_hash = "$2b$12$eX/././././././././././.e" # Placeholder hash or use auth module
        # Actually, let's just insert basic:
        uid = data.run_query("INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)", 
                       (username, "$2b$12$123456789012345678901uXyZ", name, role)) # Fake hash
        print(f"Created User: {name}")
    else:
        uid = res.iloc[0]['id']

    # Assign to active project
    # Check assignment
    check = data.run_query("SELECT id FROM project_assignments WHERE project_id = ? AND user_id = ?", (active_pid, uid), return_df=True)
    if check.empty:
        data.run_query("INSERT INTO project_assignments (project_id, user_id, role) VALUES (?, ?, ?)", (active_pid, uid, role))
        print(f"Assigned {name} to Project {active_pid}")

# Use the first project for most demos
active_pid = project_ids[0] if project_ids else 1

# --- MODULE 2: LICITACIONES (TENDERS) ---
print("Populating Tenders...")
tender_titles = [
    "Instalación de Faenas y Cierros",
    "Movimiento de Tierras Masivo",
    "Obra Gruesa - Hormigonado Torre A",
    "Instalación Eléctrica e Iluminación",
    "Climatización y HVAC",
    "Terminaciones Húmedas y Secas"
]

existing_tenders = licitaciones.get_tenders(active_pid)
if existing_tenders.empty:
    for title in tender_titles:
        budget = random.randint(10000000, 500000000)
        licitaciones.create_tender(active_pid, title, budget, f"SSD-{random.randint(1000,9999)}")
        print(f"Added Tender: {title}")
    
    # Update some to Active/Closed to show variety
    df_t = licitaciones.get_tenders(active_pid)
    for index, row in df_t.iterrows():
        status = random.choice(['Activa', 'Adjudicada', 'Desierta', 'Borrador'])
        licitaciones.update_tender_status(row['id'], status)

# --- MODULE 3: FINANCE (PURCHASE ORDERS) ---
print("Populating Purchase Orders...")
providers = ["Construmart Pro", "Sodimac Industrial", "Cementos Melón", "Acero Sostenible SA", "Rentamaq Ltda"]
descriptions = ["Compra de Fierro 12mm", "Arriendo Generador 100kVA", "Hormigón H30", "EPP y Seguridad", "Instalación Ventanas PVC"]

existing_pos = finance.get_purchase_orders(active_pid)
if existing_pos.empty:
    for _ in range(15):
        prov = random.choice(providers)
        date = datetime.now() - timedelta(days=random.randint(0, 60))
        amount = random.randint(500000, 15000000)
        desc = random.choice(descriptions)
        finance.create_purchase_order(active_pid, prov, date.date(), amount, desc)
    
    # Update statuses
    df_p = finance.get_purchase_orders(active_pid)
    for index, row in df_p.iterrows():
        status = random.choice(['Pendiente', 'Aprobada', 'Pagada'])
        if status == 'Aprobada':
            finance.approve_purchase_order(row['id'])
        elif status == 'Pagada':
            finance.approve_purchase_order(row['id'])
            finance.mark_as_paid(row['id'])
    print("Added 15 Purchase Orders")

# --- MODULE 4: LEAN CONSTRUCTION (TASKS) ---
print("Populating Lean Tasks...")
lean_tasks = [
    ("Armado de Enfierradura Muro Eje 4", "Done"),
    ("Descimbre Losa Nivel 3", "Done"),
    ("Trazado Tabiquería Piso 4", "In Progress"),
    ("Instalación de Ductos HVAC", "In Progress"),
    ("Hormigonado Viga Perimetral", "To Do"),
    ("Montaje de Grúa Torre 2", "Blocked"),
    ("Recepción de Cerámicas baño", "To Do"),
    ("Pintura Fachada Norte", "To Do")
]

existing_tasks = lean.get_tasks(active_pid)
if existing_tasks.empty:
    base_date = datetime.now()
    for task_name, initial_status in lean_tasks:
        start = base_date + timedelta(days=random.randint(-5, 5))
        end = start + timedelta(days=random.randint(1, 10))
        lean.create_task(active_pid, task_name, start.date(), end.date(), initial_status)
    print(f"Added {len(lean_tasks)} Lean Tasks")

# --- MODULE 5: COMPLIANCE (SUBCONTRACTORS) ---
print("Populating Subcontractors...")
subs = [
    ("Ingeniería del Sur Ltda", "77.111.222-3"),
    ("Electricidad Total SpA", "76.444.555-K"),
    ("Clima y Ventilación SA", "96.888.777-1"),
    ("Pinturas y Revestimientos Hnos", "55.333.111-9")
]

existing_subs = compliance.get_subcontractors()
if existing_subs.empty:
    for name, rut in subs:
        compliance.create_subcontractor(name, rut, f"contacto@{name.split()[0].lower()}.cl")
    print(f"Added {len(subs)} Subcontractors")

# --- MODULE 6: QUALITY (LOGS) ---
print("Populating Quality Logs...")
logs = [
    ("Recepción Enfierradura Losa 3", "Se revisa cuantía y espaciamiento. Todo OK según plano C-204.", "Residente de Obra"),
    ("Control de Hormigón H30", "Temperatura de colocación 22°C. Slump 8cm. Muestras tomadas.", "Inspector Técnico (ITO)"),
    ("Inspección de Soldaduras Estructura Metálica", "Se rechazan 3 puntos de soldadura en pilar 4. Repasar.", "Inspector Técnico (ITO)"),
    ("Prueba de Estanqueidad Red Agua Potable", "Prueba a 150 PSI por 4 horas. Sin fugas detectadas.", "Residente de Obra"),
    ("Revisión Verticalidad Moldajes", "Ejes 4 y 5 revisados con topografía. Desviación 2mm (dentro de tolerancia).", "Residente de Obra")
]

existing_logs = quality.get_logs(active_pid)
if existing_logs.empty:
    for title, desc, role in logs:
        quality.create_log(active_pid, title, desc, role)
    print(f"Added {len(logs)} Quality Logs")

print("--------------------------------------------------")
print("FULL APP POPULATION COMPLETED SUCCESSFULLY")
print("You can now restart the app with 'streamlit run app.py'")

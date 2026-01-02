import sqlite3
import pandas as pd

DB_NAME = "novenapp.db"

def init_schema():
    """Initializes the extended ERP Database Schema."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # --- CORE MODULE ---
    # Projects (Existing + Expanded)
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            budget_total REAL DEFAULT 0,
            start_date DATE,
            end_date DATE,
            status TEXT DEFAULT 'Activo',
            latitude REAL DEFAULT -33.4489,
            longitude REAL DEFAULT -70.6693
        )
    ''')
    
    # Migration for existing projects table (if missing columns)
    try:
        c.execute("ALTER TABLE projects ADD COLUMN latitude REAL DEFAULT -33.4489")
        c.execute("ALTER TABLE projects ADD COLUMN longitude REAL DEFAULT -70.6693")
    except sqlite3.OperationalError:
        pass # Columns already exist

    # Project Assignments (Teams)
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            user_id INTEGER,
            role TEXT, -- Jefe de Cuadrilla, Capataz, Prevencionista
            assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Users (Existing)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL
        )
    ''')

    # --- MODULE 1: LICITACIONES Y CONTRATOS ---
    # Tenders (Licitaciones)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            title TEXT NOT NULL,
            type TEXT NOT NULL, -- L1 (<100), LE (<1000), LP (>1000)
            budget_estimated REAL,
            utm_value_at_creation REAL, -- To freeze the classification context
            status TEXT DEFAULT 'Borrador', -- Borrador, Publicada, Evaluacion, Adjudicada
            ssd_code TEXT, -- Integration with government system
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')
    
    # Contracts
    c.execute('''
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id INTEGER,
            contractor_name TEXT,
            rut_contractor TEXT,
            amount REAL,
            start_date DATE,
            end_date DATE,
            status TEXT DEFAULT 'Activo', -- Activo, Finalizado, Cancelado
            FOREIGN KEY(tender_id) REFERENCES tenders(id)
        )
    ''')

    # Guarantees (Boletas de Garantía)
    c.execute('''
        CREATE TABLE IF NOT EXISTS guarantees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER,
            type TEXT, -- Seriedad Oferta, Fiel Cumplimiento, Correcta Ejecución
            amount REAL,
            expiration_date DATE,
            status TEXT DEFAULT 'Vigente', -- Vigente, Cobrada, Devuelta
            scanned_doc_path TEXT,
            FOREIGN KEY(contract_id) REFERENCES contracts(id)
        )
    ''')

    # --- MODULE 2: FINANCE ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            contract_id INTEGER,
            provider_name TEXT,
            date DATE,
            total_amount REAL,
            status TEXT DEFAULT 'Pendiente', -- Pendiente, Aprobada, Pagada
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')

    # --- MODULE 4: PRODUCTION (LEAN) ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            name TEXT NOT NULL,
            start_date DATE,
            end_date DATE,
            type TEXT, -- Master, Lookahead, Weekly
            status TEXT DEFAULT 'To Do',
            tags TEXT
        )
    ''')

    # --- MODULE 5: COMPLIANCE ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS subcontractors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rut TEXT UNIQUE,
            name TEXT NOT NULL,
            contact_email TEXT,
            status TEXT DEFAULT 'Activo'
        )
    ''')

    # --- MODULE 6: QUALITY ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS quality_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            title TEXT,
            description TEXT,
            inspector_name TEXT,
            date DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Pendiente', -- Pendiente, Aprobado, Rechazado
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')

    # Ensure existing legacy tables exist if not covered (Expenses, Faenas, Units)
    # Copied from original data.py to ensure full coverage
    c.execute('''
        CREATE TABLE IF NOT EXISTS faenas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            name TEXT NOT NULL,
            supervisor TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT, 
            details TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            project_id INTEGER,
            faena_id INTEGER,
            unit_id INTEGER,
            category TEXT, 
            amount REAL NOT NULL,
            description TEXT,
            evidence_path TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(faena_id) REFERENCES faenas(id),
            FOREIGN KEY(unit_id) REFERENCES units(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Database Schema Initialized.")

if __name__ == "__main__":
    init_schema()

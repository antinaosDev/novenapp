"""
Migracion: Extrae todos los datos de Supabase y los escribe en Google Sheets.
Crea una pestaña por tabla en el libro especificado.
"""

import os
import json
import toml
import gspread
from google.oauth2.service_account import Credentials
from supabase import create_client

# --- Config ---
SPREADSHEET_ID = "1dFeMiekQKnA4xRPju9Wd62JWd_4fmW-xvqZ7XpdXDEY"
CREDENTIALS_FILE = "google_credentials.json"

# Cargar credenciales de Supabase desde secrets.toml
secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
with open(secrets_path, "r") as f:
    secrets = toml.load(f)

SUPABASE_URL = secrets["supabase"]["URL"]
SUPABASE_KEY = secrets["supabase"]["KEY"]

# Tablas a migrar (ordenadas por dependencias)
TABLES = [
    "users",
    "roles",
    "projects",
    "units",
    "faenas",
    "project_assignments",
    "tenders",
    "contracts",
    "guarantees",
    "purchase_orders",
    "subcontractors",
    "compliance_documents",
    "quality_logs",
    "lab_tests",
    "phases",
    "tasks",
    "expenses",
    "comments",
    "budget_items",
    "warehouse_items",
    "system_config",
    "ai_usage_logs",
]


def main():
    # 1. Conectar a Supabase
    print("Conectando a Supabase...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    all_data = {}
    for table in TABLES:
        print(f"  Extrayendo {table}...")
        try:
            resp = supabase.table(table).select("*").execute()
            data = resp.data
            all_data[table] = data
            print(f"    -> {len(data)} registros")
        except Exception as e:
            print(f"    -> Error: {e}")
            all_data[table] = []

    # 2. Conectar a Google Sheets
    print("\nConectando a Google Sheets...")
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(SPREADSHEET_ID)

    # 3. Escribir cada tabla a una pestaña
    for table_name, rows in all_data.items():
        print(f"\nEscribiendo {table_name}...")

        # Obtener o crear la hoja
        try:
            ws = sheet.worksheet(table_name)
            ws.clear()
        except gspread.WorksheetNotFound:
            ws = sheet.add_worksheet(title=table_name, rows=1000, cols=26)

        if not rows:
            # Escribir solo el header
            ws.update([["(sin datos)"]], "A1")
            print(f"  -> Sin datos, colocado placeholder")
            continue

        # Convertir a lista de listas con headers
        headers = list(rows[0].keys())
        values = []
        for row in rows:
            values.append([str(row.get(h, "")) if row.get(h) is not None else "" for h in headers])

        data_to_write = [headers] + values
        ws.update(data_to_write, "A1")

        # Ajustar numero de filas en la hoja si es necesario
        needed_rows = len(data_to_write)
        current_rows = ws.row_count
        if needed_rows > current_rows:
            ws.add_rows(needed_rows - current_rows)

        print(f"  -> {len(rows)} registros escritos ({len(headers)} columnas)")

    print("\nMigracion completada exitosamente!")


if __name__ == "__main__":
    main()

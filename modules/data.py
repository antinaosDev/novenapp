import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import time
import random
import threading

# --- Config ---
SPREADSHEET_ID = "1dFeMiekQKnA4xRPju9Wd62JWd_4fmW-xvqZ7XpdXDEY"
CREDENTIALS_FILE = "google_credentials.json"

# --- Global API Rate Limiter ---
_api_lock = threading.Lock()
_last_api_call = 0.0

_THROTTLE_INTERVAL = 2.0  # seconds (was 1.0 — increased for multi-instance safety)

def _throttle():
    """Enforce minimum interval between API calls (serializes across threads/instances)."""
    global _last_api_call
    with _api_lock:
        now = time.time()
        elapsed = now - _last_api_call
        if elapsed < _THROTTLE_INTERVAL:
            time.sleep(_THROTTLE_INTERVAL - elapsed)
        _last_api_call = time.time()

# --- Modular Cache (replaces @st.cache_data) ---
_CACHE = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL = 120  # seconds

# --- Google Sheets Connection ---
def _get_credentials():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        gcp = st.secrets["gcp"]
        if "GOOGLE_CREDENTIALS_B64" in gcp:
            import base64
            json_str = base64.b64decode(gcp["GOOGLE_CREDENTIALS_B64"]).decode("utf-8")
            info = json.loads(json_str)
        else:
            info = {
                "type": gcp["type"],
                "project_id": gcp["project_id"],
                "private_key_id": gcp["private_key_id"],
                "private_key": gcp["private_key"],
                "client_email": gcp["client_email"],
                "client_id": gcp["client_id"],
                "auth_uri": gcp["auth_uri"],
                "token_uri": gcp["token_uri"],
                "auth_provider_x509_cert_url": gcp["auth_provider_x509_cert_url"],
                "client_x509_cert_url": gcp["client_x509_cert_url"],
                "universe_domain": gcp.get("universe_domain", "googleapis.com"),
            }
        return Credentials.from_service_account_info(info, scopes=scope)
    except Exception:
        return Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)

@st.cache_resource
def get_gs_client():
    creds = _get_credentials()
    return gspread.authorize(creds)

@st.cache_resource
def get_sheet():
    client = get_gs_client()
    return client.open_by_key(SPREADSHEET_ID)

def _read_worksheet_cached(worksheet_name):
    with _CACHE_LOCK:
        entry = _CACHE.get(worksheet_name)
        if entry and time.time() - entry['time'] < _CACHE_TTL:
            return entry['data']
    for attempt in range(5):
        try:
            _throttle()
            ws = get_sheet().worksheet(worksheet_name)
            _throttle()
            data = ws.get_all_values()
            with _CACHE_LOCK:
                _CACHE[worksheet_name] = {'data': data, 'time': time.time()}
            return data
        except Exception as e:
            if _is_rate_limit(e) and attempt < 4:
                delay = 1.5 ** attempt + random.random()
                time.sleep(delay)
                continue
            if _is_rate_limit(e):
                print(f"Rate limit exceeded for {worksheet_name} after 5 retries")
            else:
                print(f"Error reading {worksheet_name}: {e}")
            return []
    return []

def _batch_read_worksheets(worksheet_names):
    names = list(dict.fromkeys(worksheet_names))
    with _CACHE_LOCK:
        needed = {n for n in names if n not in _CACHE or time.time() - _CACHE[n]['time'] >= _CACHE_TTL}
    if not needed:
        with _CACHE_LOCK:
            return {n: _CACHE[n]['data'] for n in names}
    for attempt in range(5):
        try:
            _throttle()
            ranges = [f"'{n}'!A:ZZ" for n in needed]
            result = get_sheet().values_batch_get(ranges)
            data_map = {}
            for vr in result.get('valueRanges', []):
                range_str = vr.get('range', '')
                if '!' not in range_str:
                    continue
                name = range_str.split('!')[0].strip("'")
                values = vr.get('values', [])
                data_map[name] = values
            now = time.time()
            with _CACHE_LOCK:
                for n in needed:
                    if n in data_map:
                        _CACHE[n] = {'data': data_map[n], 'time': now}
                result_map = {}
                for n in names:
                    cached = _CACHE.get(n)
                    if cached:
                        result_map[n] = cached['data']
                    else:
                        result_map[n] = data_map.get(n, [])
            return result_map
        except Exception as e:
            if _is_rate_limit(e) and attempt < 4:
                delay = 1.5 ** attempt + random.random()
                time.sleep(delay)
                continue
            if _is_rate_limit(e):
                print(f"Rate limit exceeded for batch read after 5 retries")
            else:
                print(f"Error in batch read: {e}")
            fallback = {}
            for n in names:
                fallback[n] = _read_worksheet_cached(n)
            return fallback
    return {}

def _clear_worksheet_cache(worksheet_name=None):
    with _CACHE_LOCK:
        if worksheet_name:
            _CACHE.pop(worksheet_name, None)
        else:
            _CACHE.clear()

def _is_rate_limit(e):
    return (hasattr(e, 'code') and e.code == 429) or '429' in str(e)

def _retry(fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return fn(), True
        except Exception as e:
            if _is_rate_limit(e) and attempt < max_retries - 1:
                delay = 1.5 ** attempt + random.random()
                time.sleep(delay)
                continue
            raise
    return None, False

def read_worksheet(worksheet_name, expected_columns=None):
    all_rows = _read_worksheet_cached(worksheet_name)
    if not all_rows or len(all_rows) <= 1:
        return pd.DataFrame(columns=expected_columns or [])
    headers = all_rows[0]
    data_rows = [dict(zip(headers, row)) for row in all_rows[1:] if any(c.strip() for c in row)]
    if not data_rows:
        return pd.DataFrame(columns=expected_columns or [])
    return pd.DataFrame(data_rows)

def write_worksheet(worksheet_name, df):
    try:
        _throttle()
        ws = get_sheet().worksheet(worksheet_name)
        _throttle()
        ws.clear()
        if df.empty:
            ws.update([["(sin datos)"]], "A1")
        else:
            headers = list(df.columns)
            values = df.values.tolist()
            ws.update([headers] + values, "A1")
        _clear_worksheet_cache(worksheet_name)
        return True
    except Exception as e:
        print(f"Error writing {worksheet_name}: {e}")
        return False

def append_row(worksheet_name, row_dict):
    try:
        _throttle()
        ws = get_sheet().worksheet(worksheet_name)
        all_rows = _read_worksheet_cached(worksheet_name)
        headers = all_rows[0] if all_rows else list(row_dict.keys())
        if not headers:
            headers = list(row_dict.keys())
        row_values = [str(row_dict.get(h, "")) if row_dict.get(h) is not None else "" for h in headers]
        next_row = len(all_rows) + 1
        col_letter = chr(64 + len(headers)) if 1 <= len(headers) <= 26 else 'Z'
        range_str = f"A{next_row}:{col_letter}{next_row}"

        def _do_update():
            ws.update(range_str, [row_values], value_input_option="USER_ENTERED")

        result, ok = _retry(_do_update)
        if not ok:
            print(f"Error appending to {worksheet_name} after retries")
            return False
        _clear_worksheet_cache(worksheet_name)
        return True
    except Exception as e:
        print(f"Error appending to {worksheet_name}: {e}")
        return False

def update_row_by_id(worksheet_name, row_id, update_dict):
    try:
        _throttle()
        ws = get_sheet().worksheet(worksheet_name)
        all_rows = _read_worksheet_cached(worksheet_name)
        headers = all_rows[0] if all_rows else []
        if 'id' not in headers:
            return False
        id_col = headers.index('id') + 1

        def _do_update():
            for i, row in enumerate(all_rows[1:], start=2):
                if len(row) >= id_col and row[id_col - 1] == str(row_id):
                    for key, value in update_dict.items():
                        if key in headers:
                            col = headers.index(key) + 1
                            ws.update_cell(i, col, str(value) if value is not None else "")
                    break

        result, ok = _retry(_do_update)
        if not ok:
            return False
        _clear_worksheet_cache(worksheet_name)
        return True
    except Exception as e:
        print(f"Error updating {worksheet_name} id={row_id}: {e}")
        return False

def delete_row_by_id(worksheet_name, row_id):
    try:
        _throttle()
        ws = get_sheet().worksheet(worksheet_name)
        all_rows = _read_worksheet_cached(worksheet_name)
        headers = all_rows[0] if all_rows else []
        if 'id' not in headers:
            return False
        id_col = headers.index('id') + 1

        def _do_delete():
            for i, row in enumerate(all_rows[1:], start=2):
                if len(row) >= id_col and row[id_col - 1] == str(row_id):
                    ws.delete_rows(i)
                    break

        result, ok = _retry(_do_delete)
        if not ok:
            return False
        _clear_worksheet_cache(worksheet_name)
        return True
    except Exception as e:
        print(f"Error deleting from {worksheet_name} id={row_id}: {e}")
        return False

def get_next_id(worksheet_name):
    try:
        all_rows = _read_worksheet_cached(worksheet_name)
        if len(all_rows) <= 1:
            return 1
        ids = []
        for row in all_rows[1:]:
            try:
                ids.append(int(row[0]))
            except (ValueError, IndexError):
                continue
        return max(ids) + 1 if ids else 1
    except:
        return 1

# --- Initialization ---
def init_db():
    """Verify sheet connection and preload common sheets via batchGet."""
    try:
        result = _batch_read_worksheets([
            "projects", "users", "purchase_orders", "tasks",
            "subcontractors", "tenders", "expenses", "comments",
            "project_assignments", "faenas", "units", "system_config"
        ])
        if not result.get("projects"):
            st.error("❌ Google Sheets no respondió (límite de 60 req/min excedido). Reintenta en 1 minuto.")
            st.stop()
    except Exception as e:
        st.error(f"❌ Error de conexión con Google Sheets: {e}")
        st.stop()

# --- Projects ---
def add_project(name, description, budget, start_date, end_date, lat=-33.4489, lon=-70.6693):
    new_id = get_next_id("projects")
    row = {
        "id": new_id, "name": name, "description": description,
        "budget_total": budget, "start_date": str(start_date),
        "end_date": str(end_date), "status": "Activo",
        "latitude": lat, "longitude": lon
    }
    return append_row("projects", row)

def get_projects():
    df = read_worksheet("projects", [
        'id', 'name', 'description', 'budget_total',
        'start_date', 'end_date', 'status', 'latitude', 'longitude'
    ])
    if df.empty:
        return pd.DataFrame(columns=[
            'id', 'name', 'description', 'budget_total',
            'start_date', 'end_date', 'status', 'latitude', 'longitude'
        ])
    numeric_cols = ['id', 'budget_total', 'latitude', 'longitude']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def update_project(project_id, name, description, budget, start_date, end_date, status="Activo", lat=-33.4489, lon=-70.6693):
    update_row_by_id("projects", project_id, {
        "name": name, "description": description, "budget_total": budget,
        "start_date": str(start_date), "end_date": str(end_date),
        "status": status, "latitude": lat, "longitude": lon
    })

def delete_project(project_id):
    sheets_to_check = [
        "project_assignments", "tasks", "quality_logs", "phases",
        "subcontractors", "lab_tests", "warehouse_items", "expenses",
        "faenas", "purchase_orders", "tenders", "budget_items",
        "comments"
    ]
    for sheet_name in sheets_to_check:
        try:
            _throttle()
            ws = get_sheet().worksheet(sheet_name)
            _throttle()
            headers = ws.row_values(1)
            if 'project_id' not in headers:
                continue
            pid_col = headers.index('project_id') + 1
            _throttle()
            all_rows = ws.get_all_values()
            rows_to_delete = []
            for i, row in enumerate(all_rows[1:], start=2):
                if len(row) >= pid_col and row[pid_col - 1] == str(project_id):
                    rows_to_delete.append(i)
            for row_idx in reversed(rows_to_delete):
                _throttle()
                ws.delete_rows(row_idx)
        except:
            pass

    delete_row_by_id("projects", project_id)
    return True

def get_projects_expiring_soon(days_threshold):
    try:
        now = datetime.now()
        target_date = now + timedelta(days=days_threshold)
        today_str = now.strftime('%Y-%m-%d')
        target_str = target_date.strftime('%Y-%m-%d')
        df = get_projects()
        if df.empty:
            return df
        df = df[df['status'] != 'Completado']
        df = df[df['status'] != 'En Cierre']
        df = df[df['end_date'].between(today_str, target_str)]
        return df
    except Exception as e:
        print(f"Error checking project deadlines: {e}")
        return pd.DataFrame()

def get_contracts_expiring_soon(days_threshold):
    try:
        now = datetime.now()
        target_date = now + timedelta(days=days_threshold)
        today_str = now.strftime('%Y-%m-%d')
        target_str = target_date.strftime('%Y-%m-%d')
        df = read_worksheet("contracts")
        if df.empty:
            return df
        df = df[df['status'] != 'Terminado']
        df = df[df['end_date'].between(today_str, target_str)]
        return df
    except Exception as e:
        print(f"Error checking contracts: {e}")
        return pd.DataFrame()

def get_guarantees_expiring_soon(days_threshold):
    try:
        now = datetime.now()
        target_date = now + timedelta(days=days_threshold)
        today_str = now.strftime('%Y-%m-%d')
        target_str = target_date.strftime('%Y-%m-%d')
        df = read_worksheet("guarantees")
        if df.empty:
            return df
        df = df[df['status'] == 'Vigente']
        df = df[df['expiration_date'].between(today_str, target_str)]
        return df
    except Exception as e:
        print(f"Error checking guarantees: {e}")
        return pd.DataFrame()

# --- Faenas ---
def add_faena(project_id, name, supervisor):
    new_id = get_next_id("faenas")
    append_row("faenas", {"id": new_id, "project_id": project_id, "name": name, "supervisor": supervisor})

def get_faenas(project_id=None):
    df = read_worksheet("faenas", ['id', 'project_id', 'name', 'supervisor'])
    if df.empty:
        return df
    if project_id is not None:
        df['project_id'] = pd.to_numeric(df['project_id'], errors='coerce')
        df = df[df['project_id'] == int(project_id)]
    return df

def update_faena(faena_id, name, supervisor):
    update_row_by_id("faenas", faena_id, {"name": name, "supervisor": supervisor})

def delete_faena(faena_id):
    df = read_worksheet("expenses")
    if not df.empty and 'faena_id' in df.columns:
        df['faena_id'] = pd.to_numeric(df['faena_id'], errors='coerce')
        df.loc[df['faena_id'] == int(faena_id), 'faena_id'] = None
        write_worksheet("expenses", df)
    delete_row_by_id("faenas", faena_id)
    return True

# --- Units ---
def add_unit(name, type_, details):
    new_id = get_next_id("units")
    append_row("units", {"id": new_id, "name": name, "type": type_, "details": details})

def get_units():
    return read_worksheet("units", ['id', 'name', 'type', 'details'])

def update_unit(unit_id, name, type_, details):
    update_row_by_id("units", unit_id, {"name": name, "type": type_, "details": details})

def delete_unit(unit_id):
    delete_row_by_id("units", unit_id)

# --- Expenses ---
def add_expense(date, project_id, faena_id, unit_id, category, amount, description):
    new_id = get_next_id("expenses")
    append_row("expenses", {
        "id": new_id, "date": str(date), "project_id": project_id,
        "faena_id": faena_id, "unit_id": unit_id,
        "category": category, "amount": amount, "description": description
    })

def get_expenses_df(project_id=None):
    df = read_worksheet("expenses", [
        'id', 'date', 'amount', 'category', 'description',
        'project_id', 'project', 'faena', 'unit'
    ])
    if df.empty:
        return pd.DataFrame(columns=[
            'id', 'date', 'amount', 'category', 'description',
            'project_id', 'project', 'faena', 'unit'
        ])

    for col in ['amount', 'project_id', 'faena_id', 'unit_id']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Join project/faena/unit names
    projects_df = get_projects()
    faenas_df = get_faenas()
    units_df = get_units()

    if 'project_id' in df.columns and not projects_df.empty:
        proj_map = projects_df.set_index('id')['name'].to_dict()
        df['project'] = df['project_id'].map(proj_map).fillna(df.get('project', ''))

    if 'faena_id' in df.columns and not faenas_df.empty:
        faena_map = faenas_df.set_index('id')['name'].to_dict()
        df['faena'] = df['faena_id'].map(faena_map).fillna(df.get('faena', ''))

    if 'unit_id' in df.columns and not units_df.empty:
        unit_map = units_df.set_index('id')['name'].to_dict()
        df['unit'] = df['unit_id'].map(unit_map).fillna(df.get('unit', ''))

    if project_id is not None:
        df = df[df['project_id'] == int(project_id)]

    if 'date' in df.columns:
        df = df.sort_values('date', ascending=False)

    return df

# --- KPIs ---
def get_kpis():
    projs = get_projects()
    total_budget = projs['budget_total'].sum() if not projs.empty else 0

    po_df = read_worksheet("purchase_orders")
    if not po_df.empty and 'total_amount' in po_df.columns:
        po_df['total_amount'] = pd.to_numeric(po_df['total_amount'], errors='coerce')
        total_spent = po_df[po_df['status'] != 'Rechazada']['total_amount'].sum()
        pending_po_amount = po_df[po_df['status'].isin(['Pendiente', 'Aprobada'])]['total_amount'].sum()
    else:
        total_spent = 0
        pending_po_amount = 0

    tasks_df = read_worksheet("tasks")
    if not tasks_df.empty and 'status' in tasks_df.columns:
        total_tasks = len(tasks_df)
        completed_tasks = len(tasks_df[tasks_df['status'] == 'Completado'])
        global_ppc = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
    else:
        global_ppc = 0

    subs_df = read_worksheet("subcontractors")
    if not subs_df.empty and 'status' in subs_df.columns:
        active_subs = len(subs_df[subs_df['status'] == 'Activo'])
        total_subs = len(subs_df)
    else:
        active_subs = 0
        total_subs = 0

    tenders_df = read_worksheet("tenders")
    if not tenders_df.empty and 'status' in tenders_df.columns:
        open_tenders = len(tenders_df[tenders_df['status'] == 'Publicada'])
    else:
        open_tenders = 0

    return {
        "total_spent": total_spent,
        "total_budget": total_budget,
        "pending_po_amount": pending_po_amount,
        "global_ppc": global_ppc,
        "active_subs": active_subs,
        "total_subs": total_subs,
        "open_tenders": open_tenders
    }

def get_dashboard_alerts():
    alerts = []

    po_df = read_worksheet("purchase_orders")
    if not po_df.empty and 'status' in po_df.columns:
        pending = po_df[po_df['status'] == 'Pendiente']
        for _, po in pending.iterrows():
            identifier = po.get('order_number') or po.get('id', '')
            alerts.append({
                "scope": "Finanzas",
                "message": f"OC #{identifier} pendiente de aprobación",
                "detail": f"Proveedor: {po.get('provider_name', '')} - ${po.get('total_amount', 0):,.0f}",
                "severity": "warning"
            })

    docs_df = read_worksheet("compliance_documents")
    if not docs_df.empty:
        today = datetime.now().date()
        subs_df = read_worksheet("subcontractors")
        sub_map = subs_df.set_index('id')['name'].to_dict() if not subs_df.empty else {}
        for _, doc in docs_df.iterrows():
            if doc.get('expiration_date'):
                try:
                    exp_date = datetime.strptime(doc['expiration_date'], '%Y-%m-%d').date()
                    days_left = (exp_date - today).days
                    sub_name = sub_map.get(int(doc.get('subcontractor_id', 0)), "Desconocido")
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
                except:
                    pass

    return alerts

def get_recent_expenses(limit=5):
    df = read_worksheet("expenses", ['date', 'description', 'category', 'amount'])
    if df.empty:
        return pd.DataFrame(columns=['date', 'description', 'category', 'amount'])
    if 'date' in df.columns:
        df = df.sort_values('date', ascending=False)
    return df.head(limit)

# --- Legacy run_query ---
def run_query(query_str, params=None, return_df=True):
    print(f"WARNING: RAW SQL ATTEMPTED: {query_str}")

    if "SELECT * FROM users WHERE username" in query_str:
        user = params[0] if params and len(params) > 0 else None
        if not user:
            return pd.DataFrame()
        df = read_worksheet("users")
        if not df.empty and 'username' in df.columns:
            return df[df['username'] == user]
        return pd.DataFrame()

    if "INSERT INTO users" in query_str:
        if not params or len(params) < 4:
            return False
        data = {
            "username": params[0], "password_hash": params[1],
            "full_name": params[2], "role": params[3]
        }
        data['id'] = get_next_id("users")
        append_row("users", data)
        return True

    if "SELECT * FROM project_assignments" in query_str:
        return read_worksheet("project_assignments")

    if query_str.startswith("SELECT * FROM"):
        parts = query_str.split()
        if len(parts) >= 4:
            table = parts[3]
            return read_worksheet(table)

    return pd.DataFrame()

# --- Users & Auth ---
def get_user_by_username(username):
    df = read_worksheet("users")
    if df.empty or 'username' not in df.columns:
        return pd.DataFrame()
    return df[df['username'] == username]

def create_user_record(username, password_hash, full_name, role, email=None):
    new_id = get_next_id("users")
    append_row("users", {
        "id": new_id, "username": username, "password_hash": password_hash,
        "full_name": full_name, "role": role, "email": email
    })

def get_all_users():
    try:
        df = read_worksheet("users")
        if df.empty or 'id' not in df.columns:
            return pd.DataFrame(columns=['id', 'full_name', 'role', 'username', 'email'])
        cols = [c for c in ['id', 'full_name', 'role', 'username', 'email'] if c in df.columns]
        return df[cols]
    except Exception as e:
        print(f"Error get_all_users: {e}")
        return pd.DataFrame(columns=['id', 'full_name', 'role', 'username', 'email'])

def get_users_full():
    return read_worksheet("users")

def update_user(user_id, username, full_name, role, password_hash=None, email=None):
    data = {"username": username, "full_name": full_name, "role": role, "email": email}
    if password_hash:
        data["password_hash"] = password_hash
    update_row_by_id("users", user_id, data)

def delete_user(user_id):
    delete_row_by_id("users", user_id)

# --- Roles ---
def get_roles():
    try:
        df = read_worksheet("roles")
        if not df.empty and 'id' in df.columns:
            return df
    except:
        pass
    return pd.DataFrame({
        'id': range(1, 7),
        'name': ["Programador", "Administrador", "Residente de Obra", "Capataz", "Bodeguero", "Prevencionista"],
        'description': ["Acceso Total", "Gestión", "Proyectos", "Cuadrillas", "Recursos", "Seguridad"]
    })

def add_role(name, description=""):
    new_id = get_next_id("roles")
    append_row("roles", {"id": new_id, "name": name, "description": description})

def delete_role(role_id):
    delete_row_by_id("roles", role_id)

# --- Project Assignments ---
def get_project_assignments(project_id):
    df = read_worksheet("project_assignments")
    if df.empty:
        return pd.DataFrame(columns=['id', 'role', 'assigned_at', 'full_name'])
    if 'project_id' in df.columns:
        df['project_id'] = pd.to_numeric(df['project_id'], errors='coerce')
        df = df[df['project_id'] == int(project_id)]
    users_df = get_all_users()
    if not users_df.empty and 'user_id' in df.columns and 'id' in users_df.columns:
        user_map = users_df.set_index('id')['full_name'].to_dict()
        df['full_name'] = df['user_id'].map(user_map).fillna('Unknown')
    return df

def get_all_project_assignments():
    df = read_worksheet("project_assignments")
    if df.empty:
        return pd.DataFrame(columns=['id', 'role', 'assigned_at', 'full_name', 'username', 'project_name'])
    users_df = get_all_users()
    projects_df = get_projects()
    if not users_df.empty and 'user_id' in df.columns:
        user_map = users_df.set_index('id')[['full_name', 'username']].to_dict('index')
        df['full_name'] = df['user_id'].map(lambda x: user_map.get(int(x), {}).get('full_name', 'Unknown') if pd.notna(x) else 'Unknown')
        df['username'] = df['user_id'].map(lambda x: user_map.get(int(x), {}).get('username', '') if pd.notna(x) else '')
    if not projects_df.empty and 'project_id' in df.columns:
        proj_map = projects_df.set_index('id')['name'].to_dict()
        df['project_name'] = df['project_id'].map(proj_map).fillna('Unknown')
    return df

def assign_user_to_project(project_id, user_id, role, assigned_at=None):
    df = get_all_project_assignments()
    if not df.empty:
        match = df[(df['project_id'] == int(project_id)) & (df['user_id'] == int(user_id))]
        if not match.empty:
            update_row_by_id("project_assignments", match.iloc[0]['id'], {"role": role})
            return
    new_id = get_next_id("project_assignments")
    append_row("project_assignments", {
        "id": new_id, "project_id": project_id, "user_id": user_id,
        "role": role, "assigned_at": str(assigned_at or datetime.now())
    })

def remove_project_assignment(assignment_id):
    delete_row_by_id("project_assignments", assignment_id)

# --- Budget ---
def get_budget_items(project_id):
    df = read_worksheet("budget_items")
    if df.empty:
        return pd.DataFrame(columns=['id', 'project_id', 'item_name', 'category', 'estimated_amount'])
    if 'project_id' in df.columns:
        df['project_id'] = pd.to_numeric(df['project_id'], errors='coerce')
        df = df[df['project_id'] == int(project_id)]
    return df

def create_budget_item(project_id, name, category, amount):
    new_id = get_next_id("budget_items")
    append_row("budget_items", {
        "id": new_id, "project_id": project_id,
        "item_name": name, "category": category, "estimated_amount": amount
    })

def update_budget_item(item_id, name, category, amount):
    update_row_by_id("budget_items", item_id, {
        "item_name": name, "category": category, "estimated_amount": amount
    })

def delete_budget_item(item_id):
    delete_row_by_id("budget_items", item_id)

def get_all_budget_items():
    return read_worksheet("budget_items")

# --- Purchase Orders ---
def create_purchase_order(project_id, provider_name, date, total_amount, order_number, description="", category="Otros"):
    new_id = get_next_id("purchase_orders")
    append_row("purchase_orders", {
        "id": new_id, "project_id": int(project_id), "provider_name": provider_name,
        "date": str(date), "total_amount": float(total_amount),
        "description": description, "category": category,
        "status": "Pagada", "order_number": order_number
    })

def get_purchase_orders(project_id=None):
    df = read_worksheet("purchase_orders")
    if df.empty:
        return pd.DataFrame(columns=[
            'id', 'project_id', 'provider_name', 'date', 'total_amount',
            'description', 'status', 'order_number', 'category', 'project_name'
        ])
    for col in ['total_amount', 'project_id']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    projects_df = get_projects()
    if not projects_df.empty:
        proj_map = projects_df.set_index('id')['name'].to_dict()
        df['project_name'] = df['project_id'].map(proj_map).fillna('Sin Proyecto')

    if project_id is not None:
        df = df[df['project_id'] == int(project_id)]

    if 'date' in df.columns:
        df = df.sort_values('date', ascending=False)
    return df

def update_purchase_order_full(po_id, project_id, provider, amount, date, order_number, desc, category="Otros"):
    update_row_by_id("purchase_orders", po_id, {
        "project_id": project_id, "provider_name": provider,
        "total_amount": amount, "date": str(date),
        "order_number": order_number, "description": desc, "category": category
    })

def update_po_status(po_id, status):
    update_row_by_id("purchase_orders", po_id, {"status": status})

def delete_purchase_order(po_id):
    delete_row_by_id("purchase_orders", po_id)

# --- Subcontractors ---
def get_subcontractors(project_id=None):
    df = read_worksheet("subcontractors", [
        'id', 'project_id', 'name', 'rut', 'contact_email',
        'contact_phone', 'specialty', 'representative', 'monto_asignado', 'status'
    ])
    if df.empty:
        return pd.DataFrame(columns=['id', 'project_id', 'name', 'rut', 'contact_email', 'contact_phone', 'specialty', 'representative', 'monto_asignado', 'status'])
    if project_id is not None and 'project_id' in df.columns:
        df['project_id'] = pd.to_numeric(df['project_id'], errors='coerce')
        df = df[df['project_id'] == int(project_id)]
    if 'monto_asignado' in df.columns:
        df['monto_asignado'] = pd.to_numeric(df['monto_asignado'], errors='coerce')
    return df

def create_subcontractor(project_id, name, rut, email, phone, specialty, rep, monto_asignado=0):
    new_id = get_next_id("subcontractors")
    append_row("subcontractors", {
        "id": new_id, "project_id": project_id, "name": name, "rut": rut,
        "contact_email": email, "contact_phone": phone, "specialty": specialty,
        "representative": rep, "monto_asignado": monto_asignado, "status": "Activo"
    })

def update_subcontractor_full(sub_id, name, rut, email, phone, specialty, rep, monto_asignado=None):
    data = {"name": name, "rut": rut, "contact_email": email,
            "contact_phone": phone, "specialty": specialty, "representative": rep}
    if monto_asignado is not None:
        data["monto_asignado"] = monto_asignado
    update_row_by_id("subcontractors", sub_id, data)

def update_sub_status(sub_id, status):
    update_row_by_id("subcontractors", sub_id, {"status": status})

def delete_subcontractor(sub_id):
    delete_row_by_id("subcontractors", sub_id)

# --- Compliance Documents ---
def get_compliance_documents(sub_id):
    df = read_worksheet("compliance_documents", [
        'id', 'subcontractor_id', 'document_type', 'status', 'expiration_date', 'last_updated'
    ])
    if df.empty:
        return pd.DataFrame(columns=['id', 'subcontractor_id', 'document_type', 'status', 'expiration_date', 'last_updated'])
    if 'subcontractor_id' in df.columns:
        df['subcontractor_id'] = pd.to_numeric(df['subcontractor_id'], errors='coerce')
        df = df[df['subcontractor_id'] == int(sub_id)]
    return df

def create_compliance_document(sub_id, doc_type, status, expiration):
    new_id = get_next_id("compliance_documents")
    append_row("compliance_documents", {
        "id": new_id, "subcontractor_id": sub_id,
        "document_type": doc_type, "status": status,
        "expiration_date": str(expiration)
    })

def delete_compliance_document(doc_id):
    delete_row_by_id("compliance_documents", doc_id)

# --- Quality ---
def get_quality_logs(project_id=None):
    df = read_worksheet("quality_logs", [
        'id', 'project_id', 'title', 'description', 'inspector_name', 'signer_name', 'date'
    ])
    if df.empty:
        return pd.DataFrame(columns=['id', 'project_id', 'title', 'description', 'inspector_name', 'signer_name', 'date'])
    if project_id is not None and 'project_id' in df.columns:
        df['project_id'] = pd.to_numeric(df['project_id'], errors='coerce')
        df = df[df['project_id'] == int(project_id)]
    if 'date' in df.columns:
        df = df.sort_values('date', ascending=False)
    return df

def create_quality_log(project_id, title, description, inspector, signer_name):
    new_id = get_next_id("quality_logs")
    append_row("quality_logs", {
        "id": new_id, "project_id": project_id, "title": title,
        "description": description, "inspector_name": inspector,
        "signer_name": signer_name
    })

def update_quality_log(log_id, title, description, inspector, signer_name):
    update_row_by_id("quality_logs", log_id, {
        "title": title, "description": description,
        "inspector_name": inspector, "signer_name": signer_name
    })

def delete_quality_log(log_id):
    delete_row_by_id("quality_logs", log_id)

# --- Lab Tests ---
def get_lab_tests(project_id=None):
    df = read_worksheet("lab_tests", ['id', 'project_id', 'test_type', 'test_date', 'result', 'observation'])
    if df.empty:
        return pd.DataFrame(columns=['id', 'project_id', 'test_type', 'test_date', 'result', 'observation'])
    if project_id is not None and 'project_id' in df.columns:
        df['project_id'] = pd.to_numeric(df['project_id'], errors='coerce')
        df = df[df['project_id'] == int(project_id)]
    if 'test_date' in df.columns:
        df = df.sort_values('test_date', ascending=False)
    return df

def create_lab_test(project_id, test_type, date, result, obs):
    new_id = get_next_id("lab_tests")
    append_row("lab_tests", {
        "id": new_id, "project_id": project_id, "test_type": test_type,
        "test_date": str(date), "result": result, "observation": obs
    })

def update_lab_test(test_id, test_type, date, result, obs):
    update_row_by_id("lab_tests", test_id, {
        "test_type": test_type, "test_date": str(date),
        "result": result, "observation": obs
    })

def delete_lab_test(test_id):
    delete_row_by_id("lab_tests", test_id)

# --- Tasks (Lean) ---
def get_tasks(project_id=None):
    df = read_worksheet("tasks", [
        'id', 'project_id', 'name', 'start_date', 'end_date', 'status', 'type', 'tags'
    ])
    if df.empty:
        return pd.DataFrame(columns=['id', 'project_id', 'name', 'start_date', 'end_date', 'status'])
    if project_id is not None and 'project_id' in df.columns:
        df['project_id'] = pd.to_numeric(df['project_id'], errors='coerce')
        df = df[df['project_id'] == int(project_id)]
    if 'start_date' in df.columns:
        df = df.sort_values('start_date')
    return df

def create_task(project_id, name, start, end, status="Por Hacer"):
    new_id = get_next_id("tasks")
    append_row("tasks", {
        "id": new_id, "project_id": project_id, "name": name,
        "start_date": str(start), "end_date": str(end), "status": status
    })

def update_task_status(task_id, new_status):
    update_row_by_id("tasks", task_id, {"status": new_status})

def update_task_details(task_id, name):
    update_row_by_id("tasks", task_id, {"name": name})

def delete_task(task_id):
    delete_row_by_id("tasks", task_id)

# --- Tenders ---
def create_tender(project_id, title, estimated_budget, tender_type, utm_value, status, ssd_code, mercado_publico_id=""):
    new_id = get_next_id("tenders")
    append_row("tenders", {
        "id": new_id, "project_id": project_id, "title": title,
        "type": tender_type, "budget_estimated": estimated_budget,
        "utm_value_at_creation": utm_value, "status": status,
        "ssd_code": ssd_code, "mercado_publico_id": mercado_publico_id
    })

def get_tenders(project_id=None):
    df = read_worksheet("tenders", [
        'id', 'project_id', 'title', 'type', 'budget_estimated',
        'utm_value_at_creation', 'status', 'ssd_code', 'mercado_publico_id'
    ])
    if df.empty:
        return pd.DataFrame(columns=[
            'id', 'project_id', 'title', 'type', 'budget_estimated',
            'utm_value_at_creation', 'status', 'ssd_code', 'mercado_publico_id'
        ])
    if project_id is not None and 'project_id' in df.columns:
        df['project_id'] = pd.to_numeric(df['project_id'], errors='coerce')
        df = df[df['project_id'] == int(project_id)]
    return df

def update_tender_status(tender_id, new_status):
    update_row_by_id("tenders", tender_id, {"status": new_status})

def update_tender(tender_id, title, budget, mercado_publico_id, tender_type):
    update_row_by_id("tenders", tender_id, {
        "title": title, "budget_estimated": budget,
        "mercado_publico_id": mercado_publico_id, "type": tender_type
    })

def delete_tender(tender_id):
    delete_row_by_id("tenders", tender_id)

# --- Contracts ---
def create_contract(tender_id, contractor_name, rut, amount, start, end):
    new_id = get_next_id("contracts")
    append_row("contracts", {
        "id": new_id, "tender_id": tender_id, "contractor_name": contractor_name,
        "rut_contractor": rut, "amount": amount,
        "start_date": str(start), "end_date": str(end)
    })

def get_contracts(tender_id=None):
    df = read_worksheet("contracts", [
        'id', 'tender_id', 'contractor_name', 'rut_contractor',
        'amount', 'start_date', 'end_date', 'status'
    ])
    if df.empty:
        return pd.DataFrame(columns=[
            'id', 'tender_id', 'contractor_name', 'rut_contractor',
            'amount', 'start_date', 'end_date', 'status'
        ])
    if tender_id is not None and 'tender_id' in df.columns:
        df['tender_id'] = pd.to_numeric(df['tender_id'], errors='coerce')
        df = df[df['tender_id'] == int(tender_id)]
    return df

def create_guarantee(contract_id, g_type, amount, expiration):
    new_id = get_next_id("guarantees")
    append_row("guarantees", {
        "id": new_id, "contract_id": contract_id, "type": g_type,
        "amount": amount, "expiration_date": str(expiration)
    })

def update_guarantee(guarantee_id, g_type, amount, expiration, status):
    update_row_by_id("guarantees", guarantee_id, {
        "type": g_type, "amount": amount,
        "expiration_date": str(expiration), "status": status
    })

def delete_guarantee(guarantee_id):
    delete_row_by_id("guarantees", guarantee_id)

def update_contract(contract_id, contractor_name, rut, amount, start, end, status):
    update_row_by_id("contracts", contract_id, {
        "contractor_name": contractor_name, "rut_contractor": rut,
        "amount": amount, "start_date": str(start),
        "end_date": str(end), "status": status
    })

def delete_contract(contract_id):
    delete_row_by_id("guarantees", contract_id)
    delete_row_by_id("contracts", contract_id)

# --- Phases ---
def get_phases(project_id):
    df = read_worksheet("phases", ['id', 'project_id', 'name', 'start_date', 'end_date', 'status'])
    if df.empty:
        return pd.DataFrame(columns=['id', 'project_id', 'name', 'start_date', 'end_date', 'status'])
    if 'project_id' in df.columns:
        df['project_id'] = pd.to_numeric(df['project_id'], errors='coerce')
        df = df[df['project_id'] == int(project_id)]
    return df

def add_phase(project_id, name, start, end):
    new_id = get_next_id("phases")
    append_row("phases", {
        "id": new_id, "project_id": project_id, "name": name,
        "start_date": str(start), "end_date": str(end)
    })

def update_phase(phase_id, name, start, end, status="Pendiente"):
    update_row_by_id("phases", phase_id, {
        "name": name, "start_date": str(start),
        "end_date": str(end), "status": status
    })

def delete_phase(phase_id):
    delete_row_by_id("phases", phase_id)

# --- Comments ---
def get_comments(project_id):
    df = read_worksheet("comments", ['id', 'project_id', 'user_id', 'content', 'timestamp'])
    if df.empty:
        return pd.DataFrame(columns=['id', 'content', 'timestamp', 'user_id', 'username'])
    if 'project_id' in df.columns:
        df['project_id'] = pd.to_numeric(df['project_id'], errors='coerce')
        df = df[df['project_id'] == int(project_id)]
    users_df = get_all_users()
    if not users_df.empty and 'user_id' in df.columns:
        user_map = users_df.set_index('id')['username'].to_dict()
        df['username'] = df['user_id'].map(user_map).fillna('Unknown')
    if 'timestamp' in df.columns:
        df = df.sort_values('timestamp', ascending=False)
    return df

def add_comment(project_id, user_id, content):
    new_id = get_next_id("comments")
    append_row("comments", {
        "id": new_id, "project_id": project_id, "user_id": user_id,
        "content": content, "timestamp": str(datetime.now())
    })

def update_comment(comment_id, content):
    update_row_by_id("comments", comment_id, {"content": content})

def delete_comment(comment_id):
    delete_row_by_id("comments", comment_id)

def get_all_comments():
    df = read_worksheet("comments")
    if df.empty:
        return pd.DataFrame(columns=['id', 'project_id'])
    return df[['id', 'project_id']] if 'project_id' in df.columns else pd.DataFrame(columns=['id', 'project_id'])

def update_project_config(project_id, status, lat, lon):
    update_row_by_id("projects", project_id, {"status": status, "latitude": lat, "longitude": lon})

# --- Teams & Stats ---
def get_global_team_stats():
    df = read_worksheet("project_assignments")
    if df.empty:
        return {
            "total_personnel": 0,
            "roles_df": pd.DataFrame(columns=['role', 'count']),
            "projects_df": pd.DataFrame(columns=['project_name', 'count'])
        }

    projects_df = get_projects()
    if not projects_df.empty and 'project_id' in df.columns:
        proj_map = projects_df.set_index('id')[['name', 'status']].to_dict('index')
        df['project_name'] = df['project_id'].map(lambda x: proj_map.get(int(x), {}).get('name', '') if pd.notna(x) else '')
        df['project_status'] = df['project_id'].map(lambda x: proj_map.get(int(x), {}).get('status', '') if pd.notna(x) else '')
        active_data = df[df['project_status'] == 'Activo']

        if active_data.empty:
            return {
                "total_personnel": 0,
                "roles_df": pd.DataFrame(columns=['role', 'count']),
                "projects_df": pd.DataFrame(columns=['project_name', 'count'])
            }

        total = len(active_data)
        roles_df = active_data['role'].value_counts().reset_index()
        roles_df.columns = ['role', 'count']
        projs_df = active_data['project_name'].value_counts().reset_index()
        projs_df.columns = ['project_name', 'count']

        return {
            "total_personnel": total,
            "roles_df": roles_df,
            "projects_df": projs_df
        }

    return {
        "total_personnel": 0,
        "roles_df": pd.DataFrame(columns=['role', 'count']),
        "projects_df": pd.DataFrame(columns=['project_name', 'count'])
    }

# --- Config ---
def get_config(key, default=None):
    df = read_worksheet("system_config")
    if df.empty or 'key' not in df.columns:
        return default
    row = df[df['key'] == key]
    if row.empty:
        return default
    return row.iloc[0].get('value', default)

def set_config(key, value):
    """Set a config key-value pair. Works with or without 'id' column."""
    try:
        _throttle()
        ws = get_sheet().worksheet("system_config")
        _throttle()
        headers = ws.row_values(1)
        if headers and 'key' in headers:
            _throttle()
            all_rows = ws.get_all_values()
            for i, row in enumerate(all_rows[1:], start=2):
                if len(row) > 0 and row[0] == key:
                    val_col = headers.index('value') + 1 if 'value' in headers else 2
                    def _do_update_cell():
                        ws.update_cell(i, val_col, str(value))
                    result, ok = _retry(_do_update_cell)
                    if not ok:
                        return False, "Failed after retries"
                    _clear_worksheet_cache("system_config")
                    return True, "Updated"
        # Not found or no headers → append
        if not headers or headers[0] != 'key':
            ws.update([['key', 'value']], 'A1')
        def _do_append():
            ws.append_row([key, str(value)])
        result, ok = _retry(_do_append)
        if not ok:
            return False, "Failed after retries"
        _clear_worksheet_cache("system_config")
        return True, "Appended"
    except Exception as e:
        print(f"Error set_config({key}): {e}")
        return False, str(e)

# --- AI Usage ---
def log_ai_usage(user_id, tokens):
    new_id = get_next_id("ai_usage_logs")
    append_row("ai_usage_logs", {
        "id": new_id, "user_id": user_id, "tokens_used": tokens
    })

def get_daily_ai_usage_count():
    try:
        today_key = f"ai_usage_{datetime.now().strftime('%Y-%m-%d')}"
        val = get_config(today_key, "0")
        return int(val)
    except:
        return 0

def increment_daily_ai_usage():
    try:
        today_key = f"ai_usage_{datetime.now().strftime('%Y-%m-%d')}"
        current = get_daily_ai_usage_count()
        set_config(today_key, current + 1)
        return current + 1
    except Exception as e:
        print(f"Error incrementing AI usage: {e}")
        return 999

def reset_ai_usage():
    try:
        today_key = f"ai_usage_{datetime.now().strftime('%Y-%m-%d')}"
        set_config(today_key, 0)
        return True
    except:
        return False

# --- Notification ---
def get_monthly_notif_count():
    try:
        month_key = f"notif_usage_{datetime.now().strftime('%Y-%m')}"
        val = get_config(month_key, "0")
        return int(val)
    except:
        return 0

def increment_monthly_notif():
    try:
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
    val = get_config("ai_daily_limit", "3")
    try:
        return int(val)
    except:
        return 3

# --- Warehouse ---
def get_warehouse_items(project_id):
    df = read_worksheet("warehouse_items", [
        'id', 'project_id', 'hoja', 'fecha', 'factura', 'cliente', 'rut',
        'obra', 'codigo', 'descripcion', 'cantidad', 'p_unitario', 'um', 'total', 'status', 'created_at'
    ])
    if df.empty:
        return pd.DataFrame(columns=[
            'id', 'project_id', 'hoja', 'fecha', 'factura', 'cliente', 'rut',
            'obra', 'codigo', 'descripcion', 'cantidad', 'p_unitario', 'um', 'total', 'status', 'created_at'
        ])
    if project_id is not None and 'project_id' in df.columns:
        df['project_id'] = pd.to_numeric(df['project_id'], errors='coerce')
        df = df[df['project_id'] == int(project_id)]
    for col in ['cantidad', 'p_unitario', 'total']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def add_warehouse_items(project_id, items_list):
    for item in items_list:
        insert_data = item.copy()
        insert_data['project_id'] = project_id
        for col in ['cantidad', 'p_unitario', 'total']:
            try:
                insert_data[col] = float(insert_data.get(col, 0))
            except:
                insert_data[col] = 0.0
        insert_data['status'] = 'En Bodega'
        insert_data['id'] = get_next_id("warehouse_items")
        append_row("warehouse_items", insert_data)

def update_warehouse_item(item_id, item_data):
    update_payload = {
        k: v for k, v in item_data.items()
        if k not in ['id', 'project_id', 'created_at']
    }
    for col in ['cantidad', 'p_unitario', 'total']:
        if col in update_payload:
            try:
                update_payload[col] = float(update_payload[col])
            except:
                update_payload[col] = 0.0
    update_row_by_id("warehouse_items", item_id, update_payload)

def delete_warehouse_item(item_id):
    delete_row_by_id("warehouse_items", item_id)

# --- OCR ---
def get_monthly_ocr_page_count():
    try:
        month_key = "ocr_pages_" + datetime.now().strftime('%Y-%m')
        val = get_config(month_key, "0")
        return int(val)
    except:
        return 0

def increment_monthly_ocr_pages(pages):
    try:
        month_key = "ocr_pages_" + datetime.now().strftime('%Y-%m')
        current = get_monthly_ocr_page_count()
        set_config(month_key, current + pages)
        return current + pages
    except Exception as e:
        print("Error incrementing OCR pages: " + str(e))
        return 999999

def reset_monthly_ocr_pages():
    try:
        month_key = "ocr_pages_" + datetime.now().strftime('%Y-%m')
        set_config(month_key, 0)
        return True
    except Exception as e:
        print("Error resetting OCR pages: " + str(e))
        return False

def get_ocr_monthly_limit():
    val = get_config("ocr_monthly_page_limit", "500")
    try:
        return int(val)
    except:
        return 500

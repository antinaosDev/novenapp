import asyncio
from notificationapi_python_server_sdk import notificationapi
from modules import data
import streamlit as st

def _init_api():
    # Get credentials from secrets
    try:
        client_id = st.secrets["NOTIFICATIONAPI"]["CLIENT_ID"]
        client_secret = st.secrets["NOTIFICATIONAPI"]["CLIENT_SECRET"]
    except:
        print("WARNING: NotificationAPI credentials not configured in secrets")
        return False
    
    if client_id and client_secret:
        notificationapi.init(client_id, client_secret)
        return True
    return False

async def _send_async(user_email, subject, message):
    try:
        await notificationapi.send({
            "notificationId": "generic_alert", 
            "user": {
                "id": user_email,
                "email": user_email
            },
            "email": {
                "subject": subject,
                "html": message
            }
        })
        print(f"DEBUG: Email SENT to {user_email} (ID: generic_alert)")
        return True
    except Exception as e:
        print(f"DEBUG: Async Send Error: {e}")
        return False

def send_notification(user_email, subject, message):
    """
    Sends a notification via Email (NotificationAPI). Enforces Monthly Limit.
    """
    if not user_email:
        print("ERROR: Email/User ID is empty.")
        return False

    # Check Limit
    current = data.get_monthly_notif_count()
    limit = data.get_notif_limit()
    
    if current >= limit:
        print(f"LIMIT REACHED: Monthly notification limit ({limit}) exceeded.")
        # Optional: We could trigger a dashboard alert here if we had a mechanism
        return False
        
    if _init_api():
        try:
            # Send
            asyncio.run(_send_async(user_email, subject, message))
            
            # Increment Usage (Success assumed if no exception)
            data.increment_monthly_notif()
            return True
        except Exception as e:
            print(f"Sync Wrapper Error: {e}")
            return False
    else:
        return False

# --- Templates ---
def _tpl_project_alert(name, end_date, days):
    return f"""
    <div style="font-family: sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #c0392b;">⚠️ Alerta de Vencimiento de Proyecto</h2>
        <p>El proyecto <strong>{name}</strong> está próximo a su fecha de término.</p>
        <ul>
            <li><strong>Fecha de Fin:</strong> {end_date}</li>
            <li><strong>Días Restantes:</strong> {days} días</li>
        </ul>
        <p style="color: #64748b; font-size: 14px;">Gestione el cierre o extensión correspondiente.</p>
        <hr>
        <small>Notificación Automática - Novenapp</small>
    </div>
    """

def _tpl_contract_alert(contractor, end_date, days):
    return f"""
    <div style="font-family: sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #d35400;">⚠️ Alerta de Vencimiento de Contrato</h2>
        <p>El contrato con <strong>{contractor}</strong> está por vencer.</p>
        <ul>
            <li><strong>Fecha de Término:</strong> {end_date}</li>
            <li><strong>Días Restantes:</strong> {days} días</li>
        </ul>
        <p style="color: #64748b; font-size: 14px;">Revise estados de pago y recepciones finales.</p>
        <hr>
        <small>Notificación Automática - Novenapp</small>
    </div>
    """

def _tpl_guarantee_alert(g_type, amount, exp_date, days):
    return f"""
    <div style="font-family: sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #e67e22;">⚠️ Alerta de Vencimiento de Garantía</h2>
        <p>Una boleta de garantía ({g_type}) está próxima a expirar.</p>
        <ul>
            <li><strong>Monto:</strong> {amount}</li>
            <li><strong>Vencimiento:</strong> {exp_date}</li>
            <li><strong>Días Restantes:</strong> {days} días</li>
        </ul>
        <p style="color: #64748b; font-size: 14px;">Gestione la renovación o devolución del documento.</p>
        <hr>
        <small>Notificación Automática - Novenapp</small>
    </div>
    """

# --- Automation ---
def check_and_notify_deadlines():
    """
    Checks for expiring projects, contracts, and guarantees.
    Sends alerts to Admin, Programador, and Residente de Obra.
    """
    if not _init_api():
        return "Error: API no configurada."
        
    log = []
    days_alert = int(data.get_config("alert_days", 15))
    
    # 1. Get Targets
    projs = data.get_projects_expiring_soon(days_alert)
    contracts = data.get_contracts_expiring_soon(days_alert)
    guarantees = data.get_guarantees_expiring_soon(days_alert)
    
    if projs.empty and contracts.empty and guarantees.empty:
        return f"Sin vencimientos próximos (Umbral: {days_alert} días)."
    
    # 2. Get Recipients
    users = data.get_all_users()
    # ROLES: Administrador, Programador, Residente de Obra
    recipients = users[users['role'].isin(['Administrador', 'Programador', 'Residente de Obra'])]
    
    # Valid Email Filter
    if 'email' in recipients.columns:
        recipients = recipients[recipients['email'].str.contains("@", na=False)]
    else:
        return "Error: Columna email no detectada o vacía."
    
    sent_count = 0
    from datetime import datetime
    
    # Helper to send batch
    def send_batch(items, type_label, name_col, date_col, tpl_func):
        count = 0
        for _, item in items.iterrows():
            # Idempotency Check: Prevent duplicate notifications for the same event
            notif_key = f"notif_{type_label}_{item['id']}"
            if data.get_config(notif_key):
                continue

            end_dt = datetime.strptime(str(item[date_col]), '%Y-%m-%d')
            days_left = (end_dt - datetime.now()).days + 1
            
            # Subject
            if type_label == 'Garantía':
                subject = f"⚠️ Vencimiento Garantía: {item.get('type', 'Doc')} ({days_left} días)"
                msg = tpl_func(item.get('type', 'Doc'), item.get('amount', 0), item[date_col], days_left)
            elif type_label == 'Contrato':
                subject = f"⚠️ Vencimiento Contrato: {item.get('contractor_name', 'Contratista')} ({days_left} días)"
                msg = tpl_func(item.get('contractor_name', 'Unknown'), item[date_col], days_left)
            else:
                subject = f"⚠️ Vencimiento Proyecto: {item[name_col]} ({days_left} días)"
                msg = tpl_func(item[name_col], item[date_col], days_left)
            
            # Send to all recipients
            success_any = False
            for _, u in recipients.iterrows():
                if send_notification(u['email'], subject, msg):
                    success_any = True
                    count += 1
            
            # Mark as notified if at least one email went out (or even if not, to avoid retry loops on errors? Better only on success)
            if success_any:
                data.set_config(notif_key, datetime.now().strftime('%Y-%m-%d'))
                log.append(f"{type_label} ID {item['id']}: Alertados {len(recipients)} usuarios.")
        return count

    # 3. Process each type
    if not projs.empty:
        sent_count += send_batch(projs, "Proyecto", "name", "end_date", _tpl_project_alert)
        
    if not contracts.empty:
        sent_count += send_batch(contracts, "Contrato", "contractor_name", "end_date", _tpl_contract_alert)
        
    if not guarantees.empty:
        sent_count += send_batch(guarantees, "Garantía", "id", "expiration_date", _tpl_guarantee_alert)

    return f"Proceso Finalizado. {sent_count} notificaciones enviadas. Detalles: {'; '.join(log)}"

def run_daily_automation():
    """
    Checks if deadlines have been checked today. If not, runs check_and_notify_deadlines.
    Called from app.py on startup/login.
    """
    try:
        from datetime import datetime
        today_str = datetime.now().strftime('%Y-%m-%d')
        last_run = data.get_config("last_notification_date_verified")
        
        if last_run != today_str:
            print(f"🔄 Executing Daily Notification Check for {today_str}...")
            result = check_and_notify_deadlines()
            if "Error" not in result:
                data.set_config("last_notification_date_verified", today_str)
                print(f"✅ Daily Check Done: {result}")
                return True, result
            else:
                print(f"❌ Daily Check Error: {result}")
                return False, result
        else:
            # Already run today
            return False, "Already checked today."
            
    except Exception as e:
        print(f"Error in daily automation: {e}")
        return False, str(e)

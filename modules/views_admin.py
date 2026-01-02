import streamlit as st
import pandas as pd
from modules import data, notifications

def render_admin_panel():
    st.title("🛡️ Panel de Administración")
    st.caption("Zona Exclusiva para Rol: Programador")
    
    tab_ai, tab_notif = st.tabs(["🤖 Gestión IA (Groq)", "🔔 Notificaciones"])
    
    # --- Tab 1: AI Management ---
    with tab_ai:
        st.subheader("Control de Uso de IA")
        
        # 1. Configuration
        with st.container(border=True):
            st.write("**Configuración General**")
            # Use new key: ai_daily_limit
            current_limit = data.get_config("ai_daily_limit", 3)
            new_limit = st.number_input("Límite de Llamadas Diarias a la API (AI)", value=int(current_limit), min_value=1)
            
            if st.button("💾 Guardar Límite AI"):
                success, msg = data.set_config("ai_daily_limit", new_limit)
                if success:
                    st.success("Límite actualizado.")
                    st.rerun()
                else:
                    st.error(f"Error al guardar: {msg}")
                    
        st.divider()
        
        # 2. Daily Stats
        st.subheader("Consumo Diario")
        count = data.get_daily_ai_usage_count()
        limit = data.get_ai_call_limit()
        
        if count > 0:
            c1, c2 = st.columns(2)
            c1.metric("Llamadas Hoy", f"{count} / {limit}")
            # Tokens Logic Removed for Simplicity (or add back if we track it in config, but we just track calls now)
            c2.progress(min(count/limit, 1.0), text="Progreso Diario")
        else:
            st.info("Sin consumo de IA registrado hoy.")
            
        # 3. Actions
        if st.button("🔄 Reiniciar Contadores (Hoy)", type="primary"):
            if data.reset_ai_usage():
                st.success("Contadores de hoy reiniciados.")
                st.rerun()
            else:
                st.error("Error al reiniciar.")

    # --- Tab 2: Notifications ---
    with tab_notif:
        st.subheader("Configuración de Notificaciones (NotificationAPI)")
        
        # 1. Configuration
        with st.container(border=True):
            st.subheader("📊 Consumo Mensual")
            n_curr = data.get_monthly_notif_count()
            n_limit = data.get_notif_limit()
            st.progress(min(n_curr/n_limit, 1.0), text=f"Emails Enviados: {n_curr} / {n_limit}")
            
            st.divider()
            st.write("**Parámetros de Envío**")
            with st.form("notif_config"):
                # Credentials are hardcoded now
                st.info("Credenciales de API: Configuradas en servidor.")
                
                monthly_limit = st.number_input("Límite de Notificaciones Mensuales", value=int(data.get_config("notif_monthly_limit", 100)))
                days_alert = st.number_input("Días de Aviso Prematuro (Plazo)", value=int(data.get_config("alert_days", 15)))
                
                if st.form_submit_button("Guardar Configuración"):
                    s1, m1 = data.set_config("notif_monthly_limit", monthly_limit)
                    s2, m2 = data.set_config("alert_days", days_alert)
                    
                    if s1 and s2:
                        st.success("Configuración guardada.")
                        st.rerun()
                    else:
                        st.error(f"Error: {m1} | {m2}")

        st.divider()
        
        # 2. Test
        with st.container(border=True):
            st.subheader("📨 Prueba de Envío")
            
            # Use current user email as default
            default_email = st.session_state.get('email', '')
            
            with st.form("test_notif"):
                t_email = st.text_input("Email Destino", value=default_email)
                t_subj = st.text_input("Asunto", value="Prueba Novenapp")
                t_msg = st.text_area("Mensaje", value="Esta es una notificación de prueba.")
                
                if st.form_submit_button("Enviar Prueba Email"):
                    if not t_email:
                        st.error("Debes ingresar un email.")
                    elif notifications.send_notification(t_email, t_subj, t_msg):
                        st.success(f"Email enviado a {t_email}")
                    else:
                        st.error("Fallo el envío. Verifique log.")
                        
                        
            st.divider()
            
            # 3. Actions
            st.subheader("🚀 Ejecutar Revisión de Plazos")
            st.caption("Barre la BD buscando proyectos que venzan en el plazo configurado.")
            if st.button("Ejecutar Revisión Ahora", type="primary"):
                with st.spinner("Revisando BD..."):
                    result_log = notifications.check_and_notify_deadlines()
                    st.success(result_log)

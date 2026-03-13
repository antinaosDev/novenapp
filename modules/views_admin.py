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

        # --- OCR Monthly Quota ---
        with st.container(border=True):
            st.write("**📄 Cuota Mensual de Hojas OCR**")
            st.caption("Cada hoja (página) de PDF analizada por la IA se contabiliza. El contador se reinicia automáticamente cada mes calendario.")
            
            ocr_used = data.get_monthly_ocr_page_count()
            ocr_limit = data.get_ocr_monthly_limit()
            ocr_pct = min(ocr_used / max(ocr_limit, 1), 1.0)

            col1, col2 = st.columns(2)
            col1.metric("Hojas Analizadas (Este Mes)", f"{ocr_used}")
            col2.metric("Límite Mensual Configurado", f"{ocr_limit}")
            st.progress(ocr_pct, text=f"{ocr_used} / {ocr_limit} hojas utilizadas ({ocr_pct*100:.1f}%)")
            
            st.divider()
            new_limit = st.number_input("Nuevo Límite Mensual (hojas)", min_value=1, value=int(ocr_limit), step=50)
            col_a, col_b = st.columns(2)
            
            if col_a.button("💾 Guardar Nuevo Límite", type="primary"):
                success, msg = data.set_config("ocr_monthly_page_limit", new_limit)
                if success:
                    st.success(f"Límite actualizado a {new_limit} hojas/mes.")
                    st.rerun()
                else:
                    st.error(f"Error: {msg}")
            
            if col_b.button("🔄 Reiniciar Contador del Mes", type="secondary"):
                if data.reset_monthly_ocr_pages():
                    st.success("Contador de hojas OCR reiniciado a 0.")
                    st.rerun()
                else:
                    st.error("Error al reiniciar el contador.")
        
        st.divider()
        
        # --- Legacy Daily AI Call Limit (for other AI features) ---
        with st.expander("⚙️ Configuración Legacy (Llamadas API Diarias)"):
            current_limit = data.get_config("ai_daily_limit", 3)
            new_daily_limit = st.number_input("Límite de Llamadas Diarias a la API (AI)", value=int(current_limit), min_value=1)
            
            if st.button("💾 Guardar Límite Diario"):
                success, msg = data.set_config("ai_daily_limit", new_daily_limit)
                if success:
                    st.success("Límite actualizado.")
                    st.rerun()
                else:
                    st.error(f"Error al guardar: {msg}")

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

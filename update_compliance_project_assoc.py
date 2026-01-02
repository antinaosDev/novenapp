
print("⚠️ IMPORTANTE: Falta vincular los subcontratos a los proyectos.")
print("Ejecuta este ultimo SQL en Supabase:")
print("-" * 50)
print("""
ALTER TABLE subcontractors ADD COLUMN project_id BIGINT REFERENCES projects(id);
""")
print("-" * 50)

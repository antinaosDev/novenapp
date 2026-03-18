print("COPIA Y EJECUTA EL SIGUIENTE SQL EN EL EDITOR SQL DE SUPABASE:")
print("-" * 50)
print("""
-- 1. Add monto_asignado to subcontractors
ALTER TABLE subcontractors ADD COLUMN monto_asignado NUMERIC DEFAULT 0;
""")
print("-" * 50)

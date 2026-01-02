
print("COPIA Y EJECUTA EL SIGUIENTE SQL EN EL EDITOR SQL DE SUPABASE PARA MIGRAR LOS ESTADOS:")
print("-" * 50)
print("""
UPDATE tasks SET status = 'Por Hacer' WHERE status = 'To Do';
UPDATE tasks SET status = 'En Curso' WHERE status = 'In Progress';
UPDATE tasks SET status = 'Bloqueado' WHERE status = 'Blocked';
UPDATE tasks SET status = 'Completado' WHERE status = 'Done';
""")
print("-" * 50)

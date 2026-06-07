import sys
sys.path.insert(0, '.')
from modules import data
import bcrypt

users = [
    ("alain_admin", "supad_alain1"),
    ("victor_astorga", "vicast.nov"),
    ("kajfv_nov", "kajfv_nov2"),
]

for username, new_password in users:
    df = data.get_user_by_username(username)
    if df.empty:
        print(f"ERROR: {username} no encontrado")
        continue

    row = df.iloc[0]
    user_id = row["id"]
    email = row.get("email", "")
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    data.update_user(user_id, row["username"], row["full_name"], row["role"], hashed, email)
    print(f"OK: {username} -> contraseña actualizada (id={user_id})")

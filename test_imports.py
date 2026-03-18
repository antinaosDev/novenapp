try:
    from modules import data, compliance
    print("Imports successful!")
except Exception as e:
    print(f"Import failed: {e}")

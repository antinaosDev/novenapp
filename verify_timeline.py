import pandas as pd
import plotly.express as px

def get_dynamic_height(phases):
    return max(350, len(phases) * 35 + 100)

def verify_logic():
    print("--- VERIFICATION START ---")
    
    # Case 1: Few phases (Under minimum)
    phases_small = pd.DataFrame({'name': ['Phase 1', 'Phase 2'], 'start_date': ['2023-01-01']*2, 'end_date': ['2023-01-05']*2})
    h_small = get_dynamic_height(phases_small)
    print(f"Small (2 items): Expected 350, Got {h_small}")
    if h_small == 350:
        print("PASS: Small Dataset uses min height.")
    else:
        print("FAIL: Small Dataset height incorrect.")

    # Case 2: Many phases (Over minimum)
    phases_large = pd.DataFrame({'name': [f'Phase {i}' for i in range(20)], 'start_date': ['2023-01-01']*20, 'end_date': ['2023-01-05']*20})
    h_large = get_dynamic_height(phases_large)
    expected = 20 * 35 + 100 # 800
    print(f"Large (20 items): Expected {expected}, Got {h_large}")
    if h_large == expected:
        print("PASS: Large Dataset uses compact dynamic height.")
    else:
        print("FAIL: Large Dataset height incorrect.")

    print("--- VERIFICATION END ---")

if __name__ == "__main__":
    verify_logic()

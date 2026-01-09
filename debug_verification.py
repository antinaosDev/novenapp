import streamlit as st
import toml
import os
import pandas as pd
import sys

# Mock secrets (same as before)
try:
    secrets = toml.load(".streamlit/secrets.toml")
    if not hasattr(st, 'secrets') or not st.secrets:
        class MockSecrets(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
            def __getitem__(self, key):
                return super().__getitem__(key)
        st.secrets = MockSecrets(secrets)
except Exception:
    pass

# Patch modules
if 'modules.data' in sys.modules:
    del sys.modules['modules.data']
from modules import data

def run_debug():
    with open("debug_verification.txt", "w", encoding="utf-8") as f:
        f.write("--- VERIFICATION START ---\n")
        
        # 1. Fetch Projects
        projects_df = data.get_projects()
        f.write(f"Projects:\n{projects_df[['id', 'name', 'budget_total']].to_string()}\n\n")

        # 2. Fetch Expenses
        expenses_df = data.get_expenses_df()
        f.write(f"Expenses Count: {len(expenses_df)}\n")

        # 3. Fetch Purchase Orders (The new part)
        f.write("Fetching Purchase Orders...\n")
        pos_df = data.get_purchase_orders()
        if not pos_df.empty:
            f.write(f"POs Found: {len(pos_df)}\n")
            f.write(f"POs Head:\n{pos_df[['id', 'project_id', 'total_amount', 'status']].head().to_string()}\n")
        else:
            f.write("No POs found.\n")

        # 4. Simulate the Logic
        if not projects_df.empty:
            # A. Expenses
            if not expenses_df.empty:
                 exp_grouped = expenses_df.groupby('project_id')['amount'].sum().reset_index()
                 exp_grouped.columns = ['project_id', 'total_exp']
            else:
                 exp_grouped = pd.DataFrame(columns=['project_id', 'total_exp'])
            
            # B. Purchase Orders
            if not pos_df.empty:
                 valid_pos = pos_df[pos_df['status'] != 'Rechazada']
                 pos_grouped = valid_pos.groupby('project_id')['total_amount'].sum().reset_index()
                 pos_grouped.columns = ['project_id', 'total_pos']
                 f.write(f"\nPOs Grouped:\n{pos_grouped.to_string()}\n")
            else:
                 pos_grouped = pd.DataFrame(columns=['project_id', 'total_pos'])

            # C. Combine
            costs_merged = pd.DataFrame(columns=['project_id', 'amount'])
            if not exp_grouped.empty or not pos_grouped.empty:
                 costs_merged = pd.merge(exp_grouped, pos_grouped, on='project_id', how='outer').fillna(0)
                 costs_merged['amount'] = costs_merged['total_exp'] + costs_merged['total_pos']
                 f.write(f"\nCombined Costs:\n{costs_merged.to_string()}\n")
            
            # D. Final Merge
            budget_analysis = pd.merge(
                projects_df[['id', 'name', 'budget_total', 'status']], 
                costs_merged[['project_id', 'amount']], 
                left_on='id', 
                right_on='project_id', 
                how='left'
            )
            budget_analysis['amount'] = budget_analysis['amount'].fillna(0)
            
            f.write(f"\nFinal Analysis:\n{budget_analysis[['name', 'budget_total', 'amount']].to_string()}\n")
            
            # Check if we have non-zero amounts now
            non_zero = budget_analysis[budget_analysis['amount'] > 0]
            if not non_zero.empty:
                f.write("\nSUCCESS: Found projects with Gasto Real > 0.\n")
            else:
                f.write("\nWARNING: Gasto Real is still 0 for all projects (might be correct if no POs/Exp exist).\n")

        f.write("\n--- VERIFICATION END ---\n")

if __name__ == "__main__":
    try:
        run_debug()
    except Exception as e:
        with open("debug_verification.txt", "a") as f:
            f.write(f"\nERROR: {e}\n")

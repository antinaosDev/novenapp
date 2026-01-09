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
    with open("debug_output.txt", "w", encoding="utf-8") as f:
        f.write("--- DEBUG START (File) ---\n")
        
        f.write("Fetching Projects...\n")
        try:
            projects_df = data.get_projects()
            f.write(f"Projects count: {len(projects_df)}\n")
            if not projects_df.empty:
                f.write(f"Projects Head:\n{projects_df.head().to_string()}\n")
                f.write(f"Projects Dtypes:\n{projects_df.dtypes}\n")
                f.write(f"Projects ID type: {projects_df['id'].dtype}\n")
            else:
                f.write("Projects DF is empty.\n")
        except Exception as e:
            f.write(f"Error fetching projects: {e}\n")
            projects_df = pd.DataFrame()

        f.write("\nFetching Expenses...\n")
        try:
            expenses_df = data.get_expenses_df()
            f.write(f"Expenses count: {len(expenses_df)}\n")
            if not expenses_df.empty:
                f.write(f"Expenses Head:\n{expenses_df.head().to_string()}\n")
                f.write(f"Expenses Dtypes:\n{expenses_df.dtypes}\n")
                f.write(f"Expenses project_id type: {expenses_df['project_id'].dtype}\n")
            else:
                f.write("Expenses DF is empty.\n")
        except Exception as e:
            f.write(f"Error fetching expenses: {e}\n")
            expenses_df = pd.DataFrame()

        if not projects_df.empty and not expenses_df.empty:
            f.write("\nAttempting Merge...\n")
            
            p_ids = projects_df['id'].unique()
            e_ids = expenses_df['project_id'].unique()
            f.write(f"Unique Project IDs in Projects: {p_ids}\n")
            f.write(f"Unique Project IDs in Expenses: {e_ids}\n")
            
            exp_by_proj = expenses_df.groupby('project_id')['amount'].sum().reset_index()
            f.write(f"Expenses by Project (Grouped):\n{exp_by_proj.to_string()}\n")
            
            budget_analysis = pd.merge(
                projects_df[['id', 'name', 'budget_total', 'status']], 
                exp_by_proj, 
                left_on='id', 
                right_on='project_id', 
                how='left'
            )
            f.write(f"Merge Result Head:\n{budget_analysis.head().to_string()}\n")
            f.write(f"Merge Result 'amount' check:\n{budget_analysis[['name', 'amount']].to_string()}\n")
            
        else:
            f.write("\nOne of the dataframes is empty or failed to load.\n")
        
        f.write("--- DEBUG END ---\n")

if __name__ == "__main__":
    try:
        run_debug()
    except Exception as e:
        with open("debug_output.txt", "a") as f:
            f.write(f"\nCRITICAL ERROR: {e}\n")

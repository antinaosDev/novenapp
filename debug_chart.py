import streamlit as st
import pandas as pd
from modules import data
import sys

def run_debug():
    print("--- DEBUG START ---")
    print("Fetching Projects...")
    projects_df = data.get_projects()
    print("Projects DF Head:")
    print(projects_df.head().to_string())
    print("Projects DF Dtypes:")
    print(projects_df.dtypes)

    print("Fetching Expenses...")
    expenses_df = data.get_expenses_df()
    print("Expenses DF Head:")
    print(expenses_df.head().to_string())
    print("Expenses DF Dtypes:")
    print(expenses_df.dtypes)

    if not projects_df.empty and not expenses_df.empty:
        print("Attempting Merge...")
        
        # Check unique IDs
        p_ids = projects_df['id'].unique()
        e_ids = expenses_df['project_id'].unique()
        print(f"Project IDs: {p_ids}")
        print(f"Expense Project IDs: {e_ids}")
        
        # Check type of IDs
        if len(p_ids) > 0:
            print(f"Type of Project ID: {type(p_ids[0])}")
        if len(e_ids) > 0:
            e_id_val = e_ids[0]
            if pd.isna(e_id_val):
                 # Find non-na
                 non_na = [x for x in e_ids if not pd.isna(x)]
                 if non_na:
                     e_id_val = non_na[0]
            print(f"Type of Expense Project ID: {type(e_id_val)}")

        exp_by_proj = expenses_df.groupby('project_id')['amount'].sum().reset_index()
        print("Expenses by Project:")
        print(exp_by_proj.to_string())
        
        budget_analysis = pd.merge(
            projects_df[['id', 'name', 'budget_total', 'status']], 
            exp_by_proj, 
            left_on='id', 
            right_on='project_id', 
            how='left'
        )
        print("Merge Result:")
        print(budget_analysis.to_string())
        
        budget_analysis['amount'] = budget_analysis['amount'].fillna(0)
        print("Final Analysis (Amount Filled):")
        print(budget_analysis[['name', 'amount']].to_string())
    else:
        print("One of the dataframes is empty.")
    
    print("--- DEBUG END ---")

if __name__ == "__main__":
    try:
        run_debug()
    except Exception as e:
        print(f"ERROR: {e}")

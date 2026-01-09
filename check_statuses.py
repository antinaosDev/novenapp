from modules import data
import pandas as pd

try:
    phases = data.get_all_phases_debug() # Assuming this exists or I'll just get all phases via SQL logic if I could.
    # But I don't have get_all_phases.
    # I'll fetch for a project I know exists or getting all projects then fetching phases.
    projects = data.get_projects()
    if not projects.empty:
        pid = projects.iloc[0]['id']
        phases = data.get_phases(pid)
        if not phases.empty:
            print(f"Statuses found: {phases['status'].unique()}")
        else:
            print("No phases for first project.")
            
        # Try to find any project with phases
        for _, p in projects.iterrows():
             ph = data.get_phases(p['id'])
             if not ph.empty:
                 print(f"Project {p['id']} Statuses: {ph['status'].unique()}")
except Exception as e:
    print(e)

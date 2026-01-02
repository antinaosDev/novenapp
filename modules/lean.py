from modules import data
import pandas as pd

def get_tasks(project_id=None):
    return data.get_tasks(project_id)

def create_task(project_id, name, start, end, status="Por Hacer"):
    data.create_task(project_id, name, start, end, status)

def update_task_status(task_id, new_status):
    data.update_task_status(task_id, new_status)

def update_task_details(task_id, name):
    data.update_task_details(task_id, name)

def delete_task(task_id):
    data.delete_task(task_id)

def get_ppc(tasks_df):
    """
    Calculates PPC (Percent Plan Complete) for the provided tasks.
    Ideally filters for current week tasks.
    """
    if tasks_df.empty:
        return 0
    
    # Simple logic: Completed / Total in the provided set
    # In a real scenario, this would filter tasks promised for *this week*
    total = len(tasks_df)
    completed = len(tasks_df[tasks_df['status'] == 'Completado'])
    
    if total == 0:
        return 0
        
    return int((completed / total) * 100)

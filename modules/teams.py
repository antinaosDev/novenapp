from modules import data
import pandas as pd

def get_project_locations():
    """Returns a DataFrame with project names and coordinates."""
    # data.get_projects returns all projects.
    # We filter status = 'Activo' and select cols.
    projects = data.get_projects()
    if not projects.empty:
        # Ensure status is Activo
        projects = projects[projects['status'] == 'Activo']
        
        # Ensure lat/long exist (should due to schema)
        if 'latitude' in projects.columns and 'longitude' in projects.columns:
             return projects[['id', 'name', 'latitude', 'longitude', 'status']]
        else:
             return pd.DataFrame()
    return pd.DataFrame()

def get_team_members(project_id):
    """Returns a DataFrame of users assigned to a project."""
    return data.get_project_assignments(project_id)

def get_all_assignments():
    """Returns all project assignments globally."""
    return data.get_all_project_assignments()

def assign_user_to_project(project_id, user_id, role, assigned_at=None):
    """Assigns a user to a project with a specific role."""
    data.assign_user_to_project(project_id, user_id, role, assigned_at)

def remove_team_member(assignment_id):
    """Removes a user from a project."""
    data.remove_project_assignment(assignment_id)

def get_all_users():
    """Returns all users for selection."""
    return data.get_all_users()

def get_stats():
    """Returns global team statistics."""
    return data.get_global_team_stats()

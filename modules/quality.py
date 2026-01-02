from modules import data
import pandas as pd

def get_logs(project_id=None):
    return data.get_quality_logs(project_id)

def create_log(project_id, title, description, inspector, signer_name):
    data.create_quality_log(project_id, title, description, inspector, signer_name)

def update_log(log_id, title, description, inspector, signer_name):
    data.update_quality_log(log_id, title, description, inspector, signer_name)

def delete_log(log_id):
    data.delete_quality_log(log_id)

# --- Lab Tests ---
def get_lab_tests(project_id):
    return data.get_lab_tests(project_id)

def create_lab_test(project_id, test_type, date, result, obs):
    data.create_lab_test(project_id, test_type, date, result, obs)

def update_lab_test(test_id, test_type, date, result, obs):
    data.update_lab_test(test_id, test_type, date, result, obs)

def delete_lab_test(test_id):
    data.delete_lab_test(test_id)

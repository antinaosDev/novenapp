import streamlit as st
from modules import data
import pandas as pd

# Mocking st.secrets for local run if needed, but data.py handles it if run via streamlit or if secrets.toml exists.
# Assuming secrets are available or we can run via 'streamlit run' if needed, but standard python execution 
# might fail if st.secrets is accessed at module level in data.py outside of streamlit context BUT
# data.py uses @st.cache_resource, so standard python might complain about st.secrets if not mocked.
# However, let's try to simulate the logic.

# Redirect output to file
with open("verification_result.txt", "w", encoding="utf-8") as f:
    f.write("--- Verifying Comment Retrieval for 'Reposición sede social numero 14, Cholchol' ---\n")

    # 1. Get Project ID
    projects = data.get_projects()
    target_proj = projects[projects['name'].str.contains("Reposición sede social numero 14", case=False, na=False)]

    if target_proj.empty:
        f.write("❌ ERROR: Target project not found.\n")
    else:
        project_id = target_proj.iloc[0]['id']
        f.write(f"✅ Project Found: ID {project_id} - {target_proj.iloc[0]['name']}\n")

        # 2. Get Comments (Informal Bitácora)
        comments = data.get_comments(project_id)
        
        if comments.empty:
            f.write("❌ ERROR: No comments found for this project.\n")
        else:
            f.write(f"✅ Comments Found: {len(comments)}\n")
            found_specific = False
            for _, c in comments.iterrows():
                f.write(f"   - [{c['timestamp']}] {c['username']}: {c['content'][:50]}...\n")
                if "ES NECESARIO COMENZAR" in c['content']:
                    found_specific = True
            
            if found_specific:
                f.write("\n✅ SUCCESS: The specific comment reported by the user was found.\n")
                f.write("   Visual Fix: These comments will now appear in the 'Calidad' view expander.\n")
            else:
                f.write("\n⚠️ WARNING: Comments found, but the specific text was not matched.\n")

    f.write("\n--- Verifying Formal Logs (Legacy/Strict) ---\n")
    # 3. Get Formal Logs
    logs = data.get_quality_logs(project_id)
    if logs.empty:
        f.write("ℹ️  Info: No formal quality logs found (as expected per user report).\n")
    else:
        f.write(f"ℹ️  Info: {len(logs)} formal logs found.\n")

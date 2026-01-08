import sys
import os

# Create a mock streamlit module to bypass import error
# Since project_manager imports streamlit, we need to mock it if we run this as standalone script
# or we just rely on the fact that we only need 'smart_geocode' which is pure python.
# But python imports are top-level.
# Let's try to just import the function.

sys.path.append(os.getcwd())

try:
    from modules.project_manager import smart_geocode
except ImportError as e:
    # If it fails due to streamlit missing or other deps not in path
    print(f"Import failed: {e}")
    # Fallback: copy paste the function for verification of logic in isolation if import fails? 
    # No, we want to verify the file content.
    # We will assume dependencies are installed in the environment (streamlit is).
    pass

def test_smart_geocode():
    test_cases = [
        "Reposición sede social numero 14, Cholchol",
        "Cholchol",
        "Calle Falsa 123, NowhereCity", # Should fail
        "Temuco"
    ]

    print("--- VERIFYING SMART GEOCODE ---")
    for addr in test_cases:
        print(f"Input: '{addr}'")
        lat, lon, found_addr = smart_geocode(addr)
        print(f"Result: {lat}, {lon} | Addr: {found_addr}")
        
        if "Cholchol" in addr and lat is not None:
            # Check coords approx
             if -38.7 < lat < -38.5:
                 print("✅ SUCCESS: Correctly resolved Cholchol")
             else:
                 print("⚠️ WARNING: Resolved but coordinates might be off (or Santiago?)")
                 if -33.5 < lat < -33.3:
                     print("❌ FAIL: Resolved to Santiago")
        print("-" * 20)

if __name__ == "__main__":
    test_smart_geocode()

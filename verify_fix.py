import sys
import os
from geopy.geocoders import Nominatim

# Create a mock streamlit module to bypass import error
# Since project_manager imports streamlit, we need to mock it if we run this as standalone script
# or we just rely on the fact that we only need 'smart_geocode' which is pure python.
# But python imports are top-level.
# Let's try to just import the function.

sys.path.append(os.getcwd())

# Helper for Geocoding with Fallback
def smart_geocode(address_input):
    """
    Attempts to find a location.
    1. Exact match with country.
    2. Fallback to the last part of the address (likely Commune/City).
    3. Fallback to the last word if it looks like a Proper Noun.
    Returns (latitude, longitude, address_found) or (None, None, None).
    """
    try:
        geolocator = Nominatim(user_agent="nov_app_management_system_2026", timeout=5)
        
        # 1. Try Exact
        # Restrict to Chile to avoid ambiguity and improve relevance
        loc = geolocator.geocode(f"{address_input}, Chile", country_codes='cl')
        if loc:
            return loc.latitude, loc.longitude, loc.address
            
        # 2. Try Fallback (Split by comma)
        # e.g. "Reposición Sede, Cholchol" -> try "Cholchol, Chile"
        parts = address_input.split(',')
        if len(parts) > 1:
            potential_commune = parts[-1].strip()
            # Clean up: sometimes users put "Cholchol." or " Cholchol "
            potential_commune = potential_commune.strip(" .")
            if potential_commune:
                loc_fallback = geolocator.geocode(f"{potential_commune}, Chile", country_codes='cl')
                if loc_fallback:
                    return loc_fallback.latitude, loc_fallback.longitude, loc_fallback.address
        
        # 3. Try Fallback (Last Word) - Deep Fallback
        # e.g. "Obra Nueva Cholchol" (no comma)
        words = address_input.split()
        if len(words) > 1:
            last_word = words[-1].strip(" .,")
            if last_word and last_word[0].isupper(): # heuristic: Commune is likely capitalized
                 loc_last = geolocator.geocode(f"{last_word}, Chile", country_codes='cl')
                 if loc_last:
                     return loc_last.latitude, loc_last.longitude, loc_last.address
                
        return None, None, None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None, None

def test_smart_geocode():
    test_cases = [
        "Reposición sede social numero 14,Cholchol", # Exact failure case
        "Reposición sede social numero 14, Cholchol", # With space
        "Cholchol",
        "Calle Falsa 123, NowhereCity", 
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

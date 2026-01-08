import sys
import os
from geopy.geocoders import Nominatim

# Helper for Geocoding with Fallback
def smart_geocode(address_input):
    geolocator = Nominatim(user_agent="nov_app_management_system_2026", timeout=5)
    
    print(f"\n[DEBUG] Input: '{address_input}'")
    
    # 1. Exact
    print(f"  [DEBUG] Step 1: Trying exact: '{address_input}, Chile'")
    try:
        loc = geolocator.geocode(f"{address_input}, Chile", country_codes='cl')
        if loc:
            print(f"    -> MATCH: {loc.address}")
            return loc.latitude, loc.longitude, loc.address
        else:
            print("    -> No match.")
    except Exception as e:
        print(f"    -> Error: {e}")

    # 2. Comma Fallback
    parts = address_input.split(',')
    print(f"  [DEBUG] Step 2: Split by comma: {parts}")
    if len(parts) > 1:
        potential = parts[-1].strip(" .")
        print(f"    -> Potential Candidate: '{potential}'")
        if potential:
            print(f"    -> Trying: '{potential}, Chile'")
            try:
                # Try plain
                loc = geolocator.geocode(f"{potential}, Chile", country_codes='cl')
                if loc:
                    print(f"    -> MATCH: {loc.address}")
                    return loc.latitude, loc.longitude, loc.address
                
                # Try 'Comuna de'
                print(f"    -> Trying: 'Comuna de {potential}, Chile'")
                loc = geolocator.geocode(f"Comuna de {potential}, Chile", country_codes='cl')
                if loc:
                    print(f"    -> PREFECTURE MATCH: {loc.address}")
                    return loc.latitude, loc.longitude, loc.address
            except Exception as e:
                print(f"    -> Error: {e}")

    # 3. Last Word Fallback
    words = address_input.split()
    print(f"  [DEBUG] Step 3: Split by space: {words}")
    if len(words) > 1:
        last = words[-1].strip(" .,")
        print(f"    -> Last Word Candidate: '{last}'")
        if last and last[0].isupper():
            print(f"    -> Trying: '{last}, Chile'")
            try:
                loc = geolocator.geocode(f"{last}, Chile", country_codes='cl')
                if loc:
                     print(f"    -> MATCH: {loc.address}")
                     return loc.latitude, loc.longitude, loc.address
            except Exception as e:
                 print(f"    -> Error: {e}")

    print("  [DEBUG] FAILED ALL STEPS")
    return None, None, None

def test_smart_geocode():
    test_cases = [
        "Av.Lastarria 099,  Cholchol",
        "Cholchol"
    ]
    
    for case in test_cases:
        smart_geocode(case)

if __name__ == "__main__":
    test_smart_geocode()

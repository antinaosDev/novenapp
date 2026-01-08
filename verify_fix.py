import sys
import os
from geopy.geocoders import Nominatim

# Helper for Geocoding with Fallback
import random
import time
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

KNOWN_LOCATIONS = {
    "cholchol": (-38.6000, -72.8500, "Cholchol, Araucanía, Chile (Ubicación Aproximada)"),
    "temuco": (-38.7359, -72.5904, "Temuco, Araucanía, Chile"),
    "padre las casas": (-38.7667, -72.6000, "Padre Las Casas, Araucanía, Chile"),
    "nueva imperial": (-38.7417, -72.9500, "Nueva Imperial, Araucanía, Chile"),
    "carahue": (-38.7000, -73.1667, "Carahue, Araucanía, Chile"),
    "lautaro": (-38.5167, -72.4500, "Lautaro, Araucanía, Chile"),
    "labranza": (-38.763, -72.713, "Labranza, Araucanía, Chile"),
    "santiago": (-33.4489, -70.6693, "Santiago, Chile"),
}

def smart_geocode(address_input):
    """
    Attempts to find a location with robust error handling, retries, and static fallback.
    Returns (latitude, longitude, address_found_or_error_msg).
    """
    # Dynamic User Agent to avoid blocking
    ua = f"nov_app_system_{int(time.time())}_{random.randint(1000,9999)}"
    
    print(f"\n[DEBUG] Input: '{address_input}' (UA: {ua})")
    
    def try_geocode(query):
        """Internal helper with retry logic"""
        retries = 3
        for i in range(retries):
            try:
                print(f"    -> Querying: '{query}' (Attempt {i+1})")
                geolocator = Nominatim(user_agent=ua, timeout=10)
                return geolocator.geocode(query, country_codes='cl')
            except (GeocoderTimedOut, GeocoderUnavailable) as e:
                print(f"    -> Warning: Retryable error {e}")
                if i < retries - 1:
                    time.sleep(1 + i) # Backoff
                    continue
            except Exception as e:
                print(f"    -> Error: {e}")
                return None
        return None

    # Helper to check static map
    def check_static(query):
        q_norm = query.lower().strip()
        print(f"    -> Checking Static Cache for: '{q_norm}'")
        for k, v in KNOWN_LOCATIONS.items():
            if k in q_norm:
                return v
        return None

    try:
        # 1. API - Try Exact
        loc = try_geocode(f"{address_input}, Chile")
        if loc:
            print(f"    -> MATCH (Exact): {loc.address}")
            return loc.latitude, loc.longitude, loc.address
            
        # 2. API - Try Fallback (Split by comma)
        parts = address_input.split(',')
        potential_commune = ""
        if len(parts) > 1:
            potential_commune = parts[-1].strip(" .")
            if potential_commune:
                # Try plain
                loc_fallback = try_geocode(f"{potential_commune}, Chile")
                if loc_fallback:
                    print(f"    -> MATCH (Comma Fallback): {loc_fallback.address}")
                    return loc_fallback.latitude, loc_fallback.longitude, loc_fallback.address
                
                # Try 'Comuna de'
                loc_comuna = try_geocode(f"Comuna de {potential_commune}, Chile")
                if loc_comuna:
                    print(f"    -> MATCH (Comuna de): {loc_comuna.address}")
                    return loc_comuna.latitude, loc_comuna.longitude, loc_comuna.address
        
        # 3. API - Try Fallback (Last Word)
        words = address_input.split()
        if len(words) > 1:
            last_word = words[-1].strip(" .,")
            if last_word and last_word[0].isupper():
                 print(f"    -> Trying Last Word Fallback: {last_word}")
                 loc_last = try_geocode(f"{last_word}, Chile")
                 if loc_last:
                     print(f"    -> MATCH (Last Word): {loc_last.address}")
                     return loc_last.latitude, loc_last.longitude, loc_last.address
        
        # 4. STATIC FALLBACK
        print("    -> [API Failed] Trying Static Fallback...")
        if potential_commune:
            static_match = check_static(potential_commune)
            if static_match:
                print(f"    -> STATIC MATCH (Comma): {static_match[2]}")
                return static_match
        
        static_match_full = check_static(address_input)
        if static_match_full:
             print(f"    -> STATIC MATCH (Full Input): {static_match_full[2]}")
             return static_match_full

        print("    -> FAILED ALL STEPS")
        return None, None, f"No se encontró satelitalmente: '{address_input}'."
    except Exception as e:
        print(f"    -> CRITICAL ERROR: {e}")
        # Even on critical error, try static mapping
        static_res = check_static(address_input)
        if static_res:
            print(f"    -> STATIC MATCH (Exception Fallback): {static_res[2]}")
            return static_res

        return None, None, f"Error del servicio de mapas: {e}"

def test_smart_geocode():
    test_cases = [
        "Av.Lastarria 099,  Cholchol",
        "Cholchol"
    ]
    
    for case in test_cases:
        smart_geocode(case)

if __name__ == "__main__":
    test_smart_geocode()

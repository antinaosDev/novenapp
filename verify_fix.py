import sys
import os
from geopy.geocoders import Nominatim

# Helper for Geocoding with Fallback
import random
import time
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

def smart_geocode(address_input):
    """
    Attempts to find a location with robust error handling and retries.
    1. Exact match with country.
    2. Fallback to the last part of the address.
    3. Fallback to 'Comuna de X'.
    4. Fallback to the last word if it looks like a Proper Noun.
    
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
                    time.sleep(2 * (i + 1)) # Backoff
                    continue
            except Exception as e:
                print(f"    -> Error: {e}")
                return None
        return None

    try:
        # 1. Try Exact
        loc = try_geocode(f"{address_input}, Chile")
        if loc:
            print(f"    -> MATCH (Exact): {loc.address}")
            return loc.latitude, loc.longitude, loc.address
            
        # 2. Try Fallback (Split by comma)
        parts = address_input.split(',')
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
        
        # 3. Try Fallback (Last Word)
        words = address_input.split()
        if len(words) > 1:
            last_word = words[-1].strip(" .,")
            if last_word and last_word[0].isupper():
                 print(f"    -> Trying Last Word Fallback: {last_word}")
                 loc_last = try_geocode(f"{last_word}, Chile")
                 if loc_last:
                     print(f"    -> MATCH (Last Word): {loc_last.address}")
                     return loc_last.latitude, loc_last.longitude, loc_last.address
                
        print("    -> FAILED ALL STEPS")
        return None, None, f"No se encontró satelitalmente: '{address_input}'."
    except Exception as e:
        print(f"    -> CRITICAL ERROR: {e}")
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

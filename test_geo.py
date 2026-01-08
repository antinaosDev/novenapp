from geopy.geocoders import Nominatim
import time

def test_geocoding(address):
    print(f"Testing: '{address}'")
    try:
        geolocator = Nominatim(user_agent="nov_app_management_system_test_2026", timeout=5)
        # Verify what happens with the exact string the user likely used
        loc = geolocator.geocode(f"{address}, Chile")
        if loc:
            print(f"FOUND: {loc.address}")
            print(f"COORDS: {loc.latitude}, {loc.longitude}")
            
            # Check if it is Santiago
            if -33.5 < loc.latitude < -33.3 and -70.8 < loc.longitude < -70.5:
                print("-> RESOLVED TO SANTIAGO")
            else:
                print("-> RESOLVED TO OTHER")
        else:
            print("NOT FOUND")
            
    except Exception as e:
        print(f"ERROR: {e}")
    print("-" * 30)

# Cases
test_geocoding("Reposición sede social numero 14, Cholchol") # User case
test_geocoding("Cholchol") # Fallback target
test_geocoding("Temuco") # Control
test_geocoding("Calle Falsa 123, Santiago") # Control
test_geocoding("Construcción Plaza, Arica") # Possible similar case

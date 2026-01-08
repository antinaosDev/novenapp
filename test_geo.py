from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="nov_app_management_system_test_debug", timeout=10)

queries = [
    "Reposición sede social numero 14, Cholchol, Chile",
    "Cholchol, Chile",
    "Sede Social, Cholchol, Chile",
    "Calle Principal, Cholchol, Chile"
]

print(f"{'Query':<50} | {'Address Found':<50} | {'Lat/Lon'}")
print("-" * 120)

for q in queries:
    try:
        loc = geolocator.geocode(q)
        if loc:
            print(f"{q:<50} | {loc.address[:50]:<50} | {loc.latitude:.4f}, {loc.longitude:.4f}")
        else:
            print(f"{q:<50} | {'Not Found':<50} | -")
    except Exception as e:
        print(f"{q:<50} | Error: {e}")

import os

def check_for_null_bytes(directory):
    # Only check root and modules
    targets = ['.', 'modules']
    
    for target in targets:
        if not os.path.exists(target): continue
        
        print(f"Scanning {target}...")
        for file in os.listdir(target):
            if file.endswith(".py") or file.endswith(".css"):
                filepath = os.path.join(target, file)
                if os.path.isdir(filepath): continue
                
                try:
                    with open(filepath, "rb") as f:
                        content = f.read()
                        if b'\x00' in content:
                            print(f"FAIL: {filepath} contains null bytes!")
                        else:
                            print(f"OK: {filepath}")
                except Exception as e:
                    print(f"ERROR reading {filepath}: {e}")

if __name__ == "__main__":
    check_for_null_bytes(".")

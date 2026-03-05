import os
import winreg

def get_path():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ) as key:
        return winreg.QueryValueEx(key, "PATH")[0]

def set_path(new_path):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)

def clean_path(path_str):
    # Split and deduplicate while preserving order
    parts = path_str.split(';')
    seen = set()
    unique_parts = []
    for p in parts:
        p = p.strip()
        if not p: continue
        if p.lower() not in seen:
            seen.add(p.lower())
            unique_parts.append(p)
    return ';'.join(unique_parts)

try:
    current_path = get_path()
    print(f"Current length: {len(current_path)}")
    
    # Deduplicate
    new_path = clean_path(current_path)
    
    # Ensure Tenrix is there
    tenrix_path = os.path.expandvars(r"%LOCALAPPDATA%\Tenrix")
    if tenrix_path.lower() not in new_path.lower():
        new_path += f";{tenrix_path}"
    
    print(f"New length: {len(new_path)}")
    print(f"Result: {new_path}")
    
    set_path(new_path)
    print("\nSUCCESS: PATH has been deduplicated and Tenrix added.")
    print("Please RESTART your terminal/PowerShell now.")
except Exception as e:
    print(f"Error: {e}")

import os
import sys
import shutil
import subprocess
from pathlib import Path

def main():
    project_root = Path(__file__).parent.resolve()
    # 1. Pastikan script installer ada
    installer_script = project_root / "tenrix_web_installer.py"
    if not installer_script.exists():
        print(f"[ERROR] {installer_script} tidak ditemukan!")
        sys.exit(1)

    print("=" * 60)
    print("  BUILDING TENRIX WEB INSTALLER (Output: .exe kecil)")
    print("=" * 60)

    # 2. Build dengan Nuitka (Minimalis)
    # Ini supaya file .exe-nya kecil (hanya 5MB-10MB).
    # Kita TIDAK include Pandas/Scipy/dll karena hanya butuh 'urllib' (standar).
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",                    # Benar-benar satu file .exe tunggal saja
        "--output-dir=dist_installer",
        "--remove-output",
        
        # Windows specifics
        "--windows-uac-admin",         # Butuh permission untuk edit Registry PATH
        "--windows-console-mode=attach",# Agar tetap jalan di terminal
        
        # Optimasi agar exe kecil
        "--noinclude-numba-mode=nofollow",
        "--enable-plugin=anti-bloat",
        
        # Jangan follow dependensi Tenrix utama, hanya script ini saja
        "--nofollow-imports", 
        
        # Beri icon kalau ada
        # "--windows-icon-from-ico=assets/logo.ico",
        
        str(installer_script)
    ]

    print("\n  Executing Nuitka build for installer...")
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print(" [V] BUILD INSTALLER SELESAI!")
        print(f" [V] Lokasi: dist_installer/tenrix_web_installer.exe")
        print("=" * 60)
    except subprocess.CalledProcessError as e:
        print(f"\n [X] Build gagal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

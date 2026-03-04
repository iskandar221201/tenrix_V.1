import os
import sys
import shutil
import zipfile
import subprocess
import urllib.request
from pathlib import Path

# --- CONFIGURATION (Sesuaikan URL download Anda) ---
# Ganti URL ini dengan URL file .zip hasil build Tenrix Anda (misal: GitHub Release)
TENRIX_ZIP_URL = "https://github.com/USER/tenrix/releases/latest/download/tenrix_windows.zip"
INSTALL_DIR = Path.home() / "AppData" / "Local" / "Tenrix"
# ---------------------------------------------------

def set_windows_path(path_to_add: Path):
    """Menambahkan folder bin ke Windows PATH user secara permanen."""
    try:
        import winreg
        
        path_str = str(path_to_add.resolve())
        
        # Buka registry Key Environment User
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS)
        try:
            current_path, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current_path = ""
            
        if path_str not in current_path:
            new_path = f"{current_path};{path_str}" if current_path else path_str
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            
            # Broadcast perubahan ke sistem agar langsung aktif di terminal baru
            import ctypes
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment")
            return True
    except Exception as e:
        print(f" [!] Gagal mendaftarkan PATH secara otomatis: {e}")
    return False

def main():
    print("=" * 60)
    print("  TENRIX WEB INSTALLER (Bootstrap)")
    print("=" * 60)
    
    # 1. Persiapkan folder instalasi
    if INSTALL_DIR.exists():
        print(f" [*] Folder instalasi sudah ada, akan diperbarui: {INSTALL_DIR}")
        # shutil.rmtree(INSTALL_DIR) # Opsional: hapus dulu jika ingin clean install
    else:
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        print(f" [+] Membuat folder instalasi: {INSTALL_DIR}")

    zip_path = INSTALL_DIR / "temp_tenrix.zip"

    # 2. Download Tenrix .zip
    print(f" [*] Mendownload Tenrix dari: {TENRIX_ZIP_URL}")
    print("     (Mohon tunggu, ukuran file cukup besar...)")
    
    try:
        def report_progress(block_num, block_size, total_size):
            read_so_far = block_num * block_size
            if total_size > 0:
                percent = read_so_far * 100 / total_size
                s = f"\r     Progress: {percent:5.1f}% [{read_so_far // 1024}/{total_size // 1024} KB]"
                sys.stdout.write(s)
                sys.stdout.flush()

        urllib.request.urlretrieve(TENRIX_ZIP_URL, zip_path, reporthook=report_progress)
        print("\n [V] Download selesai.")
    except Exception as e:
        print(f"\n [X] Gagal mendownload: {e}")
        sys.exit(1)

    # 3. Ekstrak file
    print(f" [*] Mengekstrak file ke: {INSTALL_DIR}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(INSTALL_DIR)
        print(" [V] Ekstraksi berhasil.")
        zip_path.unlink() # Hapus temp zip
    except Exception as e:
        print(f" [X] Gagal mengekstrak: {e}")
        sys.exit(1)

    # 4. Daftarkan ke PATH (agar user bisa panggil 'tenrix' di mana saja)
    # Kita asumsikan biner hasil build ada di folder 'main.dist' atau root extract
    # Sesuaikan dengan struktur folder di dalam .zip Anda
    bin_dir = INSTALL_DIR / "main.dist" 
    if not bin_dir.exists():
        bin_dir = INSTALL_DIR # Jika .zip tidak punya folder 'main.dist'

    print(" [*] Mendaftarkan Tenrix ke sistem PATH...")
    if set_windows_path(bin_dir):
        print(" [V] Tenrix berhasil didaftarkan ke PATH.")
        print("     Silakan BUKA TERMINAL BARU dan ketik 'tenrix' (atau 'tenrix.exe').")
    else:
        print(" [!] Mohon tambahkan folder berikut ke PATH secara manual:")
        print(f"     {bin_dir}")

    print("\n" + "=" * 60)
    print("  INSTALASI SELESAI!")
    print("=" * 60)
    input("\nTekan ENTER untuk keluar...")

if __name__ == "__main__":
    main()

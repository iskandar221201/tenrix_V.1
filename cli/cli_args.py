"""
cli/cli_args.py
===============
Handle CLI arguments untuk Tenrix.
Dipanggil di awal main.py sebelum logic utama.

Usage:
  tenrix -v              → tampilkan versi
  tenrix --version       → sama
  tenrix -h              → tampilkan help
  tenrix --help          → sama
  tenrix run             → jalankan interactive mode (tanpa file)
  tenrix run data.csv    → jalankan dengan file langsung
  tenrix data.csv        → shortcut, sama seperti run data.csv
  tenrix --update        → update Tenrix ke versi terbaru dari GitHub
"""

from __future__ import annotations
import sys

TENRIX_VERSION = "1.0.0"

HELP_TEXT = """
Tenrix — AI-Powered Data Analysis CLI
======================================

Usage:
  tenrix [command] [file]

Commands:
  run [file]     Analyze a data file
                 Supported: .csv .tsv .xlsx .xls .db .sqlite .sql
  --update       Update Tenrix to the latest version from GitHub
  -v, --version  Show Tenrix version
  -h, --help     Show this help message

Examples:
  tenrix run sales.csv
  tenrix run database.db
  tenrix run report.xlsx
  tenrix sales.csv          (shortcut for 'run')
  tenrix --update           (pull latest version)

Source : https://github.com/iskandar221201/tenrix_V.1
Issues : https://github.com/iskandar221201/tenrix_V.1/issues
"""


def parse_args() -> dict:
    """
    Parse sys.argv dan return dict berisi:
      {
        "command":   "run" | "version" | "help" | None,
        "file":      str | None,
      }
    """
    argv = sys.argv[1:]   # skip script name

    if not argv:
        return {"command": "run", "file": None}

    first = argv[0].lower()

    # Version
    if first in ("-v", "--version"):
        return {"command": "version", "file": None}

    # Help
    if first in ("-h", "--help"):
        return {"command": "help", "file": None}

    # Update
    if first == "--update":
        return {"command": "update", "file": None}

    # run [file]
    if first == "run":
        file_path = argv[1] if len(argv) > 1 else None
        return {"command": "run", "file": file_path}

    # Shortcut: tenrix data.csv (tanpa 'run')
    if first.endswith((".csv", ".tsv", ".xlsx", ".xls",
                        ".db", ".sqlite", ".sqlite3", ".sql")):
        return {"command": "run", "file": argv[0]}

    # Unknown command
    return {"command": "unknown", "file": None, "raw": argv[0]}


def handle_meta_commands(args: dict) -> None:
    """
    Handle -v dan -h langsung, lalu exit.
    Kalau command adalah 'run', tidak melakukan apa-apa (lanjut ke main logic).
    """
    cmd = args.get("command")

    if cmd == "version":
        print(f"Tenrix v{TENRIX_VERSION}")
        sys.exit(0)

    if cmd == "help":
        print(HELP_TEXT)
        sys.exit(0)

    if cmd == "update":
        _run_update()
        sys.exit(0)

    if cmd == "unknown":
        raw = args.get("raw", "")
        print(f"Unknown command: '{raw}'")
        print("Run 'tenrix -h' for usage information.")
        sys.exit(1)


def _run_update() -> None:
    """
    Update Tenrix ke versi terbaru via git pull.
    Dipanggil saat user ketik: tenrix --update
    """
    import subprocess
    from pathlib import Path
    import os

    # LocalAppData path is the standard install location on Windows
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        install_dir = Path(local_app_data) / "Tenrix"
    else:
        install_dir = Path.home() / "AppData" / "Local" / "Tenrix"

    # Fallback: cari dari lokasi script ini (untuk dev mode)
    if not install_dir.exists() or not (install_dir / ".git").exists():
        install_dir = Path(__file__).resolve().parent.parent

    print(f"Tenrix v{TENRIX_VERSION}")
    print(f"Checking for updates...")
    print(f"Location: {install_dir}\n")

    # Cek git tersedia
    import shutil
    if not shutil.which("git"):
        print("ERROR: Git is not installed.")
        print("Install Git from: https://git-scm.com/download/win")
        return

    # Cek ini folder git repo
    if not (install_dir / ".git").exists():
        print("ERROR: Tenrix installation not found or not a git repository.")
        print(f"Expected location: {install_dir}")
        print("Try reinstalling Tenrix.")
        return

    # Ambil versi saat ini (commit hash)
    try:
        before = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=install_dir, capture_output=True, text=True
        ).stdout.strip()
    except Exception:
        before = "unknown"

    # Git pull
    print("Pulling latest version from GitHub...")
    result = subprocess.run(
        ["git", "pull"],
        cwd=install_dir,
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"Update failed:\n{result.stderr}")
        print("\nTry running: git pull manually in the Tenrix folder.")
        return

    # Ambil versi setelah update
    try:
        after = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=install_dir, capture_output=True, text=True
        ).stdout.strip()
    except Exception:
        after = "unknown"

    if before == after:
        print("✓ Tenrix is already up to date.")
    else:
        print(f"✓ Updated successfully! ({before} → {after})")
        print("\nUpdating dependencies...")
        # Use sys.executable to ensure we use the same python interpreter
        pip_result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt",
             "--upgrade", "--quiet"],
            cwd=install_dir
        )
        if pip_result.returncode == 0:
            print("✓ Dependencies updated.")
        else:
            print("⚠ Could not update dependencies automatically.")
            print(f"  Run manually: pip install -r requirements.txt")

    print("\nRestart your terminal to use the latest version.")

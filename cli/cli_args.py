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

import sys
from tui.theme import APP_VERSION

TENRIX_VERSION = APP_VERSION

HELP_TEXT = """
Tenrix — AI-Powered Data Analysis CLI
======================================

Usage:
  tenrix [command] [file]

Commands:
  run [file]              Analyze a data file
                          Supported: .csv .tsv .xlsx .xls .db .sqlite .sql
  save-template [name]    Save current analysis config as a template
  templates               List all saved templates
  --update                Update Tenrix to the latest version from GitHub
  -v, --version           Show Tenrix version
  -h, --help              Show this help message

Options:
  --template [name]       Use a saved template for this analysis
  --template-desc [text]  Description when saving a template

Examples:
  tenrix run sales.csv
  tenrix run database.db --template monthly-sales
  tenrix sales.csv        (shortcut for 'run')
  tenrix save-template my-template
  tenrix templates
  tenrix --update         (pull latest version)

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

    # tenrix save-template [name]
    if first == "save-template":
        name = argv[1] if len(argv) > 1 else None
        desc = ""
        if "--template-desc" in argv:
            idx = argv.index("--template-desc")
            desc = argv[idx + 1] if idx + 1 < len(argv) else ""
        return {
            "command": "save-template",
            "template_name": name,
            "template_desc": desc,
        }

    # tenrix templates [--delete name]
    if first == "templates":
        if "--delete" in argv:
            idx = argv.index("--delete")
            name = argv[idx + 1] if idx + 1 < len(argv) else None
            return {"command": "templates-delete", "template_name": name}
        return {"command": "templates-list"}

    # run [file]
    if first == "run":
        file_path = argv[1] if len(argv) > 1 else None
        template_name = None
        if "--template" in argv:
            idx = argv.index("--template")
            template_name = argv[idx + 1] if idx + 1 < len(argv) else None
        return {"command": "run", "file": file_path, "template_name": template_name}

    # Shortcut: tenrix data.csv (tanpa 'run')
    if first.endswith((".csv", ".tsv", ".xlsx", ".xls",
                        ".db", ".sqlite", ".sqlite3", ".sql")):
        template_name = None
        if "--template" in argv:
            idx = argv.index("--template")
            template_name = argv[idx + 1] if idx + 1 < len(argv) else None
        return {"command": "run", "file": argv[0], "template_name": template_name}

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

    if cmd in ("templates-list", "templates-delete", "save-template"):
        _run_template_commands(args)
        sys.exit(0)

    if cmd == "unknown":
        raw = args.get("raw", "")
        print(f"Unknown command: '{raw}'")
        print("Run 'tenrix -h' for usage information.")
        sys.exit(1)


def _run_template_commands(args: dict) -> None:
    from core.template_manager import TemplateManager
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Prompt, Confirm

    console = Console()
    tm = TemplateManager()
    cmd = args.get("command")

    if cmd == "templates-list":
        templates = tm.list_all()
        if not templates:
            console.print("[dim]Belum ada template tersimpan.[/dim]")
            console.print("Gunakan opsi 'Save Template' di menu TUI sesudah analisis selesai.")
        else:
            tbl = Table(title="Analysis Templates", border_style="cyan")
            tbl.add_column("Nama", style="bold cyan")
            tbl.add_column("Dibuat", style="dim")
            tbl.add_column("Deskripsi")
            tbl.add_column("Kolom", style="dim")
            tbl.add_column("Analisis", style="dim")

            for t in templates:
                cols = ", ".join(t.selected_columns) if t.selected_columns else "semua"
                tbl.add_row(
                    t.name,
                    t.created_at,
                    t.description or "-",
                    cols,
                    str(len(t.analyses)),
                )
            console.print(tbl)
        return

    if cmd == "templates-delete":
        name = args.get("template_name")
        if not name:
            console.print("[red]Nama template diperlukan.[/red]")
            sys.exit(1)

        if not tm.exists(name):
            console.print(f"[red]Template '{name}' tidak ditemukan.[/red]")
            sys.exit(1)

        if Confirm.ask(f"Hapus template '[cyan]{name}[/cyan]'?", default=False):
            tm.delete(name)
            console.print(f"[green]✓ Template '{name}' dihapus.[/green]")
        return
        
    if cmd == "save-template":
        console.print("[yellow]⚠ Command 'save-template' kini dipindahkan ke dalam menu TUI secara langsung.[/yellow]")
        console.print("[dim]Silakan analisis data Anda via 'tenrix run data.csv', setelah selesai keluar menu dan pilih 'Save Template'.[/dim]")
        return


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

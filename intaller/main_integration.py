# ============================================================
# Tambahkan ini di AWAL main.py (sebelum semua logic lain)
# ============================================================

from cli.cli_args import parse_args, handle_meta_commands

# Parse dan handle -v, -h, unknown commands
args = parse_args()
handle_meta_commands(args)   # exit di sini kalau -v atau -h

# Ambil file path dari args
file_path = args.get("file")

# ── Contoh output setelah integrasi ──────────────────────────
#
# $ tenrix -v
# Tenrix v1.0.0
#
# $ tenrix -h
# Tenrix — AI-Powered Data Analysis CLI
# ======================================
# Usage:
#   tenrix [command] [file]
# ...
#
# $ tenrix run
# (masuk ke interactive mode, tanya file ke user)
#
# $ tenrix run sales.csv
# (langsung load sales.csv)
#
# $ tenrix sales.csv
# (shortcut, sama seperti run sales.csv)
#
# ── Lanjutkan dengan logic main.py yang sudah ada ────────────

# Kalau file_path None, tanya ke user (interactive mode)
if file_path is None:
    from rich.prompt import Prompt
    file_path = Prompt.ask("\n[bold blue]Enter file path[/bold blue]")

# ... existing logic: load_source, bias_detection, session, dll ...

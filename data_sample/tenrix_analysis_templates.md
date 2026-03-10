# Tenrix — Analysis Templates Feature

**Versi:** 1.0.0  
**Depends on:** `cli/cli_args.py`, `core/session.py`

---

## Gambaran Umum

Analysis Templates memungkinkan user menyimpan konfigurasi analisis favorit
dan memakainya ulang di data berbeda. Berguna untuk recurring analysis —
misalnya laporan bulanan dengan struktur data yang sama.

```bash
# Simpan konfigurasi analisis sesi ini sebagai template
tenrix save-template monthly-sales

# Pakai template di data bulan depan
tenrix run februari.csv --template monthly-sales

# Lihat semua template yang tersimpan
tenrix templates

# Hapus template
tenrix templates --delete monthly-sales
```

---

## Apa yang Disimpan di Template

Template menyimpan **konfigurasi analisis**, bukan datanya:

```json
{
  "name": "monthly-sales",
  "created_at": "2024-01-15",
  "description": "Analisis bulanan data penjualan Samsung",
  "selected_columns": ["revenue", "product_category", "region", "date"],
  "analyses": ["descriptive_stats", "time_series", "anomaly_detection"],
  "news_mode": null,
  "export_formats": ["pdf", "excel"]
}
```

---

## Lokasi Penyimpanan Template

Template disimpan di OS keychain folder yang sudah dipakai Tenrix,
bukan di folder project — agar tersedia dari direktori manapun:

```
Windows: %APPDATA%\Tenrix\templates\
           C:\Users\nama\AppData\Roaming\Tenrix\templates\
```

Setiap template = satu file JSON dengan nama `{template_name}.json`.

---

## File yang Perlu Dibuat

```
core/
  template_manager.py   ← save, load, list, delete templates
```

## File yang Perlu Diupdate

```
cli/cli_args.py         ← tambah save-template, --template, templates command
main.py                 ← handle save-template dan --template flow
```

---

## 1. `core/template_manager.py`

```python
"""
core/template_manager.py
========================
Manage analysis templates — save, load, list, delete.

Template disimpan sebagai JSON di:
  Windows: %APPDATA%\Tenrix\templates\
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class AnalysisTemplate:
    name: str
    created_at: str
    description: str
    selected_columns: list[str] | None        # None = semua kolom
    analyses: list[str]                        # list analysis_id yang dijalankan
    news_mode: str | None                      # "url", "auto", atau None
    export_formats: list[str]                  # ["pdf", "excel"]
    source_filename: str = ""                  # nama file asli (info saja)
    row_count: int = 0                         # jumlah rows data asli (info saja)


class TemplateManager:

    def __init__(self):
        self.templates_dir = self._get_templates_dir()
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────

    def save(
        self,
        name: str,
        session: "Session",
        description: str = "",
    ) -> AnalysisTemplate:
        """
        Simpan konfigurasi sesi saat ini sebagai template.
        Jika nama sudah ada, timpa (overwrite).
        """
        template = AnalysisTemplate(
            name=name,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            description=description,
            selected_columns=session.selected_columns,
            analyses=list(session.results.keys()),
            news_mode=session.news_result.mode if session.news_result else None,
            export_formats=session.export_formats,
            source_filename=Path(session.source_path).name if session.source_path else "",
            row_count=session.data_profile.row_count if session.data_profile else 0,
        )

        path = self.templates_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(template), f, indent=2, ensure_ascii=False)

        return template

    def load(self, name: str) -> AnalysisTemplate | None:
        """Load template by name. Return None jika tidak ditemukan."""
        path = self.templates_dir / f"{name}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AnalysisTemplate(**data)

    def list_all(self) -> list[AnalysisTemplate]:
        """Return semua template yang tersimpan, diurutkan by name."""
        templates = []
        for path in sorted(self.templates_dir.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                templates.append(AnalysisTemplate(**data))
            except Exception:
                continue  # skip file rusak
        return templates

    def delete(self, name: str) -> bool:
        """Hapus template. Return True jika berhasil, False jika tidak ada."""
        path = self.templates_dir / f"{name}.json"
        if not path.exists():
            return False
        path.unlink()
        return True

    def exists(self, name: str) -> bool:
        return (self.templates_dir / f"{name}.json").exists()

    # ── Private ───────────────────────────────────────────────

    def _get_templates_dir(self) -> Path:
        """Return path folder templates sesuai OS."""
        if os.name == "nt":  # Windows
            base = Path(os.environ.get("APPDATA", Path.home()))
        else:  # macOS / Linux
            base = Path.home() / ".config"
        return base / "Tenrix" / "templates"
```

---

## 2. `cli/cli_args.py` — Tambahan

```python
# Tambahkan ke HELP_TEXT
"""
Commands:
  run [file]              Analyze a data file
  save-template [name]    Save current analysis config as a template
  templates               List all saved templates

Options:
  --template [name]       Use a saved template for this analysis
  --template-desc [text]  Description when saving a template
"""

def parse_args(argv: list[str] | None = None) -> dict:
    import sys
    argv = argv or sys.argv[1:]

    if not argv:
        return {"command": "interactive"}

    command = argv[0]

    # tenrix save-template [name]
    if command == "save-template":
        name = argv[1] if len(argv) > 1 else None
        desc = ""
        if "--template-desc" in argv:
            idx  = argv.index("--template-desc")
            desc = argv[idx + 1] if idx + 1 < len(argv) else ""
        return {
            "command": "save-template",
            "template_name": name,
            "template_desc": desc,
        }

    # tenrix templates [--delete name]
    if command == "templates":
        if "--delete" in argv:
            idx  = argv.index("--delete")
            name = argv[idx + 1] if idx + 1 < len(argv) else None
            return {"command": "templates-delete", "template_name": name}
        return {"command": "templates-list"}

    # tenrix run [file] --template [name]
    if command == "run" or (command.endswith((".csv", ".xlsx", ".db", ".sql"))):
        template_name = None
        if "--template" in argv:
            idx           = argv.index("--template")
            template_name = argv[idx + 1] if idx + 1 < len(argv) else None

        # ... existing parsing untuk --columns, --news, dll ...

        return {
            "command": "run",
            "file": argv[1] if command == "run" else command,
            "template_name": template_name,
            # ... existing keys ...
        }

    # ... existing commands (-v, -h, --update) ...
```

---

## 3. `main.py` — Integrasi

```python
from core.template_manager import TemplateManager
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()
tm = TemplateManager()


# ── Handle `tenrix templates` ─────────────────────────────────
if args["command"] == "templates-list":
    templates = tm.list_all()

    if not templates:
        console.print("[dim]Belum ada template tersimpan.[/dim]")
        console.print("Jalankan analisis lalu ketik: [cyan]tenrix save-template nama[/cyan]")
    else:
        tbl = Table(title="Analysis Templates", border_style="cyan")
        tbl.add_column("Nama",        style="bold cyan")
        tbl.add_column("Dibuat",      style="dim")
        tbl.add_column("Deskripsi")
        tbl.add_column("Kolom",       style="dim")
        tbl.add_column("Analisis",    style="dim")

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
    exit(0)


# ── Handle `tenrix templates --delete` ────────────────────────
if args["command"] == "templates-delete":
    name = args.get("template_name")
    if not name:
        console.print("[red]Nama template diperlukan.[/red]")
        exit(1)

    if not tm.exists(name):
        console.print(f"[red]Template '{name}' tidak ditemukan.[/red]")
        exit(1)

    if Confirm.ask(f"Hapus template '[cyan]{name}[/cyan]'?", default=False):
        tm.delete(name)
        console.print(f"[green]✓ Template '{name}' dihapus.[/green]")
    exit(0)


# ── Handle `tenrix save-template` ─────────────────────────────
if args["command"] == "save-template":
    name = args.get("template_name")

    if not name:
        name = Prompt.ask("Nama template")

    # Validasi nama — hanya huruf, angka, dash, underscore
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        console.print("[red]Nama template hanya boleh huruf, angka, - dan _[/red]")
        exit(1)

    # Cek apakah session ada (harus ada analisis sebelumnya di sesi ini)
    if not session or not session.results:
        console.print(
            "[yellow]⚠ Tidak ada analisis aktif di sesi ini.[/yellow]\n"
            "[dim]Jalankan analisis dulu: tenrix run data.csv[/dim]"
        )
        exit(1)

    # Konfirmasi kalau nama sudah ada
    if tm.exists(name):
        if not Confirm.ask(
            f"Template '[cyan]{name}[/cyan]' sudah ada. Timpa?",
            default=False
        ):
            exit(0)

    desc = args.get("template_desc") or ""
    if not desc:
        desc = Prompt.ask("Deskripsi (opsional, Enter untuk skip)", default="")

    template = tm.save(name=name, session=session, description=desc)

    console.print(f"\n[green]✓ Template '[bold]{name}[/bold]' tersimpan![/green]")
    console.print(f"  [dim]Kolom  : {', '.join(template.selected_columns) if template.selected_columns else 'semua'}[/dim]")
    console.print(f"  [dim]Analisis: {len(template.analyses)} analisis[/dim]")
    console.print(f"\n[dim]Pakai di data lain: tenrix run data.csv --template {name}[/dim]")
    exit(0)


# ── Handle `--template` saat run ──────────────────────────────
template_name = args.get("template_name")
if template_name:
    template = tm.load(template_name)

    if not template:
        console.print(f"[red]Template '{template_name}' tidak ditemukan.[/red]")
        console.print("[dim]Lihat template tersedia: tenrix templates[/dim]")
        exit(1)

    console.print(f"[cyan]→ Menggunakan template: [bold]{template_name}[/bold][/cyan]")
    if template.description:
        console.print(f"  [dim]{template.description}[/dim]")

    # Override args dengan config dari template
    # (hanya jika user tidak eksplisit set di command line)
    if not args.get("selected_columns") and template.selected_columns:
        args["selected_columns"] = template.selected_columns
        console.print(f"  [dim]Kolom: {', '.join(template.selected_columns)}[/dim]")

    if not args.get("news_mode") and template.news_mode:
        args["news_mode"] = template.news_mode

    # Simpan nama template ke session untuk info di report
    session.template_used = template_name

# ... lanjut flow analisis seperti biasa ...
```

---

## Contoh Tampilan Terminal

```
$ tenrix run samsung_sales.csv --columns revenue,region,product_category
[analisis selesai...]

$ tenrix save-template monthly-sales
Deskripsi (opsional, Enter untuk skip): Analisis bulanan penjualan Samsung

✓ Template 'monthly-sales' tersimpan!
  Kolom   : revenue, region, product_category
  Analisis: 6 analisis

Pakai di data lain: tenrix run data.csv --template monthly-sales


$ tenrix templates
┌─────────────────┬──────────────────┬────────────────────────────┬──────────────────────┬──────────┐
│ Nama            │ Dibuat           │ Deskripsi                  │ Kolom                │ Analisis │
├─────────────────┼──────────────────┼────────────────────────────┼──────────────────────┼──────────┤
│ monthly-sales   │ 2024-01-15 09:30 │ Analisis bulanan Samsung   │ revenue, region, ... │ 6        │
│ inventory-check │ 2024-01-10 14:22 │ Cek stok dan perputaran    │ semua                │ 4        │
└─────────────────┴──────────────────┴────────────────────────────┴──────────────────────┴──────────┘


$ tenrix run februari.csv --template monthly-sales
→ Menggunakan template: monthly-sales
  Analisis bulanan penjualan Samsung
  Kolom: revenue, region, product_category

✓ Data loaded: 16.200 rows × 3 columns
[analisis berjalan dengan config dari template...]
```

---

## Urutan Implementasi

1. Buat `core/template_manager.py`
2. Update `cli/cli_args.py` — tambah `save-template`, `templates`, `--template`, `--template-desc`
3. Update `core/session.py` — tambah field `template_used: str | None = None`
4. Update `main.py` — handle semua command dan flag baru

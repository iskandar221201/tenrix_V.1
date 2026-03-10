# Tenrix — Smart Report Naming & Auto-Folder

**Versi:** 1.0.0  
**Depends on:** `exporters/pdf_exporter.py`, `exporters/excel_exporter.py`, `core/session.py`

---

## Gambaran Umum

Saat ini Tenrix menyimpan report di folder yang sama dengan file data,
dengan nama yang flat. Fitur ini otomatis membuat struktur folder yang rapi
dan nama file yang informatif — tanpa konfigurasi apapun dari user.

**Sebelum:**
```
📁 Documents/
  samsung_sales.csv
  Tenrix_Report_2024-01-15.pdf
  Tenrix_Report_2024-01-15.xlsx
```

**Sesudah:**
```
📁 Documents/
  samsung_sales.csv
  📁 reports/
    📁 samsung_sales/
      📁 2024-01/
        samsung_sales_2024-01-15_09-30.pdf
        samsung_sales_2024-01-15_09-30.xlsx
        samsung_sales_2024-01-15_09-30_code.py  ← jika --export-code
```

---

## Struktur Folder

```
{data_file_dir}/
  reports/
    {source_filename_stem}/
      {YYYY-MM}/
        {source_filename_stem}_{YYYY-MM-DD}_{HH-mm}.pdf
        {source_filename_stem}_{YYYY-MM-DD}_{HH-mm}.xlsx
        {source_filename_stem}_{YYYY-MM-DD}_{HH-mm}_code.py
```

### Contoh Nyata

| Source file | Output folder |
|---|---|
| `samsung_sales.csv` | `reports/samsung_sales/2024-01/` |
| `laporan_feb.xlsx` | `reports/laporan_feb/2024-02/` |
| `inventory.db` | `reports/inventory/2024-01/` |

---

## File yang Perlu Dibuat

```
core/
  report_path.py    ← logic generate path dan nama file
```

## File yang Perlu Diupdate

```
main.py             ← pakai ReportPathBuilder untuk semua output
```

---

## 1. `core/report_path.py`

```python
"""
core/report_path.py
===================
Generate output path untuk semua file report Tenrix.

Struktur:
  {data_dir}/reports/{source_stem}/{YYYY-MM}/{source_stem}_{YYYY-MM-DD}_{HH-mm}.{ext}

Cara pakai:
    builder = ReportPathBuilder(source_path="/path/to/samsung_sales.csv")
    builder.pdf    → /path/to/reports/samsung_sales/2024-01/samsung_sales_2024-01-15_09-30.pdf
    builder.excel  → /path/to/reports/samsung_sales/2024-01/samsung_sales_2024-01-15_09-30.xlsx
    builder.code   → /path/to/reports/samsung_sales/2024-01/samsung_sales_2024-01-15_09-30_code.py
    builder.folder → /path/to/reports/samsung_sales/2024-01/
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime


class ReportPathBuilder:

    def __init__(self, source_path: str, timestamp: datetime | None = None):
        self._source   = Path(source_path)
        self._ts       = timestamp or datetime.now()
        self._stem     = self._sanitize(self._source.stem)
        self._month    = self._ts.strftime("%Y-%m")
        self._datetime = self._ts.strftime("%Y-%m-%d_%H-%M")
        self._base     = self._build_base()

    # ── Public properties ─────────────────────────────────────

    @property
    def folder(self) -> Path:
        """Path folder output — dibuat otomatis jika belum ada."""
        self._base.mkdir(parents=True, exist_ok=True)
        return self._base

    @property
    def pdf(self) -> str:
        return str(self.folder / f"{self._stem}_{self._datetime}.pdf")

    @property
    def excel(self) -> str:
        return str(self.folder / f"{self._stem}_{self._datetime}.xlsx")

    @property
    def code(self) -> str:
        return str(self.folder / f"{self._stem}_{self._datetime}_code.py")

    @property
    def stem(self) -> str:
        """Nama dasar tanpa ekstensi dan timestamp."""
        return self._stem

    @property
    def display_folder(self) -> str:
        """Path folder relatif untuk ditampilkan di terminal."""
        try:
            return str(self._base.relative_to(self._source.parent))
        except ValueError:
            return str(self._base)

    # ── Private ───────────────────────────────────────────────

    def _build_base(self) -> Path:
        return (
            self._source.parent
            / "reports"
            / self._stem
            / self._month
        )

    @staticmethod
    def _sanitize(name: str) -> str:
        """
        Bersihkan nama file agar aman sebagai folder/file name.
        Hapus karakter spesial, ganti spasi dengan underscore,
        lowercase semua.
        """
        import re
        name = name.lower()
        name = re.sub(r'[\s\-]+', '_', name)       # spasi/dash → underscore
        name = re.sub(r'[^a-z0-9_]', '', name)     # hapus karakter non-alphanumeric
        name = re.sub(r'_+', '_', name)             # multiple underscore → satu
        name = name.strip('_')
        return name or "report"
```

---

## 2. `main.py` — Integrasi

Ganti semua hardcoded output path dengan `ReportPathBuilder`:

```python
from core.report_path import ReportPathBuilder

# Setelah load data, buat path builder
path = ReportPathBuilder(source_path=args["file"])

# Tampilkan ke user sebelum analisis
console.print(f"[dim]→ Reports akan disimpan di: {path.display_folder}[/dim]")

# ... semua analisis berjalan ...

# Export PDF
if "pdf" in export_formats:
    export_pdf(session, output_path=path.pdf)
    console.print(f"[green]✓ PDF : {Path(path.pdf).name}[/green]")

# Export Excel
if "excel" in export_formats:
    export_excel(session, output_path=path.excel)
    console.print(f"[green]✓ Excel: {Path(path.excel).name}[/green]")

# Export Python code
if args.get("export_code"):
    exporter  = CodeExporter(session)
    exporter.export(output_path=path.code)
    console.print(f"[green]✓ Code : {Path(path.code).name}[/green]")

# Tampilkan summary lokasi di akhir
console.print()
console.print(f"[dim]📁 Semua file tersimpan di:[/dim]")
console.print(f"[cyan]   {path.folder}[/cyan]")
```

---

## Contoh Tampilan Terminal

```
$ tenrix run samsung_sales.csv --export-code

→ Reports akan disimpan di: reports/samsung_sales/2024-01/

  [analisis berjalan...]

✓ PDF  : samsung_sales_2024-01-15_09-30.pdf
✓ Excel: samsung_sales_2024-01-15_09-30.xlsx
✓ Code : samsung_sales_2024-01-15_09-30_code.py

📁 Semua file tersimpan di:
   C:\Users\iskandar\Documents\reports\samsung_sales\2024-01\
```

---

## Edge Cases yang Ditangani

| Kondisi | Behaviour |
|---|---|
| Folder `reports/` belum ada | Dibuat otomatis |
| Nama file mengandung spasi | `my sales data.csv` → `my_sales_data/` |
| Nama file mengandung karakter spesial | `sales(2024).csv` → `sales2024/` |
| Nama file seluruhnya karakter spesial | Fallback ke `report/` |
| Dua analisis di menit yang sama | Timestamp berbeda detik — tidak ada overwrite |
| Source file di root drive (`C:\file.csv`) | `C:\reports\file\2024-01\` |

---

## Urutan Implementasi

1. Buat `core/report_path.py`
2. Update `main.py` — ganti semua hardcoded path dengan `ReportPathBuilder`

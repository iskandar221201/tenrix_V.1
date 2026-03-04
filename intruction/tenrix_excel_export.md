# Tenrix — Fix: Excel Export (exporters/excel_exporter.py)

## Overview

Tenrix sekarang bisa export hasil analisis ke dua format sekaligus:
- `report.pdf`   — untuk presentasi dan sharing (existing)
- `report.xlsx`  — untuk analisis lanjutan di Excel (baru)

Excel export jauh lebih simpel dari PDF.
Dependency tambahan hanya `openpyxl` yang sudah ada di requirements.txt.

---

## 1. Buat file baru: `exporters/excel_exporter.py`

```python
"""
exporters/excel_exporter.py
===========================
Export hasil analisis Tenrix ke file Excel (.xlsx).

Struktur output:
  Sheet 1: README       — ringkasan sesi, metadata, AI interpretation gabungan
  Sheet 2: Data Profile — stats profil dataset (rows, cols, missing, dll)
  Sheet 3+: per analisis — satu sheet per analisis yang dijalankan

Setiap sheet analisis berisi:
  - Summary table (metrics dari analisis)
  - Data table (hasil detail, kalau ada)
  - AI Interpretation (sebagai teks di bawah tabel)

Dependency: openpyxl (sudah ada di requirements.txt)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import (
    Alignment, Border, Font, PatternFill, Side
)
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows

from core.data_loader import DataProfile
from core.result import AnalysisResult


# ── Warna tema ────────────────────────────────────────────────────────────────
BLUE_DARK   = "1E3A5F"   # header utama
BLUE_MID    = "2563EB"   # header sekunder
BLUE_LIGHT  = "EFF6FF"   # row highlight
GRAY_LIGHT  = "F8FAFC"   # alternating row
WHITE       = "FFFFFF"
GREEN       = "10B981"
ORANGE      = "D97706"
TEXT_DARK   = "0F172A"
TEXT_GRAY   = "64748B"


# ── Entry point ───────────────────────────────────────────────────────────────

def export_excel(
    results:    list[AnalysisResult],
    profile:    DataProfile,
    file_path:  str,
    source_file: str = "",
) -> str:
    """
    Export semua hasil analisis ke .xlsx.
    Return path file yang dibuat.

    Dipanggil dari main.py setelah semua analisis selesai:
        excel_path = export_excel(results, profile, "output/report.xlsx", args.file)
    """
    wb = Workbook()

    # Hapus sheet default
    wb.remove(wb.active)

    # Sheet 1: README
    _write_readme_sheet(wb, results, profile, source_file)

    # Sheet 2: Data Profile
    _write_profile_sheet(wb, profile)

    # Sheet 3+: satu per analisis
    for i, result in enumerate(results, 1):
        if result.success:
            _write_analysis_sheet(wb, result, index=i)

    # Simpan
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(path))

    return str(path)


# ── Sheet: README ─────────────────────────────────────────────────────────────

def _write_readme_sheet(
    wb:          Workbook,
    results:     list[AnalysisResult],
    profile:     DataProfile,
    source_file: str,
) -> None:
    ws = wb.create_sheet("README", 0)
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 52

    # Judul
    ws.merge_cells("A1:B1")
    cell = ws["A1"]
    cell.value          = "TENRIX — Data Analysis Report"
    cell.font           = Font(name="Calibri", bold=True, size=16, color=WHITE)
    cell.fill           = PatternFill("solid", fgColor=BLUE_DARK)
    cell.alignment      = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # Metadata
    meta = [
        ("File",       Path(source_file).name if source_file else "—"),
        ("Date",       datetime.now().strftime("%Y-%m-%d %H:%M")),
        ("Rows",       f"{profile.row_count:,}"),
        ("Columns",    str(len(profile.columns))),
        ("Analyses",   str(sum(1 for r in results if r.success))),
        ("Generated",  "Tenrix CLI"),
    ]
    for r_idx, (key, val) in enumerate(meta, 2):
        k_cell        = ws.cell(row=r_idx, column=1, value=key)
        k_cell.font   = Font(bold=True, color=TEXT_DARK)
        k_cell.fill   = PatternFill("solid", fgColor=BLUE_LIGHT)

        v_cell        = ws.cell(row=r_idx, column=2, value=val)
        v_cell.font   = Font(color=TEXT_DARK)

        ws.row_dimensions[r_idx].height = 18

    # Spacer
    spacer_row = len(meta) + 3
    ws.cell(row=spacer_row, column=1, value="Analyses in this report").font = Font(
        bold=True, size=12, color=BLUE_DARK
    )

    # Daftar analisis
    for i, result in enumerate(results, 1):
        row  = spacer_row + i
        icon = "✅" if result.success else "❌"
        ws.cell(row=row, column=1, value=f"{icon} {result.analysis_name}")
        ws.cell(row=row, column=1).font = Font(color=TEXT_DARK)
        ws.cell(row=row, column=2, value=f"→ Sheet: {_safe_sheet_name(result.analysis_name, i)}")
        ws.cell(row=row, column=2).font = Font(color=TEXT_GRAY)

    _apply_thin_border(ws, 1, 1, len(meta) + 1, 2)


# ── Sheet: Data Profile ───────────────────────────────────────────────────────

def _write_profile_sheet(wb: Workbook, profile: DataProfile) -> None:
    ws = wb.create_sheet("Data Profile")
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 20

    _write_section_header(ws, 1, "Data Profile")

    rows = [
        ("Rows",             f"{profile.row_count:,}"),
        ("Columns",          str(len(profile.columns))),
        ("Numeric Columns",  str(len(profile.numeric_columns))),
        ("Categorical Cols", str(len(profile.categorical_columns))),
        ("Date Columns",     str(len(profile.date_columns))),
        ("Missing Values",   f"{profile.missing_count:,}" if hasattr(profile, "missing_count") else "—"),
        ("Duplicate Rows",   f"{profile.duplicate_count:,}" if hasattr(profile, "duplicate_count") else "—"),
    ]

    for i, (key, val) in enumerate(rows, 2):
        ws.cell(row=i, column=1, value=key).font  = Font(bold=True)
        ws.cell(row=i, column=2, value=val).font  = Font(color=TEXT_DARK)
        if i % 2 == 0:
            for col in [1, 2]:
                ws.cell(row=i, column=col).fill = PatternFill("solid", fgColor=GRAY_LIGHT)

    # Daftar kolom
    col_start = len(rows) + 4
    ws.cell(row=col_start, column=1, value="All Columns").font = Font(bold=True, color=BLUE_DARK)

    col_df = pd.DataFrame({
        "Column":   profile.columns,
        "Type":     [
            "numeric"     if c in profile.numeric_columns     else
            "date"        if c in profile.date_columns        else
            "categorical"
            for c in profile.columns
        ],
    })
    _write_dataframe(ws, col_df, start_row=col_start + 1, start_col=1)


# ── Sheet: per analisis ───────────────────────────────────────────────────────

def _write_analysis_sheet(
    wb:     Workbook,
    result: AnalysisResult,
    index:  int,
) -> None:
    sheet_name = _safe_sheet_name(result.analysis_name, index)
    ws         = wb.create_sheet(sheet_name)

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 30

    current_row = 1

    # ── Judul analisis
    current_row = _write_section_header(ws, current_row, result.analysis_name)
    current_row += 1

    # ── Summary table (metrics)
    if result.summary:
        ws.cell(row=current_row, column=1, value="Summary").font = Font(
            bold=True, size=11, color=BLUE_MID
        )
        current_row += 1

        for key, val in result.summary.items():
            ws.cell(row=current_row, column=1, value=str(key)).font  = Font(bold=True)
            ws.cell(row=current_row, column=2, value=str(val))
            if current_row % 2 == 0:
                for col in [1, 2]:
                    ws.cell(row=current_row, column=col).fill = PatternFill(
                        "solid", fgColor=BLUE_LIGHT
                    )
            current_row += 1

        current_row += 1

    # ── Data table (hasil detail)
    data_df = _extract_data_table(result)
    if data_df is not None and not data_df.empty:
        ws.cell(row=current_row, column=1, value="Detail Data").font = Font(
            bold=True, size=11, color=BLUE_MID
        )
        current_row += 1
        current_row  = _write_dataframe(ws, data_df, start_row=current_row, start_col=1)
        current_row += 2

    # ── AI Interpretation
    if result.interpretation:
        ws.cell(row=current_row, column=1, value="AI Interpretation").font = Font(
            bold=True, size=11, color=BLUE_MID
        )
        current_row += 1

        # Merge cells untuk teks panjang
        ws.merge_cells(
            start_row=current_row, start_column=1,
            end_row=current_row,   end_column=6
        )
        interp_cell               = ws.cell(row=current_row, column=1)
        interp_cell.value         = result.interpretation
        interp_cell.alignment     = Alignment(wrap_text=True, vertical="top")
        interp_cell.font          = Font(color=TEXT_DARK, size=10)
        interp_cell.fill          = PatternFill("solid", fgColor=BLUE_LIGHT)

        # Hitung tinggi row berdasarkan panjang teks
        line_count = max(4, len(result.interpretation) // 120 + 1)
        ws.row_dimensions[current_row].height = line_count * 15

    # Set lebar kolom B–F
    for col_letter in ["B", "C", "D", "E", "F"]:
        ws.column_dimensions[col_letter].width = 20


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_section_header(ws, row: int, title: str) -> int:
    """Tulis header section berwarna biru gelap. Return row berikutnya."""
    ws.merge_cells(
        start_row=row, start_column=1,
        end_row=row,   end_column=6
    )
    cell           = ws.cell(row=row, column=1, value=title)
    cell.font      = Font(name="Calibri", bold=True, size=13, color=WHITE)
    cell.fill      = PatternFill("solid", fgColor=BLUE_DARK)
    cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[row].height = 28
    return row + 1


def _write_dataframe(
    ws,
    df:         pd.DataFrame,
    start_row:  int,
    start_col:  int,
    max_rows:   int = 5000,
) -> int:
    """
    Tulis DataFrame ke worksheet.
    Return row setelah data selesai ditulis.
    Header row diberi warna biru.
    Alternating row warna abu.
    """
    # Potong kalau terlalu besar
    if len(df) > max_rows:
        df = df.head(max_rows)

    # Header
    for col_idx, col_name in enumerate(df.columns, start_col):
        cell           = ws.cell(row=start_row, column=col_idx, value=str(col_name))
        cell.font      = Font(bold=True, color=WHITE)
        cell.fill      = PatternFill("solid", fgColor=BLUE_MID)
        cell.alignment = Alignment(horizontal="center", vertical="center")

        # Auto width berdasarkan nama kolom
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = max(
            ws.column_dimensions[col_letter].width,
            min(len(str(col_name)) + 4, 40)
        )

    ws.row_dimensions[start_row].height = 20

    # Data rows
    for row_idx, row_data in enumerate(df.itertuples(index=False), start_row + 1):
        for col_idx, value in enumerate(row_data, start_col):
            cell        = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font   = Font(color=TEXT_DARK, size=10)
            if (row_idx - start_row) % 2 == 0:
                cell.fill = PatternFill("solid", fgColor=GRAY_LIGHT)

    return start_row + len(df) + 1


def _extract_data_table(result: AnalysisResult) -> Optional[pd.DataFrame]:
    """
    Ekstrak DataFrame dari result.data untuk ditampilkan sebagai tabel detail.
    Tiap tipe analisis punya key yang berbeda.
    """
    data = result.data or {}

    # Coba key umum yang mengandung list of dicts atau DataFrame
    for key in ("grouped_table", "top_items", "forecast_values",
                "top_pairs", "anomalies", "cluster_sizes",
                "coefficients", "top_anomalies", "association_rules"):
        val = data.get(key)
        if val is None:
            continue
        if isinstance(val, pd.DataFrame) and not val.empty:
            return val
        if isinstance(val, list) and val:
            try:
                return pd.DataFrame(val)
            except Exception:
                continue
        if isinstance(val, dict) and val:
            try:
                return pd.DataFrame(
                    list(val.items()), columns=["key", "value"]
                )
            except Exception:
                continue

    return None


def _safe_sheet_name(name: str, index: int) -> str:
    """
    Buat nama sheet yang valid untuk Excel:
    - Maksimal 31 karakter
    - Tidak boleh: [ ] : * ? / \
    - Tambah prefix nomor supaya unik
    """
    import re
    clean = re.sub(r'[\\/*?:\[\]]', '', name)
    clean = clean.strip()
    prefix = f"{index:02d}_"
    max_len = 31 - len(prefix)
    return prefix + clean[:max_len]


def _apply_thin_border(ws, min_row, min_col, max_row, max_col) -> None:
    thin = Side(style="thin", color="E2E8F0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for row in ws.iter_rows(
        min_row=min_row, max_row=max_row,
        min_col=min_col, max_col=max_col
    ):
        for cell in row:
            cell.border = border
```

---

## 2. Update `main.py` — generate Excel setelah PDF

Setiap exporter berjalan independen dalam try/except masing-masing.
Kalau satu gagal, yang lain tetap jalan. Di akhir, ringkasan ditampilkan.

```python
from exporters.excel_exporter import export_excel
from exporters.pdf_exporter   import export_pdf   # existing

# ── Export results — masing-masing independen ────────────────────────────────

export_results = {}   # dict: format → path atau error message

# PDF
try:
    pdf_path = export_pdf(results, profile, output_dir / "report.pdf", args.file)
    export_results["pdf"] = ("ok", str(pdf_path))
except Exception as e:
    export_results["pdf"] = ("error", str(e))

# Excel
try:
    xlsx_path = export_excel(results, profile, output_dir / "report.xlsx", args.file)
    export_results["xlsx"] = ("ok", str(xlsx_path))
except Exception as e:
    export_results["xlsx"] = ("error", str(e))

# ── Tampilkan ringkasan export ────────────────────────────────────────────────

console.print("\n[bold]Export results:[/bold]")

for fmt, (status, detail) in export_results.items():
    if status == "ok":
        icon  = "✅"
        label = "[green]saved[/green]"
        console.print(f"  {icon} [bold]{fmt.upper()}[/bold] {label} → {detail}")
    else:
        icon  = "❌"
        label = "[red]failed[/red]"
        console.print(f"  {icon} [bold]{fmt.upper()}[/bold] {label} — {detail}")
        # Log error lengkap ke file agar bisa di-debug
        _log_export_error(fmt, detail, output_dir)

# Kalau semua gagal, beri tahu user
all_failed = all(status == "error" for status, _ in export_results.values())
if all_failed:
    console.print(
        "\n[yellow]⚠ Semua export gagal. "
        "Data analisis tetap tersimpan di memori sesi ini.[/yellow]"
    )
```

Tambahkan helper `_log_export_error` di `main.py`:

```python
def _log_export_error(fmt: str, error: str, output_dir: Path) -> None:
    """Simpan error export ke file log agar bisa di-debug."""
    import traceback
    log_path = output_dir / "export_errors.log"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now().isoformat()}] {fmt.upper()} export failed:\n")
        f.write(f"{error}\n")
```

---

## 3. Tambah `requirements.txt`

```
openpyxl>=3.1.0    # sudah ada dari connectors, pastikan versi >= 3.1
```

Tidak ada dependency tambahan. `openpyxl` sudah cukup untuk semua fitur di atas.

---

## 4. Struktur Excel output

```
report.xlsx
├── README           ← metadata sesi + daftar analisis + link ke sheet
├── Data Profile     ← rows, cols, missing, list semua kolom + tipe
├── 01_Pareto        ← summary metrics + top items table + AI interpretation
├── 02_Correlation   ← summary + correlation pairs table + AI interpretation
├── 03_Descriptive   ← summary + grouped table + AI interpretation
├── 04_Prophet       ← summary + forecast values table + AI interpretation
└── ...              ← satu sheet per analisis
```

---

## 5. Contoh tampilan di Excel

### Sheet README:
```
┌─────────────────────────────────────────┐
│   TENRIX — Data Analysis Report         │  ← biru gelap, putih
├─────────────────┬───────────────────────┤
│ File            │ samsung.csv           │  ← biru muda
│ Date            │ 2026-03-04 15:09      │
│ Rows            │ 15,500                │
│ Columns         │ 28                    │
│ Analyses        │ 8                     │
├─────────────────┴───────────────────────┤
│ Analyses in this report                 │
│ ✅ Pareto Analysis     → Sheet: 01_Pareto│
│ ✅ Prophet Forecast    → Sheet: 02_Pro...│
│ ✅ Correlation         → Sheet: 03_Corr  │
└─────────────────────────────────────────┘
```

### Sheet 01_Pareto:
```
┌──────────────────────────────────────────┐
│  Pareto Analysis (80/20)                 │  ← header biru gelap
├──────────────────┬───────────────────────┤
│ Summary          │                       │  ← sub-header biru
│ Category Column  │ category              │
│ Value Column     │ revenue_usd           │
│ Total Categories │ 11                    │
│ 80% Threshold    │ 6                     │
│ Top Category     │ Smart TV (5,559,343)  │
├──────────────────┴───────────────────────┤
│ Detail Data                              │  ← sub-header biru
│ label    │ value    │ pct  │ cum_pct     │  ← header biru mid
│ Smart TV │ 5559343  │ 29.0 │ 29.0        │  ← alternating abu
│ Galaxy S │ 4218721  │ 22.1 │ 51.1        │
│ ...                                      │
├──────────────────────────────────────────┤
│ AI Interpretation                        │  ← sub-header biru
│ Enam dari sebelas kategori produk...     │  ← wrap text, biru muda bg
└──────────────────────────────────────────┘
```

---

## 6. Verify

```bash
python -c "
import pandas as pd
from core.data_loader import DataProfile
from core.result import AnalysisResult
from exporters.excel_exporter import export_excel

# Mock profile
profile = DataProfile(
    columns=['category', 'revenue_usd', 'units_sold'],
    numeric_columns=['revenue_usd', 'units_sold'],
    categorical_columns=['category'],
    date_columns=[],
    row_count=100,
    missing_count=5,
    duplicate_count=0,
)

# Mock result
result = AnalysisResult(
    success         = True,
    analysis_id     = 'pareto',
    analysis_name   = 'Pareto Analysis (80/20)',
    summary         = {'Total Categories': 11, '80% Threshold Items': 6, 'Top Category': 'Smart TV'},
    data            = {
        'top_items': [
            {'label': 'Smart TV',  'value': 5559343, 'pct': 29.0, 'cumulative_pct': 29.0},
            {'label': 'Galaxy S',  'value': 4218721, 'pct': 22.1, 'cumulative_pct': 51.1},
            {'label': 'Galaxy Z',  'value': 3101234, 'pct': 16.3, 'cumulative_pct': 67.4},
        ]
    },
    interpretation  = 'Enam dari sebelas kategori produk menyumbang 80% pendapatan.',
)

path = export_excel([result], profile, '/tmp/test_report.xlsx', 'samsung.csv')

# Verify
from openpyxl import load_workbook
wb = load_workbook(path)
assert 'README'       in wb.sheetnames
assert 'Data Profile' in wb.sheetnames
assert '01_Pareto Ana' in wb.sheetnames or any('Pareto' in s for s in wb.sheetnames)
print('✅ Excel export ok:', path)
print('   Sheets:', wb.sheetnames)
"
```

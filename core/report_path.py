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
            Path.home()
            / "Downloads"
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

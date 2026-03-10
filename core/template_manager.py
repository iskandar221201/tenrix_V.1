"""
core/template_manager.py
========================
Manage analysis templates — save, load, list, delete.

Template disimpan sebagai JSON di:
  Windows: %APPDATA%\\Tenrix\\templates\\
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
        # Collect analysis IDs run in the session
        analysis_ids = [result.analysis_id for result in getattr(session, "results", [])]
        export_formats = session.export_formats if hasattr(session, "export_formats") else ["pdf", "excel"]
        selected_columns = getattr(session, "selected_columns", None)
        news_mode = session.news_result.mode if getattr(session, "news_result", None) else None

        # Data Profile info
        row_count = 0
        from core.data_loader import DataProfile
        if hasattr(session, "data_profile") and isinstance(session.data_profile, DataProfile):
            row_count = session.data_profile.row_count
        elif hasattr(session, "data_profile") and isinstance(session.data_profile, dict):
            row_count = session.data_profile.get("row_count", 0)

        template = AnalysisTemplate(
            name=name,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            description=description,
            selected_columns=selected_columns,
            analyses=analysis_ids,
            news_mode=news_mode,
            export_formats=export_formats,
            source_filename=Path(getattr(session, "file_path", "")).name if getattr(session, "file_path", "") else "",
            row_count=row_count,
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

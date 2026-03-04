"""
core/session.py
===============
Menyimpan semua hasil analisis dalam satu sesi.
AI Planner dan Interpreter bisa cross-reference temuan sebelumnya.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SessionEntry:
    question:        str
    analysis_name:   str
    analysis_id:     str
    key_finding:     str
    timestamp:       str = field(default_factory=lambda: datetime.now().isoformat())
    params:          dict = field(default_factory=dict)
    counter_finding: Optional[str] = None


@dataclass
class Session:
    file_path:       str
    started_at:      str = field(default_factory=lambda: datetime.now().isoformat())
    entries:         list[SessionEntry] = field(default_factory=list)
    guardrails:      dict = field(default_factory=dict)   # analysis_id → GuardrailResult
    queued_question: Optional[str] = None
    executive_summary: str = ""

    def add(self, question: str, result, counter_finding: Optional[str] = None) -> None:
        self.entries.append(SessionEntry(
            question        = question,
            analysis_name   = result.analysis_name,
            analysis_id     = result.analysis_id,
            key_finding     = _extract_key_finding(result),
            params          = result.data if hasattr(result, "data") else {},
            counter_finding = counter_finding,
        ))

    @property
    def ran_analyses(self) -> list[str]:
        return [e.analysis_name for e in self.entries]

    @property
    def all_findings(self) -> list[str]:
        findings = []
        for e in self.entries:
            findings.append(f"[{e.analysis_name}] {e.key_finding}")
            if e.counter_finding:
                findings.append(f"  → {e.counter_finding}")
        return findings

    def context_for_planner(self) -> str:
        if not self.entries:
            return ""
        lines = ["Konteks dari analisis sebelumnya di sesi ini:"]
        for e in self.entries[-5:]:
            lines.append(f"  - {e.analysis_name}: {e.key_finding}")
        return "\n".join(lines)

    def context_for_interpreter(self) -> str:
        if not self.entries:
            return ""
        return "\n".join(self.all_findings[-6:])


def _extract_key_finding(result) -> str:
    """Extract a concise key finding from an AnalysisResult."""
    # Use interpretation if available (first 200 chars)
    interp = getattr(result, 'interpretation', None)
    if interp:
        return interp[:200]

    # Fall back to summary dict
    summary = getattr(result, 'summary', None)
    if summary and isinstance(summary, dict):
        items = list(summary.items())[:3]
        return "; ".join(f"{k}: {v}" for k, v in items)

    return getattr(result, 'analysis_name', 'N/A')

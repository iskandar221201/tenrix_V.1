"""
ai/executive_summary.py
========================
Generate executive summary naratif di akhir sesi.
Masuk ke halaman pertama PDF dan sheet README Excel.
"""

from __future__ import annotations

EXECUTIVE_SUMMARY_PROMPT = """
Kamu adalah business analyst yang menulis executive summary.
Rangkum temuan dari sesi analisis data ini menjadi laporan eksekutif
yang ringkas, naratif, dan actionable.

File      : {file_name}
Tanggal   : {date}
Analisis  : {n_analyses}

Temuan sesi:
{all_findings}

Tulis dengan struktur:
  1. Ringkasan Eksekutif (2-3 kalimat gambaran besar)
  2. Temuan Kunci (3-5 bullet dengan angka spesifik)
  3. Temuan Tidak Terduga (jika ada counter-intuitive findings)
  4. Rekomendasi Prioritas (top 3 aksi paling impactful)

Aturan: angka spesifik, Bahasa Indonesia formal, 250-350 kata,
tanpa markdown symbols (**, *, #), tulis bullet dengan tanda —
"""


def generate_executive_summary(session, api_manager, file_name: str = "") -> str:
    if not session.entries:
        return "Tidak ada analisis yang dijalankan dalam sesi ini."

    try:
        from datetime import datetime
        prompt = EXECUTIVE_SUMMARY_PROMPT.format(
            file_name    = file_name or "dataset",
            date         = datetime.now().strftime("%d %B %Y"),
            n_analyses   = len(session.entries),
            all_findings = "\n".join(session.all_findings) or "(tidak ada temuan)",
        )
        return api_manager.call(prompt=prompt, max_tokens=800)

    except Exception:
        lines = [f"Executive Summary — {file_name}",
                 f"Sesi ini menjalankan {len(session.entries)} analisis.", "", "Temuan:"]
        for e in session.entries:
            lines.append(f"  — {e.analysis_name}: {e.key_finding}")
        return "\n".join(lines)

# Tenrix — AI Pipeline Improvements (6 Features + Guardrail dalam Laporan)

Priority: Pre-Analysis Guardrails → Counter-Intuitive Discovery →
Analysis Memory → Confidence Score → Executive Summary → Interactive Refinement

File baru yang perlu dibuat:
  analysis/guardrails.py
  analysis/confidence.py
  core/session.py
  ai/executive_summary.py

File yang perlu diupdate:
  ai/prompts.py
  ai/interpreter.py
  ai/planner.py
  core/result.py
  tui/components.py
  exporters/pdf_exporter.py
  exporters/excel_exporter.py
  main.py

---

## Feature 1: Pre-Analysis Guardrails
### File baru: `analysis/guardrails.py`

```python
"""
analysis/guardrails.py
======================
Uji asumsi statistik sebelum analisis dijalankan.
Jika asumsi tidak terpenuhi, Tenrix menampilkan disclaimer
dan tetap menjalankan analisis — tapi dengan peringatan.

Asumsi yang dicek per analisis:
  regression_linear   — normalitas, multikolinearitas (VIF), sample size
  regression_logistic — class balance, sample size per class
  anova               — normalitas per group, homogenitas varians (Levene)
  correlation         — normalitas kedua variabel (untuk Pearson)
  clustering_kmeans   — feature scaling, outlier ekstrem
  time_series_prophet — panjang data minimal, temporal gaps
  anomaly_isolation   — sample size minimal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class AssumptionViolation:
    test:     str            # "shapiro_wilk" | "levene" | "vif" | "sample_size" | dll
    column:   str
    stat:     float
    p_value:  Optional[float]
    passed:   bool
    message:  str            # pesan singkat untuk terminal dan laporan


@dataclass
class GuardrailResult:
    analysis_id: str
    violations:  list[AssumptionViolation] = field(default_factory=list)
    passed:      bool = True
    disclaimer:  str = ""    # teks disclaimer untuk terminal & PDF

    def has_violations(self) -> bool:
        return any(not v.passed for v in self.violations)


# ── Entry point ───────────────────────────────────────────────────────────────

def check_assumptions(
    analysis_id: str,
    df:          pd.DataFrame,
    params:      dict,
    profile,
) -> GuardrailResult:
    """
    Jalankan uji asumsi untuk analysis_id tertentu.
    Dipanggil dari analysis engine SEBELUM analisis dijalankan.

        guard = check_assumptions("regression_linear", df, params, profile)
        if guard.has_violations():
            show_guardrail_warning(guard)
        result = run_analysis(...)   # tetap jalan walau ada violations
    """
    checkers = {
        "regression_linear":   _check_linear_regression,
        "regression_logistic": _check_logistic_regression,
        "anova":               _check_anova,
        "correlation":         _check_correlation,
        "clustering_kmeans":   _check_kmeans,
        "time_series_prophet": _check_prophet,
        "time_series_arima":   _check_prophet,
        "anomaly_isolation":   _check_anomaly,
    }

    checker = checkers.get(analysis_id)
    if checker is None:
        return GuardrailResult(analysis_id=analysis_id, passed=True)

    violations = checker(df, params, profile)
    passed     = not any(not v.passed for v in violations)
    disclaimer = _build_disclaimer(analysis_id, violations) if not passed else ""

    return GuardrailResult(
        analysis_id = analysis_id,
        violations  = violations,
        passed      = passed,
        disclaimer  = disclaimer,
    )


# ── Checkers ──────────────────────────────────────────────────────────────────

def _check_linear_regression(df, params, profile) -> list[AssumptionViolation]:
    violations = []
    target     = params.get("target") or (profile.numeric_columns[0] if profile.numeric_columns else None)
    features   = params.get("features", profile.numeric_columns[:5])

    if not target or target not in df.columns:
        return violations

    y      = df[target].dropna()
    sample = y.sample(min(5000, len(y)), random_state=42) if len(y) > 5000 else y

    # 1. Normalitas (Shapiro-Wilk)
    try:
        stat, p = stats.shapiro(sample)
        violations.append(AssumptionViolation(
            test    = "shapiro_wilk",
            column  = target,
            stat    = round(float(stat), 4),
            p_value = round(float(p), 4),
            passed  = p >= 0.05,
            message = (
                f"Normalitas '{target}': {'✓ normal' if p >= 0.05 else '✗ tidak normal'} "
                f"(Shapiro-Wilk W={stat:.3f}, p={p:.4f})"
            ),
        ))
    except Exception:
        pass

    # 2. Multikolinearitas (VIF)
    num_features = [f for f in features if f in df.columns and f != target]
    if len(num_features) >= 2:
        try:
            from statsmodels.stats.outliers_influence import variance_inflation_factor
            X = df[num_features].dropna()
            for i, col in enumerate(num_features):
                vif = variance_inflation_factor(X.values, i)
                if vif > 10:
                    violations.append(AssumptionViolation(
                        test    = "vif",
                        column  = col,
                        stat    = round(float(vif), 2),
                        p_value = None,
                        passed  = False,
                        message = f"Multikolinearitas tinggi '{col}': VIF={vif:.1f} > 10",
                    ))
        except ImportError:
            pass
        except Exception:
            pass

    # 3. Sample size minimal (10 obs per fitur)
    min_required = len(num_features) * 10
    if len(y) < min_required:
        violations.append(AssumptionViolation(
            test    = "sample_size",
            column  = target,
            stat    = len(y),
            p_value = None,
            passed  = False,
            message = (
                f"Sample size kurang: {len(y)} baris, "
                f"minimal {min_required} untuk {len(num_features)} fitur."
            ),
        ))

    return violations


def _check_logistic_regression(df, params, profile) -> list[AssumptionViolation]:
    violations = []
    target     = params.get("target")
    if not target or target not in df.columns:
        return violations

    counts = df[target].value_counts()
    if len(counts) < 2:
        return violations

    ratio = counts.iloc[0] / counts.iloc[-1]
    if ratio > 10:
        violations.append(AssumptionViolation(
            test    = "class_balance",
            column  = target,
            stat    = round(float(ratio), 1),
            p_value = None,
            passed  = False,
            message = (
                f"Class imbalance tinggi: rasio {ratio:.0f}:1. "
                f"Logistic regression bisa bias ke kelas mayoritas."
            ),
        ))

    min_count = counts.min()
    if min_count < 50:
        violations.append(AssumptionViolation(
            test    = "sample_size",
            column  = target,
            stat    = float(min_count),
            p_value = None,
            passed  = False,
            message = f"Kelas minoritas hanya {min_count} sampel (min. 50 disarankan).",
        ))

    return violations


def _check_anova(df, params, profile) -> list[AssumptionViolation]:
    violations = []
    group_col  = params.get("groupby") or params.get("focus_column")
    value_col  = params.get("target") or (profile.numeric_columns[0] if profile.numeric_columns else None)

    if not group_col or not value_col:
        return violations
    if group_col not in df.columns or value_col not in df.columns:
        return violations

    groups = [g[value_col].dropna().values for _, g in df.groupby(group_col) if len(g) >= 5]
    if len(groups) < 2:
        return violations

    # Normalitas per group
    non_normal = 0
    for g in groups[:5]:
        try:
            _, p = stats.shapiro(g[:5000])
            if p < 0.05:
                non_normal += 1
        except Exception:
            pass

    if non_normal > 0:
        violations.append(AssumptionViolation(
            test    = "shapiro_wilk",
            column  = value_col,
            stat    = float(non_normal),
            p_value = None,
            passed  = False,
            message = (
                f"{non_normal} dari {min(len(groups), 5)} group tidak normal. "
                f"Pertimbangkan Kruskal-Wallis sebagai alternatif non-parametrik."
            ),
        ))

    # Homogenitas varians (Levene)
    try:
        stat, p = stats.levene(*groups[:5])
        violations.append(AssumptionViolation(
            test    = "levene",
            column  = value_col,
            stat    = round(float(stat), 4),
            p_value = round(float(p), 4),
            passed  = p >= 0.05,
            message = (
                f"Homogenitas varians: {'✓ homogen' if p >= 0.05 else '✗ tidak homogen'} "
                f"(Levene p={p:.4f})."
                + ("" if p >= 0.05 else " Gunakan Welch ANOVA sebagai alternatif.")
            ),
        ))
    except Exception:
        pass

    return violations


def _check_correlation(df, params, profile) -> list[AssumptionViolation]:
    violations = []
    for col in profile.numeric_columns[:2]:
        if col not in df.columns:
            continue
        series = df[col].dropna()
        sample = series.sample(min(5000, len(series)), random_state=42)
        try:
            stat, p = stats.shapiro(sample)
            if p < 0.05:
                violations.append(AssumptionViolation(
                    test    = "shapiro_wilk",
                    column  = col,
                    stat    = round(float(stat), 4),
                    p_value = round(float(p), 4),
                    passed  = False,
                    message = (
                        f"'{col}' tidak normal (p={p:.4f}). "
                        f"Pearson kurang tepat — Spearman lebih robust untuk data ini."
                    ),
                ))
        except Exception:
            pass
    return violations


def _check_kmeans(df, params, profile) -> list[AssumptionViolation]:
    violations = []
    features  = params.get("features", profile.numeric_columns[:5])
    num_feats = [f for f in features if f in df.columns]
    if not num_feats:
        return violations

    stds = df[num_feats].std()
    if stds.max() / (stds.min() + 1e-9) > 10:
        violations.append(AssumptionViolation(
            test    = "feature_scaling",
            column  = stds.idxmax(),
            stat    = round(float(stds.max() / stds.min()), 1),
            p_value = None,
            passed  = False,
            message = (
                f"Skala fitur sangat berbeda (rasio std = {stds.max()/stds.min():.0f}x). "
                f"StandardScaler akan diaplikasikan otomatis."
            ),
        ))

    for col in num_feats[:3]:
        series = df[col].dropna()
        z      = np.abs(stats.zscore(series))
        pct    = (z > 3).mean()
        if pct > 0.10:
            violations.append(AssumptionViolation(
                test    = "outlier",
                column  = col,
                stat    = round(float(pct * 100), 1),
                p_value = None,
                passed  = False,
                message = (
                    f"'{col}': {pct*100:.1f}% outlier ekstrem. "
                    f"K-Means sensitif — hasil cluster bisa tidak stabil."
                ),
            ))

    return violations


def _check_prophet(df, params, profile) -> list[AssumptionViolation]:
    violations = []
    date_col   = params.get("date_col") or (profile.date_columns[0] if profile.date_columns else None)
    if not date_col or date_col not in df.columns:
        return violations

    dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
    n     = len(dates)

    if n < 30:
        violations.append(AssumptionViolation(
            test    = "sample_size",
            column  = date_col,
            stat    = float(n),
            p_value = None,
            passed  = False,
            message = f"Hanya {n} data poin. Prophet butuh minimal 30, idealnya 2+ siklus.",
        ))

    if n >= 2:
        gaps       = dates.sort_values().diff().dropna()
        median_gap = gaps.median()
        max_gap    = gaps.max()
        if max_gap > median_gap * 10:
            violations.append(AssumptionViolation(
                test    = "temporal_gaps",
                column  = date_col,
                stat    = float(max_gap.days if hasattr(max_gap, "days") else max_gap),
                p_value = None,
                passed  = False,
                message = (
                    f"Gap besar dalam data waktu (max={max_gap}, median={median_gap}). "
                    f"Forecast mungkin tidak akurat di area gap."
                ),
            ))

    return violations


def _check_anomaly(df, params, profile) -> list[AssumptionViolation]:
    violations = []
    if len(df) < 50:
        violations.append(AssumptionViolation(
            test    = "sample_size",
            column  = "dataset",
            stat    = float(len(df)),
            p_value = None,
            passed  = False,
            message = f"Hanya {len(df)} baris. Isolation Forest butuh minimal 50 sampel.",
        ))
    return violations


def _build_disclaimer(analysis_id: str, violations: list[AssumptionViolation]) -> str:
    failed = [v for v in violations if not v.passed]
    if not failed:
        return ""
    lines = [f"Menjalankan {analysis_id.replace('_', ' ').title()} — perlu dicatat:"]
    for v in failed:
        lines.append(f"  ⚠ {v.message}")
    return "\n".join(lines)
```

---

## Feature 1b: Guardrail dalam Laporan (PDF + Excel)

### Update `exporters/pdf_exporter.py`

Tambah helper `_draw_guardrail_box()`:

```python
from reportlab.lib      import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm

def _draw_guardrail_box(story: list, guardrail, styles) -> None:
    """
    Box kuning/hijau di bawah judul setiap analisis.
    Hijau = semua asumsi terpenuhi. Kuning = ada violations.
    """
    if guardrail is None:
        return

    violations = [v for v in guardrail.violations if not v.passed]
    passed_all = len(violations) == 0

    if passed_all:
        bg_color     = colors.HexColor("#F0FDF4")
        border_color = colors.HexColor("#10B981")
        icon         = "✓ Pre-Analysis Check: semua asumsi terpenuhi"
        font_color   = "#065F46"
    else:
        bg_color     = colors.HexColor("#FFFBEB")
        border_color = colors.HexColor("#D97706")
        icon         = f"⚠ Pre-Analysis Check: {len(violations)} asumsi tidak terpenuhi"
        font_color   = "#92400E"

    rows = [Paragraph(f'<font color="{font_color}"><b>{icon}</b></font>', styles["small_bold"])]
    for v in violations:
        rows.append(Paragraph(f"• {v.message}", styles["small_warning"]))
    if not passed_all:
        rows.append(Paragraph(
            "<i>Catatan: analisis tetap dijalankan. "
            "Pertimbangkan temuan ini saat menginterpretasi hasil.</i>",
            styles["small_italic"]
        ))

    tbl = Table([[rows]], colWidths=[170 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), bg_color),
        ("BOX",          (0, 0), (-1, -1), 0.5, border_color),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))

    story.append(tbl)
    story.append(Spacer(1, 4 * mm))
```

Update `_build_analysis_section()` — tambah parameter guardrail:

```python
def _build_analysis_section(
    story:     list,
    result:    AnalysisResult,
    styles:    dict,
    guardrail = None,    # ← TAMBAH
) -> None:
    story.append(Paragraph(result.analysis_name, styles["h2"]))
    story.append(Spacer(1, 2 * mm))

    # ← TAMBAH: guardrail box setelah judul, sebelum konten
    _draw_guardrail_box(story, guardrail, styles)

    # ... existing: chart, tabel, interpretasi, confidence bar ...
```

Update `export_pdf()` signature:

```python
def export_pdf(
    results:      list[AnalysisResult],
    profile:      DataProfile,
    file_path:    str,
    source_file:  str = "",
    guardrails:   dict[str, GuardrailResult] = None,   # ← TAMBAH
    exec_summary: str = "",                             # ← TAMBAH
) -> str:
    guardrails = guardrails or {}
    for result in results:
        guard = guardrails.get(result.analysis_id)
        _build_analysis_section(story, result, styles, guardrail=guard)
```

### Update `exporters/excel_exporter.py`

Tambah helper `_write_guardrail_section()`:

```python
def _write_guardrail_section(ws, start_row: int, guardrail) -> int:
    """
    Tulis guardrail ke worksheet. Return row berikutnya.

    Kalau pass: 1 baris hijau.
    Kalau ada violations: header oranye + tabel Test/Kolom/Status/Detail.
    """
    if guardrail is None:
        return start_row

    violations = [v for v in guardrail.violations if not v.passed]
    passed_all = len(violations) == 0

    ws.merge_cells(start_row=start_row, start_column=1,
                   end_row=start_row,   end_column=4)
    hdr       = ws.cell(row=start_row, column=1)
    hdr.font  = Font(bold=True, size=10, color="FFFFFF")
    hdr.alignment = Alignment(vertical="center", indent=1)

    if passed_all:
        hdr.value = "✓ PRE-ANALYSIS CHECK — Semua asumsi terpenuhi"
        hdr.fill  = PatternFill("solid", fgColor="10B981")
        ws.row_dimensions[start_row].height = 20
        return start_row + 2

    hdr.value = f"⚠ PRE-ANALYSIS CHECK — {len(violations)} asumsi tidak terpenuhi"
    hdr.fill  = PatternFill("solid", fgColor="D97706")
    ws.row_dimensions[start_row].height = 20
    current_row = start_row + 1

    # Sub-header
    for col_idx, h in enumerate(["Test", "Kolom", "Status", "Detail"], 1):
        cell       = ws.cell(row=current_row, column=col_idx, value=h)
        cell.font  = Font(bold=True, size=10, color="92400E")
        cell.fill  = PatternFill("solid", fgColor="FEF3C7")
        cell.alignment = Alignment(horizontal="center")

    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 50
    current_row += 1

    for v in guardrail.violations:
        passed_v = v.passed
        ws.cell(row=current_row, column=1, value=v.test)
        ws.cell(row=current_row, column=2, value=v.column)

        sc       = ws.cell(row=current_row, column=3,
                           value="✓ OK" if passed_v else "✗ GAGAL")
        sc.font  = Font(bold=True, size=10,
                        color="065F46" if passed_v else "991B1B")
        sc.fill  = PatternFill("solid",
                               fgColor="D1FAE5" if passed_v else "FEE2E2")
        sc.alignment = Alignment(horizontal="center")

        dc           = ws.cell(row=current_row, column=4, value=v.message)
        dc.font      = Font(size=9, color="374151")
        dc.alignment = Alignment(wrap_text=True)
        ws.row_dimensions[current_row].height = 30
        current_row += 1

    note = ws.cell(
        row=current_row, column=1,
        value="Analisis tetap dijalankan. Pertimbangkan temuan ini saat interpretasi."
    )
    note.font = Font(italic=True, size=9, color="6B7280")
    ws.merge_cells(start_row=current_row, start_column=1,
                   end_row=current_row,   end_column=4)
    return current_row + 2


def _write_data_quality_sheet(
    wb:         Workbook,
    guardrails: dict,
    results:    list,
) -> None:
    """
    Sheet ke-2: ringkasan status guardrail semua analisis.
    Pembaca bisa lihat sekilas analisis mana yang reliable.
    """
    ws = wb.create_sheet("Data Quality", 1)
    _write_section_header(ws, 1, "Data Quality & Pre-Analysis Guardrails")

    headers = ["Analisis", "Status", "Violations", "Confidence", "Catatan"]
    widths  = [30, 12, 12, 16, 44]
    for col_idx, (h, w) in enumerate(zip(headers, widths), 1):
        cell       = ws.cell(row=2, column=col_idx, value=h)
        cell.font  = Font(bold=True, color="FFFFFF")
        cell.fill  = PatternFill("solid", fgColor=BLUE_MID)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(col_idx)].width = w
    ws.row_dimensions[2].height = 20

    for row_idx, result in enumerate(results, 3):
        guard      = guardrails.get(result.analysis_id)
        violations = [v for v in guard.violations if not v.passed] if guard else []
        n_viol     = len(violations)
        passed     = n_viol == 0

        conf_score = getattr(result, "confidence_score", None)
        conf_text  = f"{conf_score*100:.0f}%" if conf_score is not None else "—"

        status_text  = "✓ PASS" if passed else f"⚠ {n_viol} violation"
        status_color = "D1FAE5" if passed else "FEF3C7"
        status_font  = "065F46" if passed else "92400E"
        note         = "; ".join(v.test for v in violations) if violations else "—"

        ws.cell(row=row_idx, column=1, value=result.analysis_name)

        sc       = ws.cell(row=row_idx, column=2, value=status_text)
        sc.font  = Font(bold=True, size=10, color=status_font)
        sc.fill  = PatternFill("solid", fgColor=status_color)
        sc.alignment = Alignment(horizontal="center")

        ws.cell(row=row_idx, column=3, value=n_viol).alignment = Alignment(horizontal="center")
        ws.cell(row=row_idx, column=4, value=conf_text).alignment = Alignment(horizontal="center")

        nc           = ws.cell(row=row_idx, column=5, value=note)
        nc.font      = Font(size=9, color=TEXT_GRAY)
        nc.alignment = Alignment(wrap_text=True)

        if row_idx % 2 == 0:
            for col in range(1, 6):
                ws.cell(row=row_idx, column=col).fill = PatternFill("solid", fgColor=GRAY_LIGHT)

        ws.row_dimensions[row_idx].height = 18
```

Update `_write_analysis_sheet()` — tambah guardrail parameter:

```python
def _write_analysis_sheet(wb, result, index, guardrail=None) -> None:
    # ... existing setup ...
    current_row = _write_section_header(ws, 1, result.analysis_name) + 1

    # ← TAMBAH: guardrail section setelah judul
    current_row = _write_guardrail_section(ws, current_row, guardrail)

    # ... existing: summary, data table, AI interpretation ...
```

Update `export_excel()` signature + tambah sheet Data Quality:

```python
def export_excel(
    results:      list,
    profile,
    file_path:    str,
    source_file:  str = "",
    guardrails:   dict = None,    # ← TAMBAH
    exec_summary: str = "",       # ← TAMBAH
) -> str:
    wb = Workbook()
    wb.remove(wb.active)
    guardrails = guardrails or {}

    _write_readme_sheet(wb, results, profile, source_file, exec_summary)
    _write_data_quality_sheet(wb, guardrails, results)    # ← BARU sheet ke-2
    _write_profile_sheet(wb, profile)

    for i, result in enumerate(results, 1):
        if result.success:
            guard = guardrails.get(result.analysis_id)
            _write_analysis_sheet(wb, result, index=i, guardrail=guard)

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(path))
    return str(path)
```

---

## Feature 2: Counter-Intuitive Discovery

### Update `ai/prompts.py` — tambah COUNTER_INTUITIVE_PROMPT

```python
COUNTER_INTUITIVE_PROMPT = """
Kamu adalah data analyst yang skeptis dan kritis.
Sebuah analisis baru saja selesai. Tugasmu: cari pola TERSEMBUNYI atau
KONTRADIKTIF yang TIDAK ditanyakan user tapi penting untuk diketahui.

Pertanyaan user    : {user_question}
Analisis dijalankan: {analysis_name}
Hasil utama        : {main_finding}
Data konteks       : {data_context}
Analisis sebelumnya: {previous_findings}

Cari satu dari pola berikut (jika ada dalam data):
  1. KONTRADIKSI      — hasil bertentangan dengan asumsi umum
  2. ANOMALI TERSEMBUNYI — pola tak wajar tidak terlihat di analisis utama
  3. KORELASI PALSU   — dua variabel tampak berhubungan tapi ada variabel ketiga
  4. SEGMEN TERSEMBUNYI — subgroup yang berperilaku sangat berbeda dari rata-rata

Aturan ketat:
  - Hanya report jika benar-benar yakin ada pola dalam data
  - Jika tidak ada, return "found": false — jangan buat-buat
  - Maksimal 1 temuan (yang paling impactful)
  - Harus spesifik: sebutkan angka, kolom, atau segmen

Return JSON only:
{{
  "found": true/false,
  "type": "kontradiksi|anomali|korelasi_palsu|segmen_tersembunyi",
  "finding": "Kalimat temuan max 2 kalimat dengan angka spesifik",
  "follow_up_analysis": "analysis_id untuk mendalami temuan ini"
}}
"""
```

### Update `ai/interpreter.py` — tambah `find_counter_intuitive()`

```python
def find_counter_intuitive(
    self,
    result:           AnalysisResult,
    profile:          DataProfile,
    user_question:    str,
    session_findings: list[str],
) -> Optional[str]:
    """
    Cari temuan counter-intuitive. Return string atau None.
    Dipanggil setelah interpret().
    """
    try:
        data_context = (
            f"Rows: {profile.row_count:,} | "
            f"Numeric: {profile.numeric_columns[:5]} | "
            f"Categorical: {profile.categorical_columns[:5]}"
        )
        if result.summary:
            data_context += " | Summary: " + str(dict(list(result.summary.items())[:3]))

        prompt = COUNTER_INTUITIVE_PROMPT.format(
            user_question     = user_question,
            analysis_name     = result.analysis_name,
            main_finding      = result.interpretation[:200] if result.interpretation else "—",
            data_context      = data_context,
            previous_findings = session_findings[-3:] if session_findings else ["(belum ada)"],
        )

        raw  = self.api_manager.call(prompt=prompt, max_tokens=400, json_mode=True)
        data = _parse_json_safe(raw)

        if not data.get("found"):
            return None

        finding = data.get("finding", "")
        if not finding:
            return None

        labels = {
            "kontradiksi":        "🔄 Kontradiksi",
            "anomali":            "⚠ Anomali Tersembunyi",
            "korelasi_palsu":     "🔗 Kemungkinan Korelasi Palsu",
            "segmen_tersembunyi": "🔍 Segmen Tersembunyi",
        }
        label = labels.get(data.get("type", ""), "💡 Temuan")
        return f"{label}: {finding}"

    except Exception as e:
        logger.warning(f"find_counter_intuitive failed: {e}")
        return None
```

### Update `tui/components.py`

```python
def show_counter_intuitive(finding: str) -> None:
    if not finding:
        return
    from rich.panel import Panel
    console.print(Panel(
        finding,
        title="[bold yellow]💡 Temuan Tidak Terduga[/bold yellow]",
        border_style="yellow",
        padding=(0, 1),
    ))
```

---

## Feature 3: Analysis Memory / Session Context
### File baru: `core/session.py`

```python
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
        from ai.interpreter import _extract_key_finding
        self.entries.append(SessionEntry(
            question        = question,
            analysis_name   = result.analysis_name,
            analysis_id     = result.analysis_id,
            key_finding     = _extract_key_finding(result),
            params          = result.params if hasattr(result, "params") else {},
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
```

### Update `ai/planner.py`

```python
# Di dalam build_plan():
session_context = session.context_for_planner() if session else ""

PLANNER_PROMPT = f"""
...existing prompt...

{session_context}

Gunakan konteks di atas untuk:
  - Hindari analisis yang sudah dijalankan
  - Jika pertanyaan bisa dijawab dari temuan sebelumnya, sebutkan
  - Jika ada kontradiksi dengan temuan sebelumnya, flag ke user
"""
```

---

## Feature 4: Confidence Score
### Update `core/result.py`

```python
@dataclass
class AnalysisResult:
    # ... existing fields ...
    confidence_score:   Optional[float] = None
    confidence_reasons: list[str] = field(default_factory=list)
```

### File baru: `analysis/confidence.py`

```python
"""
analysis/confidence.py
======================
Hitung confidence score 0–100 per analisis.
Faktor: sample size, missing values, guardrail violations, model metrics.
"""

from __future__ import annotations


def calculate_confidence(result, guardrail, profile, df_size: int) -> tuple[float, list[str]]:
    """Return (score 0.0–1.0, reasons). 0.8+= tinggi, 0.5–0.8= sedang, <0.5= rendah."""
    score   = 1.0
    reasons = []

    # Sample size
    if df_size < 30:
        score -= 0.40; reasons.append(f"Sample sangat kecil ({df_size} baris)")
    elif df_size < 100:
        score -= 0.20; reasons.append(f"Sample kecil ({df_size} baris)")
    elif df_size < 500:
        score -= 0.10

    # Missing values
    missing_pct = getattr(profile, "missing_pct", 0)
    if missing_pct > 0.50:
        score -= 0.30; reasons.append(f"Missing values tinggi ({missing_pct*100:.0f}%)")
    elif missing_pct > 0.20:
        score -= 0.15; reasons.append(f"Missing values moderat ({missing_pct*100:.0f}%)")

    # Guardrail violations
    violations = [v for v in guardrail.violations if not v.passed]
    if violations:
        penalty = min(0.10 * len(violations), 0.35)
        score  -= penalty
        reasons.append(f"{len(violations)} asumsi statistik tidak terpenuhi")

    # Model metrics
    data = result.data or {}
    r2   = data.get("r2_score")
    if r2 is not None:
        if r2 < 0.3:
            score -= 0.20; reasons.append(f"R² rendah ({r2:.2f}) — model fit lemah")
        elif r2 > 0.7:
            score += 0.05

    sil = data.get("silhouette_score")
    if sil is not None and sil < 0.3:
        score -= 0.15; reasons.append(f"Silhouette score rendah ({sil:.2f})")

    return round(max(0.0, min(1.0, score)), 2), reasons


def confidence_bar(score: float, width: int = 10) -> str:
    filled = round(score * width)
    color  = "green" if score >= 0.75 else "yellow" if score >= 0.50 else "red"
    bar    = "█" * filled + "░" * (width - filled)
    return f"[{color}]{bar}[/{color}] [dim]{score*100:.0f}%[/dim]"
```

### Update `tui/components.py`

```python
def show_confidence(score: float, reasons: list[str]) -> None:
    from analysis.confidence import confidence_bar
    bar = confidence_bar(score)
    console.print(f"\n  [dim]Confidence:[/dim] {bar}", end="")
    if reasons and score < 0.75:
        console.print(f"  [dim]({'; '.join(reasons[:2])})[/dim]")
    else:
        console.print()
```

---

## Feature 5: Executive Summary
### File baru: `ai/executive_summary.py`

```python
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
```

---

## Feature 6: Interactive Refinement
### Update `tui/components.py`

```python
REFINEMENT_TEMPLATES = {
    "clustering_kmeans": [
        ("Dalami cluster terbesar",     "Analisis detail cluster {top_cluster}"),
        ("Hilangkan outlier & ulangi",  "Jalankan ulang clustering tanpa outlier"),
        ("Coba jumlah cluster berbeda", "Coba clustering dengan {k_plus_1} cluster"),
    ],
    "regression_linear": [
        ("Hilangkan outlier & ulangi",  "Jalankan ulang regresi setelah remove outlier"),
        ("Coba fitur lain",             "Regresi dengan fitur berbeda"),
        ("Lihat distribusi residual",   "Analisis distribusi residual regresi"),
    ],
    "time_series_prophet": [
        ("Prediksi lebih panjang",      "Forecast 180 hari ke depan"),
        ("Filter periode tertentu",     "Forecast hanya dari data 2023 ke atas"),
        ("Per kategori",                "Forecast revenue per kategori produk"),
    ],
    "pareto": [
        ("Drill down top item",         "Analisis detail {top_item}"),
        ("Pareto per region",           "Pareto analysis difilter per region"),
        ("Tren top item",               "Forecast revenue {top_item} 90 hari ke depan"),
    ],
    "descriptive_stats": [
        ("Filter subgroup",             "Analisis deskriptif hanya untuk {top_group}"),
        ("Bandingkan dua grup",         "Bandingkan {group_a} vs {group_b}"),
        ("Cek distribusi tanpa outlier","Tampilkan distribusi tanpa nilai ekstrem"),
    ],
}


def show_refinement_options(result, session) -> Optional[str]:
    templates = REFINEMENT_TEMPLATES.get(result.analysis_id, [])
    if not templates:
        return None

    filled = []
    data   = result.data or {}
    for label, question in templates:
        replacements = {
            "top_cluster": str(data.get("top_cluster", "1")),
            "k_plus_1":    str(data.get("n_clusters", 3) + 1),
            "top_item":    str(data.get("top_item", data.get("top_category", "item teratas"))),
            "top_group":   str(data.get("top_group", "grup teratas")),
            "group_a":     str(data.get("group_a", "grup A")),
            "group_b":     str(data.get("group_b", "grup B")),
        }
        for key, val in replacements.items():
            question = question.replace(f"{{{key}}}", val)
            label    = label.replace(f"{{{key}}}", val)
        filled.append((label, question))

    console.print("\n[bold]🔧 Ingin mendalami lebih lanjut?[/bold]")
    for i, (label, _) in enumerate(filled, 1):
        console.print(f"  [cyan]{i}[/cyan]. {label}")
    console.print(f"  [dim]Ketik 1–{len(filled)} atau Enter untuk skip[/dim]")

    raw = Prompt.ask("[bold blue]Pilihan[/bold blue]", default="").strip()
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(filled):
            _, question = filled[idx]
            return question
    except ValueError:
        pass
    return None
```

---

## Integrasi `main.py` — semua fitur

```python
from analysis.guardrails    import check_assumptions
from analysis.confidence    import calculate_confidence
from ai.executive_summary   import generate_executive_summary
from core.session           import Session
from tui.components         import (
    show_bias_report, show_guardrail_warning, show_counter_intuitive,
    show_confidence, show_next_suggestions, show_refinement_options,
)

# ── Init ──────────────────────────────────────────────────────────────────────
session = Session(file_path=args.file)

# Bias detection di awal sesi (dari bias_detector.py)
bias_report      = run_bias_detection(df, profile)
session.bias_report = bias_report
show_bias_report(bias_report)

# ── Loop analisis ─────────────────────────────────────────────────────────────
while True:
    question = session.queued_question or get_user_question()
    session.queued_question = None
    if not question:
        break

    plan = planner.build_plan(question, profile, session=session)

    for step in plan.steps:

        # 1. Guardrail — cek asumsi sebelum analisis
        guard = check_assumptions(step.analysis_id, df, step.params, profile)
        session.guardrails[step.analysis_id] = guard    # simpan untuk laporan
        if guard.has_violations():
            show_guardrail_warning(guard)               # terminal warning

        # 2. Jalankan analisis
        result = engine.run_step(step, df)
        if not result.success:
            console.print(f"[red]✗ {result.analysis_name}: {result.error}[/red]")
            continue

        # 3. Confidence score
        score, reasons = calculate_confidence(result, guard, profile, len(df))
        result.confidence_score   = score
        result.confidence_reasons = reasons

        # 4. AI Interpretation
        result.interpretation = interpreter.interpret(
            result, profile,
            bias_report     = session.bias_report,
            session_context = session.context_for_interpreter(),
            guardrail       = guard,
        )

        # 5. Counter-intuitive
        counter = interpreter.find_counter_intuitive(
            result, profile, question, session.all_findings
        )

        # 6. Tampilkan
        print_analysis_result(result)
        show_confidence(score, reasons)
        show_counter_intuitive(counter)

        # 7. Session memory
        session.add(question, result, counter)

        # 8. Suggested next + refinement
        suggestions   = interpreter.suggest_next(result, profile, session.ran_analyses)
        next_question = show_next_suggestions(suggestions, session)
        if not next_question:
            next_question = show_refinement_options(result, session)
        if next_question:
            session.queued_question = next_question
            break

# ── End of session ────────────────────────────────────────────────────────────
console.print("\n[bold blue]📝 Generating executive summary...[/bold blue]")
exec_summary             = generate_executive_summary(session, api_manager, args.file)
session.executive_summary = exec_summary
console.print("\n" + exec_summary)

# Export — masing-masing independen
for fmt, exporter, path in [
    ("pdf",  export_pdf,   output_dir / "report.pdf"),
    ("xlsx", export_excel, output_dir / "report.xlsx"),
]:
    try:
        out = exporter(
            results      = session.entries,
            profile      = profile,
            file_path    = str(path),
            source_file  = args.file,
            guardrails   = session.guardrails,    # ← guardrail masuk laporan
            exec_summary = exec_summary,
        )
        console.print(f"  ✅ {fmt.upper()}: {out}")
    except Exception as e:
        console.print(f"  ❌ {fmt.upper()}: {e}")
        _log_export_error(fmt, str(e), output_dir)
```

---

## Struktur laporan akhir

### PDF (per halaman analisis):
```
[ Judul Analisis ]
[ ⚠ Pre-Analysis Check box — kuning/hijau ]
[ Chart + Summary Table ]
[ AI Interpretation ]
[ Confidence: ████░░░░ 41% ]
```

### Excel (urutan sheet):
```
README        ← metadata + exec summary + daftar analisis
Data Quality  ← ringkasan guardrail semua analisis + confidence score
Data Profile  ← info dataset lengkap
01_Pareto     ← guardrail section + summary + data + interpretasi
02_Regression ← guardrail section + summary + data + interpretasi
...
```

---

## Verify

```bash
# Guardrails
python -c "
import pandas as pd, numpy as np
from analysis.guardrails import check_assumptions
from unittest.mock import MagicMock

df = pd.DataFrame({
    'revenue': np.concatenate([np.random.exponential(1000, 900), [50000]*100]),
    'units':   np.random.randint(1, 10, 1000),
})
profile = MagicMock()
profile.numeric_columns = ['revenue', 'units']

g = check_assumptions('regression_linear', df, {'target': 'revenue'}, profile)
assert g.has_violations()
assert any(v.test == 'shapiro_wilk' for v in g.violations)
print('✅ Guardrails ok:', [(v.test, v.passed) for v in g.violations])
"

# Confidence score
python -c "
from analysis.confidence import calculate_confidence, confidence_bar
from analysis.guardrails import GuardrailResult, AssumptionViolation
from unittest.mock import MagicMock

result  = MagicMock(); result.data = {'r2_score': 0.25}
profile = MagicMock(); profile.missing_pct = 0.05
g = GuardrailResult('regression_linear', [
    AssumptionViolation('shapiro_wilk','revenue',0.85,0.001,False,'Tidak normal')
])
score, reasons = calculate_confidence(result, g, profile, 500)
assert 0 <= score <= 1
print('✅ Confidence:', score, reasons)
print('   Bar:', confidence_bar(score))
"

# Session memory
python -c "
from core.session import Session
from unittest.mock import MagicMock

session = Session(file_path='test.csv')
result  = MagicMock()
result.analysis_name = 'Pareto Analysis'
result.analysis_id   = 'pareto'
result.interpretation = 'Smart TV dominasi 29%.'
result.data = {}

session.add('Produk mana paling profit?', result, 'Return rate Smart TV naik 23%')
assert len(session.entries) == 1
assert 'Smart TV' in session.context_for_planner()
print('✅ Session memory ok:', session.context_for_planner())
"

# Excel dengan guardrail
python -c "
import pandas as pd, numpy as np
from unittest.mock import MagicMock
from analysis.guardrails import check_assumptions
from analysis.confidence import calculate_confidence
from exporters.excel_exporter import export_excel

df = pd.DataFrame({'revenue': np.random.exponential(1000,100), 'units': range(100)})
profile = MagicMock()
profile.numeric_columns     = ['revenue','units']
profile.categorical_columns = []; profile.date_columns = []
profile.row_count = 100; profile.missing_pct = 0.0
profile.columns = ['revenue','units']

guard = check_assumptions('regression_linear', df, {'target':'revenue'}, profile)

result = MagicMock()
result.success = True; result.analysis_id = 'regression_linear'
result.analysis_name = 'Linear Regression'
result.summary = {'R2': 0.45}; result.interpretation = 'Test.'
result.data = {'r2_score': 0.45}

score, reasons = calculate_confidence(result, guard, profile, 100)
result.confidence_score = score; result.confidence_reasons = reasons

path = export_excel(
    results=[result], profile=profile,
    file_path='/tmp/test_merged.xlsx',
    guardrails={'regression_linear': guard},
)
from openpyxl import load_workbook
wb = load_workbook(path)
assert 'Data Quality' in wb.sheetnames
print('✅ Excel with guardrail ok, sheets:', wb.sheetnames)
"
```

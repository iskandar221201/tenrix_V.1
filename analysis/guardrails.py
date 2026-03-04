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
        "anomaly_isolation_forest": _check_anomaly,
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
    target     = params.get("target") or params.get("target_column") or (
        profile.numeric_columns[0] if hasattr(profile, 'numeric_columns') and profile.numeric_columns else None
    )
    features   = params.get("features") or params.get("feature_columns") or (
        getattr(profile, 'numeric_columns', [])[:5]
    )

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
    if min_required > 0 and len(y) < min_required:
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
    target     = params.get("target") or params.get("target_column")
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
    group_col  = params.get("groupby") or params.get("group_column") or params.get("focus_column")
    value_col  = params.get("target") or params.get("target_column") or (
        profile.numeric_columns[0] if hasattr(profile, 'numeric_columns') and profile.numeric_columns else None
    )

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
    num_cols = getattr(profile, 'numeric_columns', [])
    for col in num_cols[:2]:
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
    features  = params.get("features") or params.get("feature_columns") or (
        getattr(profile, 'numeric_columns', [])[:5]
    )
    num_feats = [f for f in features if f in df.columns]
    if not num_feats:
        return violations

    stds = df[num_feats].std()
    if stds.min() > 0 and stds.max() / stds.min() > 10:
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
        if len(series) < 3:
            continue
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
    date_col   = params.get("date_col") or params.get("date_column") or (
        profile.date_columns[0] if hasattr(profile, 'date_columns') and profile.date_columns else None
    )
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

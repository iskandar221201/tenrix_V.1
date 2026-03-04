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
    missing_pct = getattr(profile, "missing_pct", 0) or 0
    if missing_pct > 0.50:
        score -= 0.30; reasons.append(f"Missing values tinggi ({missing_pct*100:.0f}%)")
    elif missing_pct > 0.20:
        score -= 0.15; reasons.append(f"Missing values moderat ({missing_pct*100:.0f}%)")

    # Guardrail violations
    if guardrail and hasattr(guardrail, 'violations'):
        violations = [v for v in guardrail.violations if not v.passed]
        if violations:
            penalty = min(0.10 * len(violations), 0.35)
            score  -= penalty
            reasons.append(f"{len(violations)} asumsi statistik tidak terpenuhi")

    # Model metrics
    data = getattr(result, 'data', None) or {}
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

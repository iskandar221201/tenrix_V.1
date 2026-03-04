from enum import Enum
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from analysis.methodology import METHODOLOGY_REGISTRY
from utils.logger import get_logger

logger = get_logger(__name__)


class ValidationStatus(Enum):
    OK         = "ok"
    WARNING    = "warning"
    PREPROCESS = "preprocess"
    BLOCKED    = "blocked"


@dataclass
class ValidationResult:
    status: ValidationStatus
    user_message: str
    warning_context: str   # injected into AI interpretation prompt
    suggestions: list[str] = field(default_factory=list)  # alternative analysis_ids if BLOCKED


def validate(analysis_id: str, df: pd.DataFrame, params: dict = None) -> ValidationResult:
    """Validate one analysis. Never raises."""
    try:
        if analysis_id not in METHODOLOGY_REGISTRY:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                user_message=f"Unknown analysis: {analysis_id}",
                warning_context="", suggestions=[],
            )

        methodology = METHODOLOGY_REGISTRY[analysis_id]
        row_count = len(df)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
        datetime_cols = _detect_datetime_cols(df)

        # Check minimum rows
        if row_count < methodology.min_rows:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                user_message=f"Need at least {methodology.min_rows} rows (have {row_count}).",
                warning_context=f"Dataset has only {row_count} rows, minimum is {methodology.min_rows}.",
                suggestions=["descriptive_stats"],
            )

        # Analysis-specific validation
        return _validate_specific(
            analysis_id, df, params or {}, numeric_cols, categorical_cols, datetime_cols, row_count
        )

    except Exception as e:
        logger.error(f"Validation error for {analysis_id}: {e}")
        return ValidationResult(
            status=ValidationStatus.WARNING,
            user_message=f"Could not fully validate: {e}",
            warning_context=str(e),
        )


def validate_all(df: pd.DataFrame) -> dict[str, ValidationResult]:
    """Validate all 23 analyses. Returns {analysis_id: ValidationResult}."""
    results = {}
    for analysis_id in METHODOLOGY_REGISTRY:
        results[analysis_id] = validate(analysis_id, df)
    return results


def _detect_datetime_cols(df: pd.DataFrame) -> list[str]:
    """Detect columns that are or can be parsed as datetime."""
    dt_cols = df.select_dtypes(include=["datetime64", "datetimetz"]).columns.tolist()
    for col in df.select_dtypes(include=["object", "string"]).columns:
        try:
            sample = df[col].dropna().head(20)
            if len(sample) > 0:
                pd.to_datetime(sample, format="mixed")
                dt_cols.append(col)
        except (ValueError, TypeError):
            pass
    return dt_cols


def _has_binary_column(df: pd.DataFrame) -> bool:
    """Check if any column has exactly 2 unique non-null values."""
    for col in df.columns:
        nunique = df[col].dropna().nunique()
        if nunique == 2:
            return True
    return False


def _has_transactional_format(df: pd.DataFrame) -> bool:
    """Check if data looks transactional (transaction_id + item columns)."""
    cols_lower = {c.lower().replace("_", "").replace(" ", ""): c for c in df.columns}
    has_transaction = any(
        kw in name for name in cols_lower
        for kw in ["transactionid", "orderid", "basketid", "invoiceno", "invoiceid", "tid"]
    )
    has_item = any(
        kw in name for name in cols_lower
        for kw in ["item", "product", "productname", "itemname", "description", "stockcode"]
    )
    return has_transaction and has_item


def _has_duration_event(df: pd.DataFrame) -> bool:
    """Check if data has duration + binary event columns for survival analysis."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    has_duration = False
    has_event = False

    for col in numeric_cols:
        vals = df[col].dropna()
        if len(vals) == 0:
            continue
        if vals.min() >= 0 and vals.nunique() > 2:
            has_duration = True
        if set(vals.unique()).issubset({0, 1, 0.0, 1.0}):
            has_event = True

    return has_duration and has_event


def _has_cohort_columns(df: pd.DataFrame) -> bool:
    """Check if data has user_id + date columns for cohort analysis."""
    datetime_cols = _detect_datetime_cols(df)
    if len(datetime_cols) < 1:
        return False

    # Need at least one ID-like column
    for col in df.columns:
        if df[col].nunique() > 1 and df[col].nunique() < len(df) * 0.9:
            return True

    return False


def _validate_specific(
    analysis_id: str, df: pd.DataFrame, params: dict,
    numeric_cols: list, categorical_cols: list, datetime_cols: list, row_count: int,
) -> ValidationResult:
    """Per-analysis validation logic."""

    # --- Time series analyses ---
    if analysis_id in ("time_series_arima", "time_series_prophet", "granger_causality"):
        if not datetime_cols:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                user_message="No datetime column found. Time series analysis requires dates.",
                warning_context="No datetime column detected.",
                suggestions=["descriptive_stats", "correlation"],
            )
        if len(numeric_cols) < 1:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                user_message="No numeric column found for time series target.",
                warning_context="No numeric columns.",
                suggestions=["descriptive_stats"],
            )

    # --- Regression logistic ---
    if analysis_id == "regression_logistic":
        if not _has_binary_column(df):
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                user_message="No binary target column found. Logistic regression needs a 0/1 target.",
                warning_context="No binary column found.",
                suggestions=["regression_linear"],
            )

    # --- Survival ---
    if analysis_id == "survival_kaplan_meier":
        if not _has_duration_event(df):
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                user_message="No duration + event columns found. Need positive numeric duration and binary event.",
                warning_context="Missing survival data columns.",
                suggestions=["descriptive_stats"],
            )

    # --- Market basket ---
    if analysis_id == "market_basket":
        if not _has_transactional_format(df):
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                user_message="Data is not in transactional format. Need transaction_id + item columns.",
                warning_context="No transactional format detected.",
                suggestions=["chi_square", "correlation"],
            )

    # --- Cohort ---
    if analysis_id == "cohort":
        if not _has_cohort_columns(df):
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                user_message="No user_id + date columns found for cohort analysis.",
                warning_context="Missing cohort columns.",
                suggestions=["descriptive_stats"],
            )

    # --- t-test, mann_whitney: PREPROCESS if group column has >2 groups ---
    if analysis_id in ("ttest", "mann_whitney"):
        group_col = params.get("group_column")
        if group_col and group_col in df.columns:
            n_groups = df[group_col].dropna().nunique()
            if n_groups > 2:
                return ValidationResult(
                    status=ValidationStatus.PREPROCESS,
                    user_message=f"Group column '{group_col}' has {n_groups} groups (need exactly 2).",
                    warning_context=f"Group column has {n_groups} groups, analysis expects 2.",
                    suggestions=["anova"],
                )

    # --- Numeric column checks ---
    if analysis_id in ("regression_linear", "regression_polynomial", "pca", "tsne", "umap",
                        "clustering_kmeans", "clustering_dbscan", "clustering_hierarchical",
                        "anomaly_isolation_forest", "anomaly_zscore", "correlation"):
        if len(numeric_cols) < 2:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                user_message="Need at least 2 numeric columns.",
                warning_context="Insufficient numeric columns.",
                suggestions=["descriptive_stats"],
            )

    # --- Dimensionality: need 5+ numeric columns ideally ---
    if analysis_id in ("pca", "tsne", "umap"):
        if len(numeric_cols) < 3:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                user_message="Need at least 3 numeric columns for dimensionality reduction.",
                warning_context="Too few numeric columns.",
                suggestions=["clustering_kmeans", "correlation"],
            )

    # --- Chi-square: needs categorical columns ---
    if analysis_id == "chi_square":
        if len(categorical_cols) < 2:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                user_message="Need at least 2 categorical columns for chi-square test.",
                warning_context="Insufficient categorical columns.",
                suggestions=["correlation", "ttest"],
            )

    # --- ANOVA: needs categorical with 3+ groups + numeric ---
    if analysis_id == "anova":
        has_group = any(df[c].nunique() >= 3 for c in categorical_cols) if categorical_cols else False
        if not has_group:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                user_message="Need a categorical column with 3+ groups for ANOVA.",
                warning_context="No suitable grouping column.",
                suggestions=["ttest", "mann_whitney"],
            )

    # --- General warnings ---
    if row_count < 100:
        return ValidationResult(
            status=ValidationStatus.WARNING,
            user_message=f"Small dataset ({row_count} rows). Results may be unreliable.",
            warning_context=f"Small sample size: {row_count} rows.",
        )

    if analysis_id.startswith("clustering_") and row_count < 200:
        return ValidationResult(
            status=ValidationStatus.WARNING,
            user_message=f"Clustering works best with 200+ rows (have {row_count}).",
            warning_context=f"Small sample for clustering: {row_count} rows.",
        )

    return ValidationResult(
        status=ValidationStatus.OK,
        user_message="Ready to run.",
        warning_context="",
    )

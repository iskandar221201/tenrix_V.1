import pandas as pd
import numpy as np
from dataclasses import dataclass
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CleaningIssue:
    column: str
    issue_type: str      # "missing_values"|"wrong_dtype"|"duplicates"|"outliers"
    severity: str        # "high"|"medium"|"low"
    count: int
    auto_fixable: bool
    fix_description: str


def detect_issues(df: pd.DataFrame) -> list[CleaningIssue]:
    """Detect issues. Never modifies df."""
    issues = []

    # Check for duplicate rows
    dup_count = df.duplicated().sum()
    if dup_count > 0:
        issues.append(CleaningIssue(
            column="(all)", issue_type="duplicates",
            severity="medium" if dup_count < len(df) * 0.1 else "high",
            count=int(dup_count), auto_fixable=True,
            fix_description=f"Remove {dup_count} duplicate rows",
        ))

    for col in df.columns:
        # Missing values
        missing = df[col].isna().sum()
        if missing > 0:
            pct = missing / len(df)
            severity = "high" if pct > 0.3 else ("medium" if pct > 0.1 else "low")
            if df[col].dtype in ("float64", "int64", "float32", "int32"):
                fix = f"Fill {missing} missing values with median"
                auto_fixable = True
            else:
                fix = f"Fill {missing} missing values with mode"
                auto_fixable = True
            issues.append(CleaningIssue(
                column=col, issue_type="missing_values",
                severity=severity, count=int(missing),
                auto_fixable=auto_fixable, fix_description=fix,
            ))

        # Outliers (numeric columns only)
        if pd.api.types.is_numeric_dtype(df[col]) and len(df[col].dropna()) > 10:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                outlier_count = int(((df[col] < lower) | (df[col] > upper)).sum())
                if outlier_count > 0:
                    issues.append(CleaningIssue(
                        column=col, issue_type="outliers",
                        severity="low", count=outlier_count,
                        auto_fixable=False,
                        fix_description=f"{outlier_count} outliers detected (IQR method)",
                    ))

    return issues


def apply_fix(df: pd.DataFrame, issue: CleaningIssue) -> pd.DataFrame:
    """Apply one fix. Returns new DataFrame."""
    df = df.copy()

    if issue.issue_type == "duplicates":
        df = df.drop_duplicates().reset_index(drop=True)

    elif issue.issue_type == "missing_values":
        if pd.api.types.is_numeric_dtype(df[issue.column]):
            df[issue.column] = df[issue.column].fillna(df[issue.column].median())
        else:
            mode_val = df[issue.column].mode()
            if len(mode_val) > 0:
                df[issue.column] = df[issue.column].fillna(mode_val.iloc[0])

    return df


def apply_all_fixes(df: pd.DataFrame, issues: list[CleaningIssue]) -> tuple:
    """Apply all auto-fixable issues. Returns (new_df, fix_summary_dict)."""
    new_df = df.copy()
    fix_summary = {"applied": [], "skipped": []}

    for issue in issues:
        if issue.auto_fixable:
            new_df = apply_fix(new_df, issue)
            fix_summary["applied"].append(issue.fix_description)
        else:
            fix_summary["skipped"].append(issue.fix_description)

    return new_df, fix_summary

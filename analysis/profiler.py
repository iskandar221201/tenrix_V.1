import pandas as pd
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)


def profile(df: pd.DataFrame) -> dict:
    """Generate data profile dict with row_count, col_count, quality_score, column details."""
    try:
        row_count = len(df)
        col_count = len(df.columns)

        # Column details
        columns = {}
        total_missing = 0
        for col in df.columns:
            col_info = {
                "dtype": str(df[col].dtype),
                "missing": int(df[col].isna().sum()),
                "missing_pct": round(df[col].isna().mean() * 100, 1),
                "unique": int(df[col].nunique()),
            }
            total_missing += col_info["missing"]

            if pd.api.types.is_numeric_dtype(df[col]):
                vals = df[col].dropna()
                if len(vals) > 0:
                    col_info["mean"] = float(vals.mean())
                    col_info["std"] = float(vals.std())
                    col_info["min"] = float(vals.min())
                    col_info["max"] = float(vals.max())
                    col_info["median"] = float(vals.median())
                col_info["type"] = "numeric"
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                col_info["type"] = "datetime"
                vals = df[col].dropna()
                if len(vals) > 0:
                    col_info["min"] = str(vals.min())
                    col_info["max"] = str(vals.max())
            else:
                col_info["type"] = "categorical"
                top = df[col].value_counts().head(5)
                col_info["top_values"] = {str(k): int(v) for k, v in top.items()}

            columns[col] = col_info

        # Quality score (0-100)
        total_cells = row_count * col_count
        missing_score = (1 - total_missing / total_cells) * 100 if total_cells > 0 else 100
        dup_score = (1 - df.duplicated().sum() / row_count) * 100 if row_count > 0 else 100
        quality_score = round((missing_score * 0.7 + dup_score * 0.3), 1)
        quality_score = max(0, min(100, quality_score))

        # Sample rows
        sample_rows = df.head(5).to_dict(orient="records")

        return {
            "row_count": row_count,
            "col_count": col_count,
            "quality_score": quality_score,
            "total_missing": total_missing,
            "total_missing_pct": round(total_missing / total_cells * 100, 1) if total_cells > 0 else 0,
            "duplicate_rows": int(df.duplicated().sum()),
            "numeric_columns": len(df.select_dtypes(include=[np.number]).columns),
            "categorical_columns": len(df.select_dtypes(include=["object", "category", "string"]).columns),
            "columns": columns,
            "sample_rows": sample_rows,
        }
    except Exception as e:
        logger.error(f"Profiling failed: {e}")
        return {
            "row_count": len(df),
            "col_count": len(df.columns),
            "quality_score": 0,
            "error": str(e),
            "columns": {},
        }

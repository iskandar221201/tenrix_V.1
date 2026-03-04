import pandas as pd
import numpy as np
import plotly.graph_objects as go
from analysis.statistics import AnalysisResult
from analysis.methodology import METHODOLOGY_REGISTRY
from utils.logger import get_logger

logger = get_logger(__name__)


def run_pareto(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        cat_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        category_col = params.get("group_column") or params.get("target_column")
        value_col = params.get("feature_columns", [None])[0] if params.get("feature_columns") else None

        if not category_col and cat_cols:
            category_col = cat_cols[0]
        if not value_col and numeric_cols:
            value_col = numeric_cols[0]

        if not category_col or not value_col:
            return AnalysisResult(
                analysis_name="Pareto Analysis (80/20)", analysis_id="pareto",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["pareto"],
                interpretation=None, warning=None, error="Need category and value columns",
            )

        grouped = df.groupby(category_col)[value_col].sum().sort_values(ascending=False)
        total = grouped.sum()
        cumulative = grouped.cumsum() / total * 100

        # Find 80% threshold
        threshold_idx = (cumulative >= 80).idxmax() if (cumulative >= 80).any() else cumulative.index[-1]
        items_80 = list(cumulative[cumulative <= 80].index)
        if len(items_80) < len(cumulative):
            items_80.append(threshold_idx)

        summary = {
            "Category Column": category_col,
            "Value Column": value_col,
            "Total Categories": len(grouped),
            "80% Threshold Items": len(items_80),
            "Top Category": f"{grouped.index[0]} ({grouped.values[0]:.0f})",
        }

        fig = go.Figure()
        fig.add_trace(go.Bar(x=grouped.index.astype(str), y=grouped.values, name="Value"))
        fig.add_trace(go.Scatter(x=cumulative.index.astype(str), y=cumulative.values,
                                 name="Cumulative %", yaxis="y2", mode="lines+markers"))
        fig.add_hline(y=80, line_dash="dash", line_color="red", yref="y2")
        fig.update_layout(
            title="Pareto Analysis (80/20)",
            xaxis_title=category_col, yaxis_title=value_col,
            yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 105]),
        )

        top_items = []
        for label, val in grouped.head(10).items():
            top_items.append({
                "label": str(label),
                "value": float(val),
                "pct": float(val / total * 100),
                "cumulative_pct": float(cumulative[label])
            })

        data = {
            "items_80_pct": len(items_80),
            "total_categories": len(grouped),
            "top_items": top_items
        }

        return AnalysisResult(
            analysis_name="Pareto Analysis (80/20)", analysis_id="pareto",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["pareto"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"pareto failed: {e}")
        return AnalysisResult(
            analysis_name="Pareto Analysis (80/20)", analysis_id="pareto",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["pareto"],
            interpretation=None, warning=None, error=str(e),
        )


def run_cohort(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        date_cols = []
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                date_cols.append(col)
        for col in df.select_dtypes(include=["object", "string"]).columns:
            try:
                pd.to_datetime(df[col].dropna().head(20), format="mixed")
                date_cols.append(col)
            except (ValueError, TypeError):
                pass

        if len(date_cols) < 1:
            return AnalysisResult(
                analysis_name="Cohort Analysis", analysis_id="cohort",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["cohort"],
                interpretation=None, warning=None, error="Need date columns for cohort analysis",
            )

        # Find user_id column
        user_col = params.get("group_column")
        if not user_col:
            for col in df.columns:
                if col not in date_cols and df[col].nunique() > 1:
                    user_col = col
                    break

        activity_col = date_cols[0]

        if not user_col:
            return AnalysisResult(
                analysis_name="Cohort Analysis", analysis_id="cohort",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["cohort"],
                interpretation=None, warning=None, error="Need user ID column",
            )

        cohort_df = df[[user_col, activity_col]].copy()
        cohort_df[activity_col] = pd.to_datetime(cohort_df[activity_col], format="mixed")

        # Assign cohort month
        cohort_df["cohort"] = cohort_df.groupby(user_col)[activity_col].transform("min").dt.to_period("M")
        cohort_df["activity_period"] = cohort_df[activity_col].dt.to_period("M")
        cohort_df["period_number"] = (cohort_df["activity_period"] - cohort_df["cohort"]).apply(lambda x: x.n)

        # Retention table
        cohort_sizes = cohort_df.groupby("cohort")[user_col].nunique()
        retention = cohort_df.groupby(["cohort", "period_number"])[user_col].nunique().unstack(fill_value=0)
        retention = retention.div(cohort_sizes, axis=0) * 100

        summary = {
            "User Column": user_col,
            "Activity Column": activity_col,
            "Total Users": int(cohort_df[user_col].nunique()),
            "Cohorts": len(cohort_sizes),
        }

        # Heatmap
        fig = go.Figure(go.Heatmap(
            z=retention.values,
            x=[f"Period {i}" for i in range(retention.shape[1])],
            y=[str(c) for c in retention.index],
            colorscale="Blues",
            text=np.round(retention.values, 1),
            texttemplate="%{text}%",
        ))
        fig.update_layout(title="Cohort Retention Heatmap",
                          xaxis_title="Period", yaxis_title="Cohort")

        data = {"cohorts": len(cohort_sizes), "total_users": int(cohort_df[user_col].nunique())}

        return AnalysisResult(
            analysis_name="Cohort Analysis", analysis_id="cohort",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["cohort"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"cohort failed: {e}")
        return AnalysisResult(
            analysis_name="Cohort Analysis", analysis_id="cohort",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["cohort"],
            interpretation=None, warning=None, error=str(e),
        )

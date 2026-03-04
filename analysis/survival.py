import pandas as pd
import numpy as np
import plotly.graph_objects as go
from analysis.statistics import AnalysisResult
from analysis.methodology import METHODOLOGY_REGISTRY
from utils.logger import get_logger

logger = get_logger(__name__)


def run_kaplan_meier(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        from lifelines import KaplanMeierFitter
        from lifelines.statistics import logrank_test

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        duration_col = params.get("target_column")
        event_col = None
        group_col = params.get("group_column")

        # Auto-detect duration and event columns
        if not duration_col:
            for col in numeric_cols:
                vals = df[col].dropna()
                if len(vals) > 0 and vals.min() >= 0 and vals.nunique() > 2:
                    duration_col = col
                    break

        for col in numeric_cols:
            if col != duration_col:
                vals = df[col].dropna()
                if set(vals.unique()).issubset({0, 1, 0.0, 1.0}):
                    event_col = col
                    break

        if not duration_col or not event_col:
            return AnalysisResult(
                analysis_name="Kaplan-Meier Survival Analysis",
                analysis_id="survival_kaplan_meier",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["survival_kaplan_meier"],
                interpretation=None, warning=None, error="Need duration (positive numeric) and event (binary) columns",
            )

        clean = df[[duration_col, event_col]].dropna()
        T = clean[duration_col].values
        E = clean[event_col].values.astype(int)

        kmf = KaplanMeierFitter()
        kmf.fit(T, E)

        median_survival = kmf.median_survival_time_

        summary = {
            "Duration Column": duration_col,
            "Event Column": event_col,
            "Total Observations": len(T),
            "Events Observed": int(E.sum()),
            "Median Survival": f"{median_survival:.2f}" if not np.isinf(median_survival) else "Not reached",
        }

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=kmf.survival_function_.index,
            y=kmf.survival_function_.iloc[:, 0],
            name="Survival", mode="lines",
        ))
        ci = kmf.confidence_interval_survival_function_
        if ci is not None and len(ci.columns) >= 2:
            fig.add_trace(go.Scatter(
                x=ci.index, y=ci.iloc[:, 0],
                name="Lower CI", mode="lines", line=dict(dash="dash"), opacity=0.3,
            ))
            fig.add_trace(go.Scatter(
                x=ci.index, y=ci.iloc[:, 1],
                name="Upper CI", mode="lines", line=dict(dash="dash"), opacity=0.3, fill="tonexty",
            ))
        fig.update_layout(title="Kaplan-Meier Survival Curve",
                          xaxis_title="Time", yaxis_title="Survival Probability")

        data = {"median_survival": float(median_survival) if not np.isinf(median_survival) else None,
                "events": int(E.sum()), "observations": len(T)}

        return AnalysisResult(
            analysis_name="Kaplan-Meier Survival Analysis",
            analysis_id="survival_kaplan_meier",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["survival_kaplan_meier"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"kaplan_meier failed: {e}")
        return AnalysisResult(
            analysis_name="Kaplan-Meier Survival Analysis",
            analysis_id="survival_kaplan_meier",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["survival_kaplan_meier"],
            interpretation=None, warning=None, error=str(e),
        )

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
from sklearn.ensemble import IsolationForest
from analysis.statistics import AnalysisResult
from analysis.methodology import METHODOLOGY_REGISTRY
from utils.logger import get_logger

logger = get_logger(__name__)


def run_isolation_forest(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_df = df.select_dtypes(include=[np.number]).dropna()
        if numeric_df.shape[1] < 2:
            return AnalysisResult(
                analysis_name="Anomaly Detection (Isolation Forest)",
                analysis_id="anomaly_isolation_forest",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["anomaly_isolation_forest"],
                interpretation=None, warning=None, error="Need at least 2 numeric columns",
            )

        model = IsolationForest(contamination="auto", random_state=42)
        predictions = model.fit_predict(numeric_df)
        scores = model.decision_function(numeric_df)

        anomaly_count = int((predictions == -1).sum())
        anomaly_pct = anomaly_count / len(predictions) * 100

        summary = {
            "Total Rows": len(predictions),
            "Anomalies Found": anomaly_count,
            "Anomaly Rate": f"{anomaly_pct:.1f}%",
        }

        charts = []
        # Score histogram
        fig1 = go.Figure(go.Histogram(x=scores, nbinsx=50))
        fig1.update_layout(title="Anomaly Scores Distribution", xaxis_title="Score", yaxis_title="Count")
        charts.append(fig1)

        # Scatter with anomalies highlighted
        if numeric_df.shape[1] >= 2:
            cols = numeric_df.columns[:2]
            fig2 = go.Figure()
            normal = predictions == 1
            fig2.add_trace(go.Scatter(x=numeric_df[cols[0]][normal], y=numeric_df[cols[1]][normal],
                                       mode="markers", name="Normal", marker=dict(color="blue")))
            fig2.add_trace(go.Scatter(x=numeric_df[cols[0]][~normal], y=numeric_df[cols[1]][~normal],
                                       mode="markers", name="Anomaly", marker=dict(color="red", size=10)))
            fig2.update_layout(title="Anomalies", xaxis_title=cols[0], yaxis_title=cols[1])
            charts.append(fig2)

        # Top anomalies
        top_indices = np.argsort(scores)[:10]
        top_anomalies = []
        for idx in top_indices:
            top_anomalies.append({
                "index": int(numeric_df.index[idx]),
                "anomaly_score": float(scores[idx])
            })

        data = {"anomaly_count": anomaly_count, "anomaly_pct": float(anomaly_pct),
                "top_anomalies": top_anomalies}

        return AnalysisResult(
            analysis_name="Anomaly Detection (Isolation Forest)",
            analysis_id="anomaly_isolation_forest",
            success=True, data=data, summary=summary, charts=charts,
            methodology=METHODOLOGY_REGISTRY["anomaly_isolation_forest"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"isolation_forest failed: {e}")
        return AnalysisResult(
            analysis_name="Anomaly Detection (Isolation Forest)",
            analysis_id="anomaly_isolation_forest",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["anomaly_isolation_forest"],
            interpretation=None, warning=None, error=str(e),
        )


def run_zscore(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.shape[1] < 1:
            return AnalysisResult(
                analysis_name="Anomaly Detection (Z-Score)",
                analysis_id="anomaly_zscore",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["anomaly_zscore"],
                interpretation=None, warning=None, error="Need at least 1 numeric column",
            )

        z_scores = numeric_df.apply(lambda x: np.abs(stats.zscore(x, nan_policy="omit")))
        anomalies = (z_scores > 3).any(axis=1)
        anomaly_count = int(anomalies.sum())

        summary = {"Total Rows": len(df), "Anomalies (|z|>3)": anomaly_count}
        per_col = {}
        for col in z_scores.columns:
            col_anom = int((z_scores[col] > 3).sum())
            if col_anom > 0:
                summary[f"Anomalies in {col}"] = col_anom
                per_col[col] = col_anom

        charts = []
        col = numeric_df.columns[0]
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=numeric_df[col].dropna(), nbinsx=50, name=col))
        mean_val = numeric_df[col].mean()
        std_val = numeric_df[col].std()
        fig.add_vline(x=mean_val + 3 * std_val, line_dash="dash", line_color="red")
        fig.add_vline(x=mean_val - 3 * std_val, line_dash="dash", line_color="red")
        fig.update_layout(title=f"Z-Score Analysis: {col}", xaxis_title=col, yaxis_title="Count")
        charts.append(fig)

        # Top anomalies by max Z-score
        max_z = z_scores.max(axis=1)
        top_indices = max_z.sort_values(ascending=False).head(10).index
        top_anomalies = []
        for idx in top_indices:
            top_anomalies.append({
                "index": int(idx),
                "anomaly_score": float(max_z.loc[idx])
            })

        data = {"anomaly_count": anomaly_count, "per_column": per_col,
                "top_anomalies": top_anomalies}

        return AnalysisResult(
            analysis_name="Anomaly Detection (Z-Score)",
            analysis_id="anomaly_zscore",
            success=True, data=data, summary=summary, charts=charts,
            methodology=METHODOLOGY_REGISTRY["anomaly_zscore"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"zscore failed: {e}")
        return AnalysisResult(
            analysis_name="Anomaly Detection (Z-Score)",
            analysis_id="anomaly_zscore",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["anomaly_zscore"],
            interpretation=None, warning=None, error=str(e),
        )

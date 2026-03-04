import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from analysis.statistics import AnalysisResult
from analysis.methodology import METHODOLOGY_REGISTRY
from utils.logger import get_logger

logger = get_logger(__name__)


def run_pca(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_df = df.select_dtypes(include=[np.number]).dropna()
        if numeric_df.shape[1] < 3:
            return AnalysisResult(
                analysis_name="PCA", analysis_id="pca",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["pca"],
                interpretation=None, warning=None, error="Need at least 3 numeric columns",
            )

        scaler = StandardScaler()
        X = scaler.fit_transform(numeric_df)
        n_components = min(numeric_df.shape[1], 10)

        pca = PCA(n_components=n_components)
        X_pca = pca.fit_transform(X)

        explained = pca.explained_variance_ratio_

        summary = {
            "Components": n_components,
            "Total Variance Explained": f"{sum(explained):.4f}",
        }
        for i in range(min(5, n_components)):
            summary[f"PC{i+1} Variance"] = f"{explained[i]:.4f}"

        charts = []
        # Scree plot
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(x=[f"PC{i+1}" for i in range(n_components)],
                              y=explained, name="Individual"))
        fig1.add_trace(go.Scatter(x=[f"PC{i+1}" for i in range(n_components)],
                                  y=np.cumsum(explained), name="Cumulative", mode="lines+markers"))
        fig1.update_layout(title="PCA Scree Plot", xaxis_title="Component", yaxis_title="Variance Explained")
        charts.append(fig1)

        # 2D biplot
        fig2 = go.Figure(go.Scatter(x=X_pca[:, 0], y=X_pca[:, 1], mode="markers"))
        fig2.update_layout(title="PCA 2D Projection", xaxis_title="PC1", yaxis_title="PC2")
        charts.append(fig2)

        data = {"explained_variance": [float(v) for v in explained], "n_components": n_components}

        return AnalysisResult(
            analysis_name="PCA", analysis_id="pca",
            success=True, data=data, summary=summary, charts=charts,
            methodology=METHODOLOGY_REGISTRY["pca"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"pca failed: {e}")
        return AnalysisResult(
            analysis_name="PCA", analysis_id="pca",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["pca"],
            interpretation=None, warning=None, error=str(e),
        )


def run_tsne(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_df = df.select_dtypes(include=[np.number]).dropna()
        if numeric_df.shape[1] < 3:
            return AnalysisResult(
                analysis_name="t-SNE", analysis_id="tsne",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["tsne"],
                interpretation=None, warning=None, error="Need at least 3 numeric columns",
            )

        sample = numeric_df.head(2000)  # Limit for performance
        scaler = StandardScaler()
        X = scaler.fit_transform(sample)

        perplexity = min(30, len(X) - 1)
        tsne = TSNE(n_components=2, perplexity=perplexity, random_state=42)
        X_2d = tsne.fit_transform(X)

        summary = {
            "Samples": len(X),
            "Original Dimensions": numeric_df.shape[1],
            "Perplexity": perplexity,
        }

        fig = go.Figure(go.Scatter(x=X_2d[:, 0], y=X_2d[:, 1], mode="markers"))
        fig.update_layout(title="t-SNE 2D Visualization", xaxis_title="t-SNE 1", yaxis_title="t-SNE 2")

        data = {"samples": len(X), "perplexity": perplexity}

        return AnalysisResult(
            analysis_name="t-SNE", analysis_id="tsne",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["tsne"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"tsne failed: {e}")
        return AnalysisResult(
            analysis_name="t-SNE", analysis_id="tsne",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["tsne"],
            interpretation=None, warning=None, error=str(e),
        )


def run_umap(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_df = df.select_dtypes(include=[np.number]).dropna()
        if numeric_df.shape[1] < 3:
            return AnalysisResult(
                analysis_name="UMAP", analysis_id="umap",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["umap"],
                interpretation=None, warning=None, error="Need at least 3 numeric columns",
            )

        sample = numeric_df.head(5000)
        scaler = StandardScaler()
        X = scaler.fit_transform(sample)

        import umap as umap_lib
        n_neighbors = min(15, len(X) - 1)
        reducer = umap_lib.UMAP(n_components=2, n_neighbors=n_neighbors, random_state=42)
        X_2d = reducer.fit_transform(X)

        summary = {
            "Samples": len(X),
            "Original Dimensions": numeric_df.shape[1],
            "N Neighbors": n_neighbors,
        }

        fig = go.Figure(go.Scatter(x=X_2d[:, 0], y=X_2d[:, 1], mode="markers"))
        fig.update_layout(title="UMAP 2D Visualization", xaxis_title="UMAP 1", yaxis_title="UMAP 2")

        data = {"samples": len(X), "n_neighbors": n_neighbors}

        return AnalysisResult(
            analysis_name="UMAP", analysis_id="umap",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["umap"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"umap failed: {e}")
        return AnalysisResult(
            analysis_name="UMAP", analysis_id="umap",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["umap"],
            interpretation=None, warning=None, error=str(e),
        )

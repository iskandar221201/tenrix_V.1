import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
from scipy.cluster.hierarchy import linkage, fcluster
from analysis.statistics import AnalysisResult
from analysis.methodology import METHODOLOGY_REGISTRY
from utils.logger import get_logger

logger = get_logger(__name__)


def run_kmeans(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_df = df.select_dtypes(include=[np.number]).dropna()
        if numeric_df.shape[1] < 2:
            return AnalysisResult(
                analysis_name="K-Means Clustering", analysis_id="clustering_kmeans",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["clustering_kmeans"],
                interpretation=None, warning=None, error="Need at least 2 numeric columns",
            )

        scaler = StandardScaler()
        X = scaler.fit_transform(numeric_df)

        # Elbow method
        inertias = []
        K_range = range(2, min(11, len(X)))
        for k in K_range:
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            km.fit(X)
            inertias.append(km.inertia_)

        # Find optimal K using elbow heuristic
        best_k = 3
        if len(inertias) >= 3:
            diffs = np.diff(inertias)
            diffs2 = np.diff(diffs)
            if len(diffs2) > 0:
                best_k = int(np.argmax(diffs2) + 2)
                best_k = max(2, min(best_k, max(K_range) - 1))

        km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        labels = km.fit_predict(X)
        sil = silhouette_score(X, labels) if len(set(labels)) > 1 else 0

        summary = {
            "Optimal K": best_k,
            "Silhouette Score": f"{sil:.4f}",
        }
        for i in range(best_k):
            summary[f"Cluster {i} Size"] = int((labels == i).sum())

        charts = []
        # Elbow chart
        fig1 = go.Figure(go.Scatter(x=list(K_range), y=inertias, mode="lines+markers"))
        fig1.update_layout(title="Elbow Method", xaxis_title="K", yaxis_title="Inertia")
        charts.append(fig1)

        # 2D PCA scatter
        if X.shape[1] >= 2:
            pca = PCA(n_components=2)
            X_2d = pca.fit_transform(X)
            fig2 = go.Figure()
            for i in range(best_k):
                mask = labels == i
                fig2.add_trace(go.Scatter(x=X_2d[mask, 0], y=X_2d[mask, 1],
                                          mode="markers", name=f"Cluster {i}"))
            fig2.update_layout(title="K-Means Clusters (PCA)", xaxis_title="PC1", yaxis_title="PC2")
            charts.append(fig2)

        cluster_sizes = {int(i): int((labels == i).sum()) for i in range(best_k)}
        data = {"k": best_k, "silhouette": float(sil), "inertias": [float(i) for i in inertias],
                "cluster_sizes": cluster_sizes}

        return AnalysisResult(
            analysis_name="K-Means Clustering", analysis_id="clustering_kmeans",
            success=True, data=data, summary=summary, charts=charts,
            methodology=METHODOLOGY_REGISTRY["clustering_kmeans"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"kmeans failed: {e}")
        return AnalysisResult(
            analysis_name="K-Means Clustering", analysis_id="clustering_kmeans",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["clustering_kmeans"],
            interpretation=None, warning=None, error=str(e),
        )


def run_dbscan(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_df = df.select_dtypes(include=[np.number]).dropna()
        if numeric_df.shape[1] < 2:
            return AnalysisResult(
                analysis_name="DBSCAN Clustering", analysis_id="clustering_dbscan",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["clustering_dbscan"],
                interpretation=None, warning=None, error="Need at least 2 numeric columns",
            )

        scaler = StandardScaler()
        X = scaler.fit_transform(numeric_df)

        # Auto-tune eps using k-distance
        from sklearn.neighbors import NearestNeighbors
        nn = NearestNeighbors(n_neighbors=min(5, len(X) - 1))
        nn.fit(X)
        distances, _ = nn.kneighbors(X)
        k_dist = np.sort(distances[:, -1])
        eps = float(np.percentile(k_dist, 90))

        db = DBSCAN(eps=eps, min_samples=5)
        labels = db.fit_predict(X)

        n_clusters = len(set(labels) - {-1})
        n_noise = int((labels == -1).sum())

        summary = {
            "Clusters Found": n_clusters,
            "Noise Points": n_noise,
            "Epsilon": f"{eps:.4f}",
        }
        for i in range(n_clusters):
            summary[f"Cluster {i} Size"] = int((labels == i).sum())

        pca = PCA(n_components=2)
        X_2d = pca.fit_transform(X)
        fig = go.Figure()
        for i in sorted(set(labels)):
            mask = labels == i
            name = f"Cluster {i}" if i >= 0 else "Noise"
            fig.add_trace(go.Scatter(x=X_2d[mask, 0], y=X_2d[mask, 1],
                                      mode="markers", name=name))
        fig.update_layout(title="DBSCAN Clusters", xaxis_title="PC1", yaxis_title="PC2")

        cluster_sizes = {int(i): int((labels == i).sum()) for i in sorted(set(labels)) if i >= 0}
        data = {"n_clusters": n_clusters, "n_noise": n_noise, "eps": float(eps),
                "cluster_sizes": cluster_sizes}

        return AnalysisResult(
            analysis_name="DBSCAN Clustering", analysis_id="clustering_dbscan",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["clustering_dbscan"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"dbscan failed: {e}")
        return AnalysisResult(
            analysis_name="DBSCAN Clustering", analysis_id="clustering_dbscan",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["clustering_dbscan"],
            interpretation=None, warning=None, error=str(e),
        )


def run_hierarchical(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_df = df.select_dtypes(include=[np.number]).dropna()
        if numeric_df.shape[1] < 2:
            return AnalysisResult(
                analysis_name="Hierarchical Clustering", analysis_id="clustering_hierarchical",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["clustering_hierarchical"],
                interpretation=None, warning=None, error="Need at least 2 numeric columns",
            )

        # Limit for performance
        sample = numeric_df.head(500)
        scaler = StandardScaler()
        X = scaler.fit_transform(sample)

        Z = linkage(X, method="ward")

        # Auto-cut
        n_clusters = min(4, len(X) - 1)
        labels = fcluster(Z, n_clusters, criterion="maxclust")

        summary = {
            "Clusters": n_clusters,
            "Samples Used": len(X),
            "Linkage Method": "Ward",
        }
        for i in range(1, n_clusters + 1):
            summary[f"Cluster {i} Size"] = int((labels == i).sum())

        pca = PCA(n_components=2)
        X_2d = pca.fit_transform(X)
        fig = go.Figure()
        for i in range(1, n_clusters + 1):
            mask = labels == i
            fig.add_trace(go.Scatter(x=X_2d[mask, 0], y=X_2d[mask, 1],
                                      mode="markers", name=f"Cluster {i}"))
        fig.update_layout(title="Hierarchical Clustering", xaxis_title="PC1", yaxis_title="PC2")

        cluster_sizes = {int(i): int((labels == i).sum()) for i in range(1, n_clusters + 1)}
        data = {"n_clusters": n_clusters, "linkage_method": "ward", "cluster_sizes": cluster_sizes}

        return AnalysisResult(
            analysis_name="Hierarchical Clustering", analysis_id="clustering_hierarchical",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["clustering_hierarchical"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"hierarchical failed: {e}")
        return AnalysisResult(
            analysis_name="Hierarchical Clustering", analysis_id="clustering_hierarchical",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["clustering_hierarchical"],
            interpretation=None, warning=None, error=str(e),
        )

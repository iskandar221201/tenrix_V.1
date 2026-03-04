import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import (mean_squared_error, mean_absolute_error, r2_score,
                             accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, confusion_matrix, roc_curve)
from analysis.statistics import AnalysisResult
from analysis.methodology import METHODOLOGY_REGISTRY
from utils.logger import get_logger

logger = get_logger(__name__)


def run_linear_regression(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        target_col = params.get("target_column")
        feature_cols = params.get("feature_columns")

        if not target_col:
            target_col = numeric_cols[-1] if numeric_cols else None
        if not feature_cols:
            feature_cols = [c for c in numeric_cols if c != target_col]

        if not target_col or not feature_cols:
            return AnalysisResult(
                analysis_name="Linear Regression", analysis_id="regression_linear",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["regression_linear"],
                interpretation=None, warning=None, error="Need target and feature columns",
            )

        valid_features = [c for c in feature_cols if c in df.columns]
        clean = df[[target_col] + valid_features].dropna()
        X = clean[valid_features].values
        y = clean[target_col].values

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        r2 = r2_score(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)

        summary = {
            "Target": target_col,
            "Features": ", ".join(valid_features),
            "R-Squared": f"{r2:.4f}",
            "RMSE": f"{rmse:.4f}",
            "MAE": f"{mae:.4f}",
            "Train Size": len(X_train),
            "Test Size": len(X_test),
        }
        for i, col in enumerate(valid_features):
            summary[f"Coeff ({col})"] = f"{model.coef_[i]:.4f}"

        # Actual vs Predicted
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=y_test, y=y_pred, mode="markers", name="Predictions"))
        mn, mx = min(y_test.min(), y_pred.min()), max(y_test.max(), y_pred.max())
        fig.add_trace(go.Scatter(x=[mn, mx], y=[mn, mx], mode="lines", name="Perfect", line=dict(dash="dash")))
        fig.update_layout(title="Actual vs Predicted", xaxis_title="Actual", yaxis_title="Predicted")

        data = {"r2": float(r2), "rmse": float(rmse), "mae": float(mae),
                "coefficients": {c: float(model.coef_[i]) for i, c in enumerate(valid_features)},
                "intercept": float(model.intercept_)}

        return AnalysisResult(
            analysis_name="Linear Regression", analysis_id="regression_linear",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["regression_linear"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"linear_regression failed: {e}")
        return AnalysisResult(
            analysis_name="Linear Regression", analysis_id="regression_linear",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["regression_linear"],
            interpretation=None, warning=None, error=str(e),
        )


def run_logistic_regression(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        target_col = params.get("target_column")
        feature_cols = params.get("feature_columns")

        if not target_col:
            for c in numeric_cols:
                if set(df[c].dropna().unique()).issubset({0, 1, 0.0, 1.0}):
                    target_col = c
                    break

        if not target_col:
            return AnalysisResult(
                analysis_name="Logistic Regression", analysis_id="regression_logistic",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["regression_logistic"],
                interpretation=None, warning=None, error="No binary target found",
            )

        if not feature_cols:
            feature_cols = [c for c in numeric_cols if c != target_col]

        valid_features = [c for c in feature_cols if c in df.columns]
        clean = df[[target_col] + valid_features].dropna()
        X = clean[valid_features].values
        y = clean[target_col].values.astype(int)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = LogisticRegression(max_iter=1000, random_state=42)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_proba) if len(np.unique(y_test)) > 1 else 0

        summary = {
            "Target": target_col,
            "Accuracy": f"{acc:.4f}",
            "Precision": f"{prec:.4f}",
            "Recall": f"{rec:.4f}",
            "F1 Score": f"{f1:.4f}",
            "AUC-ROC": f"{auc:.4f}",
        }

        fpr, tpr, _ = roc_curve(y_test, y_proba)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=fpr, y=tpr, name=f"ROC (AUC={auc:.3f})"))
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(dash="dash"), name="Random"))
        fig.update_layout(title="ROC Curve", xaxis_title="FPR", yaxis_title="TPR")

        data = {"accuracy": float(acc), "precision": float(prec), "recall": float(rec),
                "f1": float(f1), "auc": float(auc),
                "coefficients": {c: float(model.coef_[0][i]) for i, c in enumerate(valid_features)}}

        return AnalysisResult(
            analysis_name="Logistic Regression", analysis_id="regression_logistic",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["regression_logistic"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"logistic_regression failed: {e}")
        return AnalysisResult(
            analysis_name="Logistic Regression", analysis_id="regression_logistic",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["regression_logistic"],
            interpretation=None, warning=None, error=str(e),
        )


def run_polynomial_regression(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        target_col = params.get("target_column")
        feature_col = params.get("feature_columns", [None])[0] if params.get("feature_columns") else None

        if not target_col and len(numeric_cols) >= 2:
            target_col = numeric_cols[-1]
        if not feature_col:
            feature_col = numeric_cols[0] if numeric_cols and numeric_cols[0] != target_col else None

        if not target_col or not feature_col:
            return AnalysisResult(
                analysis_name="Polynomial Regression", analysis_id="regression_polynomial",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["regression_polynomial"],
                interpretation=None, warning=None, error="Need target and feature column",
            )

        clean = df[[feature_col, target_col]].dropna()
        X = clean[feature_col].values.reshape(-1, 1)
        y = clean[target_col].values

        best_r2, best_degree = -np.inf, 2
        for degree in range(2, 5):
            poly = PolynomialFeatures(degree=degree)
            X_poly = poly.fit_transform(X)
            X_train, X_test, y_train, y_test = train_test_split(X_poly, y, test_size=0.2, random_state=42)
            model = LinearRegression()
            model.fit(X_train, y_train)
            r2 = r2_score(y_test, model.predict(X_test))
            if r2 > best_r2:
                best_r2 = r2
                best_degree = degree

        poly = PolynomialFeatures(degree=best_degree)
        X_poly = poly.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(X_poly, y, test_size=0.2, random_state=42)
        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))

        summary = {
            "Target": target_col,
            "Feature": feature_col,
            "Best Degree": best_degree,
            "R-Squared": f"{best_r2:.4f}",
            "RMSE": f"{rmse:.4f}",
        }

        X_sort = np.sort(X, axis=0)
        X_sort_poly = poly.transform(X_sort)
        y_curve = model.predict(X_sort_poly)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=X.flatten(), y=y, mode="markers", name="Data"))
        fig.add_trace(go.Scatter(x=X_sort.flatten(), y=y_curve, mode="lines", name=f"Degree {best_degree}"))
        fig.update_layout(title=f"Polynomial Regression (degree={best_degree})",
                          xaxis_title=feature_col, yaxis_title=target_col)

        data = {"r2": float(best_r2), "rmse": float(rmse), "degree": best_degree,
                "coefficients": {f"{feature_col}^{i}": float(model.coef_[i]) for i in range(1, best_degree + 1)}}

        return AnalysisResult(
            analysis_name="Polynomial Regression", analysis_id="regression_polynomial",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["regression_polynomial"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"polynomial_regression failed: {e}")
        return AnalysisResult(
            analysis_name="Polynomial Regression", analysis_id="regression_polynomial",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["regression_polynomial"],
            interpretation=None, warning=None, error=str(e),
        )

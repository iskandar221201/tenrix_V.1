import pandas as pd
import numpy as np
import plotly.graph_objects as go
from analysis.statistics import AnalysisResult
from analysis.methodology import METHODOLOGY_REGISTRY
from utils.logger import get_logger

logger = get_logger(__name__)


def _detect_date_target(df, params):
    """Auto-detect date and target columns."""
    date_col = params.get("date_column")
    target_col = params.get("target_column")

    if not date_col:
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                date_col = col
                break
        if not date_col:
            for col in df.select_dtypes(include=["object", "string"]).columns:
                try:
                    pd.to_datetime(df[col].dropna().head(20), format="mixed")
                    date_col = col
                    break
                except (ValueError, TypeError):
                    pass

    if not target_col:
        for col in df.select_dtypes(include=[np.number]).columns:
            if col != date_col:
                target_col = col
                break

    return date_col, target_col


def run_arima(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        date_col, target_col = _detect_date_target(df, params)
        if not date_col or not target_col:
            return AnalysisResult(
                analysis_name="ARIMA Forecast", analysis_id="time_series_arima",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["time_series_arima"],
                interpretation=None, warning=None, error="Need date and numeric target columns",
            )

        ts_df = df[[date_col, target_col]].dropna().copy()
        ts_df[date_col] = pd.to_datetime(ts_df[date_col], format="mixed")
        ts_df = ts_df.sort_values(date_col).set_index(date_col)
        series = ts_df[target_col]

        from statsmodels.tsa.stattools import adfuller
        from statsmodels.tsa.arima.model import ARIMA

        adf_stat, adf_p, _, _, _, _ = adfuller(series.dropna())

        # Auto ARIMA simple: try a few orders
        best_aic, best_order = np.inf, (1, 1, 1)
        for p in range(3):
            for d in range(2):
                for q in range(3):
                    try:
                        model = ARIMA(series, order=(p, d, q))
                        fit = model.fit()
                        if fit.aic < best_aic:
                            best_aic = fit.aic
                            best_order = (p, d, q)
                    except Exception:
                        pass

        model = ARIMA(series, order=best_order)
        fit = model.fit()
        forecast = fit.forecast(steps=30)
        conf = fit.get_forecast(steps=30).conf_int()

        rmse = np.sqrt(np.mean(fit.resid**2))

        summary = {
            "Target": target_col,
            "ARIMA Order": str(best_order),
            "AIC": f"{best_aic:.2f}",
            "RMSE": f"{rmse:.4f}",
            "ADF Statistic": f"{adf_stat:.4f}",
            "ADF P-Value": f"{adf_p:.6f}",
            "Forecast Periods": 30,
        }

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=series.index, y=series.values, name="Historical"))
        fig.add_trace(go.Scatter(x=forecast.index, y=forecast.values, name="Forecast"))
        if hasattr(conf, 'iloc'):
            fig.add_trace(go.Scatter(x=conf.index, y=conf.iloc[:, 0], name="Lower CI",
                                     line=dict(dash="dash"), opacity=0.3))
            fig.add_trace(go.Scatter(x=conf.index, y=conf.iloc[:, 1], name="Upper CI",
                                     line=dict(dash="dash"), opacity=0.3, fill="tonexty"))
        fig.update_layout(title="ARIMA Forecast", xaxis_title="Date", yaxis_title=target_col)

        forecast_values = []
        for ds, yhat in forecast.items():
            forecast_values.append({
                "ds": str(ds),
                "yhat": float(yhat),
                "yhat_lower": float(conf.loc[ds].iloc[0]) if hasattr(conf, "loc") else float(yhat),
                "yhat_upper": float(conf.loc[ds].iloc[1]) if hasattr(conf, "loc") else float(yhat)
            })

        peak_month = int(forecast.index.month[forecast.argmax()])
        low_month = int(forecast.index.month[forecast.argmin()])

        data = {
            "order": best_order,
            "aic": float(best_aic),
            "rmse": float(rmse),
            "peak_month": peak_month,
            "low_month": low_month,
            "forecast_values": forecast_values
        }

        return AnalysisResult(
            analysis_name="ARIMA Forecast", analysis_id="time_series_arima",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["time_series_arima"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"arima failed: {e}")
        return AnalysisResult(
            analysis_name="ARIMA Forecast", analysis_id="time_series_arima",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["time_series_arima"],
            interpretation=None, warning=None, error=str(e),
        )


def run_prophet(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        date_col, target_col = _detect_date_target(df, params)
        if not date_col or not target_col:
            return AnalysisResult(
                analysis_name="Prophet Forecast", analysis_id="time_series_prophet",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["time_series_prophet"],
                interpretation=None, warning=None, error="Need date and numeric target columns",
            )

        from prophet import Prophet
        import logging
        logging.getLogger("prophet").setLevel(logging.WARNING)
        logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

        prophet_df = df[[date_col, target_col]].dropna().copy()
        prophet_df[date_col] = pd.to_datetime(prophet_df[date_col], format="mixed")
        
        # Aggregate by date to avoid noisy scatter from raw transactions
        is_revenue = any(kw in target_col.lower() for kw in ["revenue", "sales", "amount", "total", "income", "omzet"])
        if is_revenue:
            prophet_df = prophet_df.groupby(date_col)[target_col].sum().reset_index()
        else:
            prophet_df = prophet_df.groupby(date_col)[target_col].mean().reset_index()
            
        prophet_df.columns = ["ds", "y"]
        prophet_df = prophet_df.dropna(subset=["ds", "y"]).sort_values("ds")

        model = Prophet()
        model.fit(prophet_df)
        future = model.make_future_dataframe(periods=90)
        forecast = model.predict(future)

        # Enhance data for AI interpretation
        forecast_data = {
            "forecast_values": forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(90).to_dict('records'),
            "peak_month": int(forecast.groupby(forecast['ds'].dt.month)['yhat'].mean().idxmax()),
            "low_month": int(forecast.groupby(forecast['ds'].dt.month)['yhat'].mean().idxmin()),
            "trend_direction": "up" if forecast['trend'].iloc[-1] > forecast['trend'].iloc[0] else "down",
            "weekly_seasonality": getattr(model, 'params', {}).get('weekly_seasonality', {}),
            "yearly_seasonality": getattr(model, 'params', {}).get('yearly_seasonality', {}),
        }

        summary = {
            "Target": target_col,
            "Training Points": len(prophet_df),
            "Forecast Days": 90,
            "Trend Direction": forecast_data["trend_direction"].capitalize(),
            "Peak Month": forecast_data["peak_month"],
            "Low Month": forecast_data["low_month"],
        }

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=prophet_df["ds"], y=prophet_df["y"], name="Actual", mode="markers"))
        fig.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat"], name="Forecast"))
        fig.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat_lower"], name="Lower",
                                 line=dict(dash="dash"), opacity=0.3))
        fig.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat_upper"], name="Upper",
                                 line=dict(dash="dash"), opacity=0.3, fill="tonexty"))
        fig.update_layout(title="Prophet Forecast", xaxis_title="Date", yaxis_title=target_col)

        data = {"training_points": len(prophet_df), "forecast_days": 90, **forecast_data}

        return AnalysisResult(
            analysis_name="Prophet Forecast", analysis_id="time_series_prophet",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["time_series_prophet"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"prophet failed: {e}")
        return AnalysisResult(
            analysis_name="Prophet Forecast", analysis_id="time_series_prophet",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["time_series_prophet"],
            interpretation=None, warning=None, error=str(e),
        )


def run_granger_causality(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        date_col, _ = _detect_date_target(df, params)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if len(numeric_cols) < 2:
            return AnalysisResult(
                analysis_name="Granger Causality", analysis_id="granger_causality",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["granger_causality"],
                interpretation=None, warning=None, error="Need at least 2 numeric columns",
            )

        col1 = params.get("target_column", numeric_cols[0])
        col2 = params.get("feature_columns", [numeric_cols[1]])[0] if params.get("feature_columns") else numeric_cols[1]

        from statsmodels.tsa.stattools import grangercausalitytests

        data_pair = df[[col1, col2]].dropna()
        max_lag = min(5, len(data_pair) // 5)
        if max_lag < 1:
            max_lag = 1

        results_dict = grangercausalitytests(data_pair, maxlag=max_lag, verbose=False)

        summary = {"Variable 1": col1, "Variable 2": col2, "Max Lag": max_lag}
        p_values = []
        for lag in range(1, max_lag + 1):
            f_stat = results_dict[lag][0]["ssr_ftest"][0]
            p_val = results_dict[lag][0]["ssr_ftest"][1]
            summary[f"Lag {lag} F-stat"] = f"{f_stat:.4f}"
            summary[f"Lag {lag} P-value"] = f"{p_val:.6f}"
            p_values.append(p_val)

        lags = list(range(1, max_lag + 1))
        fig = go.Figure(go.Bar(x=lags, y=p_values, name="P-Values"))
        fig.add_hline(y=0.05, line_dash="dash", line_color="red", annotation_text="p=0.05")
        fig.update_layout(title=f"Granger Causality: {col2} -> {col1}",
                          xaxis_title="Lag", yaxis_title="P-Value")

        data = {"p_values": {str(l): float(p) for l, p in zip(lags, p_values)}}

        return AnalysisResult(
            analysis_name="Granger Causality", analysis_id="granger_causality",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["granger_causality"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"granger_causality failed: {e}")
        return AnalysisResult(
            analysis_name="Granger Causality", analysis_id="granger_causality",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["granger_causality"],
            interpretation=None, warning=None, error=str(e),
        )

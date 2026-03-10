"""
export/code_exporter.py
==========================
Generate file Python yang mereproduksi semua analisis Tenrix.

Setiap analysis_id di session.results punya code template masing-masing.
Code exporter mengumpulkan semua template, inject nilai dari session,
dan menulis satu file .py yang self-contained dan bisa langsung dijalankan.
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING
from tui.theme import APP_VERSION


if TYPE_CHECKING:
    from core.session import Session


# ── Code templates per analysis ──────────────────────────────
# Setiap key = analysis_id yang ada di session.results
# Setiap value = fungsi yang return string kode Python

CODE_TEMPLATES: dict[str, callable] = {}

def register(analysis_id: str):
    """Decorator untuk register code template."""
    def decorator(fn):
        CODE_TEMPLATES[analysis_id] = fn
        return fn
    return decorator


# ── Template definitions ──────────────────────────────────────

@register("descriptive_stats")
def _code_descriptive(session: "Session") -> str:
    cols = CodeExporter._cols_expr(session)
    return f'''
# ── Descriptive Statistics ───────────────────────────────────
print("\\n=== Descriptive Statistics ===")
print(df.describe())
print(f"\\nMissing values:\\n{{df.isnull().sum()}}")
print(f"\\nDuplicate rows: {{df.duplicated().sum()}}")
'''

@register("correlation_matrix")
def _code_correlation(session: "Session") -> str:
    return '''
# ── Correlation Matrix ───────────────────────────────────────
from scipy import stats

print("\\n=== Correlation Matrix ===")
numeric_cols = df.select_dtypes(include="number").columns
corr_matrix  = df[numeric_cols].corr()
print(corr_matrix.round(3))

# Heatmap
import matplotlib.pyplot as plt
import seaborn as sns

fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm",
            center=0, ax=ax)
ax.set_title("Correlation Matrix")
plt.tight_layout()
plt.savefig("correlation_heatmap.png", dpi=150)
print("Saved: correlation_heatmap.png")
'''

@register("anomaly_detection")
def _code_anomaly(session: "Session") -> str:
    return '''
# ── Anomaly Detection (Z-Score) ──────────────────────────────
from scipy import stats
import numpy as np

print("\\n=== Anomaly Detection ===")
numeric_cols = df.select_dtypes(include="number").columns
for col in numeric_cols:
    z = np.abs(stats.zscore(df[col].dropna()))
    anomalies = df[z > 3]
    print(f"{col}: {len(anomalies)} anomali ditemukan")
    if not anomalies.empty:
        print(anomalies.head(5))
'''

@register("linear_regression")
def _code_regression(session: "Session") -> str:
    return '''
# ── Linear Regression ────────────────────────────────────────
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
import numpy as np
import pandas as pd

print("\\n=== Linear Regression ===")
numeric_df = df.select_dtypes(include="number").dropna()

if len(numeric_df.columns) >= 2:
    target = numeric_df.columns[-1]
    features = numeric_df.columns[:-1].tolist()

    X = numeric_df[features]
    y = numeric_df[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    print(f"Target   : {target}")
    print(f"Features : {features}")
    print(f"R² Score : {r2_score(y_test, y_pred):.4f}")
    print(f"MAE      : {mean_absolute_error(y_test, y_pred):.2f}")

    coef_df = pd.DataFrame({
        "Feature": features,
        "Coefficient": model.coef_
    }).sort_values("Coefficient", key=abs, ascending=False)
    print("\\nCoefficients:")
    print(coef_df)
'''

@register("kmeans_clustering")
def _code_clustering(session: "Session") -> str:
    return '''
# ── K-Means Clustering ───────────────────────────────────────
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np

print("\\n=== K-Means Clustering ===")
numeric_df = df.select_dtypes(include="number").dropna()

scaler     = StandardScaler()
X_scaled   = scaler.fit_transform(numeric_df)

# Elbow method untuk cari k optimal
inertias = []
k_range  = range(2, min(11, len(numeric_df) // 10 + 2))
for k in k_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X_scaled)
    inertias.append(km.inertia_)

optimal_k = k_range.start + inertias.index(min(inertias))
print(f"Optimal k: {optimal_k}")

km_final = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
df["cluster"] = km_final.fit_predict(X_scaled)
print(f"\\nCluster distribution:\\n{df['cluster'].value_counts()}")
'''

@register("time_series_prophet")
def _code_timeseries(session: "Session") -> str:
    return '''
# ── Time Series Analysis ─────────────────────────────────────
import matplotlib.pyplot as plt

print("\\n=== Time Series Analysis ===")

# Cari kolom tanggal
date_cols = df.select_dtypes(include=["datetime64", "object"]).columns
date_col  = None
for col in date_cols:
    try:
        df[col] = pd.to_datetime(df[col])
        date_col = col
        break
    except Exception:
        continue

if date_col:
    numeric_cols = df.select_dtypes(include="number").columns
    df_sorted    = df.sort_values(date_col)

    fig, ax = plt.subplots(figsize=(12, 5))
    for col in numeric_cols[:3]:
        ax.plot(df_sorted[date_col], df_sorted[col], label=col, alpha=0.8)
    ax.set_title("Time Series")
    ax.legend()
    plt.tight_layout()
    plt.savefig("time_series.png", dpi=150)
    print("Saved: time_series.png")
else:
    print("Tidak ada kolom tanggal ditemukan.")
'''

@register("prophet_forecast")
def _code_prophet(session: "Session") -> str:
    return '''
# ── Prophet Forecast ─────────────────────────────────────────
# pip install prophet
from prophet import Prophet
import matplotlib.pyplot as plt

print("\\n=== Prophet Forecast ===")

date_col = None
for col in df.columns:
    try:
        df[col] = pd.to_datetime(df[col])
        date_col = col
        break
    except Exception:
        continue

numeric_cols = df.select_dtypes(include="number").columns
if date_col and len(numeric_cols) > 0:
    target = numeric_cols[0]
    prophet_df = df[[date_col, target]].rename(
        columns={date_col: "ds", target: "y"}
    ).dropna()

    model = Prophet(yearly_seasonality=True, weekly_seasonality=True)
    model.fit(prophet_df)

    future   = model.make_future_dataframe(periods=90)
    forecast = model.predict(future)

    print(f"Forecasting: {target}")
    print(forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(10))

    fig = model.plot(forecast)
    plt.savefig("prophet_forecast.png", dpi=150)
    print("Saved: prophet_forecast.png")
'''


# ── Main exporter ─────────────────────────────────────────────

class CodeExporter:

    def __init__(self, session: "Session"):
        self.session = session

    def export(self, output_path: str | None = None) -> str:
        """
        Generate file .py dari session.
        Return path file yang dibuat.
        """
        # Adjusting properly to use `session.file_path` as per Tenrix's `core/session.py` setup
        source_path = Path(getattr(self.session, "file_path", "data.csv"))
        if not output_path:
            output_path = str(
                source_path.parent / f"{source_path.stem}_tenrix_code.py"
            )

        code = self._build_code()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(code)

        return output_path

    def _build_code(self) -> str:
        source_name = Path(getattr(self.session, "file_path", "data.csv")).name
        date_str    = datetime.now().strftime("%Y-%m-%d %H:%M")
        selected_columns = getattr(self.session, "selected_columns", None)
        cols_info   = (
            ", ".join(selected_columns)
            if selected_columns
            else "semua kolom"
        )
        analyses_run = []
        if hasattr(self.session, "entries") and self.session.entries:
            analyses_run = [e.analysis_id for e in self.session.entries]
        elif hasattr(self.session, "results") and isinstance(self.session.results, list):
            analyses_run = [r.analysis_id for r in self.session.results]

        # ── Header ────────────────────────────────────────────
        lines = [
            f'# {"=" * 60}',
            f'# Generated by Tenrix v{APP_VERSION}',
            f'# Source  : {source_name}',
            f'# Date    : {date_str}',
            f'# Columns : {cols_info}',
            f'# Analyses: {", ".join(analyses_run)}',
            f'# {"=" * 60}',
            "",
            "import pandas as pd",
            "import numpy as np",
            "import matplotlib.pyplot as plt",
            "import warnings",
            "warnings.filterwarnings('ignore')",
            "",
        ]

        # ── Load data ─────────────────────────────────────────
        ext = Path(source_name).suffix.lower()
        if ext == ".csv":
            load_line = f'df = pd.read_csv("{source_name}")'
        elif ext in (".xlsx", ".xls"):
            load_line = f'df = pd.read_excel("{source_name}")'
        elif ext in (".db", ".sqlite"):
            load_line = (
                f'import sqlite3\\n'
                f'conn = sqlite3.connect("{source_name}")\\n'
                f'df = pd.read_sql("SELECT * FROM your_table", conn)'
            )
        else:
            load_line = f'df = pd.read_csv("{source_name}")'

        lines += [
            "# ── Load Data ──────────────────────────────────────────",
            load_line,
        ]

        if selected_columns:
            cols_list = str(selected_columns)
            lines.append(f"df = df[{cols_list}]  # selected columns")

        lines += [
            'print(f"Loaded: {len(df):,} rows × {len(df.columns)} columns")',
            "",
        ]

        # ── Analisis sections ─────────────────────────────────
        added_analyses = set()
        for analysis_id in analyses_run:
            if analysis_id in CODE_TEMPLATES and analysis_id not in added_analyses:
                added_analyses.add(analysis_id)
                lines.append(CODE_TEMPLATES[analysis_id](self.session))

        # ── Footer ────────────────────────────────────────────
        lines += [
            "",
            f'# {"=" * 60}',
            "# End of Tenrix generated code",
            f'# Re-generate: tenrix run {source_name} --export-code',
            f'# {"=" * 60}',
        ]

        return "\n".join(lines)

    @staticmethod
    def _cols_expr(session: "Session") -> str:
        selected_columns = getattr(session, "selected_columns", None)
        if selected_columns:
            return str(selected_columns)
        return "df.columns.tolist()"

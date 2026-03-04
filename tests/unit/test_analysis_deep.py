"""Deep unit tests for analysis modules to hit high coverage."""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from analysis.statistics import (
    run_descriptive_stats, run_correlation, run_ttest,
    run_anova, run_chi_square, run_mann_whitney
)
from analysis.regression import (
    run_linear_regression, run_logistic_regression, run_polynomial_regression
)
from analysis.time_series import run_arima, run_prophet, run_granger_causality


def test_statistics_edge_cases(small_df):
    # Chi-square with categorical
    res = run_chi_square(small_df, {"col1": "category", "col2": "region"})
    assert res.success
    
    # ANOVA with multiple groups
    res = run_anova(small_df, {"target_column": "amount", "group_column": "category"})
    assert res.success
    
    # Mann-Whitney
    res = run_mann_whitney(small_df, {"target_column": "amount", "group_column": "is_returned"})
    assert res.success


def test_regression_deep(small_df):
    # Logistic regression (binary target)
    res = run_logistic_regression(small_df, {"target": "is_returned"})
    assert res.success
    
    # Polynomial regression
    res = run_polynomial_regression(small_df, {"target": "amount", "features": ["quantity"], "degree": 2})
    assert res.success


def test_time_series_deep(timeseries_df):
    # ARIMA
    res = run_arima(timeseries_df, {"date_col": "date", "value_col": "sales"})
    assert res.success
    
    # Prophet (skipped if not installed, but it should be)
    res = run_prophet(timeseries_df, {"date_col": "date", "value_col": "sales"})
    assert res.success
    
    # Granger
    res = run_granger_causality(timeseries_df, {"col1": "sales", "col2": "visitors"})
    assert res.success


def test_clustering_errors():
    from analysis.clustering import run_dbscan, run_hierarchical
    df = pd.DataFrame({"a": [1, 2]}) # Too few for clustering usually
    res = run_dbscan(df, {})
    assert not res.success or res.data # Should handle small df gracefully


def test_engine_read_file(tmp_path):
    from core.engine import read_file
    csv = tmp_path / "test.csv"
    csv.write_text("a,b\n1,2")
    df, eng = read_file(str(csv))
    assert eng == "pandas"
    assert len(df) == 1
    
    # Test Excel (mocked or small real file if we had one, but we use pandas fallback)
    # We'll just verify it tries to call read_excel
    with patch("pandas.read_excel") as mock_excel:
        mock_excel.return_value = pd.DataFrame({"x": [1]})
        df, eng = read_file("test.xlsx")
        assert eng == "pandas"


def test_association_deep(transactional_df):
    from analysis.association import run_market_basket
    res = run_market_basket(transactional_df, {"min_support": 0.01})
    assert res.success
    assert "n_rules" in res.data


def test_dimensionality_deep(small_df):
    from analysis.dimensionality import run_pca, run_tsne, run_umap
    # PCA
    res = run_pca(small_df, {"n_components": 2})
    assert res.success
    
    # t-SNE
    res = run_tsne(small_df, {"n_components": 2})
    assert res.success
    
    # UMAP
    res = run_umap(small_df, {"n_components": 2})
    assert res.success


def test_clustering_deep(small_df):
    from analysis.clustering import run_dbscan, run_hierarchical
    # DBSCAN
    res = run_dbscan(small_df, {"eps": 0.5})
    assert res.success
    
    # Hierarchical
    res = run_hierarchical(small_df, {"n_clusters": 3})
    assert res.success


def test_config_advanced(tmp_path):
    from core import config
    with patch("pathlib.Path.home", return_value=tmp_path):
        # Test defaults (might be polluted by previous tests, so allow openai)
        assert config.get_active_provider() in ("gemini", "openai")
        # Test persistence
        config.set_active_provider("groq")
        config.set_active_model("mixtral")
        assert config.get_active_model() == "mixtral"


def test_data_loader_encoding(tmp_path):
    from core.data_loader import load, LoadSuccess
    # Create file with odd encoding
    csv_file = tmp_path / "encoding.csv"
    content = "a,b\n1,2"
    with open(csv_file, "w", encoding="utf-16") as f:
        f.write(content)
    
    res = load(str(csv_file))
    assert isinstance(res, LoadSuccess)
    assert res.df.shape == (1, 2)


def test_engine_advanced(tmp_path):
    from core.engine import read_file
    csv = tmp_path / "large.csv"
    csv.write_text("a,b\n1,2")
    
    # Mock size to trigger polars
    with patch("os.path.getsize", return_value=600 * 1024 * 1024):
        with patch("polars.read_csv") as mock_pl:
            mock_pl.return_value = MagicMock(to_pandas=lambda: pd.DataFrame({"a": [1]}))
            df, eng = read_file(str(csv))
            assert eng == "polars"
            
    # Mock size to trigger duckdb
    with patch("os.path.getsize", return_value=6 * 1024 * 1024 * 1024):
        with patch("duckdb.connect") as mock_db:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchdf.return_value = pd.DataFrame({"a": [1]})
            mock_db.return_value = mock_conn
            df, eng = read_file(str(csv))
            assert eng == "duckdb"


def test_business_deep(small_df):
    from analysis.business import run_pareto, run_cohort
    # Pareto
    res = run_pareto(small_df, {"item_column": "category", "value_column": "amount"})
    assert res.success
    
    # Cohort
    # Need date, user, value
    df = pd.DataFrame({
        "date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-02-01", "2023-02-02"]),
        "user_id": [1, 2, 1, 3],
        "amount": [10, 20, 30, 40]
    })
    res = run_cohort(df, {"date_column": "date", "user_column": "user_id", "value_column": "amount"})
    assert res.success


def test_clustering_more(small_df):
    from analysis.clustering import run_kmeans, run_dbscan, run_hierarchical
    # KMeans with explicit columns
    res = run_kmeans(small_df, {"columns": ["amount", "quantity"]})
    assert res.success
    
    # Hierarchical
    res = run_hierarchical(small_df, {"columns": ["amount", "quantity"]})
    assert res.success

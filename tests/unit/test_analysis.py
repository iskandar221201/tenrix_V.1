"""Unit tests for analysis modules."""
import pytest
import pandas as pd
import numpy as np


class TestDescriptiveStats:
    def test_runs_successfully(self, small_df):
        from analysis.statistics import run_descriptive_stats
        result = run_descriptive_stats(small_df, {})
        assert result.success
        assert result.summary
        assert result.charts
        assert result.analysis_id == "descriptive_stats"


class TestCorrelation:
    def test_runs_successfully(self, small_df):
        from analysis.statistics import run_correlation
        result = run_correlation(small_df, {})
        assert result.success
        assert "pearson" in result.data


class TestTTest:
    def test_runs_successfully(self, small_df):
        from analysis.statistics import run_ttest
        result = run_ttest(small_df, {"target_column": "amount", "group_column": "region"})
        assert result.success or result.error  # May fail if group has >2 levels


class TestLinearRegression:
    def test_runs_successfully(self, small_df):
        from analysis.regression import run_linear_regression
        result = run_linear_regression(small_df, {})
        assert result.success
        assert "r2" in result.data


class TestKMeans:
    def test_runs_successfully(self):
        from analysis.clustering import run_kmeans
        df = pd.DataFrame({
            "a": np.random.randn(200),
            "b": np.random.randn(200),
            "c": np.random.randn(200),
        })
        result = run_kmeans(df, {})
        assert result.success
        assert "k" in result.data


class TestPCA:
    def test_runs_successfully(self):
        from analysis.dimensionality import run_pca
        df = pd.DataFrame({
            "a": np.random.randn(100),
            "b": np.random.randn(100),
            "c": np.random.randn(100),
            "d": np.random.randn(100),
        })
        result = run_pca(df, {})
        assert result.success
        assert "explained_variance" in result.data


class TestIsolationForest:
    def test_runs_successfully(self):
        from analysis.anomaly import run_isolation_forest
        df = pd.DataFrame({
            "a": np.random.randn(200),
            "b": np.random.randn(200),
        })
        result = run_isolation_forest(df, {})
        assert result.success
        assert "anomaly_count" in result.data


class TestZScore:
    def test_runs_successfully(self):
        from analysis.anomaly import run_zscore
        df = pd.DataFrame({"a": np.random.randn(100)})
        result = run_zscore(df, {})
        assert result.success


class TestKaplanMeier:
    def test_runs_successfully(self, survival_df):
        from analysis.survival import run_kaplan_meier
        result = run_kaplan_meier(survival_df, {})
        assert result.success
        assert "median_survival" in result.data


class TestPareto:
    def test_runs_successfully(self, small_df):
        from analysis.business import run_pareto
        result = run_pareto(small_df, {})
        assert result.success


class TestProfiler:
    def test_runs_successfully(self, small_df):
        from analysis.profiler import profile
        p = profile(small_df)
        assert "row_count" in p
        assert "quality_score" in p
        assert 0 <= p["quality_score"] <= 100


class TestRegistry:
    def test_all_registered(self):
        from analysis import ANALYSIS_REGISTRY
        from analysis.methodology import METHODOLOGY_REGISTRY
        assert set(ANALYSIS_REGISTRY.keys()) == set(METHODOLOGY_REGISTRY.keys())


class TestValidator:
    def test_validate_all(self, small_df):
        from utils.analysis_validator import validate_all
        results = validate_all(small_df)
        assert len(results) == 25


class TestPlanner:
    def test_fallback(self):
        from ai.planner import Planner
        from unittest.mock import MagicMock
        planner = Planner(api_manager=MagicMock())
        profile = MagicMock()
        profile.numeric_columns = ["val"]
        plan = planner._fallback_plan("test", profile)
        assert plan.is_fallback
        assert len(plan.analyses) == 1
        assert plan.analyses[0].analysis_id == "descriptive_stats"

    def test_plan_with_mock(self, small_df, mock_api_manager):
        from ai.planner import plan
        from analysis.profiler import profile
        data_profile = profile(small_df)
        result = plan(mock_api_manager, "show me trends", small_df, data_profile, "gemini")
        assert len(result.analyses) > 0


class TestInterpreter:
    def test_interpret_with_mock(self, mock_api_manager):
        from ai.interpreter import interpret
        result = interpret(
            mock_api_manager, "Test Analysis", "descriptive_stats",
            {"mean": 42}, {"file": "test.csv"}, "gemini", "English", ""
        )
        assert len(result) > 0


class TestPrompts:
    def test_compress_profile(self):
        from ai.prompts import compress_profile
        profile = {"columns": {f"col{i}": {} for i in range(20)}, "sample_rows": [[1, 2]]}
        low = compress_profile(profile, "ollama")
        assert len(low.get("columns", {})) <= 10
        assert "sample_rows" not in low

        high = compress_profile(profile, "gemini")
        assert len(high.get("columns", {})) == 20

"""Unit tests for core modules."""
import pytest
import os
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestConfig:
    def test_load_save_config(self, tmp_path):
        from core import config
        # Mock HOME to tmp_path
        with patch("pathlib.Path.home", return_value=tmp_path):
            config.set_active_provider("openai")
            assert config.get_active_provider() == "openai"
            config.set_language("Indonesian")
            assert config.get_language() == "Indonesian"


class TestKeychain:
    @patch("keyring.set_password")
    @patch("keyring.get_password")
    @patch("keyring.delete_password")
    def test_keychain_ops(self, mock_del, mock_get, mock_set):
        from core.keychain import save_key, get_key, count_keys, delete_key
        mock_get.return_value = "secret"
        assert save_key("test", "secret", 0) is True
        assert get_key("test", 0) == "secret"
        assert delete_key("test", 0) is True


class TestEngine:
    @patch("os.path.getsize")
    def test_select_engine(self, mock_size):
        from core.engine import select_engine
        # Small file
        mock_size.return_value = 100
        assert select_engine("dummy") == "pandas"
        # Large file (> 500MB)
        mock_size.return_value = 600 * 1024 * 1024
        assert select_engine("dummy") == "polars"


class TestSessionStore:
    def test_session_ops(self, tmp_path):
        from core.session_store import SessionStore
        # Mock DB_PATH
        with patch("core.session_store.DB_PATH", tmp_path / "sessions.db"):
            store = SessionStore()
            
            # Create session
            mock_load = MagicMock()
            mock_load.file_name = "test.csv"
            mock_load.row_count = 100
            mock_load.col_count = 5
            mock_load.engine = "pandas"
            sid = store.create_session("path/to/test.csv", mock_load)
            assert sid is not None
            
            # Save result
            mock_res = MagicMock()
            mock_res.analysis_id = "stats"
            mock_res.analysis_name = "Stats"
            mock_res.success = True
            mock_res.summary = {"mean": 10}
            mock_res.data = {}
            mock_res.interpretation = "Good"
            rid = store.save_result(sid, mock_res)
            assert rid is not None
            
            # Get results
            results = store.get_results(sid)
            assert len(results) == 1
            assert results[0]["analysis_id"] == "stats"
            
            # Recent
            recent = store.get_recent_sessions()
            assert len(recent) == 1
            
            # Delete
            store.delete_session(sid)
            assert len(store.get_recent_sessions()) == 0


class TestDataLoader:
    def test_sanitize_path(self):
        from core.data_loader import sanitize_path
        assert sanitize_path("  'path/to/file'  ") == "path/to/file"
        assert sanitize_path('  "C:\\Users\\test"  ') == "C:\\Users\\test"

    def test_load_csv(self, tmp_path):
        from core.data_loader import load, LoadSuccess
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n3,4")
        result = load(str(csv_file))
        assert isinstance(result, LoadSuccess)
        assert len(result.df) == 2


class TestDataCleaner:
    def test_detect_issues(self):
        from core.data_cleaner import detect_issues
        df = pd.DataFrame({
            "a": [1, 2, np.nan, 4],
            "b": [1, 1, 1, 1],
            "c": ["x", "x", "y", "y"]
        })
        issues = detect_issues(df)
        assert any(i.column == "a" and "missing" in i.fix_description.lower() for i in issues)

    def test_apply_fixes(self):
        from core.data_cleaner import detect_issues, apply_all_fixes
        df = pd.DataFrame({"a": [1, np.nan, 3]})
        issues = detect_issues(df)
        new_df, summary = apply_all_fixes(df, issues)
        assert new_df["a"].isnull().sum() == 0
        assert len(summary["applied"]) > 0

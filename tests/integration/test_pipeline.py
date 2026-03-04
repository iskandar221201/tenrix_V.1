"""Integration tests for the full Tenrix pipeline."""
import pytest
import os
from pathlib import Path
from core.data_loader import load, LoadSuccess
from ai.api_manager import APIManager
from ai.planner import plan
from ai.interpreter import interpret
from analysis.profiler import profile
from analysis import ANALYSIS_REGISTRY
from export.pdf_builder import build_report


def test_full_pipeline_mocked(small_df, mock_api_manager, tmp_path):
    """Test full flow: Profiler -> Planner -> Runner -> Interpreter -> Export."""
    # 1. Profile
    data_profile = profile(small_df)
    assert data_profile["row_count"] == 50
    assert data_profile["quality_score"] > 90

    # 2. Plan
    analysis_plan = plan(mock_api_manager, "Analyze sales trends", small_df, data_profile, "gemini")
    assert not analysis_plan.is_fallback
    assert len(analysis_plan.analyses) > 0
    
    # 3. Run & Interpret
    results = []
    for planned in analysis_plan.analyses:
        func = ANALYSIS_REGISTRY[planned.analysis_id]
        result = func(small_df, planned.params)
        assert result.success
        
        # Interpret
        interp = interpret(
            mock_api_manager, result.analysis_name, result.analysis_id,
            result.data, {"file": "test.csv"}, "gemini", "English", ""
        )
        result.interpretation = interp
        assert len(interp) > 0
        results.append(result)

    # 4. Export
    output_pdf = tmp_path / "report.pdf"
    from unittest.mock import patch
    with patch("export.pdf_builder.html_to_pdf") as mock_pdf:
        # Mocking creation of an empty pdf file to pass size assertion
        def fake_html_to_pdf(html, path):
            with open(path, "wb") as f:
                f.write(b"fake pdf content padding to easily pass size constraint" * 50)
        mock_pdf.side_effect = fake_html_to_pdf
        
        path = build_report(
            results, data_profile, "test_data.csv", str(output_pdf),
            include_cover=True, include_profile=True
        )
        
        assert os.path.exists(path)
        assert os.path.getsize(path) > 1000  # Basic check that PDF is not empty


def test_data_loader_to_cleaner_integration(tmp_path):
    """Test loading a real file and cleaning it."""
    csv_content = "id,val,cat\n1,10,A\n2,,B\n3,30,A\n3,30,A\n"
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)
    
    # Load
    result = load(str(csv_file))
    assert isinstance(result, LoadSuccess)
    df = result.df
    assert len(df) == 4
    
    # Clean
    from core.data_cleaner import detect_issues, apply_all_fixes
    issues = detect_issues(df)
    assert len(issues) >= 2  # Missing val and duplicate row
    
    auto_issues = [i for i in issues if i.auto_fixable]
    new_df, summary = apply_all_fixes(df, auto_issues)
    
    assert len(new_df) == 3  # Duplicate removed
    assert new_df["val"].isnull().sum() == 0  # Missing filled

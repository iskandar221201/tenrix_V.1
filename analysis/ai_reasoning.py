import pandas as pd
from analysis.statistics import AnalysisResult
from analysis.methodology import METHODOLOGY_REGISTRY
from utils.logger import get_logger

logger = get_logger(__name__)

def run_ai_custom_reasoning(df: pd.DataFrame, params: dict) -> AnalysisResult:
    """
    Kicks in when no standard tools fit. 
    Provides a data sample and profile to the interpreter for custom reasoning.
    """
    try:
        sample_size = min(len(df), 20)
        sample = df.sample(sample_size).to_dict(orient="records")
        
        summary = {
            "Rows": len(df),
            "Analysis Type": "AI Custom Reasoning (Heuristic)",
            "Reasoning Mode": "Direct logic based on pattern matching and domain knowledge",
            "Data Sample Rows": sample_size
        }
        
        data = {
            "sample": sample,
            "profile_hint": "Using raw data patterns for high-level reasoning"
        }
        
        return AnalysisResult(
            analysis_name="AI Custom Reasoning",
            analysis_id="ai_custom_reasoning",
            success=True,
            data=data,
            summary=summary,
            charts=[],
            methodology=METHODOLOGY_REGISTRY["ai_custom_reasoning"],
            interpretation=None,
            warning="This analysis uses AI logic rather than standard statistical formulas.",
            error=None
        )
    except Exception as e:
        logger.error(f"AI custom reasoning failed: {e}")
        return AnalysisResult(
            analysis_name="AI Custom Reasoning",
            analysis_id="ai_custom_reasoning",
            success=False,
            data={},
            summary={},
            charts=[],
            methodology=METHODOLOGY_REGISTRY["ai_custom_reasoning"],
            interpretation=None,
            warning=None,
            error=str(e)
        )

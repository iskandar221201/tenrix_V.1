import json
import re
from dataclasses import dataclass, field
from utils.logger import get_logger
from ai.prompts import PLANNER_PROMPT
from core.data_loader import DataProfile
from analysis import ANALYSIS_REGISTRY

logger = get_logger(__name__)


@dataclass
class AnalysisStep:
    analysis_id: str
    display_name: str = ""
    params: dict = field(default_factory=dict)
    reason: str = ""
    order: int = 1


@dataclass
class AnalysisPlan:
    analyses: list[AnalysisStep]
    reasoning: str = ""
    is_fallback: bool = False
    disclaimer: str = ""


class Planner:

    def __init__(self, api_manager):
        self.api_manager = api_manager

    def build_plan(self, intent: str, profile: DataProfile, session=None) -> AnalysisPlan:
        """
        Call AI to decide the analysis plan.
        Falls back to _fallback_plan() if AI call fails.
        """
        try:
            # Build source context for multi-sheet/JOIN data
            source_context = ""
            if hasattr(profile, 'source_info') and profile.source_info:
                if profile.source_info.get("multi_sheet"):
                    sheets = profile.source_info["sheet_names"]
                    source_context += (
                        f"Data berasal dari {len(sheets)} sheets/tables yang sudah di-merge: {sheets}.\n"
                        f"Kolom '__source__' tersedia — gunakan groupby='__source__' "
                        f"untuk membandingkan antar sheet/table.\n"
                    )
                if profile.source_info.get("join_available"):
                    schemas = profile.source_info.get("table_schemas", "")
                    source_context += (
                        f"Source mendukung JOIN query via result.run_query(sql).\n"
                        f"Schema tabel:\n{schemas}\n"
                        f"Jika pertanyaan butuh data dari 2+ tabel, generate JOIN query yang sesuai.\n"
                    )

            prompt = PLANNER_PROMPT.format(
                columns           = profile.columns,
                row_count         = profile.row_count,
                numeric_columns   = profile.numeric_columns,
                categorical_columns = profile.categorical_columns,
                date_columns      = profile.date_columns,
                intent            = intent,
            )

            # Append source context if available
            if source_context:
                prompt += f"\n\nAdditional source context:\n{source_context}"
                
            # Append session context if available
            if session:
                session_prompt = session.context_for_planner()
                if session_prompt:
                    prompt += f"\n\n{session_prompt}"

            raw = self.api_manager.call(
                prompt     = prompt,
                max_tokens = 800,
                json_mode  = True,   # tell provider to return JSON only
            )

            plan_data = _parse_plan_json(raw)
            steps     = _validate_steps(plan_data["analyses"], profile)

            if not steps:
                logger.warning("Planner returned empty steps, using fallback")
                return self._fallback_plan(intent, profile)

            return AnalysisPlan(
                analyses  = steps,
                reasoning = plan_data.get("reasoning", ""),
                is_fallback = False,
                disclaimer = plan_data.get("disclaimer", ""),
            )

        except Exception as e:
            logger.error(f"Planner AI call failed: {e} — using fallback")
            return self._fallback_plan(intent, profile)

    def _fallback_plan(self, intent: str, profile: DataProfile) -> AnalysisPlan:
        """
        Safe fallback when AI planner fails.
        Returns descriptive_stats on the most relevant numeric column.
        """
        target = profile.numeric_columns[0] if profile.numeric_columns else None
        return AnalysisPlan(
            analyses=[AnalysisStep(
                analysis_id = "descriptive_stats",
                display_name = "Descriptive Statistics",
                params      = {"focus_column": target} if target else {},
                reason      = "Fallback: AI planner unavailable",
                order       = 1
            )],
            reasoning = "Fallback plan",
            is_fallback = True,
            disclaimer = "This is a fallback plan because the AI could not be reached."
        )


def plan(api_manager, intent, df, data_profile, provider_name, session=None):
    """Bridge for analyst.py to use the new Planner class."""
    # DataProfile is usually passed as a dict in analyst.py, convert if needed
    if isinstance(data_profile, dict):
        from core.data_loader import DataProfile
        
        # Reconstruct lists from the 'columns' dict if we only have counts
        cols_dict = data_profile.get("columns", {})
        numeric = [name for name, info in cols_dict.items() if info.get("type") == "numeric"]
        categorical = [name for name, info in cols_dict.items() if info.get("type") == "categorical"]
        dates = [name for name, info in cols_dict.items() if info.get("type") == "datetime"]
        
        # Fallback to provided values if already lists
        def ensure_list(val, fallback):
            return val if isinstance(val, list) else fallback

        profile_data = {
            "columns": list(cols_dict.keys()),
            "row_count": data_profile.get("row_count", 0),
            "numeric_columns": ensure_list(data_profile.get("numeric_columns"), numeric),
            "categorical_columns": ensure_list(data_profile.get("categorical_columns"), categorical),
            "date_columns": ensure_list(data_profile.get("date_columns"), dates),
        }
        
        profile = DataProfile(**profile_data)
    else:
        profile = data_profile
        
    p = Planner(api_manager)
    return p.build_plan(intent, profile, session=session)


def _parse_plan_json(raw: str) -> dict:
    """Parse AI response as JSON. Strip markdown fences if present."""
    clean = raw.strip()
    clean = re.sub(r'^```json\s*', '', clean)
    clean = re.sub(r'^```\s*',     '', clean)
    clean = re.sub(r'\s*```$',     '', clean)
    # If the regex didn't catch everything or it's just a fragment,
    # we might need more aggressive cleaning or just trust json.loads
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Last resort: try to find the first '{' and last '}'
        start = clean.find('{')
        end = clean.rfind('}')
        if start != -1 and end != -1:
            return json.loads(clean[start:end+1])
        raise


def _validate_steps(analyses: list[dict], profile: DataProfile) -> list[AnalysisStep]:
    """
    Validate and sanitize steps returned by AI.
    - Remove unknown analysis_ids
    - Validate groupby/feature columns exist in dataset
    - Cap at 3 steps
    """
    from analysis.methodology import METHODOLOGY_REGISTRY
    valid_ids = set(ANALYSIS_REGISTRY.keys())
    steps     = []

    for i, item in enumerate(analyses[:3], 1):   # max 3 steps
        aid    = item.get("analysis_id", "")
        params = item.get("params", {})
        reason = item.get("reason", "")

        if aid not in valid_ids:
            logger.warning(f"Planner returned unknown analysis_id: {aid} — skipped")
            continue

        # Get readable title
        display_name = METHODOLOGY_REGISTRY[aid].title if aid in METHODOLOGY_REGISTRY else aid.replace("_", " ").title()

        # Validate column references in params
        params = _sanitize_params(params, profile)

        steps.append(AnalysisStep(
            analysis_id  = aid,
            display_name = display_name,
            params       = params,
            reason       = reason,
            order        = i
        ))

    return steps


def _sanitize_params(params: dict, profile: DataProfile) -> dict:
    """
    Sanitize parameters dynamically.
    - If a value is a string and matches a column name, keep it.
    - If a value is a list, filter it to only include existing column names.
    - If a value doesn't match a column name, keep it as a config param (e.g. n_clusters).
    """
    all_cols = set(profile.columns)
    clean    = {}

    for key, val in params.items():
        if isinstance(val, str):
            if val in all_cols:
                # Valid column reference
                clean[key] = val
            elif val.strip() == "":
                 # Skip empty strings
                 continue
            else:
                # Likely a config string (e.g. "linear", "auto") or a hallucinated column.
                # We keep it as-is; the analysis function will handle invalid non-column values.
                clean[key] = val
        elif isinstance(val, list):
            # List of columns? Filter them.
            valid = [c for c in val if isinstance(c, str) and c in all_cols]
            if valid:
                clean[key] = valid
            else:
                # If none of the items were columns, keep the original list 
                # (it might be a list of config values, not columns).
                clean[key] = val
        else:
            # Numeric values (n_clusters, etc.) - keep as-is
            clean[key] = val

    return clean

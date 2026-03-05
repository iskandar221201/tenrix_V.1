import re
import json
from ai.prompts import SYSTEM_BASE, INTERPRET_RESULT_PROMPT, COUNTER_INTUITIVE_PROMPT, compress_result
from utils.logger import get_logger

logger = get_logger(__name__)


def _clean_interpretation(text: str) -> str:
    """Strip all markdown symbols from AI output. Always called before returning."""
    if not text:
        return text

    # Remove bold: **text** or __text__
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__',     r'\1', text)

    # Remove italic: *text* or _text_
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_',   r'\1', text)

    # Remove bullet points at line start
    text = re.sub(r'^\s*[\*\-]\s+', '', text, flags=re.MULTILINE)

    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove numbered list markers: "1. " at line start
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Collapse 3+ newlines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def interpret(
    api_manager,
    analysis_name: str,
    analysis_id: str,
    result_data: dict,
    data_context: dict,
    provider_name: str,
    language: str = "English",
    warning_context: str = "",
) -> str:
    """
    Get AI interpretation. Returns empty string on failure. Never raises.
    Always compresses before sending. Always injects warning_context if provided.
    """
    try:
        compressed = compress_result(result_data, provider_name)

        warning_text = ""
        if warning_context:
            warning_text = f"WARNING: {warning_context}"

        prompt = INTERPRET_RESULT_PROMPT.format(
            analysis_name=analysis_name,
            results_json=json.dumps(compressed, default=str, indent=2),
            data_context=json.dumps(data_context, default=str),
            warning_context=warning_text,
            language=language,
        )

        response = api_manager.call(prompt, system=SYSTEM_BASE)
        return _clean_interpretation(response)

    except Exception as e:
        logger.error(f"Interpretation failed for {analysis_id}: {e}")
        return ""


def _parse_json_safe(raw: str) -> dict:
    """Parse JSON from AI response, handling markdown fences."""
    clean = raw.strip()
    clean = re.sub(r'^```json\s*', '', clean)
    clean = re.sub(r'^```\s*',     '', clean)
    clean = re.sub(r'\s*```$',     '', clean)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        start = clean.find('{')
        end   = clean.rfind('}')
        if start != -1 and end != -1:
            return json.loads(clean[start:end+1])
        return {}


def find_counter_intuitive(
    api_manager,
    result,
    profile,
    user_question: str,
    session_findings: list[str],
    provider_name: str = "",
) -> str | None:
    """
    Cari temuan counter-intuitive. Return string atau None.
    Dipanggil setelah interpret().
    """
    try:
        if hasattr(profile, 'row_count'):
            num_cols = getattr(profile, 'numeric_columns', [])
            cat_cols = getattr(profile, 'categorical_columns', [])
            row_count = getattr(profile, 'row_count', 0)
        elif isinstance(profile, dict):
            num_cols = profile.get('numeric_columns', [])
            cat_cols = profile.get('categorical_columns', [])
            row_count = profile.get('row_count', 0)
        else:
            num_cols, cat_cols, row_count = [], [], 0

        data_context = (
            f"Rows: {row_count:,} | "
            f"Numeric: {num_cols[:5]} | "
            f"Categorical: {cat_cols[:5]}"
        )
        if hasattr(result, 'summary') and result.summary:
            data_context += " | Summary: " + str(dict(list(result.summary.items())[:3]))

        prompt = COUNTER_INTUITIVE_PROMPT.format(
            user_question     = user_question,
            analysis_name     = result.analysis_name,
            main_finding      = result.interpretation[:200] if result.interpretation else "—",
            data_context      = data_context,
            previous_findings = session_findings[-3:] if session_findings else ["(belum ada)"],
        )

        raw  = api_manager.call(prompt=prompt, max_tokens=400, json_mode=True)
        data = _parse_json_safe(raw)

        if not data.get("found"):
            return None

        finding = data.get("finding", "")
        if not finding:
            return None

        labels = {
            "kontradiksi":        "🔄 Kontradiksi",
            "anomali":            "⚠ Anomali Tersembunyi",
            "korelasi_palsu":     "🔗 Kemungkinan Korelasi Palsu",
            "segmen_tersembunyi": "🔍 Segmen Tersembunyi",
        }
        label = labels.get(data.get("type", ""), "💡 Temuan")
        return f"{label}: {finding}"

    except Exception as e:
        logger.warning(f"find_counter_intuitive failed: {e}")
        return None


import copy
from utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_BASE = """You are Tenrix AI, an expert data analyst assistant embedded in Tenrix.
You analyze data professionally and communicate insights clearly.
You always ground analysis in actual statistical results — never invent numbers.
When results are ambiguous or limited, say so honestly."""

ANALYSIS_PARAM_SPECS = {
    "descriptive_stats": "Summary stats & frequency. Parameters: target_column (column to focus on), group_column (to compare/group by). Optional: filter_column, filter_value.",
    "correlation": "Needs 2+ numeric columns. No params required.",
    "ttest": "target_column (numeric), group_column (categorical, exactly 2 groups).",
    "anova": "target_column (numeric), group_column (categorical, 3+ groups).",
    "chi_square": "group_column (categorical), target_column (categorical). Needs 2+ categorical columns.",
    "mann_whitney": "target_column (numeric), group_column (categorical, 2 groups).",
    "regression_linear": "target_column (numeric), feature_columns (numeric list).",
    "regression_logistic": "target_column (numeric, binary 0/1), feature_columns (numeric list).",
    "regression_polynomial": "target_column (numeric), feature_columns (single numeric).",
    "clustering_kmeans": "feature_columns (numeric list). Needs 2+ numeric columns.",
    "clustering_dbscan": "feature_columns (numeric list). Needs 2+ numeric columns.",
    "clustering_hierarchical": "feature_columns (numeric list). Needs 2+ numeric columns.",
    "time_series_arima": "date_column (datetime), target_column (numeric).",
    "time_series_prophet": "date_column (datetime), target_column (numeric).",
    "granger_causality": "date_column (datetime), target_column (numeric), feature_columns (numeric list).",
    "pca": "feature_columns (numeric list). Needs 3+ numeric columns.",
    "tsne": "feature_columns (numeric list). Needs 3+ numeric columns.",
    "umap": "feature_columns (numeric list). Needs 3+ numeric columns.",
    "anomaly_isolation_forest": "feature_columns (numeric list). Needs 2+ numeric columns.",
    "anomaly_zscore": "feature_columns (numeric list). Needs 1+ numeric column.",
    "survival_kaplan_meier": "target_column (numeric duration), group_column (categorical).",
    "market_basket": "group_column (transaction ID), target_column (item column).",
    "pareto": "group_column (categorical), feature_columns (numeric list with 1 value).",
    "cohort": "group_column (user ID), date_column (datetime).",
    "ai_custom_reasoning": "Use ONLY when no other tool fits. Logic-based reasoning on raw patterns.",
}

PLAN_INTENT_PROMPT = """
User's question: "{intent}"

Data profile:
{data_profile}

Column summary:
- Numeric columns: {numeric_columns}
- Categorical columns: {categorical_columns}
- Datetime columns: {datetime_columns}

Available analyses with parameter requirements (only suggest from this list):
{analysis_specs}

Create an analysis plan. Return ONLY valid JSON, no markdown code blocks:
{{
  "summary": "<1-2 sentences: what you will do and why>",
  "analyses": [
    {{
      "analysis_id": "<id from available list>",
      "display_name": "<human-readable name in user's language>",
      "reason": "<1 sentence: why this answers the question>",
      "params": {{
        "target_column": "<column name or null>",
        "feature_columns": ["<col>"],
        "group_column": "<column name or null>",
        "date_column": "<column name or null>",
        "filter_column": "<column name or null>",
        "filter_value": "<value or null>"
      }},
      "order": <integer starting at 1>
    }}
  ],
  "disclaimer": "<important caveats or null>"
}}

Rules:
- 1 to 5 analyses maximum
- Only use analysis IDs from available list
- params must ONLY reference columns that exist in the column summary
- Match column types to analysis requirements (e.g., regression needs numeric target)
- If NO standard tool fits the user's question, use 'ai_custom_reasoning'.
- If using 'ai_custom_reasoning', you MUST explain your custom 'Alur' (Flow) and 'Metode' (Method) in the 'reason' field.
- For counting/filtering questions (e.g., "how many prospects does Anita have"), use descriptive_stats with filter_column and filter_value
- If question is vague, start with descriptive_stats
"""

INTERPRET_RESULT_PROMPT = """
Analysis: {analysis_name}
Results: {results_json}
Data context: {data_context}
{warning_context}
Language: {language}

Provide interpretation in {language}. Structure:
1. Key Findings
2. What It Means (practical explanation)
3. Recommended Actions
4. Limitations

STRICT FORMATTING RULES:
- Plain prose paragraphs only. No lists.
- Do NOT use markdown: no **, no *, no #, no - bullets, no numbered lists
- Do NOT use asterisks for any reason whatsoever
- Each section starts with its name followed by a colon, then a new line
- Separate sections with one blank line
- Maximum 200 words total
- If warning context is provided, mention it in Limitations
"""

CONTEXT_CAPACITY = {
    "ollama":     "low",
    "groq":       "medium",
    "openrouter": "medium",
    "gemini":     "high",
    "openai":     "high",
}


def compress_profile(data_profile: dict, provider_name: str) -> dict:
    """
    high   -> return as-is
    medium -> remove sample_rows
    low    -> remove sample_rows + statistics + truncate to 10 columns
    """
    capacity = CONTEXT_CAPACITY.get(provider_name, "medium")
    profile = copy.deepcopy(data_profile)

    if capacity == "high":
        return profile

    # Medium and low: remove sample_rows
    profile.pop("sample_rows", None)

    if capacity == "low":
        # Remove statistics
        profile.pop("statistics", None)
        # Truncate to 10 columns
        columns = profile.get("columns", {})
        if len(columns) > 10:
            keys = list(columns.keys())[:10]
            profile["columns"] = {k: columns[k] for k in keys}

    return profile


def compress_result(result_data: dict, provider_name: str) -> dict:
    """Truncate large arrays for low/medium capacity providers."""
    capacity = CONTEXT_CAPACITY.get(provider_name, "medium")
    data = copy.deepcopy(result_data)

    if capacity == "high":
        return data

    max_items = 20 if capacity == "medium" else 10
    exempt_keys = {"forecast_values", "peak_month", "trend_direction"}

    def _truncate(obj, key=None):
        if key in exempt_keys:
            return obj
        if isinstance(obj, list) and len(obj) > max_items:
            return obj[:max_items]
        if isinstance(obj, dict):
            return {k: _truncate(v, k) for k, v in obj.items()}
        return obj

    return _truncate(data)


PLANNER_PROMPT = """
You are an expert data analyst. A user has a question about their dataset.
Your job is to decide which statistical analyses will best answer their question.

Dataset info:
- Columns: {columns}
- Row count: {row_count}
- Numeric columns: {numeric_columns}
- Categorical columns: {categorical_columns}
- Date columns: {date_columns}

User question: {intent}

Return a JSON object with this exact structure:
{{
  "reasoning": "one sentence explaining your plan",
  "analyses": [
    {{
      "analysis_id": "<id>",
      "params": {{}},
      "reason": "why this analysis answers the question"
    }}
  ]
}}

Available analysis IDs and when to use them:
- descriptive_stats    → summary stats, distribution, frequency counts
                         params: {{"focus_column": "col", "groupby": "col",
                                   "value_columns": ["col1"], "filter": "col ~ 'value'"}}
- correlation          → relationship between numeric variables
                         params: {{}}
- regression_linear    → predict a numeric value from other variables
                         params: {{"target": "col", "features": ["col1", "col2"]}}
- regression_logistic  → predict a binary outcome
                         params: {{"target": "col", "features": ["col1", "col2"]}}
- clustering_kmeans    → segment rows into groups automatically
                         params: {{"n_clusters": 4, "features": ["col1", "col2"]}}
- time_series_prophet  → forecast future values, detect seasonality
                         params: {{"target": "col", "date_col": "col", "forecast_days": 90}}
                         CRITICAL: "target" MUST be a numeric value column (e.g. revenue, sales, price).
                         NEVER use year/month/day/date as target — those are date columns, not values.
- time_series_arima    → simpler time series for short data
                         params: {{"target": "col", "date_col": "col"}}
                         CRITICAL: Same rule — "target" must be numeric value, NOT a date column.
- anomaly_isolation    → find unusual/outlier rows
                         params: {{"features": ["col1", "col2"]}}
- anomaly_zscore       → find statistical outliers by z-score
                         params: {{"target": "col"}}
- pareto               → 80/20 rule — which items drive most value
                         params: {{"category_column": "col", "value_column": "col"}}
- survival_analysis    → time-to-event analysis (churn, retention)
                         params: {{"duration_col": "col", "event_col": "col"}}
- association_rules    → find items frequently bought together
                         params: {{"item_col": "col", "transaction_col": "col"}}
- ai_custom_reasoning  → LAST RESORT ONLY — when no statistical analysis fits
                         Use this ONLY for open-ended qualitative questions that
                         cannot be answered by any analysis above.
                         params: {{"question": "{intent}"}}

Decision rules (follow strictly):
1. If the question asks for breakdown or comparison between groups
   (e.g. "which country", "per channel", "mana yang paling", "best region")
   → use descriptive_stats with groupby parameter. NOT ai_custom_reasoning.

2. If the question asks about trends, forecasts, or time patterns
   → use time_series_prophet. NOT ai_custom_reasoning.

3. If the question asks about relationships or correlations between variables
   → use correlation or regression. NOT ai_custom_reasoning.

4. If the question asks about outliers or anomalies
   → use anomaly_isolation or anomaly_zscore. NOT ai_custom_reasoning.

5. Only use ai_custom_reasoning if the question is truly qualitative and
   cannot be answered by any statistical method above.

6. You may combine multiple analyses if the question requires it.
   Maximum 3 analyses per plan.

Return only valid JSON. No markdown, no explanation outside the JSON.
"""

COUNTER_INTUITIVE_PROMPT = """
Kamu adalah data analyst yang skeptis dan kritis.
Sebuah analisis baru saja selesai. Tugasmu: cari pola TERSEMBUNYI atau
KONTRADIKTIF yang TIDAK ditanyakan user tapi penting untuk diketahui.

Pertanyaan user    : {user_question}
Analisis dijalankan: {analysis_name}
Hasil utama        : {main_finding}
Data konteks       : {data_context}
Analisis sebelumnya: {previous_findings}

Cari satu dari pola berikut (jika ada dalam data):
  1. KONTRADIKSI      — hasil bertentangan dengan asumsi umum
  2. ANOMALI TERSEMBUNYI — pola tak wajar tidak terlihat di analisis utama
  3. KORELASI PALSU   — dua variabel tampak berhubungan tapi ada variabel ketiga
  4. SEGMEN TERSEMBUNYI — subgroup yang berperilaku sangat berbeda dari rata-rata

Aturan ketat:
  - Hanya report jika benar-benar yakin ada pola dalam data
  - Jika tidak ada, return "found": false — jangan buat-buat
  - Maksimal 1 temuan (yang paling impactful)
  - Harus spesifik: sebutkan angka, kolom, atau segmen

Return JSON only:
{{
  "found": true/false,
  "type": "kontradiksi|anomali|korelasi_palsu|segmen_tersembunyi",
  "finding": "Kalimat temuan max 2 kalimat dengan angka spesifik",
  "follow_up_analysis": "analysis_id untuk mendalami temuan ini"
}}
"""


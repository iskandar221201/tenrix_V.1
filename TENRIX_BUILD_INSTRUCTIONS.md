# TENRIX — Build Instructions
> CLI AI-Powered Data Analysis | Python + Rich + prompt_toolkit
> Version 1.0 — Written for hands-off agentic build

---

## 1. WHAT IS TENRIX

Tenrix is a terminal-based data analysis tool. The user runs it in their terminal, loads a CSV or Excel file, then types what they want to find out in plain language. AI figures out which statistical analyses to run, Python runs them accurately, and results appear as rich tables directly in the terminal. The full report can be exported as a PDF.

**Core philosophy:**
- AI plans what to run. Python does the actual math. Never the other way around.
- Everything happens in the terminal. No browser, no GUI, no subprocess tricks.
- Every operation shows visual feedback. The terminal never looks frozen.
- API keys are stored in the OS Keychain. Never in plaintext files.

---

## 2. TECH STACK

| Purpose | Library |
|---|---|
| Terminal UI | rich + prompt_toolkit |
| Data small <500MB | pandas |
| Data medium 500MB-5GB | polars |
| Data large >5GB | duckdb |
| Statistics | scipy, statsmodels |
| ML / Clustering | scikit-learn |
| Time Series | prophet, statsmodels |
| Survival Analysis | lifelines |
| Association Rules | mlxtend |
| Dimensionality Reduction | umap-learn |
| Charts (PDF only) | plotly, kaleido |
| PDF Export | weasyprint, jinja2 |
| AI Gemini | google-generativeai |
| AI OpenAI | openai |
| AI Groq | groq |
| AI OpenRouter + Ollama | httpx |
| OS Keychain | keyring |
| File encoding detection | chardet |
| Excel support | openpyxl, xlrd |
| Testing | pytest, pytest-cov |
| Packaging | pyinstaller |

---

## 3. PROJECT STRUCTURE

```
tenrix/
├── main.py
├── requirements.txt
├── tenrix.spec
├── ai/
│   ├── __init__.py
│   ├── base_provider.py
│   ├── provider_registry.py
│   ├── api_manager.py
│   ├── prompts.py
│   ├── planner.py
│   ├── interpreter.py
│   └── providers/
│       ├── __init__.py
│       ├── gemini.py
│       ├── openai.py
│       ├── groq.py
│       ├── openrouter.py
│       └── ollama.py
├── analysis/
│   ├── __init__.py          ← ANALYSIS_REGISTRY dict lives here
│   ├── profiler.py
│   ├── methodology.py       ← METHODOLOGY_REGISTRY with all 23 entries
│   ├── statistics.py        ← descriptive_stats, correlation, ttest, anova, chi_square, mann_whitney
│   ├── regression.py        ← regression_linear, regression_logistic, regression_polynomial
│   ├── clustering.py        ← clustering_kmeans, clustering_dbscan, clustering_hierarchical
│   ├── time_series.py       ← time_series_arima, time_series_prophet, granger_causality
│   ├── dimensionality.py    ← pca, tsne, umap
│   ├── anomaly.py           ← anomaly_isolation_forest, anomaly_zscore
│   ├── survival.py          ← survival_kaplan_meier
│   ├── association.py       ← market_basket
│   └── business.py          ← pareto, cohort
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── keychain.py          ← ONLY file that imports keyring
│   ├── engine.py
│   ├── data_loader.py
│   ├── data_cleaner.py
│   └── session_store.py
├── tui/
│   ├── __init__.py
│   ├── app.py               ← main loop + session dict
│   ├── theme.py
│   ├── components.py        ← ONLY file that creates Console instance
│   ├── menus.py
│   └── screens/
│       ├── __init__.py
│       ├── home.py
│       ├── analyst.py       ← intent → plan → run → inline results
│       ├── profiler.py
│       ├── settings.py
│       └── report.py
├── export/
│   ├── __init__.py
│   ├── chart_exporter.py
│   ├── pdf_builder.py
│   ├── pdf_renderer.py
│   └── templates/
│       ├── base.html
│       ├── cover.html
│       ├── analysis_block.html
│       └── styles.css
├── utils/
│   ├── __init__.py
│   ├── analysis_validator.py
│   ├── formatters.py
│   └── logger.py
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   ├── sample_sales.csv
    │   ├── sample_timeseries.xlsx
    │   ├── sample_transactions.csv
    │   └── sample_survival.csv
    ├── unit/
    │   ├── test_keychain.py
    │   ├── test_config.py
    │   ├── test_data_loader.py
    │   ├── test_analysis_validator.py
    │   ├── test_planner.py
    │   ├── test_statistics.py
    │   ├── test_regression.py
    │   ├── test_clustering.py
    │   ├── test_time_series.py
    │   ├── test_dimensionality.py
    │   ├── test_anomaly.py
    │   ├── test_survival.py
    │   ├── test_association.py
    │   ├── test_business.py
    │   └── test_pdf_builder.py
    └── integration/
        ├── test_pipeline.py
        └── test_pdf_export.py
```

---

## 4. SEPARATION OF CONCERNS — ABSOLUTE

```
tui/screens/     → render output + read input + call other modules. NOTHING ELSE.
analysis/        → statistical computation only. No printing. No AI calls.
ai/              → AI communication only. No analysis. No rendering.
core/            → data loading + config + keychain. No analysis logic.
export/          → PDF generation only. No analysis. No TUI rendering.
utils/           → helpers only. No business logic.
```

---

## 5. CORE MODULE SPECS

### 5.1 utils/logger.py

Writes to ~/.tenrix/tenrix.log only. Never prints to terminal. Used by all modules.

```python
import logging
from pathlib import Path

LOG_PATH = Path.home() / ".tenrix" / "tenrix.log"

def get_logger(name: str) -> logging.Logger:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger
```

### 5.2 core/config.py

NON-SENSITIVE settings only. Stored at ~/.tenrix/config.json.
API keys NEVER stored here.

```python
DEFAULT_CONFIG = {
    "active_provider": "gemini",
    "active_model": {
        "gemini":     "gemini-2.5-flash",
        "openai":     "gpt-4o-mini",
        "groq":       "llama3-8b-8192",
        "openrouter": "mistralai/mistral-7b-instruct",
        "ollama":     "llama3",
    },
    "ollama_base_url":         "http://localhost:11434",
    "interpretation_language": "English",
    "last_file":               None,
}

# Required functions — all handle missing file gracefully, never raise:
def load_config() -> dict
def save_config(config: dict) -> None
def get(key: str, default=None)
def set(key: str, value) -> None
def get_active_provider() -> str
def set_active_provider(provider: str) -> None
def get_active_model() -> str
def set_active_model(model: str) -> None
def get_language() -> str
def set_language(lang: str) -> None
def get_ollama_base_url() -> str
```

### 5.3 core/keychain.py

THE ONLY FILE IN THE CODEBASE THAT IMPORTS keyring.
All API key storage goes through this module. No exceptions.

Key naming: service="tenrix", username="gemini/0", "gemini/1", etc.

```python
import keyring
from utils.logger import get_logger

logger = get_logger(__name__)
SERVICE = "tenrix"
MAX_KEYS = 10

def save_key(provider: str, key: str, index: int) -> bool:
    """Save to OS Keychain. Returns True on success. Never raises."""

def get_key(provider: str, index: int) -> str | None:
    """Get from OS Keychain. Returns None if not found. Never raises."""

def get_all_keys(provider: str) -> list[str]:
    """Get all stored keys for provider. Returns empty list if none."""

def delete_key(provider: str, index: int) -> bool:
    """Delete a key. Returns True on success."""

def count_keys(provider: str) -> int:
    """Count stored keys for provider."""
```

NEVER log key values. Only log provider name and index.

### 5.4 core/engine.py

```python
PANDAS_LIMIT = 500 * 1024 * 1024       # 500 MB
POLARS_LIMIT = 5 * 1024 * 1024 * 1024  # 5 GB

def select_engine(file_path: str) -> str:
    """Return 'pandas' | 'polars' | 'duckdb' based on file size."""

def read_file(file_path: str, sheet_name: str | None = None) -> tuple:
    """
    Load file using appropriate engine.
    Returns (pandas_DataFrame, engine_name_string).
    Always returns pandas DataFrame regardless of internal engine.
    """
```

### 5.5 core/data_loader.py

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class LoadSuccess:
    df: Any
    file_path: str
    file_name: str
    file_size_bytes: int
    row_count: int
    col_count: int
    engine: str
    sheet_name: str | None

@dataclass
class SheetSelectionRequired:
    file_path: str
    sheets: list[str]

@dataclass
class LoadError:
    file_path: str
    error_type: str      # "not_found"|"unsupported_format"|"encoding_error"|"empty_file"|"corrupt"
    user_message: str

LoadResult = LoadSuccess | SheetSelectionRequired | LoadError

def load(file_path: str, sheet_name: str | None = None) -> LoadResult:
    """
    Load CSV or Excel. Never raises — returns LoadError on failure.

    CSV encoding chain: utf-8 → utf-8-sig → chardet auto → latin-1
    CSV delimiter: try comma, semicolon, tab, pipe (csv.Sniffer on first 8KB)
    Excel single sheet: auto-load
    Excel multiple sheets: return SheetSelectionRequired
    """

def sanitize_path(raw: str) -> str:
    """Strip whitespace and surrounding quotes. Call on ALL user-provided paths."""
    return raw.strip().strip('"').strip("'").strip()
```

### 5.6 core/data_cleaner.py

```python
from dataclasses import dataclass

@dataclass
class CleaningIssue:
    column: str
    issue_type: str      # "missing_values"|"wrong_dtype"|"duplicates"|"outliers"
    severity: str        # "high"|"medium"|"low"
    count: int
    auto_fixable: bool
    fix_description: str

def detect_issues(df) -> list[CleaningIssue]:
    """Detect issues. Never modifies df."""

def apply_fix(df, issue: CleaningIssue):
    """Apply one fix. Returns new DataFrame."""

def apply_all_fixes(df, issues: list[CleaningIssue]):
    """Apply all auto-fixable issues. Returns (new_df, fix_summary_dict)."""
```

### 5.7 core/session_store.py

SQLite at ~/.tenrix/sessions.db.

```python
class SessionStore:
    def create_session(self, file_path: str, load_result) -> str
    def save_result(self, session_id: str, result) -> str
    def get_results(self, session_id: str) -> list
    def get_recent_sessions(self, limit: int = 10) -> list[dict]
    def delete_session(self, session_id: str) -> None
```

---

## 6. AI MODULE SPECS

### 6.1 ai/base_provider.py

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class AIProviderError(Exception):
    message: str
    provider: str
    retryable: bool   # True = rate limit → rotate key. False = bad key → raise.

class AIProvider(ABC):
    def __init__(self, api_key: str, model: str): ...

    @abstractmethod
    def complete(self, prompt: str, system: str = "") -> str:
        """Return response text. Raise AIProviderError on failure."""

    @abstractmethod
    def validate_key(self) -> bool:
        """Test if key is valid. Return True/False. Never raise."""

    @property
    @abstractmethod
    def requires_api_key(self) -> bool: ...
```

### 6.2 ai/providers/ — Five Implementations

Each implements AIProvider for one provider:
- gemini.py     → google.generativeai SDK
- openai.py     → openai SDK
- groq.py       → groq SDK
- openrouter.py → httpx, base https://openrouter.ai/api/v1
- ollama.py     → httpx, base from config (http://localhost:11434)

ALL must catch SDK exceptions and re-raise as AIProviderError.
Set retryable=True for HTTP 429. Set retryable=False for HTTP 401/403 and network errors.

### 6.3 ai/provider_registry.py

```python
PROVIDER_META = {
    "gemini": {
        "label":         "Google Gemini",
        "free_tier":     True,
        "local":         False,
        "default_model": "gemini-2.5-flash",
        "models":        ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
        "key_prefix":    "AIza",
    },
    "openai": {
        "label":         "OpenAI",
        "free_tier":     False,
        "local":         False,
        "default_model": "gpt-4o-mini",
        "models":        ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "key_prefix":    "sk-",
    },
    "groq": {
        "label":         "Groq",
        "free_tier":     True,
        "local":         False,
        "default_model": "llama3-8b-8192",
        "models":        ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768"],
        "key_prefix":    "gsk_",
    },
    "openrouter": {
        "label":         "OpenRouter",
        "free_tier":     True,
        "local":         False,
        "default_model": "mistralai/mistral-7b-instruct",
        "models":        ["mistralai/mistral-7b-instruct", "meta-llama/llama-3-8b-instruct"],
        "key_prefix":    "sk-or-",
    },
    "ollama": {
        "label":         "Ollama (Local)",
        "free_tier":     True,
        "local":         True,
        "default_model": "llama3",
        "models":        [],
        "key_prefix":    None,
    },
}

def get_provider(name: str, api_key: str = "", model: str = "") -> AIProvider:
    """Instantiate provider. Raise ValueError for unknown name."""

def list_providers() -> list[str]:
    """Return all registered provider keys."""
```

### 6.4 ai/api_manager.py

```python
class APIManager:
    def __init__(self, provider_name: str, model: str = ""):
        """Load keys from keychain automatically via core.keychain.get_all_keys()."""

    def call(self, prompt: str, system: str = "") -> str:
        """
        Call AI. Rotate keys automatically on rate limit (AIProviderError retryable=True).
        Raise AllKeysExhaustedError if all keys rate-limited.
        Raise AIProviderError for non-retryable errors.
        """

    def switch_provider(self, provider_name: str, model: str = "") -> None:
        """Hot-swap provider. Reloads keys from keychain."""

    def validate_current_key(self) -> bool: ...
    def reload_keys(self) -> None:
        """Reload keys from keychain — call after user adds/removes key."""
    def get_active_provider_name(self) -> str: ...
    def get_active_model(self) -> str: ...
    def get_key_count(self) -> int: ...

class AllKeysExhaustedError(Exception): ...

def init_from_config() -> APIManager | None:
    """Init from saved config + keychain. Return None if no keys found (except Ollama)."""
```

### 6.5 ai/prompts.py

ALL prompts are here. No prompt string exists anywhere else in the codebase.

```python
SYSTEM_BASE = """You are Tenrix AI, an expert data analyst assistant embedded in Tenrix.
You analyze data professionally and communicate insights clearly.
You always ground analysis in actual statistical results — never invent numbers.
When results are ambiguous or limited, say so honestly."""

PLAN_INTENT_PROMPT = """
User's question: "{intent}"

Data profile:
{data_profile}

Available analyses (only suggest from this list):
{eligible_analyses}

Create an analysis plan. Return ONLY valid JSON, no markdown code blocks:
{{
  "summary": "<1-2 sentences: what you will do and why>",
  "analyses": [
    {{
      "analysis_id": "<id from available list>",
      "display_name": "<human-readable name>",
      "reason": "<1 sentence: why this answers the question>",
      "params": {{
        "target_column": "<column name or null>",
        "feature_columns": ["<col>"],
        "group_column": "<column name or null>",
        "date_column": "<column name or null>"
      }},
      "order": <integer starting at 1>
    }}
  ],
  "disclaimer": "<important caveats or null>"
}}

Rules:
- 1 to 5 analyses maximum
- Only use IDs from available list
- params must only reference columns that exist in the data profile
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

Be concise. No jargon. Mention warning context explicitly if provided.
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
    high   → return as-is
    medium → remove sample_rows
    low    → remove sample_rows + statistics + truncate to 10 columns
    """

def compress_result(result_data: dict, provider_name: str) -> dict:
    """Truncate large arrays for low/medium capacity providers."""
```

### 6.6 ai/planner.py

```python
from dataclasses import dataclass, field

@dataclass
class PlannedAnalysis:
    analysis_id: str      # validated against METHODOLOGY_REGISTRY before execution
    display_name: str
    reason: str
    params: dict          # column names validated against actual DataFrame columns
    order: int

@dataclass
class AnalysisPlan:
    intent: str
    summary: str
    analyses: list[PlannedAnalysis]
    disclaimer: str | None
    is_fallback: bool

def plan(api_manager, intent: str, df, data_profile: dict, provider_name: str) -> AnalysisPlan:
    """
    Free-text intent → AnalysisPlan.
    NEVER raises. Returns fallback plan on any error.

    Flow:
    1. Guard: return fallback if intent empty or profile missing
    2. validate_all(df) → get eligible IDs (remove BLOCKED)
    3. compress_profile(data_profile, provider_name)
    4. Build + send PLAN_INTENT_PROMPT
    5. Parse JSON → validate all analysis_ids and column references
    6. Return validated AnalysisPlan
    """

def _fallback_plan(intent: str) -> AnalysisPlan:
    """Safety net. Always returns descriptive_stats as single analysis. Never fails."""

def _validate_plan(plan: AnalysisPlan, eligible: list[str], df) -> AnalysisPlan:
    """
    Remove analyses where:
    - analysis_id not in METHODOLOGY_REGISTRY
    - analysis_id in BLOCKED list
    - params reference columns that don't exist in df
    Re-number order after filtering.
    """
```

### 6.7 ai/interpreter.py

```python
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
```

---

## 7. ANALYSIS MODULE SPECS

### 7.1 AnalysisResult — Universal Return Type

```python
from dataclasses import dataclass, field

@dataclass
class AnalysisResult:
    analysis_name: str
    analysis_id: str
    success: bool
    data: dict                # raw results — full numbers for PDF
    summary: dict             # key metrics — rendered as rich.Table in terminal
    charts: list              # Plotly figures — PDF ONLY. Never shown in terminal.
    methodology: object       # MethodologyDefinition from METHODOLOGY_REGISTRY
    interpretation: str | None  # filled by interpreter.py after computation
    warning: str | None       # from validation — injected into AI prompt
    error: str | None

# Rules:
# - summary must be non-empty dict when success=True
# - charts must have at least 1 Plotly figure when success=True
# - If success=False: summary={}, charts=[], error=<message>
# - interpretation starts None — filled by interpreter.py separately
# - NEVER raise from analysis functions — always return AnalysisResult
```

### 7.2 analysis/methodology.py — All 23 Entries

```python
from dataclasses import dataclass

@dataclass
class MethodologyDefinition:
    title: str
    category: str       # "Descriptive"|"Regression"|"Clustering"|"Time Series"|
                        # "Dimensionality"|"Anomaly"|"Survival"|"Association"|"Business"
    overview: str
    when_to_use: str
    steps: list[str]
    assumptions: list[str]
    libraries_used: list[str]
    min_rows: int

METHODOLOGY_REGISTRY: dict[str, MethodologyDefinition] = {
    "descriptive_stats": MethodologyDefinition(
        title="Descriptive Statistics", category="Descriptive",
        overview="Summarizes central tendency, spread, and distribution of numeric columns.",
        when_to_use="Always a good starting point before any other analysis.",
        steps=["Compute mean/median/mode", "Compute std/variance/IQR/skewness/kurtosis",
               "Count missing and unique values", "Frequency counts for categorical columns",
               "Generate histograms + bar charts"],
        assumptions=["No specific assumptions required"],
        libraries_used=["pandas", "scipy.stats"], min_rows=1,
    ),
    "correlation": MethodologyDefinition(
        title="Correlation Analysis", category="Descriptive",
        overview="Measures linear relationships between numeric columns.",
        when_to_use="Use to identify which variables move together.",
        steps=["Compute Pearson correlation matrix", "Compute Spearman correlation matrix",
               "Identify top correlated pairs", "Generate heatmap + top-pairs chart"],
        assumptions=["Pearson assumes linearity; Spearman is non-parametric"],
        libraries_used=["pandas", "scipy.stats"], min_rows=10,
    ),
    "ttest": MethodologyDefinition(
        title="T-Test", category="Descriptive",
        overview="Tests whether means of two groups are significantly different.",
        when_to_use="Use when comparing a numeric metric between two groups.",
        steps=["Auto-detect test type (one-sample/independent/paired)",
               "Shapiro-Wilk normality test", "Levene equal-variance test",
               "Run t-test", "Report t-stat, p-value, CI, Cohen's d"],
        assumptions=["Approximately normal within groups", "Independent groups"],
        libraries_used=["scipy.stats"], min_rows=10,
    ),
    "anova": MethodologyDefinition(
        title="ANOVA", category="Descriptive",
        overview="Tests whether means differ across 3+ groups.",
        when_to_use="Use when comparing a numeric metric across 3 or more categories.",
        steps=["One-way ANOVA F-statistic and p-value",
               "Tukey HSD post-hoc if significant", "Report eta-squared effect size",
               "Generate box plots per group"],
        assumptions=["Normality within groups", "Homogeneity of variances"],
        libraries_used=["scipy.stats", "statsmodels"], min_rows=20,
    ),
    "chi_square": MethodologyDefinition(
        title="Chi-Square Test", category="Descriptive",
        overview="Tests whether two categorical variables are independent.",
        when_to_use="Use when both variables are categorical.",
        steps=["Build contingency table", "Compute expected frequencies",
               "Chi-square stat and p-value", "Cramer's V effect size",
               "Generate contingency heatmap"],
        assumptions=["Expected frequency >= 5 per cell", "Independent observations"],
        libraries_used=["scipy.stats"], min_rows=20,
    ),
    "mann_whitney": MethodologyDefinition(
        title="Mann-Whitney U Test", category="Descriptive",
        overview="Non-parametric alternative to T-Test. Compares two groups without normality assumption.",
        when_to_use="Use instead of T-Test when data is not normally distributed.",
        steps=["Rank all observations", "Compute U-statistic and p-value",
               "Rank-biserial correlation effect size", "Generate box plots + density plot"],
        assumptions=["Independent observations", "Ordinal or continuous data"],
        libraries_used=["scipy.stats"], min_rows=10,
    ),
    "regression_linear": MethodologyDefinition(
        title="Linear Regression", category="Regression",
        overview="Models the linear relationship between a target and predictor variables.",
        when_to_use="Use to predict a continuous value or understand predictor effects.",
        steps=["Select target and features", "80/20 train-test split",
               "Fit OLS regression", "Report R2, RMSE, MAE, coefficients with p-values",
               "Generate actual vs predicted scatter + residual plot"],
        assumptions=["Linear relationship", "Homoscedasticity", "Normal residuals"],
        libraries_used=["scikit-learn", "statsmodels"], min_rows=30,
    ),
    "regression_logistic": MethodologyDefinition(
        title="Logistic Regression", category="Regression",
        overview="Predicts probability of a binary outcome.",
        when_to_use="Use when target has two categories (yes/no, churn/retain).",
        steps=["Select binary target and features", "80/20 split",
               "Fit logistic regression", "Report accuracy, precision, recall, F1, AUC-ROC",
               "Generate ROC curve + confusion matrix"],
        assumptions=["Binary outcome", "Independent observations"],
        libraries_used=["scikit-learn"], min_rows=50,
    ),
    "regression_polynomial": MethodologyDefinition(
        title="Polynomial Regression", category="Regression",
        overview="Fits a curved relationship between a single predictor and target.",
        when_to_use="Use when the relationship is clearly curved.",
        steps=["Select target and single feature", "Auto-select degree 2-4 by R2",
               "Fit polynomial regression", "Report R2, RMSE, chosen degree",
               "Generate scatter + fitted curve + residual plot"],
        assumptions=["Polynomial relationship", "Approximately normal residuals"],
        libraries_used=["scikit-learn"], min_rows=20,
    ),
    "clustering_kmeans": MethodologyDefinition(
        title="K-Means Clustering", category="Clustering",
        overview="Groups data into K clusters based on feature similarity.",
        when_to_use="Use to find natural segments (customer segments, product groups).",
        steps=["Select numeric features", "Standardize with StandardScaler",
               "Elbow method K=2 to 10", "Fit K-Means with optimal K",
               "Report cluster sizes, silhouette score, centroids",
               "Generate elbow chart + 2D scatter (PCA-reduced)"],
        assumptions=["Spherical clusters", "Similar cluster sizes"],
        libraries_used=["scikit-learn"], min_rows=50,
    ),
    "clustering_dbscan": MethodologyDefinition(
        title="DBSCAN Clustering", category="Clustering",
        overview="Density-based clustering — finds arbitrary-shape clusters and labels outliers.",
        when_to_use="Use when clusters are not spherical or when outliers matter.",
        steps=["Select numeric features", "Standardize features",
               "Optimize epsilon via k-distance graph", "Fit DBSCAN",
               "Report cluster count, noise points, cluster sizes",
               "Generate 2D scatter with noise highlighted"],
        assumptions=["Density-based clusters present"],
        libraries_used=["scikit-learn"], min_rows=50,
    ),
    "clustering_hierarchical": MethodologyDefinition(
        title="Hierarchical Clustering", category="Clustering",
        overview="Builds a tree of clusters showing how data merges at different scales.",
        when_to_use="Use to visualize the hierarchy of groupings.",
        steps=["Select numeric features", "Standardize features",
               "Compute Ward linkage matrix", "Generate dendrogram + auto cut",
               "Report cluster sizes and within-cluster variance",
               "Generate dendrogram + 2D scatter"],
        assumptions=["Euclidean distance meaningful"],
        libraries_used=["scikit-learn", "scipy.cluster.hierarchy"], min_rows=20,
    ),
    "time_series_arima": MethodologyDefinition(
        title="ARIMA Forecast", category="Time Series",
        overview="Forecasts future values using past patterns.",
        when_to_use="Use when you have a date column and want to predict future values.",
        steps=["Detect date + target columns", "ADF stationarity test",
               "Auto-select ARIMA(p,d,q)", "Fit and forecast 30 periods",
               "Report AIC, RMSE, forecast + confidence intervals",
               "Generate historical + forecast line chart with confidence bands"],
        assumptions=["Stationary after differencing", "No missing dates"],
        libraries_used=["statsmodels"], min_rows=50,
    ),
    "time_series_prophet": MethodologyDefinition(
        title="Prophet Forecast", category="Time Series",
        overview="Forecasting with automatic seasonality detection.",
        when_to_use="Use for business time series with weekly/yearly seasonality.",
        steps=["Detect ds (date) and y (target) columns",
               "Fit Prophet with auto seasonality", "Forecast 90 days",
               "Decompose trend + weekly + yearly seasonality",
               "Generate forecast + component charts"],
        assumptions=["Regular intervals", "At least 2 full seasonal cycles"],
        libraries_used=["prophet"], min_rows=100,
    ),
    "granger_causality": MethodologyDefinition(
        title="Granger Causality", category="Time Series",
        overview="Tests whether one time series helps predict another.",
        when_to_use="Use to test if variable X leads variable Y.",
        steps=["Select two time series columns", "Stationarity test for both",
               "Granger test for lags 1-5", "Report F-stat and p-value per lag",
               "Generate dual line chart + p-value bar chart per lag"],
        assumptions=["Both series stationary", "> 50 time periods"],
        libraries_used=["statsmodels"], min_rows=50,
    ),
    "pca": MethodologyDefinition(
        title="PCA", category="Dimensionality",
        overview="Reduces many numeric columns into uncorrelated components.",
        when_to_use="Use to simplify high-dimensional data or visualize in 2D.",
        steps=["Select numeric columns", "Standardize features",
               "Compute principal components", "Calculate explained variance",
               "Generate scree plot + 2D biplot"],
        assumptions=["Linear relationships", "Numeric features"],
        libraries_used=["scikit-learn"], min_rows=30,
    ),
    "tsne": MethodologyDefinition(
        title="t-SNE", category="Dimensionality",
        overview="Non-linear 2D visualization of high-dimensional data.",
        when_to_use="Use to visualize clusters in complex datasets.",
        steps=["Select numeric columns", "Standardize",
               "Run t-SNE with auto perplexity", "Generate 2D scatter"],
        assumptions=["For visualization only — distances not directly interpretable"],
        libraries_used=["scikit-learn"], min_rows=50,
    ),
    "umap": MethodologyDefinition(
        title="UMAP", category="Dimensionality",
        overview="Faster alternative to t-SNE preserving global structure.",
        when_to_use="Use for large datasets where t-SNE is too slow.",
        steps=["Select numeric columns", "Standardize",
               "Fit UMAP with auto n_neighbors", "Generate 2D scatter"],
        assumptions=["Numeric features", "More data = better results"],
        libraries_used=["umap-learn"], min_rows=50,
    ),
    "anomaly_isolation_forest": MethodologyDefinition(
        title="Anomaly Detection (Isolation Forest)", category="Anomaly",
        overview="Identifies unusual data points that don't fit normal patterns.",
        when_to_use="Use to find outliers, fraud, or errors.",
        steps=["Select numeric columns", "Fit Isolation Forest (auto contamination)",
               "Score each row", "Report anomaly count + top anomalous rows",
               "Generate scatter with anomalies highlighted + score histogram"],
        assumptions=["Anomalies < 10% of data", "Numeric features"],
        libraries_used=["scikit-learn"], min_rows=50,
    ),
    "anomaly_zscore": MethodologyDefinition(
        title="Anomaly Detection (Z-Score)", category="Anomaly",
        overview="Flags values more than 3 standard deviations from the mean.",
        when_to_use="Use for simple outlier detection on normally-distributed data.",
        steps=["Compute z-score per numeric column",
               "Flag rows with |z| > 3", "Report anomaly count per column",
               "Generate scatter + histogram with threshold lines"],
        assumptions=["Approximately normally distributed data"],
        libraries_used=["scipy.stats"], min_rows=20,
    ),
    "survival_kaplan_meier": MethodologyDefinition(
        title="Kaplan-Meier Survival Analysis", category="Survival",
        overview="Estimates how long until an event occurs.",
        when_to_use="Use with duration + binary event columns (churn, failure, etc.).",
        steps=["Auto-detect duration (numeric) + event (binary) columns",
               "Fit Kaplan-Meier estimator",
               "Log-rank test if group column provided",
               "Report median survival, survival probabilities, at-risk table",
               "Generate survival curve + confidence bands"],
        assumptions=["Independent event times", "Non-informative censoring"],
        libraries_used=["lifelines"], min_rows=30,
    ),
    "market_basket": MethodologyDefinition(
        title="Market Basket Analysis", category="Association",
        overview="Finds items frequently appearing together in transactions.",
        when_to_use="Use with transactional data — needs transaction ID + item columns.",
        steps=["Detect transaction ID + item columns",
               "Build transaction-item matrix", "Run Apriori (min_support=0.01)",
               "Generate association rules (min_confidence=0.3, min_lift=1.0)",
               "Report top rules by lift", "Generate rules bar chart + network graph"],
        assumptions=["Transactional format data"],
        libraries_used=["mlxtend"], min_rows=100,
    ),
    "pareto": MethodologyDefinition(
        title="Pareto Analysis (80/20)", category="Business",
        overview="Identifies which items contribute 80% of total value.",
        when_to_use="Use to prioritize — find the few items driving most of the outcome.",
        steps=["Select category + numeric value columns",
               "Sort descending by value", "Compute cumulative percentage",
               "Mark 80% threshold",
               "Report top contributors", "Generate Pareto chart (bar + cumulative line)"],
        assumptions=["Additive numeric metric", "Mutually exclusive categories"],
        libraries_used=["pandas"], min_rows=5,
    ),
    "cohort": MethodologyDefinition(
        title="Cohort Analysis", category="Business",
        overview="Tracks how groups of users behave over time — measures retention.",
        when_to_use="Use with user ID + acquisition date + activity date.",
        steps=["Detect user ID + acquisition + activity date columns",
               "Assign users to monthly cohorts by first activity",
               "Compute retention rate per cohort per period",
               "Generate retention heatmap + retention curves"],
        assumptions=["Clear user acquisition date", "Parseable dates"],
        libraries_used=["pandas"], min_rows=100,
    ),
}
```

### 7.3 Analysis Function Pattern

Every analysis function follows this exact pattern. No exceptions.

```python
def run_X(df, params: dict) -> AnalysisResult:
    """
    Args:
        df: pandas DataFrame
        params: may contain None values — handle gracefully

    Returns:
        AnalysisResult — always. Never raises.
    """
    try:
        # ... computation ...
        return AnalysisResult(
            analysis_name="X",
            analysis_id="x",
            success=True,
            data={"full_results": ...},
            summary={"Key Metric": value, ...},   # non-empty dict
            charts=[plotly_fig_1, ...],            # at least 1 figure
            methodology=METHODOLOGY_REGISTRY["x"],
            interpretation=None,
            warning=None,
            error=None,
        )
    except Exception as e:
        get_logger(__name__).error(f"X failed: {e}")
        return AnalysisResult(
            analysis_name="X", analysis_id="x", success=False,
            data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["x"],
            interpretation=None, warning=None, error=str(e),
        )
```

### 7.4 analysis/__init__.py — ANALYSIS_REGISTRY

```python
# Import all run_* functions and expose them in one registry
ANALYSIS_REGISTRY: dict[str, callable] = {
    "descriptive_stats":        run_descriptive_stats,
    "correlation":              run_correlation,
    "ttest":                    run_ttest,
    "anova":                    run_anova,
    "chi_square":               run_chi_square,
    "mann_whitney":             run_mann_whitney,
    "regression_linear":        run_linear_regression,
    "regression_logistic":      run_logistic_regression,
    "regression_polynomial":    run_polynomial_regression,
    "clustering_kmeans":        run_kmeans,
    "clustering_dbscan":        run_dbscan,
    "clustering_hierarchical":  run_hierarchical,
    "time_series_arima":        run_arima,
    "time_series_prophet":      run_prophet,
    "granger_causality":        run_granger_causality,
    "pca":                      run_pca,
    "tsne":                     run_tsne,
    "umap":                     run_umap,
    "anomaly_isolation_forest": run_isolation_forest,
    "anomaly_zscore":           run_zscore,
    "survival_kaplan_meier":    run_kaplan_meier,
    "market_basket":            run_market_basket,
    "pareto":                   run_pareto,
    "cohort":                   run_cohort,
}
```

### 7.5 utils/analysis_validator.py

```python
from enum import Enum
from dataclasses import dataclass

class ValidationStatus(Enum):
    OK         = "ok"
    WARNING    = "warning"
    PREPROCESS = "preprocess"
    BLOCKED    = "blocked"

@dataclass
class ValidationResult:
    status: ValidationStatus
    user_message: str
    warning_context: str   # injected into AI interpretation prompt
    suggestions: list[str] # alternative analysis_ids if BLOCKED

def validate(analysis_id: str, df, params: dict = None) -> ValidationResult:
    """Validate one analysis. Never raises."""

def validate_all(df) -> dict[str, ValidationResult]:
    """Validate all 23 analyses. Returns {analysis_id: ValidationResult}."""
```

Key rules:
- market_basket       → BLOCKED if no transactional format
- survival_kaplan_meier → BLOCKED if no duration + binary event column pair
- cohort              → BLOCKED if no user ID + date columns
- time_series_*       → BLOCKED if no datetime column
- regression_logistic → BLOCKED if no binary target column
- Any analysis        → WARNING if rows < 100
- clustering_*        → WARNING if rows < 200
- ttest, mann_whitney → PREPROCESS if group column has > 2 unique values

---

## 8. TUI SPEC

### 8.1 tui/theme.py

```python
from rich.theme import Theme

THEME = Theme({
    "header":       "bold bright_blue",
    "subheader":    "dim white",
    "key":          "bold cyan",
    "label":        "white",
    "disabled":     "dim white",
    "success":      "bold green",
    "warning":      "bold yellow",
    "error":        "bold red",
    "info":         "dim cyan",
    "ai":           "italic white",
    "spinner":      "cyan",
    "panel.border": "grey50",
    "table.header": "bold bright_white on grey23",
})
```

### 8.2 tui/components.py

ONLY FILE THAT CREATES A Console INSTANCE. All other files import console from here.

```python
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from tui.theme import THEME

console = Console(theme=THEME)

def with_spinner(message: str, func, *args, **kwargs):
    """Run func while showing animated spinner. Transient — removes spinner when done."""
    with Live(
        Spinner("dots", text=message, style="spinner"),
        console=console, refresh_per_second=10, transient=True
    ):
        return func(*args, **kwargs)

def run_with_progress(items: list, process_func, description: str = "") -> list:
    """
    Run process_func on each item with a progress bar.
    Shows: spinner + item name + bar + count.
    Returns list of results.
    """
    results = []
    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  BarColumn(), TextColumn("{task.completed}/{task.total}"),
                  console=console) as progress:
        task = progress.add_task(description, total=len(items))
        for item in items:
            progress.update(task, description=f"Running {getattr(item, 'display_name', str(item))}...")
            result = process_func(item)
            results.append(result)
            progress.advance(task)
    return results

def print_header(title: str, subtitle: str = ""):
    console.rule(style="panel.border")
    console.print(f"[header]{title}[/]")
    if subtitle:
        console.print(f"[subheader]{subtitle}[/]")
    console.print()

def print_success(msg: str): console.print(f"[success]✅  {msg}[/]")
def print_error(msg: str):   console.print(f"[error]❌  {msg}[/]")
def print_warning(msg: str): console.print(f"[warning]⚠️  {msg}[/]")
def print_info(msg: str):    console.print(f"[info]ℹ️  {msg}[/]")

def build_summary_table(summary: dict, title: str = "") -> Table:
    """Build rich.Table from dict for analysis result display."""
    t = Table(title=title, show_header=True, header_style="table.header",
              border_style="panel.border")
    t.add_column("Metric", style="key", no_wrap=True)
    t.add_column("Value",  style="label")
    for k, v in summary.items():
        t.add_row(str(k), str(v))
    return t

def print_analysis_result(result):
    """
    Render AnalysisResult to terminal.
    Order: header → summary table → AI interpretation panel.
    Charts are NEVER shown — they are for PDF only.
    """
    status = "[success]✅[/]" if result.success else "[error]❌[/]"
    console.print(f"\n{status} [header]{result.analysis_name}[/]")
    console.rule(style="panel.border")

    if not result.success:
        print_error(f"Analysis failed: {result.error}")
        return

    # 1. Summary table — mandatory
    table = build_summary_table(result.summary)
    console.print(table)
    console.print()

    # 2. AI interpretation — mandatory
    interp = result.interpretation or "[dim]AI interpretation not available.[/]"
    console.print(Panel(interp, title="💬 AI Interpretation",
                        border_style="panel.border", padding=(1, 2)))
```

### 8.3 tui/app.py — Main Loop

```python
def run():
    """Called by main.py. Manages session and routes to screens."""
    session = {
        "filepath":     None,
        "filename":     None,
        "df":           None,
        "data_profile": None,
        "engine":       None,
        "session_id":   None,
        "api_manager":  None,
        "results":      [],   # AnalysisResult objects added to report
    }

    _print_banner()

    # Try to restore API manager from config + keychain
    from ai.api_manager import init_from_config
    session["api_manager"] = init_from_config()

    # First launch: no API keys → send to settings
    if session["api_manager"] is None:
        print_warning("No API key configured. Please add one in Settings.")
        from tui.screens.settings import run_settings
        run_settings(session)

    while True:
        _show_main_menu(session)
        key = _get_keypress()

        if   key in ("l", "L"): _load_data(session)
        elif key in ("a", "A"): _run_analyst(session)
        elif key in ("r", "R"): _run_analysis_picker(session)
        elif key in ("p", "P"): _run_profiler(session)
        elif key in ("e", "E"): _run_export(session)
        elif key in ("s", "S"): _run_settings(session)
        elif key in ("q", "Q"): _quit()
```

### 8.4 Main Menu Display

```
┌─────────────────────────────────────┐
│  TENRIX  •  v1.0                    │
│  sales_q3.xlsx  •  1,234 × 15 cols  │
└─────────────────────────────────────┘

  [L] Load data
  [A] Ask AI           ask what you want to find out
  [R] Run analysis     pick from 23 analyses
  [P] Profile data     data quality report
  [E] Export report    generate PDF
  [S] Settings         API keys, provider, language
  [Q] Quit

  >
```

Rules:
- Second header line: filename + shape when loaded, "No data loaded" when not
- [A][R][P][E] show as dim + "(load data first)" when df is None
- [A] additionally shows "(add API key in Settings)" when api_manager is None
- Single keypress. No Enter required for menu selection.
- After any screen returns: re-render main menu with updated header

### 8.5 tui/screens/analyst.py — Full Intent Flow

```
SCREEN FLOW:

1. print_header("ASK AI")
2. prompt_toolkit input: "What do you want to find out?\n> "
   (with history enabled — user can press up for previous questions)

3. with_spinner("Planning analysis...", planner.plan, ...)
   → If is_fallback: print_warning("AI unavailable — running basic analysis")
   → Print plan:
     "📋 I'll run N analyses to answer your question:"
     "  1. [analysis name] — [reason]"
     "  2. [analysis name] — [reason]"
     ""
     "  [Enter] Run all   [E] Edit plan   [C] Cancel"

4. If user picks E → show numbered list, allow removing items
5. If user picks C → return to main menu

6. run_with_progress(planned_analyses, _run_one_analysis)
   where _run_one_analysis:
     a. validate() → if BLOCKED: return failed result immediately
     b. run analysis func with with_spinner()
     c. get interpretation with with_spinner("Getting AI interpretation...")
     d. attach interpretation to result
     e. print_analysis_result(result) immediately

7. After all done:
   "[A] Ask another question   [+] Add all to report   [B] Back to menu"
```

### 8.6 tui/screens/settings.py

```
SCREEN FLOW:

1. print_header("SETTINGS")
2. Print current provider panel:
   Active: Google Gemini
   Model: gemini-2.5-flash
   Keys stored: 2  (Windows Credential Manager)
   Status: ✅ Connected

3. Menu:
   [1] Switch provider
   [2] Add API key
   [3] Remove API key
   [4] Test connection
   [5] Change model
   [6] Change language
   [B] Back

Add key flow:
   - Use prompt_toolkit with is_password=True for hidden input
   - with_spinner("Validating key...", api_manager.validate_current_key)
   - If valid: save_key() → print_success("Key saved to OS Keychain")
   - If invalid: print_error("Invalid key — please check and try again")
   - After add: api_manager.reload_keys()
```

### 8.7 tui/screens/report.py

```
SCREEN FLOW:

1. Print list of results marked for report
2. Toggle options:
   [✓] Cover page
   [✓] Data profile summary
   [✓] Analysis results
   [ ] Methodology details

3. Show output path (default ~/Downloads/Tenrix_Report_YYYY-MM-DD.pdf)
4. [Enter] Generate PDF

During generation — step progress:
   → "Rendering charts (1/N)..."
   → "Rendering charts (2/N)..."
   → "Building PDF..."
   → print_success(f"PDF saved: {output_path}")
   → "[O] Open file   [B] Back"
```

---

## 9. EXPORT SPEC

### export/chart_exporter.py

```python
def figure_to_png_bytes(fig) -> bytes:
    """Convert Plotly figure to PNG via kaleido. For PDF embedding only."""

def export_all_charts(results: list, output_dir: str) -> dict[str, list[str]]:
    """Export all charts from results as PNG files. Returns {result_id: [file_paths]}."""
```

### export/pdf_builder.py

```python
def build_report(
    results: list,
    data_profile: dict,
    file_name: str,
    output_path: str,
    include_cover: bool = True,
    include_profile: bool = True,
    include_methodology: bool = False,
) -> str:
    """
    Build PDF. Returns output_path on success.
    Shows step progress via tui/components.console during generation.
    """
```

PDF structure:
1. Cover — Tenrix branding, file name, date, analysis count
2. Data profile — rows/cols/quality score/key issues
3. Per analysis — chart(s) + statistics table + AI interpretation
4. Methodology appendix (optional)

---

## 10. MAIN ENTRY POINT

```python
# main.py
import sys
from utils.logger import get_logger

logger = get_logger(__name__)

def main():
    try:
        from tui.app import run
        run()
    except KeyboardInterrupt:
        print("\nGoodbye.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        print(f"\n❌ Unexpected error: {e}")
        print("Details logged to ~/.tenrix/tenrix.log")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## 11. REQUIREMENTS.TXT

```
rich>=13.7.0
prompt_toolkit>=3.0.43
pandas>=2.0.0
polars>=0.20.0
duckdb>=0.10.0
openpyxl>=3.1.0
xlrd>=2.0.1
chardet>=5.0.0
scipy>=1.13.0
statsmodels>=0.14.0
scikit-learn>=1.4.0
prophet>=1.1.5
lifelines>=0.28.0
mlxtend>=0.23.0
umap-learn>=0.5.0
google-generativeai>=0.7.0
openai>=1.30.0
groq>=0.9.0
httpx>=0.27.0
plotly>=5.20.0
kaleido>=0.2.1
weasyprint>=61.0
jinja2>=3.1.0
keyring>=24.0.0
psutil>=5.9.0
pytest>=8.0.0
pytest-cov>=5.0.0
pyinstaller>=6.0.0
```

---

*Tenrix Build Instructions v1.0*

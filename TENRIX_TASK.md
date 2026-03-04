# TENRIX — Build Task (Hands-Off Agent Execution)
> Execute steps in order. Run verify command after each step. Fix before proceeding.
> If verify fails: debug, fix, re-verify. Do NOT skip to next step.

---

## SETUP

```bash
mkdir -p tenrix/ai/providers tenrix/analysis tenrix/core tenrix/tui/screens
mkdir -p tenrix/export/templates tenrix/utils tenrix/tests/unit tenrix/tests/integration tenrix/tests/fixtures
touch tenrix/ai/__init__.py tenrix/ai/providers/__init__.py
touch tenrix/analysis/__init__.py tenrix/core/__init__.py
touch tenrix/tui/__init__.py tenrix/tui/screens/__init__.py
touch tenrix/export/__init__.py tenrix/utils/__init__.py tenrix/tests/__init__.py
touch tenrix/tests/unit/__init__.py tenrix/tests/integration/__init__.py
```

Create requirements.txt (full list from Build Instructions Section 11).
Create virtual environment and install all dependencies.

---

## PHASE 1 — FOUNDATION

### Step 1 — utils/logger.py
Build: File logger writing to ~/.tenrix/tenrix.log. get_logger(name) function. Never prints to terminal.
Verify:
```bash
cd tenrix && python -c "from utils.logger import get_logger; l=get_logger('test'); l.info('ok'); print('✅ logger')"
```

### Step 2 — core/config.py
Build: Load/save ~/.tenrix/config.json. All functions handle missing file gracefully. DEFAULT_CONFIG as spec.
Verify:
```bash
python -c "from core.config import load_config, get_active_provider, get_language; print('✅ config provider:', get_active_provider(), 'lang:', get_language())"
```

### Step 3 — core/keychain.py
Build: save_key, get_key, get_all_keys, delete_key, count_keys. Only file that imports keyring. Never raises. Never logs key values.
Verify:
```bash
python -c "
from core.keychain import save_key, get_key, delete_key, count_keys
assert save_key('test_prov', 'test_val_123', 0) == True
assert get_key('test_prov', 0) == 'test_val_123'
assert count_keys('test_prov') == 1
assert delete_key('test_prov', 0) == True
assert get_key('test_prov', 0) is None
print('✅ keychain — all operations verified')
"
```

### Step 4 — core/engine.py
Build: select_engine() by file size. read_file() returns (pandas_df, engine_name). Always returns pandas DataFrame.
Verify:
```bash
python -c "from core.engine import select_engine; assert select_engine.__doc__ is not None; print('✅ engine')"
```

### Step 5 — core/data_loader.py
Build: LoadSuccess, SheetSelectionRequired, LoadError dataclasses. load() function. sanitize_path(). Full encoding chain. Delimiter detection.
Verify:
```bash
python -c "
from core.data_loader import sanitize_path, LoadSuccess, LoadError, SheetSelectionRequired
assert sanitize_path('  \"my file.csv\" ') == 'my file.csv'
assert sanitize_path(\"  'data.xlsx'  \") == 'data.xlsx'
print('✅ data_loader — sanitize_path ok')
"
```
Also create tests/fixtures/sample_sales.csv (50+ rows, mixed types) and verify load() works on it.

### Step 6 — core/data_cleaner.py
Build: CleaningIssue dataclass. detect_issues(), apply_fix(), apply_all_fixes(). Never modifies input df.
Verify:
```bash
python -c "
import pandas as pd, numpy as np
from core.data_cleaner import detect_issues, apply_all_fixes
df = pd.DataFrame({'a': [1, None, 3, None, 5]*10, 'b': ['x','y']*25})
issues = detect_issues(df)
assert len(issues) > 0
new_df, summary = apply_all_fixes(df, [i for i in issues if i.auto_fixable])
print('✅ data_cleaner —', len(issues), 'issues detected')
"
```

---

## PHASE 2 — AI LAYER

### Step 7 — ai/base_provider.py
Build: AIProviderError dataclass. AIProvider abstract class with complete(), validate_key(), requires_api_key.
Verify:
```bash
python -c "from ai.base_provider import AIProvider, AIProviderError; print('✅ base_provider')"
```

### Step 8 — ai/providers/gemini.py
Build: GeminiProvider implementing AIProvider. Catches google SDK exceptions → AIProviderError. retryable=True for 429.
Verify:
```bash
python -c "from ai.providers.gemini import GeminiProvider; p = GeminiProvider('fake_key', 'gemini-2.5-flash'); assert p.requires_api_key == True; print('✅ gemini provider')"
```

### Step 9 — ai/providers/openai.py
Build: OpenAIProvider. Same pattern as Gemini.
Verify:
```bash
python -c "from ai.providers.openai import OpenAIProvider; p = OpenAIProvider('fake_key', 'gpt-4o-mini'); print('✅ openai provider')"
```

### Step 10 — ai/providers/groq.py
Verify:
```bash
python -c "from ai.providers.groq import GroqProvider; p = GroqProvider('fake_key', 'llama3-8b-8192'); print('✅ groq provider')"
```

### Step 11 — ai/providers/openrouter.py
Build: Uses httpx. Base URL https://openrouter.ai/api/v1.
Verify:
```bash
python -c "from ai.providers.openrouter import OpenRouterProvider; p = OpenRouterProvider('fake_key', 'mistralai/mistral-7b-instruct'); print('✅ openrouter provider')"
```

### Step 12 — ai/providers/ollama.py
Build: Uses httpx. Base URL from config. requires_api_key = False.
Verify:
```bash
python -c "from ai.providers.ollama import OllamaProvider; p = OllamaProvider('', 'llama3'); assert p.requires_api_key == False; print('✅ ollama provider')"
```

### Step 13 — ai/provider_registry.py
Build: PROVIDER_META dict with all 5 providers. get_provider(name, api_key, model). list_providers().
Verify:
```bash
python -c "
from ai.provider_registry import PROVIDER_META, list_providers, get_provider
assert len(list_providers()) == 5
assert set(list_providers()) == {'gemini','openai','groq','openrouter','ollama'}
p = get_provider('ollama', '', 'llama3')
print('✅ provider_registry — 5 providers registered')
"
```

### Step 14 — ai/api_manager.py
Build: APIManager class. Loads keys from keychain in __init__. call() with key rotation. switch_provider(), reload_keys(), validate_current_key(). AllKeysExhaustedError. init_from_config().
Verify:
```bash
python -c "
from ai.api_manager import APIManager, AllKeysExhaustedError, init_from_config
# Test init with no keys (should not crash)
mgr = APIManager('ollama', 'llama3')
print('✅ api_manager — initialized')
result = init_from_config()
print('  init_from_config returned:', type(result).__name__)
"
```

### Step 15 — ai/prompts.py
Build: SYSTEM_BASE, PLAN_INTENT_PROMPT, INTERPRET_RESULT_PROMPT strings. CONTEXT_CAPACITY dict. compress_profile(). compress_result().
Verify:
```bash
python -c "
from ai.prompts import SYSTEM_BASE, PLAN_INTENT_PROMPT, compress_profile, compress_result
assert '{intent}' in PLAN_INTENT_PROMPT
assert '{data_profile}' in PLAN_INTENT_PROMPT
profile = {'columns': {f'col{i}': {} for i in range(20)}, 'row_count': 100}
compressed = compress_profile(profile, 'ollama')
assert len(compressed.get('columns', {})) <= 10, 'low capacity should truncate to 10 cols'
compressed_high = compress_profile(profile, 'gemini')
assert len(compressed_high.get('columns', {})) == 20, 'high capacity should not truncate'
print('✅ prompts — compression verified')
"
```

### Step 16 — ai/planner.py
Build: PlannedAnalysis + AnalysisPlan dataclasses. plan() function — NEVER raises. _fallback_plan(). _validate_plan().
Verify:
```bash
python -c "
from ai.planner import _fallback_plan, _validate_plan, AnalysisPlan
import pandas as pd

# Fallback always works
p = _fallback_plan('test intent')
assert p.is_fallback == True
assert len(p.analyses) == 1
assert p.analyses[0].analysis_id == 'descriptive_stats'

# Validate removes unknown IDs
from ai.planner import PlannedAnalysis
fake_plan = AnalysisPlan(
    intent='test', summary='test',
    analyses=[
        PlannedAnalysis('descriptive_stats', 'Desc Stats', 'reason', {}, 1),
        PlannedAnalysis('FAKE_ID_XYZ', 'Fake', 'reason', {}, 2),
    ],
    disclaimer=None, is_fallback=False
)
df = pd.DataFrame({'a': range(10)})
validated = _validate_plan(fake_plan, ['descriptive_stats'], df)
assert len(validated.analyses) == 1, 'FAKE_ID should be removed'
assert validated.analyses[0].analysis_id == 'descriptive_stats'

print('✅ planner — fallback and validation verified')
"
```

### Step 17 — ai/interpreter.py
Build: interpret() function. Always compresses. Injects warning_context. Returns empty string on failure. Never raises.
Verify:
```bash
python -c "from ai.interpreter import interpret; print('✅ interpreter importable')"
```

---

## PHASE 3 — ANALYSIS FOUNDATION

### Step 18 — analysis/methodology.py
Build: MethodologyDefinition dataclass. METHODOLOGY_REGISTRY with ALL 23 entries (from Build Instructions Section 7.2). Every entry must have min_rows set.
Verify:
```bash
python -c "
from analysis.methodology import METHODOLOGY_REGISTRY, MethodologyDefinition
EXPECTED = {
    'descriptive_stats','correlation','ttest','anova','chi_square','mann_whitney',
    'regression_linear','regression_logistic','regression_polynomial',
    'clustering_kmeans','clustering_dbscan','clustering_hierarchical',
    'time_series_arima','time_series_prophet','granger_causality',
    'pca','tsne','umap',
    'anomaly_isolation_forest','anomaly_zscore',
    'survival_kaplan_meier','market_basket','pareto','cohort'
}
assert set(METHODOLOGY_REGISTRY.keys()) == EXPECTED, f'Missing: {EXPECTED - set(METHODOLOGY_REGISTRY.keys())}'
for k, v in METHODOLOGY_REGISTRY.items():
    assert v.min_rows >= 1, f'{k} has invalid min_rows'
    assert len(v.steps) >= 1, f'{k} has no steps'
print('✅ methodology — all 23 entries verified')
"
```

### Step 19 — utils/analysis_validator.py
Build: ValidationStatus enum. ValidationResult dataclass. validate(). validate_all() covering all 23 analyses with correct BLOCKED/WARNING/PREPROCESS/OK logic.
Verify:
```bash
python -c "
import pandas as pd, numpy as np
from utils.analysis_validator import validate_all, ValidationStatus

# Test with a simple numeric df
df = pd.DataFrame({'a': range(200), 'b': range(200), 'c': list('xy')*100})
results = validate_all(df)
assert len(results) == 23, f'Expected 23, got {len(results)}'

# market_basket should be BLOCKED (no transactional format)
assert results['market_basket'].status == ValidationStatus.BLOCKED

# descriptive_stats should be OK
assert results['descriptive_stats'].status == ValidationStatus.OK

# survival should be BLOCKED (no duration/event columns)
assert results['survival_kaplan_meier'].status == ValidationStatus.BLOCKED

print('✅ analysis_validator — 23 analyses, key rules verified')
"
```

---

## PHASE 4 — ANALYSIS MODULES

For EVERY analysis module in steps 20-30, use this verification template:

```bash
python -c "
import pandas as pd, numpy as np

# Create appropriate test DataFrame for this analysis type
df = pd.DataFrame({'a': np.random.randn(200), 'b': np.random.randn(200)})

from analysis.MODULENAME import run_FUNCTIONNAME
result = run_FUNCTIONNAME(df, {})

assert isinstance(result.success, bool), 'success must be bool'
if result.success:
    assert result.summary, 'summary must be non-empty when success=True'
    assert result.charts,  'charts must be non-empty when success=True'
    assert result.methodology is not None, 'methodology must not be None'
else:
    assert result.error, 'error message required when success=False'
print('✅ FUNCTIONNAME')
"
```

### Step 20 — analysis/statistics.py
Functions: run_descriptive_stats, run_correlation, run_ttest, run_anova, run_chi_square, run_mann_whitney
Test df needs: numeric cols + categorical col + enough rows for each test

### Step 21 — analysis/regression.py
Functions: run_linear_regression, run_logistic_regression, run_polynomial_regression
Test df needs: numeric target + features. For logistic: binary target (0/1).

### Step 22 — analysis/clustering.py
Functions: run_kmeans, run_dbscan, run_hierarchical
Test df needs: 2+ numeric columns, 100+ rows

### Step 23 — analysis/time_series.py
Functions: run_arima, run_prophet, run_granger_causality
Test df needs: datetime column + numeric column. 100+ rows.

### Step 24 — analysis/dimensionality.py
Functions: run_pca, run_tsne, run_umap
Test df needs: 5+ numeric columns, 100+ rows

### Step 25 — analysis/anomaly.py
Functions: run_isolation_forest, run_zscore
Test df needs: numeric columns, 100+ rows

### Step 26 — analysis/survival.py
Functions: run_kaplan_meier
Test df needs: duration column (positive numeric) + event column (binary 0/1)

### Step 27 — analysis/association.py
Functions: run_market_basket
Test df needs: transaction_id column + item column (transactional format). 500+ rows.

### Step 28 — analysis/business.py
Functions: run_pareto, run_cohort
Pareto test df: category column + numeric value column
Cohort test df: user_id + acquisition_date + activity_date. 200+ rows.

### Step 29 — analysis/__init__.py
Build: Import all run_* functions. Expose ANALYSIS_REGISTRY dict with all 23 entries.
Verify:
```bash
python -c "
from analysis import ANALYSIS_REGISTRY
from analysis.methodology import METHODOLOGY_REGISTRY
assert len(ANALYSIS_REGISTRY) == 23, f'Expected 23, got {len(ANALYSIS_REGISTRY)}'
assert set(ANALYSIS_REGISTRY.keys()) == set(METHODOLOGY_REGISTRY.keys()), 'Keys must match exactly'
print('✅ ANALYSIS_REGISTRY — 23 functions registered, keys match METHODOLOGY_REGISTRY')
"
```

### Step 30 — analysis/profiler.py
Build: profile(df) → dict with row_count, col_count, quality_score, column details, missing%, distributions.
Verify:
```bash
python -c "
import pandas as pd, numpy as np
from analysis.profiler import profile
df = pd.DataFrame({'a': np.random.randn(100), 'b': list('xy')*50, 'c': [None]*10 + list(range(90))})
p = profile(df)
assert 'row_count' in p
assert 'col_count' in p
assert 'quality_score' in p
assert 0 <= p['quality_score'] <= 100
print('✅ profiler — quality_score:', p['quality_score'])
"
```

---

## PHASE 5 — TESTS (run before building TUI)

### Step 31 — tests/conftest.py + fixtures

Create conftest.py with shared fixtures:
- small_df (50 rows, mixed types)
- timeseries_df (200 rows, datetime + numeric)
- transactional_df (1000 rows, transaction format)
- survival_df (100 rows, duration + event)
- mock_api_manager (returns canned JSON responses, never calls real API)

Create fixture CSV/XLSX files in tests/fixtures/.

### Step 32 — Run all unit tests
```bash
pytest tests/unit/ -v --tb=short
```
All must pass before proceeding to TUI phase.

---

## PHASE 6 — TUI

### Step 33 — tui/theme.py
Build: THEME (rich Theme), APP_NAME, APP_VERSION constants.
Verify:
```bash
python -c "from tui.theme import THEME, APP_NAME; print('✅ theme:', APP_NAME)"
```

### Step 34 — tui/components.py
Build: console instance. with_spinner(). run_with_progress(). print_header/success/error/warning/info(). build_summary_table(). print_analysis_result().
Verify:
```bash
python -c "
from tui.components import console, with_spinner, build_summary_table, print_analysis_result
import time
result = with_spinner('Testing spinner...', lambda: 'ok')
assert result == 'ok'
table = build_summary_table({'Rows': 100, 'Cols': 5})
console.print(table)
print('✅ components')
"
```

### Step 35 — core/session_store.py
Build: SQLite at ~/.tenrix/sessions.db. SessionStore class with create_session, save_result, get_results, get_recent_sessions, delete_session.
Verify:
```bash
python -c "
from core.session_store import SessionStore
store = SessionStore()
print('✅ session_store — DB initialized')
"
```

### Step 36 — tui/screens/home.py
Build: prompt_file_path() with PathCompleter. Load file flow with spinner. Handle SheetSelectionRequired (prompt user to pick sheet). Handle LoadError (print_error).

### Step 37 — tui/screens/profiler.py
Build: Show data quality report — quality score bar, column summary table, issues list. [C] Auto-Clean option.

### Step 38 — tui/screens/analyst.py
Build: Full intent → plan → run → inline results flow. with_spinner for planning. run_with_progress for analyses. print_analysis_result after each. Edit plan option. Add to report option.
This is the most complex screen — take time to get it right.

### Step 39 — tui/screens/settings.py
Build: Show current provider panel. Add/remove/test key flows. Switch provider. Change model. Change language.
Hidden input for API key using prompt_toolkit is_password=True.
Validate key with with_spinner() before saving.
Save to keychain, not config.

### Step 40 — tui/screens/report.py
Build: Show results list. Toggle options. Confirm output path. Generate PDF with step progress.

### Step 41 — tui/menus.py
Build: Helper functions for single-keypress input. Menu display utilities.

### Step 42 — tui/app.py
Build: run() function. Session dict init. Main menu loop. Route to screens. Re-render menu after each screen returns.
Verify:
```bash
python -c "from tui.app import run; print('✅ tui/app importable')"
```

---

## PHASE 7 — EXPORT

### Step 43 — export/chart_exporter.py
Build: figure_to_png_bytes() using kaleido. export_all_charts().
Verify:
```bash
python -c "
import plotly.graph_objects as go
from export.chart_exporter import figure_to_png_bytes
fig = go.Figure(go.Bar(x=['A','B'], y=[1,2]))
png = figure_to_png_bytes(fig)
assert len(png) > 1000, 'PNG too small — kaleido may not be working'
print('✅ chart_exporter —', len(png), 'bytes')
"
```

### Step 44 — export/templates/
Create: base.html, cover.html, analysis_block.html, styles.css
Professional PDF styling. Charts embedded as base64 PNG. Tables formatted. AI interpretation in styled box.

### Step 45 — export/pdf_renderer.py
Build: WeasyPrint + Jinja2 rendering. render_template() → HTML → PDF bytes.

### Step 46 — export/pdf_builder.py
Build: build_report() with step progress display. Charts exported → embedded in HTML → WeasyPrint → PDF file.
Verify:
```bash
python -c "from export.pdf_builder import build_report; print('✅ pdf_builder importable')"
```

---

## PHASE 8 — ENTRY POINT + PACKAGING

### Step 47 — main.py
Build: main() with try/except KeyboardInterrupt and general Exception. Logs unhandled errors to file. Never shows stack trace to user.
Verify:
```bash
python -c "import main; print('✅ main.py importable')"
```

### Step 48 — End-to-End Test
```bash
# Run full app manually:
python main.py

# Verify:
# 1. Banner shows
# 2. [L] loads sample_sales.csv without error
# 3. [P] shows profile with quality score
# 4. [A] accepts intent input
# 5. If API key configured: plan shows, analyses run, results display with table + interpretation
# 6. [E] generates PDF (if results added to report)
# 7. [S] shows settings, add/test key flow works
# 8. [Q] exits cleanly
```

### Step 49 — Integration Tests
```bash
pytest tests/integration/ -v --tb=short
```

### Step 50 — Full Test Suite
```bash
pytest tests/ -v --cov=. --cov-report=term-missing
# Target: >80% coverage on analysis/ and core/
```

### Step 51 — tenrix.spec + PyInstaller Build
Build tenrix.spec with:
- console=True (CLI app)
- All hidden imports from Agent Rules Section PYINSTALLER

```bash
pyinstaller tenrix.spec
```

### Step 52 — Smoke Test on Built Executable
```
[ ] tenrix.exe launches and shows main menu
[ ] [L] loads a CSV file correctly
[ ] [A] accepts input and shows plan (with valid API key)
[ ] Analysis runs and table appears in terminal
[ ] [E] generates PDF and file is valid
[ ] API key saves to Windows Credential Manager (verify with cmdkey /list)
[ ] Ctrl+C exits cleanly
[ ] Close terminal → no hanging processes
```

---

## DONE

When Step 52 checklist is complete, Tenrix is ready.

*Tenrix Task v1.0*

# TENRIX — Agent Rules
> Read this entire file before writing a single line of code.

---

## THE 5 RULES THAT CANNOT BE BROKEN

### Rule 1 — Architecture is Law
```
tui/screens/   → UI only. Call other modules. Never compute. Never import analysis/.
analysis/      → Compute only. Never print. Never import tui/ or ai/.
ai/            → AI calls only. Never import tui/ or analysis/.
core/          → Data + config + keychain. No analysis logic.
export/        → PDF only. No analysis. No TUI.
utils/         → Helpers only. No business logic.
```

### Rule 2 — Keychain is the ONLY Key Storage
```python
# ✅ ONLY correct way
from core.keychain import get_all_keys, save_key
keys = get_all_keys("gemini")

# ❌ FORBIDDEN — anywhere in codebase
import keyring                          # never import keyring outside core/keychain.py
config["keys"]["gemini"] = ["AIza..."]  # never store keys in config
logger.debug(f"key: {api_key[:4]}")    # never log any part of a key
```

### Rule 3 — Analysis Functions Never Raise
```python
# ✅ CORRECT
def run_regression(df, params) -> AnalysisResult:
    try:
        ...compute...
        return AnalysisResult(success=True, ...)
    except Exception as e:
        logger.error(f"regression failed: {e}")
        return AnalysisResult(success=False, error=str(e), ...)

# ❌ FORBIDDEN
def run_regression(df, params):
    result = scipy.stats.linregress(...)   # can raise — not caught
    return result                          # never returns AnalysisResult
```

Same for: ai/planner.py (always return AnalysisPlan), core/keychain.py (always return None on error), core/data_loader.py (always return LoadError, never raise).

### Rule 4 — Every Operation > 300ms Must Show a Spinner
```python
# ✅ CORRECT
result = with_spinner("Running Pareto Analysis...", run_pareto, df, params)

# ❌ FORBIDDEN — silent long operation
result = run_pareto(df, params)   # terminal appears frozen
```

Mandatory spinners for: file loading, data profiling, AI planning, every analysis run,
AI interpretation, PDF generation steps, API key validation.

### Rule 5 — Terminal Results Always Show Table + Interpretation
```python
# ✅ CORRECT — in print_analysis_result()
console.print(build_summary_table(result.summary))  # always
console.print(Panel(result.interpretation or "AI unavailable"))  # always

# ❌ FORBIDDEN
for fig in result.charts:
    fig.show()   # NEVER show charts in terminal — charts are for PDF only
```

---

## SELF-VERIFICATION COMMANDS

Run these after each module. If they fail, fix before moving on.

```bash
# After utils/logger.py
python -c "from utils.logger import get_logger; l=get_logger('test'); l.info('ok'); print('✅ logger')"

# After core/config.py
python -c "from core.config import load_config, get_active_provider; print('✅ config:', get_active_provider())"

# After core/keychain.py
python -c "from core.keychain import save_key, get_key, delete_key; save_key('test','val',0); assert get_key('test',0)=='val'; delete_key('test',0); print('✅ keychain')"

# After core/data_loader.py
python -c "from core.data_loader import sanitize_path; assert sanitize_path('  \"file.csv\" ') == 'file.csv'; print('✅ data_loader')"

# After ai/base_provider.py
python -c "from ai.base_provider import AIProvider, AIProviderError; print('✅ base_provider')"

# After ai/provider_registry.py
python -c "from ai.provider_registry import PROVIDER_META, list_providers; assert len(list_providers())==5; print('✅ provider_registry')"

# After ai/api_manager.py
python -c "from ai.api_manager import APIManager, AllKeysExhaustedError, init_from_config; print('✅ api_manager')"

# After ai/prompts.py
python -c "from ai.prompts import SYSTEM_BASE, PLAN_INTENT_PROMPT, compress_profile; compress_profile({}, 'gemini'); print('✅ prompts')"

# After ai/planner.py
python -c "from ai.planner import plan, _fallback_plan; p=_fallback_plan('test'); assert p.is_fallback; assert len(p.analyses)==1; print('✅ planner')"

# After analysis/methodology.py
python -c "from analysis.methodology import METHODOLOGY_REGISTRY; assert len(METHODOLOGY_REGISTRY)==23; print('✅ methodology:', len(METHODOLOGY_REGISTRY), 'analyses')"

# After analysis/__init__.py
python -c "from analysis import ANALYSIS_REGISTRY; assert len(ANALYSIS_REGISTRY)==23; print('✅ ANALYSIS_REGISTRY:', len(ANALYSIS_REGISTRY), 'functions')"

# After each analysis module (example for statistics.py)
python -c "
import pandas as pd, numpy as np
from analysis.statistics import run_descriptive_stats
df = pd.DataFrame({'a': np.random.randn(100), 'b': np.random.randn(100), 'c': ['x','y']*50})
r = run_descriptive_stats(df, {})
assert r.success, f'Failed: {r.error}'
assert r.summary, 'summary is empty'
assert r.charts,  'charts is empty'
assert r.methodology is not None, 'methodology is None'
print('✅ descriptive_stats')
"

# After utils/analysis_validator.py
python -c "
import pandas as pd, numpy as np
from utils.analysis_validator import validate_all, ValidationStatus
df = pd.DataFrame({'a': range(200), 'b': range(200)})
result = validate_all(df)
assert len(result) == 23, f'Expected 23, got {len(result)}'
print('✅ analysis_validator:', len(result), 'analyses validated')
"

# After tui/components.py
python -c "from tui.components import console, with_spinner, build_summary_table, print_analysis_result; print('✅ components')"

# After tui/app.py
python -c "from tui.app import run; print('✅ tui/app importable')"

# After main.py
python -c "import main; print('✅ main.py importable')"
```

---

## QUICK REFERENCE

```
User drags file to terminal
→ core/data_loader.sanitize_path()     strip quotes Windows adds
→ core/data_loader.load()              detect encoding + delimiter + engine
→ analysis/profiler.profile()          generate data_profile dict

User types intent
→ ai/planner.plan()                    intent → AnalysisPlan
  → utils/analysis_validator.validate_all()   filter BLOCKED
  → ai/prompts.compress_profile()             compress for provider
  → ai/api_manager.call()                     send to AI
  → core/keychain.get_all_keys()              keys loaded here

Analysis execution (per PlannedAnalysis)
→ utils/analysis_validator.validate()  check before run
→ analysis.ANALYSIS_REGISTRY[id]()    run Python computation
→ ai/interpreter.interpret()           get AI text
→ tui/components.print_analysis_result()  render to terminal

PDF export
→ export/chart_exporter.figure_to_png_bytes()  Plotly → PNG
→ export/pdf_builder.build_report()            assemble
→ export/pdf_renderer                          WeasyPrint → file

Settings / key management
→ tui/screens/settings.py             UI
→ core/keychain.save_key()            persist to OS Keychain
→ ai/api_manager.reload_keys()        refresh in-memory keys
→ core/config.py                      non-sensitive settings only
```

---

## HEAVY ANALYSES — USE THREADING

These 6 analyses MUST run in ThreadPoolExecutor to prevent terminal freeze:
- clustering_dbscan
- time_series_prophet
- clustering_hierarchical
- umap
- market_basket
- granger_causality

Pattern:
```python
import concurrent.futures

if analysis_id in HEAVY_ANALYSES:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(analysis_func, df, params)
        result = with_spinner(f"Running {name}...", future.result)
else:
    result = with_spinner(f"Running {name}...", analysis_func, df, params)
```

---

## PYINSTALLER — MANDATORY HIDDEN IMPORTS

tenrix.spec must explicitly list:
```
keyring, keyring.backends.Windows, keyring.backends.SecretService
prompt_toolkit, rich
prophet, prophet.forecaster
lifelines, lifelines.fitters
mlxtend, mlxtend.frequent_patterns
umap, umap.umap_
sklearn.utils._cython_blas, sklearn.neighbors._typedefs
scipy._lib.messagestream
weasyprint, weasyprint.text.ffi
kaleido, psutil, duckdb, polars
```

---

## NEW FEATURE CHECKLIST

Before marking any feature done:
- [ ] Logic in correct module (Rule 1)?
- [ ] If analysis: returns AnalysisResult with non-empty summary + charts?
- [ ] If AI call: goes through api_manager.call()?
- [ ] If key operation: goes through core/keychain.py?
- [ ] Error handled — never raises to caller?
- [ ] Visual feedback added for operations > 300ms?
- [ ] Methodology entry in METHODOLOGY_REGISTRY?
- [ ] requirements.txt updated if new dependency?
- [ ] Self-verification command passes?
- [ ] No API keys in any log?

---

*Tenrix Agent Rules v1.0*

"""Analyst screen - full intent -> plan -> run -> results flow."""
import concurrent.futures
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.history import InMemoryHistory
from tui.components import (console, print_header, print_success, print_error,
                            print_warning, print_info, with_spinner,
                            run_with_progress, print_analysis_result,
                            show_guardrail_warning, show_confidence,
                            show_counter_intuitive, show_refinement_options,
                            REFINEMENT_TEMPLATES)
from tui.menus import get_keypress
from ai.planner import plan as ai_plan
from ai.interpreter import interpret, find_counter_intuitive
from ai.executive_summary import generate_executive_summary
from analysis import ANALYSIS_REGISTRY
from analysis.methodology import METHODOLOGY_REGISTRY
from analysis.guardrails import check_assumptions
from analysis.confidence import calculate_confidence
from core.session import Session
from utils.analysis_validator import validate, ValidationStatus

_history = InMemoryHistory()

HEAVY_ANALYSES = {
    "clustering_dbscan", "time_series_prophet", "clustering_hierarchical",
    "umap", "market_basket", "granger_causality",
}


def run_analyst(session: dict) -> None:
    """Full intent -> plan -> run -> inline results flow."""
    if session.get("df") is None:
        print_warning("Load data first.")
        return
    if session.get("api_manager") is None:
        print_warning("Add an API key in Settings first.")
        return

    df = session["df"]
    api_manager = session["api_manager"]
    data_profile = session.get("data_profile", {})
    provider_name = api_manager.get_active_provider_name()
    
    if "session_obj" not in session:
        session["session_obj"] = Session(file_path=session.get("filename", "data"))
        
    session_obj = session["session_obj"]

    print_header("ASK AI", "What do you want to find out?")

    try:
        default_intent = session.pop("queued_intent", "")
        intent = pt_prompt(">> ", default=default_intent, history=_history)
    except (KeyboardInterrupt, EOFError):
        return

    if not intent.strip():
        return

    # Plan
    analysis_plan = with_spinner("Planning analysis...", ai_plan,
                                  api_manager, intent, df, data_profile, provider_name, session_obj)

    if analysis_plan.is_fallback:
        print_warning("AI unavailable - running basic analysis")

    # Show plan
    console.print(f"\n  [header]I'll run {len(analysis_plan.analyses)} analyses:[/]")
    has_custom = False
    for a in analysis_plan.analyses:
        color = "warning" if a.analysis_id == "ai_custom_reasoning" else "key"
        console.print(f"    {a.order}. [{color}]{a.display_name}[/] - {a.reason}")
        if a.analysis_id == "ai_custom_reasoning":
            has_custom = True

    if analysis_plan.disclaimer:
        print_info(f"  Note: {analysis_plan.disclaimer}")

    if has_custom:
        print_warning("\n  [bold]CAUTION:[/] One or more analyses use custom AI logic (Wild Logic).")
        console.print("  This might be less precise than standard statistics.")
        console.print(f"  [key][Enter][/] Confirm AI Logic   [key][E][/] Edit plan   [key][C][/] Cancel")
    else:
        console.print(f"\n  [key][Enter][/] Run all   [key][E][/] Edit plan   [key][C][/] Cancel")
    
    key = get_keypress()

    if key == "c":
        return
    elif key == "e":
        analysis_plan = _edit_plan(analysis_plan)
        if not analysis_plan.analyses:
            print_warning("No analyses remaining.")
            return

    # Run all analyses
    results = []
    language = session.get("language", "English")
    from core.config import get_language
    language = get_language()

    for planned in analysis_plan.analyses:
        # Validate
        validation = validate(planned.analysis_id, df, planned.params)
        if validation.status == ValidationStatus.BLOCKED:
            print_warning(f"Skipped {planned.display_name}: {validation.user_message}")
            continue

        # Run guardrails before analysis
        guardrail = check_assumptions(planned.analysis_id, df, planned.params, data_profile)
        show_guardrail_warning(guardrail)
        session_obj.guardrails[planned.analysis_id] = guardrail

        # Run analysis
        analysis_func = ANALYSIS_REGISTRY.get(planned.analysis_id)
        if not analysis_func:
            print_error(f"Unknown analysis: {planned.analysis_id}")
            continue

        if planned.analysis_id in HEAVY_ANALYSES:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(analysis_func, df, planned.params)
                result = with_spinner(f"Running {planned.display_name}...", future.result)
        else:
            result = with_spinner(f"Running {planned.display_name}...", analysis_func, df, planned.params)

        # Set warning context
        if validation.warning_context:
            result.warning = validation.warning_context
            
        # Calc confidence
        score, reasons = calculate_confidence(result, guardrail, data_profile, len(df))
        result.confidence_score = score
        result.confidence_reasons = reasons

        # Get AI interpretation
        counter_finding = None
        if result.success and api_manager:
            try:
                interp = with_spinner(
                    "Getting AI interpretation...",
                    interpret,
                    api_manager,
                    result.analysis_name,
                    result.analysis_id,
                    result.data,
                    {
                        "file": session.get("filename", ""),
                        "rows": len(df),
                        "cols": len(df.columns),
                        "user_question": intent,
                    },
                    provider_name,
                    language,
                    result.warning or "",
                )
                result.interpretation = interp
                
                # Check for counter-intuitive patterns
                counter_finding = with_spinner(
                    "Checking for hidden patterns...",
                    find_counter_intuitive,
                    api_manager,
                    result,
                    data_profile,
                    intent,
                    session_obj.all_findings,
                    provider_name
                )
            except Exception:
                pass

        # Display
        print_analysis_result(result)
        show_confidence(score, reasons)
        show_counter_intuitive(counter_finding)
        
        # Save to memory
        session_obj.add(intent, result, counter_finding)
        
        results.append(result)

    if not results:
        print_warning("No analyses completed.")
        return
        
    # Generate executive summary if we have new results
    session_obj.executive_summary = with_spinner(
        "Updating executive summary...",
        generate_executive_summary,
        session_obj,
        api_manager,
        session.get("filename", "dataset")
    )


    # Auto-add to report
    session["results"].extend(results)

    # Post-analysis Interactive Refinement
    show_refinement_options()
    
    while True:
        key = get_keypress()
        if key in REFINEMENT_TEMPLATES:
            session["queued_intent"] = REFINEMENT_TEMPLATES[key]
            run_analyst(session)
            break
        elif key == "5":
            run_analyst(session)
            break
        elif key in ("\r", "\n", "enter"):
            break


def _edit_plan(plan):
    """Let user remove analyses from plan."""
    while True:
        console.print("\n  Current plan:")
        for a in plan.analyses:
            console.print(f"    {a.order}. {a.display_name}")
        console.print(f"\n  Enter number to remove, or [key][D][/] Done:")
        key = get_keypress()
        if key == "d":
            break
        try:
            idx = int(key) - 1
            if 0 <= idx < len(plan.analyses):
                removed = plan.analyses.pop(idx)
                print_info(f"Removed: {removed.display_name}")
                # Renumber
                for i, a in enumerate(plan.analyses, 1):
                    a.order = i
        except (ValueError, IndexError):
            pass
    return plan

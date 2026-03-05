"""Main TUI application loop."""
from tui.components import (console, print_header, print_warning, print_info)
from tui.theme import APP_NAME, APP_VERSION
from tui.menus import get_keypress
from utils.logger import get_logger

logger = get_logger(__name__)


def run(initial_file: str | None = None):
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
        "source":       None, # SourceResult from connectors
        "data_profile_obj": None, # DataProfile dataclass for planner
    }

    _print_banner()

    # Try to restore API manager from config + keychain
    from ai.api_manager import init_from_config
    session["api_manager"] = init_from_config()

    # Direct file load from CLI
    if initial_file:
        from tui.screens.home import perform_load
        perform_load(session, initial_file)

    # First launch: no API keys -> send to settings
    if session["api_manager"] is None:
        print_warning("No API key configured. Please add one in Settings.")
        from tui.screens.settings import run_settings
        run_settings(session)

    while True:
        _show_main_menu(session)
        key = get_keypress()

        if   key in ("l",): _load_data(session)
        elif key in ("a",): _run_analyst(session)
        elif key in ("r",): _run_analysis_picker(session)
        elif key in ("p",): _run_profiler(session)
        elif key in ("e",): _run_export(session)
        elif key in ("s",): _run_settings(session)
        elif key in ("t",): _run_about()
        elif key in ("q",): _quit()


def _print_banner():
    from rich.panel import Panel
    from rich.align import Align
    from rich.text import Text
    
    # Large ASCII Art for TENRIX (Solid & Professional)
    banner_text_large = [
        "████████ ███████ ███    ██ ██████  ██ ██   ██",
        "   ██    ██      ████   ██ ██   ██ ██  ██ ██ ",
        "   ██    █████   ██ ██  ██ ██████  ██   ███  ",
        "   ██    ██      ██  ██ ██ ██   ██ ██  ██ ██ ",
        "   ██    ███████ ██   ████ ██   ██ ██ ██   ██"
    ]
    
    # Small ASCII Art (Fallback for small terminals)
    banner_text_small = [
        " ▀█▀ █▀▀ █▄ █ █▀█ █ ▀▄▀",
        "  █  ██▄ █ ▀█ █▀▄ █ █ █"
    ]
    
    # Responsive based on terminal width
    width = console.size.width
    lines = banner_text_large if width > 60 else banner_text_small
    
    # Pad lines to exact same length to prevent centering distortion
    max_len = max(len(line) for line in lines)
    padded_lines = [line.ljust(max_len) for line in lines]
    btn_text = "\n".join(padded_lines)
    
    # Left justify the text block itself, so ASCII art keeps its shape
    banner = Text(btn_text, style="header", justify="left", no_wrap=True, overflow="crop")
    
    # Subtitle
    subtitle = Text(f"\n\nv{APP_VERSION} | AI-Powered Data Analysis", style="subheader", justify="center")
    
    # Render using Align.center for the whole block
    artist_panel = Panel(
        Align.center(banner + subtitle),
        border_style="panel.border",
        padding=(1, 2),
    )
    console.print()
    console.print(artist_panel)
    console.print()


def _show_main_menu(session: dict):
    console.print()
    # Header
    if session.get("filename"):
        df = session["df"]
        info = f"{session['filename']}  |  {len(df):,} x {len(df.columns)} cols"
        console.print(f"  [subheader]{info}[/]")
    else:
        console.print(f"  [disabled]No data loaded[/]")
    console.print()

    has_data = session.get("df") is not None
    has_ai = session.get("api_manager") is not None

    console.print(f"  [key][L][/] Load data")

    if has_data and has_ai:
        console.print(f"  [key][A][/] Ask AI           [subheader]ask what you want to find out[/]")
    elif has_data:
        console.print(f"  [disabled][A] Ask AI           (add API key in Settings)[/]")
    else:
        console.print(f"  [disabled][A] Ask AI           (load data first)[/]")

    if has_data:
        console.print(f"  [key][R][/] Run analysis     [subheader]pick from 24 analyses[/]")
        console.print(f"  [key][P][/] Profile data     [subheader]data quality report[/]")
        console.print(f"  [key][E][/] Export report    [subheader]generate PDF & Excel[/]")
    else:
        console.print(f"  [disabled][R] Run analysis     (load data first)[/]")
        console.print(f"  [disabled][P] Profile data     (load data first)[/]")
        console.print(f"  [disabled][E] Export report    (load data first)[/]")

    console.print(f"  [key][S][/] Settings         [subheader]API keys, provider, language[/]")
    console.print(f"  [key][T][/] About            [subheader]What is Tenrix?[/]")
    console.print(f"  [key][Q][/] Quit")
    console.print()


def _load_data(session):
    from tui.screens.home import run_home
    run_home(session)


def _run_analyst(session):
    if session.get("df") is None:
        print_warning("Load data first.")
        return
    if session.get("api_manager") is None:
        print_warning("Add an API key in Settings first.")
        return
    from tui.screens.analyst import run_analyst
    run_analyst(session)


def _run_analysis_picker(session):
    """Direct analysis picker with numbered list."""
    if session.get("df") is None:
        print_warning("Load data first.")
        return

    from analysis import ANALYSIS_REGISTRY
    from analysis.methodology import METHODOLOGY_REGISTRY
    from utils.analysis_validator import validate_all, ValidationStatus
    from tui.components import with_spinner, print_analysis_result

    print_header("RUN ANALYSIS", "Select from available analyses")

    validations = with_spinner("Validating...", validate_all, session["df"])

    ids = list(ANALYSIS_REGISTRY.keys())
    for i, aid in enumerate(ids, 1):
        meth = METHODOLOGY_REGISTRY[aid]
        v = validations[aid]
        if v.status == ValidationStatus.BLOCKED:
            console.print(f"  [disabled]{i:2d}. {meth.title} (BLOCKED: {v.user_message})[/]")
        elif v.status == ValidationStatus.WARNING:
            console.print(f"  [warning]{i:2d}. {meth.title} (WARNING)[/]")
        else:
            console.print(f"  [key]{i:2d}.[/] {meth.title}")

    console.print(f"\n  [key][B][/] Back")
    try:
        from prompt_toolkit import prompt as pt_prompt
        choice = pt_prompt("\n  Select analysis number: ")
        if choice.lower() == "b":
            return
        idx = int(choice) - 1
        if 0 <= idx < len(ids):
            aid = ids[idx]
            v = validations[aid]
            if v.status == ValidationStatus.BLOCKED:
                print_warning(f"Cannot run: {v.user_message}")
                return

            func = ANALYSIS_REGISTRY[aid]
            result = with_spinner(f"Running {METHODOLOGY_REGISTRY[aid].title}...", func, session["df"], {})
            print_analysis_result(result)
            session["results"].append(result)
    except (ValueError, KeyboardInterrupt, EOFError):
        pass


def _run_profiler(session):
    if session.get("df") is None:
        print_warning("Load data first.")
        return
    from tui.screens.profiler import run_profiler
    run_profiler(session)


def _run_export(session):
    if session.get("df") is None:
        print_warning("Load data first.")
        return
    from tui.screens.report import run_report
    run_report(session)


def _run_settings(session):
    from tui.screens.settings import run_settings
    run_settings(session)


def _run_about():
    from rich.panel import Panel
    from rich.align import Align
    from tui.components import console
    import os
    
    # Clear screen for a clean view
    os.system('cls' if os.name == 'nt' else 'clear')
    _print_banner()

    about_text = """
[bold]Tenrix[/bold] is a CLI-based data analysis tool that combines
23 statistical methods with artificial intelligence. 

Users simply type a question in natural language — Tenrix
automatically formulates an analysis plan, runs the
appropriate statistics, and delivers an AI interpretation
directly in the terminal.

[dim]Built by aska[/dim]
"""
    
    panel = Panel(
        Align.center(about_text),
        title="[bold green]About Tenrix[/]",
        border_style="green",
        padding=(1, 4),
        expand=False
    )
    
    console.print()
    console.print(Align.center(panel))
    console.print()
    console.print(Align.center("[key][Enter][/] Back to Main Menu"))
    
    try:
        from prompt_toolkit import prompt as pt_prompt
        pt_prompt("")
    except (KeyboardInterrupt, EOFError):
        pass


def _quit():
    from tui.components import print_info
    print_info("Goodbye!")
    import sys
    sys.exit(0)

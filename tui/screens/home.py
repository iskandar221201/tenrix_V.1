"""Home screen - file loading with multi-source connectors."""
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import PathCompleter
from tui.components import (console, print_header, print_success, print_error,
                            print_warning, print_info, with_spinner)
from core.data_loader import sanitize_path, DataProfile
from core.connectors import load_source, SourceResult
from core.session_store import SessionStore
from analysis.profiler import profile

import numpy as np
import pandas as pd


def run_home(session: dict) -> None:
    """File loading flow with multi-source support."""
    print_header("LOAD DATA",
                 "Drag a file to the terminal, or type the path\n"
                 "  Supported: .csv .tsv .xlsx .xls .db .sqlite .sql")

    try:
        raw_path = pt_prompt(
            "File path: ",
            completer=PathCompleter(),
        )
    except (KeyboardInterrupt, EOFError):
        return

    if not raw_path.strip():
        print_warning("No path entered.")
        return

    file_path = sanitize_path(raw_path)

    # Use multi-source connector
    try:
        source: SourceResult = load_source(file_path)
    except (FileNotFoundError, ValueError) as e:
        print_error(str(e))
        return
    except Exception as e:
        print_error(f"Failed to load file: {e}")
        return

    df = source.merged

    # Store source and dataframe in session
    session["filepath"] = source.file_path
    session["filename"] = __import__("os").path.basename(source.file_path)
    session["df"] = df
    session["engine"] = "pandas"
    session["source"] = source

    # Profile data
    session["data_profile"] = with_spinner("Profiling data...", profile, df)

    # Build DataProfile for AI planner with source_info
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
    date_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    session["data_profile_obj"] = DataProfile(
        columns=df.columns.tolist(),
        row_count=len(df),
        numeric_columns=numeric_cols,
        categorical_columns=categorical_cols,
        date_columns=date_cols,
        missing_count=int(df.isnull().sum().sum()),
        duplicate_count=int(df.duplicated().sum()),
        source_info={
            "type":           source.source_type,
            "sheet_names":    source.sheet_names,
            "multi_sheet":    len(source.sheet_names) > 1,
            "join_available": source.source_type in ("sqlite", "sql_dump"),
            "table_schemas":  source.table_schemas() if len(source.sheet_names) > 1 else "",
            "file":           source.file_path,
        },
    )

    # Create session
    class _MockLoadResult:
        def __init__(self, s):
            self.file_name = __import__("os").path.basename(s.file_path)
            self.row_count = len(s.merged)
            self.col_count = len(s.merged.columns)
            self.engine = "pandas"

    store = SessionStore()
    session["session_id"] = store.create_session(source.file_path, _MockLoadResult(source))

    print_success(f"Loaded: {session['filename']}")
    print_info(f"  {len(df):,} rows x {len(df.columns)} columns | Source: {source.source_type}")
    if len(source.sheet_names) > 1:
        print_info(f"  Sheets/Tables: {', '.join(source.sheet_names)}")
    quality = session["data_profile"].get("quality_score", 0)
    print_info(f"  Data quality: {quality:.0f}%")

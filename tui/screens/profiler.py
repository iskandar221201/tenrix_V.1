"""Data profiler screen."""
from tui.components import (console, print_header, print_success, print_warning,
                            print_info, build_summary_table, with_spinner)
from tui.menus import get_keypress
from core.data_cleaner import detect_issues, apply_all_fixes


def run_profiler(session: dict) -> None:
    """Show data quality report."""
    if session.get("df") is None:
        print_warning("Load data first.")
        return

    df = session["df"]
    profile = session.get("data_profile", {})

    print_header("DATA PROFILE", session.get("filename", ""))

    # Quality score
    quality = profile.get("quality_score", 0)
    bar_len = 30
    filled = int(quality / 100 * bar_len)
    bar = "=" * filled + "-" * (bar_len - filled)
    color = "success" if quality >= 80 else ("warning" if quality >= 50 else "error")
    console.print(f"  Data Quality: [{color}][{bar}] {quality:.0f}%[/]\n")

    # Summary table
    summary = {
        "Rows": f"{profile.get('row_count', 0):,}",
        "Columns": profile.get("col_count", 0),
        "Numeric Columns": profile.get("numeric_columns", 0),
        "Categorical Columns": profile.get("categorical_columns", 0),
        "Total Missing": f"{profile.get('total_missing', 0):,} ({profile.get('total_missing_pct', 0):.1f}%)",
        "Duplicate Rows": f"{profile.get('duplicate_rows', 0):,}",
    }
    console.print(build_summary_table(summary, "Overview"))
    console.print()

    # Column details
    columns = profile.get("columns", {})
    if columns:
        from rich.table import Table
        col_table = Table(title="Column Summary", show_header=True,
                         header_style="table.header", border_style="panel.border")
        col_table.add_column("Column", style="key")
        col_table.add_column("Type", style="label")
        col_table.add_column("Missing", style="label")
        col_table.add_column("Unique", style="label")

        for name, info in columns.items():
            missing_str = f"{info.get('missing', 0)} ({info.get('missing_pct', 0):.1f}%)"
            col_table.add_row(name, info.get("type", ""), missing_str, str(info.get("unique", "")))

        console.print(col_table)
        console.print()

    # Issues
    issues = with_spinner("Checking for issues...", detect_issues, df)
    if issues:
        console.print(f"  [warning]Found {len(issues)} issue(s):[/]")
        for issue in issues:
            severity_color = {"high": "error", "medium": "warning", "low": "info"}.get(issue.severity, "info")
            fix_label = " (auto-fixable)" if issue.auto_fixable else ""
            console.print(f"    [{severity_color}]{issue.severity.upper()}[/] {issue.column}: {issue.fix_description}{fix_label}")
        console.print()

        auto_fixable = [i for i in issues if i.auto_fixable]
        if auto_fixable:
            console.print("  [key][C][/] Auto-clean data   [key][B][/] Back")
            key = get_keypress()
            if key == "c":
                new_df, summary = with_spinner("Cleaning data...", apply_all_fixes, df, auto_fixable)
                session["df"] = new_df
                from analysis.profiler import profile as do_profile
                session["data_profile"] = with_spinner("Re-profiling...", do_profile, new_df)
                print_success(f"Applied {len(summary.get('applied', []))} fixes")
                for fix in summary.get("applied", []):
                    print_info(f"  {fix}")
    else:
        print_success("No issues detected!")

    console.print("\n  Press any key to go back...")
    get_keypress()

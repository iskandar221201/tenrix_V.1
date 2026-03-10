"""Report screen - PDF + Excel export configuration and generation."""
from pathlib import Path
from datetime import datetime
from core.report_path import ReportPathBuilder
from tui.components import (console, print_header, print_success, print_error,
                            print_warning, print_info)
from tui.menus import get_keypress
from prompt_toolkit import prompt as pt_prompt


def run_report(session: dict) -> None:
    """Report export screen — generates both PDF and Excel."""
    results = session.get("results", [])
    if not results:
        print_warning("No results to export. Run analyses first and add them to the report.")
        return

    print_header("EXPORT REPORT", f"{len(results)} analyses ready")

    # Show results list
    for i, r in enumerate(results, 1):
        status = "[success]OK[/]" if r.success else "[error]FAIL[/]"
        console.print(f"  {i}. {status} {r.analysis_name}")
    console.print()

    # Toggle options
    include_cover = True
    include_profile = True
    include_methodology = False

    console.print("  Report options:")
    console.print(f"  [success][x][/] Cover page")
    console.print(f"  [success][x][/] Data profile summary")
    console.print(f"  [success][x][/] Analysis results")
    console.print(f"  [ ] Methodology details")
    if session.get("export_code"):
        console.print(f"  [success][x][/] Python code script")
    console.print()

    # Output paths
    # Output paths
    session_filename = session.get("filename", "data")
    path_builder = ReportPathBuilder(source_path=session_filename)

    console.print(f"  [dim]→ Reports akan disimpan di: {path_builder.display_folder}[/dim]")
    
    prompt_text = "Generate PDF + Excel" + (" + Python Script" if session.get("export_code") else "")
    console.print(f"\n  [key][Enter][/] {prompt_text}   [key][C][/] Cancel")
    key = get_keypress()

    if key == "c":
        return

    from tui.components import with_spinner
    export_results = {}

    # Extract session features
    session_obj = session.get("session_obj")
    guardrails = session_obj.guardrails if session_obj else {}
    exec_summary = session_obj.executive_summary if session_obj else ""

    # ── PDF Export ─────────────────────────────────────────────────────────
    try:
        from export.pdf_builder import build_report

        output_path = with_spinner(
            "Generating PDF report...",
            build_report,
            results,
            session.get("data_profile", {}),
            session_filename,
            path_builder.pdf,
            include_cover=include_cover,
            include_profile=include_profile,
            include_methodology=include_methodology,
            guardrails=guardrails,
            exec_summary=exec_summary,
        )
        export_results["pdf"] = ("ok", str(output_path))
    except Exception as e:
        export_results["pdf"] = ("error", str(e))

    # ── Excel Export ──────────────────────────────────────────────────────
    try:
        from export.excel_exporter import export_excel

        excel_output = with_spinner(
            "Generating Excel report...",
            export_excel,
            results,
            session.get("data_profile", {}),
            path_builder.excel,
            session_filename,
            guardrails=guardrails,
            exec_summary=exec_summary,
        )
        export_results["xlsx"] = ("ok", str(excel_output))
    except Exception as e:
        export_results["xlsx"] = ("error", str(e))

    # ── Python Code Export ────────────────────────────────────────────────
    if session.get("export_code"):
        try:
            from export.code_exporter import CodeExporter
            
            # Reattach file_path properties dynamically to match core exporter needs
            session_obj.file_path = session_filename
            exporter = CodeExporter(session_obj)
            
            code_output = with_spinner(
                "Exporting Python code...",
                exporter.export,
                output_path=str(path_builder.code)
            )
            export_results["py"] = ("ok", str(code_output))
        except Exception as e:
            export_results["py"] = ("error", str(e))

    # ── Show summary ──────────────────────────────────────────────────────
    console.print("\n[bold]Export results:[/bold]")

    for fmt, (status, detail) in export_results.items():
        if status == "ok":
            icon  = "✅"
            label = "[green]saved[/green]"
            console.print(f"  {icon} [bold]{fmt.upper()}[/bold] {label} → {detail}")
        else:
            icon  = "❌"
            label = "[red]failed[/red]"
            console.print(f"  {icon} [bold]{fmt.upper()}[/bold] {label} — {detail}")

    all_failed = all(status == "error" for status, _ in export_results.values())
    if all_failed:
        console.print(
            "\n[yellow]⚠ All exports failed. "
            "Analysis data is still available in the current session.[/yellow]"
        )
    else:
        # Show final exact output folder location
        console.print()
        console.print(f"[dim]📁 Semua file tersimpan di:[/dim]")
        console.print(f"[cyan]   {path_builder.folder}[/cyan]")

    console.print(f"\n  [key][B][/] Back to menu")
    get_keypress()

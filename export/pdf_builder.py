"""PDF report builder."""
import base64
from datetime import datetime
from export.chart_exporter import figure_to_png_bytes
from export.pdf_renderer import render_template, html_to_pdf
from utils.logger import get_logger

logger = get_logger(__name__)


def build_report(
    results: list,
    data_profile: dict,
    file_name: str,
    output_path: str,
    include_cover: bool = True,
    include_profile: bool = True,
    include_methodology: bool = False,
    guardrails: dict = None,
    exec_summary: str = "",
) -> str:
    """
    Build PDF. Returns output_path on success.
    Shows step progress via tui/components.console during generation.
    """
    html_parts = []

    # Cover page
    if include_cover:
        cover = render_template(
            "cover.html",
            file_name=file_name,
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            analysis_count=len(results),
        )
        html_parts.append(cover)

    # Executive Summary (if provided)
    if exec_summary:
        exec_html = f'<div class="page-break"></div><h2>Executive Summary</h2><div class="exec-summary">{exec_summary.replace(chr(10), "<br>")}</div>'
        html_parts.append(exec_html)

    # Data profile section
    if include_profile and data_profile:
        profile_html = _build_profile_html(data_profile)
        html_parts.append(profile_html)

    # Analysis blocks
    for i, result in enumerate(results):
        if not result.success:
            continue

        # Export charts to base64
        chart_b64_list = []
        for fig in result.charts:
            try:
                png = figure_to_png_bytes(fig)
                if png:
                    chart_b64_list.append(base64.b64encode(png).decode("utf-8"))
            except Exception as e:
                logger.error(f"Chart export failed: {e}")

        # Guardrail template insertion
        guardrail_html = ""
        if guardrails and result.analysis_id in guardrails:
            g = guardrails[result.analysis_id]
            guardrail_html = render_template(
                "guardrail_box.html",
                passed=g.passed,
                violations=g.violations
            )

        block = render_template(
            "analysis_block.html",
            analysis_name=result.analysis_name,
            charts=chart_b64_list,
            summary=result.summary,
            interpretation=result.interpretation or "",
        )
        # Inject guardrail right before the charts/summary if we don't have a placeholder in analysis_block.html yet
        if guardrail_html:
            block = block.replace("<h2>", guardrail_html + "<h2>", 1) if "<h2>" in block else guardrail_html + block

        html_parts.append(block)

    # Methodology appendix
    if include_methodology:
        meth_html = _build_methodology_html(results)
        html_parts.append(meth_html)

    # Wrap in base template
    full_content = "\n".join(html_parts)
    full_html = render_template("base.html", content=full_content)

    # Render to PDF
    html_to_pdf(full_html, output_path)
    return output_path


def _build_profile_html(profile: dict) -> str:
    """Build data profile HTML section."""
    html = '<div class="profile-section">'
    html += '<h2>Data Profile</h2>'
    html += '<table class="summary-table">'
    html += '<thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>'

    items = {
        "Rows": f"{profile.get('row_count', 0):,}",
        "Columns": profile.get("col_count", 0),
        "Quality Score": f"{profile.get('quality_score', 0):.0f}%",
        "Missing Values": f"{profile.get('total_missing', 0):,}",
        "Duplicate Rows": f"{profile.get('duplicate_rows', 0):,}",
    }
    for k, v in items.items():
        html += f'<tr><td>{k}</td><td>{v}</td></tr>'

    html += '</tbody></table></div>'
    html += '<div class="page-break"></div>'
    return html


def _build_methodology_html(results: list) -> str:
    """Build methodology appendix."""
    html = '<div class="page-break"></div>'
    html += '<h2>Methodology Appendix</h2>'

    for result in results:
        if not result.success or not result.methodology:
            continue
        m = result.methodology
        html += f'<h3>{m.title}</h3>'
        html += f'<p><strong>Category:</strong> {m.category}</p>'
        html += f'<p>{m.overview}</p>'
        html += '<p><strong>Steps:</strong></p><ol>'
        for step in m.steps:
            html += f'<li>{step}</li>'
        html += '</ol>'
        html += f'<p><strong>Assumptions:</strong> {", ".join(m.assumptions)}</p>'

    return html

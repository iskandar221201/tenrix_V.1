from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from tui.theme import THEME

console = Console(theme=THEME)


def with_spinner(message: str, func, *args, **kwargs):
    """Run func while showing animated spinner. Transient - removes spinner when done."""
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


def print_success(msg: str): console.print(f"[success]  {msg}[/]")
def print_error(msg: str):   console.print(f"[error]  {msg}[/]")
def print_warning(msg: str): console.print(f"[warning]  {msg}[/]")
def print_info(msg: str):    console.print(f"[info]  {msg}[/]")


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
    Order: header -> rich summary -> AI interpretation panel.
    Charts are NEVER shown -- they are for PDF only.
    """
    status = "[success]✅[/]" if result.success else "[error]❌[/]"
    console.print(f"\n{status} [header]{result.analysis_name}[/]")
    console.rule(style="panel.border")

    if not result.success:
        print_error(f"Analysis failed: {result.error}")
        return

    # 1. Rich summary (new) — replaces plain table
    _print_rich_summary(result)

    # 2. AI interpretation — unchanged
    interp = result.interpretation or "[dim]AI interpretation not available.[/]"
    console.print(Panel(interp, title="💬 AI Interpretation",
                        border_style="panel.border", padding=(1, 2)))


def _print_rich_summary(result):
    """
    Render a rich terminal summary based on analysis_id.
    Each analysis type gets a custom layout showing its most important numbers.
    Falls back to plain key-value table if no custom layout defined.
    """
    aid = result.analysis_id
    data = result.data
    summary = result.summary

    if aid == "pareto":
        _print_pareto_summary(data, summary)
    elif aid == "correlation":
        _print_correlation_summary(data, summary)
    elif aid == "descriptive_stats":
        _print_descriptive_summary(data, summary)
    elif aid in ("time_series_arima", "time_series_prophet"):
        _print_forecast_summary(data, summary)
    elif aid in ("clustering_kmeans", "clustering_dbscan", "clustering_hierarchical"):
        _print_clustering_summary(data, summary)
    elif aid in ("regression_linear", "regression_logistic", "regression_polynomial"):
        _print_regression_summary(data, summary)
    elif aid in ("anomaly_isolation_forest", "anomaly_zscore"):
        _print_anomaly_summary(data, summary)
    else:
        # Generic fallback — plain key-value table
        console.print(build_summary_table(summary))


def _print_pareto_summary(data: dict, summary: dict):
    """Bar-style breakdown showing top contributors."""
    top_items = data.get("top_items", [])   # list of {label, value, pct, cumulative_pct}
    threshold = summary.get("80% Threshold Items", "?")
    total_cats = summary.get("Total Categories", "?")

    console.print(f"\n  [key]Top Contributors to 80% of Revenue:[/]")
    console.print(f"  [dim]{'─' * 52}[/]")

    max_val = max((i.get("value", 0) for i in top_items), default=1)
    for i, item in enumerate(top_items, 1):
        label   = str(item.get("label", ""))[:18].ljust(18)
        value   = item.get("value", 0)
        pct     = item.get("pct", 0)
        cum_pct = item.get("cumulative_pct", 0)
        bar_len = int((value / max_val) * 20)
        bar     = "█" * bar_len
        marker  = " [warning]← 80%[/]" if abs(cum_pct - 80) < 5 else ""
        console.print(
            f"  [key]{i:2}.[/] [label]{label}[/]  "
            f"[success]{bar:<20}[/]  "
            f"[key]{pct:5.1f}%[/]{marker}"
        )

    console.print(f"  [dim]{'─' * 52}[/]")
    console.print(f"  [info]{threshold} of {total_cats} categories = 80% of revenue[/]\n")


def _print_correlation_summary(data: dict, summary: dict):
    """Show top correlated pairs ranked by strength."""
    pairs = data.get("top_pairs", [])   # list of {col1, col2, pearson, spearman}

    console.print(f"\n  [key]Strongest Correlations:[/]")
    console.print(f"  [dim]{'─' * 55}[/]")

    for i, p in enumerate(pairs[:8], 1):
        col1    = str(p.get("col1", ""))
        col2    = str(p.get("col2", ""))
        r       = p.get("pearson", 0)
        label   = f"{col1} × {col2}"[:38].ljust(38)
        bar_len = int(abs(r) * 15)
        bar     = "█" * bar_len
        color   = "success" if abs(r) > 0.7 else "warning" if abs(r) > 0.4 else "info"
        sign    = "+" if r >= 0 else "-"
        console.print(
            f"  [key]{i}.[/] [label]{label}[/]  "
            f"[{color}]{bar:<15}[/]  [{color}]{sign}{abs(r):.4f}[/]"
        )

    console.print(f"  [dim]{'─' * 55}[/]\n")


def _print_descriptive_summary(data: dict, summary: dict):
    """Key stats in a clean two-column layout."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="key",   no_wrap=True)
    table.add_column(style="label", no_wrap=True)
    table.add_column(style="key",   no_wrap=True)
    table.add_column(style="label", no_wrap=True)

    items = list(summary.items())
    mid   = (len(items) + 1) // 2
    left  = items[:mid]
    right = items[mid:]

    for i in range(max(len(left), len(right))):
        lk, lv = left[i]  if i < len(left)  else ("", "")
        rk, rv = right[i] if i < len(right) else ("", "")
        table.add_row(str(lk), str(lv), str(rk), str(rv))

    console.print()
    console.print(table)
    console.print()


def _print_forecast_summary(data: dict, summary: dict):
    """Forecast direction + peak/low month + next 30-day outlook."""
    trend     = summary.get("Trend Direction", "unknown").upper()
    peak_m    = data.get("peak_month", "?")
    low_m     = data.get("low_month", "?")
    forecast  = data.get("forecast_values", [])

    trend_icon  = "📈" if trend == "UP" else "📉" if trend == "DOWN" else "➡️"
    trend_color = "success" if trend == "UP" else "error" if trend == "DOWN" else "info"

    console.print(f"\n  [{trend_color}]{trend_icon}  Trend: {trend}[/]")

    if peak_m != "?":
        import calendar
        peak_name = calendar.month_name[int(peak_m)] if str(peak_m).isdigit() else peak_m
        low_name  = calendar.month_name[int(low_m)]  if str(low_m).isdigit()  else low_m
        console.print(f"  [key]Peak month:[/]  [success]{peak_name}[/]")
        console.print(f"  [key]Low month:[/]   [warning]{low_name}[/]")

    if forecast:
        next_30 = forecast[:30]
        avg_val = sum(r.get("yhat", 0) for r in next_30) / len(next_30)
        console.print(f"  [key]30-day avg forecast:[/]  [label]{avg_val:,.0f}[/]")

    console.print()


def _print_clustering_summary(data: dict, summary: dict):
    """Cluster sizes as a visual breakdown."""
    clusters    = data.get("cluster_sizes", {})   # {cluster_id: size}
    silhouette  = summary.get("Silhouette Score", None)
    n_clusters  = summary.get("Clusters", len(clusters))

    console.print(f"\n  [key]Clusters Found: {n_clusters}[/]")
    if silhouette:
        try:
            color = "success" if float(silhouette) > 0.5 else "warning"
            console.print(f"  [key]Silhouette Score:[/] [{color}]{silhouette}[/]  "
                          f"[dim](>0.5 = well-separated)[/]")
        except (ValueError, TypeError):
             console.print(f"  [key]Silhouette Score:[/] [label]{silhouette}[/]")

    total = sum(clusters.values()) or 1
    console.print(f"  [dim]{'─' * 40}[/]")
    for cid, size in sorted(clusters.items(), key=lambda x: -x[1]):
        pct     = size / total * 100
        bar_len = int(pct / 3)
        bar     = "█" * bar_len
        console.print(
            f"  [key]Cluster {cid}:[/]  [success]{bar:<34}[/]  "
            f"[label]{size:,} rows ({pct:.1f}%)[/]"
        )
    console.print()


def _print_regression_summary(data: dict, summary: dict):
    """R², RMSE, and top coefficients."""
    r2      = summary.get("R-Squared", summary.get("AUC-ROC", "?"))
    rmse    = summary.get("RMSE", "?")
    coeffs  = data.get("coefficients", {})   # {feature: coeff_value}

    try:
        r2_f    = float(r2)
        r2_color = "success" if r2_f > 0.7 else "warning" if r2_f > 0.4 else "error"
        r2_bar  = "█" * int(r2_f * 20)
        console.print(f"\n  [key]R²:[/]    [{r2_color}]{r2_bar:<20}[/]  [{r2_color}]{r2_f:.4f}[/]")
    except (ValueError, TypeError):
        console.print(f"\n  [key]Score:[/] [label]{r2}[/]")

    if rmse != "?":
        console.print(f"  [key]RMSE:[/]  [label]{rmse}[/]")

    if coeffs:
        console.print(f"\n  [key]Top Feature Coefficients:[/]")
        sorted_c = sorted(coeffs.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        for feat, coef in sorted_c:
            sign  = "[success]+[/]" if coef >= 0 else "[error]-[/]"
            console.print(f"    {sign} [label]{feat}[/]: [key]{coef:+.4f}[/]")

    console.print()


def _print_anomaly_summary(data: dict, summary: dict):
    """Anomaly count + rate prominently displayed."""
    count   = summary.get("Anomaly Count", summary.get("Anomalies Found", "?"))
    rate    = summary.get("Anomaly Rate", "?")
    top_rows = data.get("top_anomalies", [])   # list of row dicts

    try:
        rate_f  = float(str(rate).replace("%", ""))
        color   = "error" if rate_f > 5 else "warning" if rate_f > 2 else "success"
    except (ValueError, TypeError):
        color   = "warning"

    console.print(f"\n  [{color}]⚠️  Anomalies detected: {count}  ({rate})[/]")

    if top_rows:
        console.print(f"\n  [key]Most anomalous rows:[/]")
        for i, row in enumerate(top_rows[:5], 1):
            score = row.get("anomaly_score", "")
            idx   = row.get("index", i)
            console.print(f"    [key]{i}.[/] Row {idx}  [dim]score: {score}[/]")

    console.print()


def show_guardrail_warning(guardrail):
    """Tampilkan peringatan guardrail dalam panel kuning jika ada asumsi statistik yang gagal."""
    if not guardrail or not guardrail.has_violations():
        return

    failed = [v for v in guardrail.violations if not v.passed]
    if not failed:
        return

    lines = ["[error]Analisis ini mungkin tidak akurat karena asumsi dasar statistik tidak terpenuhi:[/]\n"]
    for v in failed:
        lines.append(f"• {v.message}")
    
    lines.append("\n[dim]Hasil tetap ditampilkan, tetapi mohon interpretasikan dengan hati-hati.[/dim]")
    
    console.print(Panel(
        "\n".join(lines),
        title="⚠️ Peringatan Kualitas Data",
        border_style="warning",
        padding=(1, 2)
    ))


def show_confidence(score: float, reasons: list[str]):
    """Tampilkan bar confidence (0-100%) dan alasan penalti."""
    from analysis.confidence import confidence_bar
    bar = confidence_bar(score, width=20)
    
    console.print(f"\n[key]Tingkat Kepercayaan Hasil:[/] {bar}")
    
    if score < 0.8 and reasons:
        console.print("[dim]Penalti karena:[/dim]")
        for reason in reasons:
            console.print(f" [error]- {reason}[/]")
    console.print()


def show_counter_intuitive(finding: str | None):
    """Tampilkan insight counter-intuitive dalam panel khusus (disorot)."""
    if not finding:
        return
        
    console.print(Panel(
        f"[label]{finding}[/]",
        title="🕵️ Temuan Tersembunyi",
        border_style="warning",
        padding=(1, 2)
    ))


REFINEMENT_TEMPLATES = {
    "1": "Gali lebih dalam segment ini",
    "2": "Cari akar masalah mengapa ini terjadi",
    "3": "Prediksi tren ini ke depan",
    "4": "Bandingkan dengan rata-rata keseluruhan",
}

def show_refinement_options():
    """Tampilkan menu pilihan refinement interaktif untuk melanjutkan analisis."""
    console.print("\n[key]Langkah Selanjutnya:[/]")
    from rich.columns import Columns
    
    options = []
    for k, v in REFINEMENT_TEMPLATES.items():
        options.append(f"[info][{k}][/] [label]{v}[/]")
    options.append("[info][5][/] [label]Ketik pertanyaan kustom...[/]")
    options.append("[info][Enter][/] [label]Selesai sesi ini[/]")
    
    console.print(Columns(options, equal=True, expand=True))
    console.print()


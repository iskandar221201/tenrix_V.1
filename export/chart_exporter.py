"""Chart exporter - Plotly figures to PNG bytes via kaleido."""
import os
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)


def figure_to_png_bytes(fig, width: int = 800, height: int = 500) -> bytes:
    """Convert Plotly figure to PNG via kaleido. For PDF embedding only."""
    try:
        return fig.to_image(format="png", width=width, height=height, engine="kaleido")
    except Exception as e:
        logger.error(f"figure_to_png_bytes failed: {e}")
        # Return minimal placeholder
        return b""


def export_all_charts(results: list, output_dir: str) -> dict[str, list[str]]:
    """Export all charts from results as PNG files. Returns {result_id: [file_paths]}."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    chart_files = {}

    for i, result in enumerate(results):
        if not result.success or not result.charts:
            continue

        result_key = f"{result.analysis_id}_{i}"
        paths = []
        for j, fig in enumerate(result.charts):
            try:
                png_bytes = figure_to_png_bytes(fig)
                if png_bytes:
                    path = os.path.join(output_dir, f"{result_key}_chart_{j}.png")
                    with open(path, "wb") as f:
                        f.write(png_bytes)
                    paths.append(path)
            except Exception as e:
                logger.error(f"Failed to export chart {j} for {result.analysis_id}: {e}")

        if paths:
            chart_files[result_key] = paths

    return chart_files

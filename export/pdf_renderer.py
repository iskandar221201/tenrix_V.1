"""PDF renderer using WeasyPrint + Jinja2."""
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from utils.logger import get_logger

logger = get_logger(__name__)

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def get_env() -> Environment:
    return Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def render_template(template_name: str, **kwargs) -> str:
    """Render a Jinja2 template to HTML string."""
    env = get_env()
    template = env.get_template(template_name)
    return template.render(**kwargs)


def html_to_pdf(html_content: str, output_path: str) -> str:
    """Convert HTML to PDF using WeasyPrint."""
    try:
        from weasyprint import HTML
        css_path = os.path.join(TEMPLATE_DIR, "styles.css")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        html = HTML(string=html_content, base_url=TEMPLATE_DIR)
        html.write_pdf(output_path)
        return output_path
    except Exception as e:
        logger.error(f"PDF rendering failed: {e}")
        raise

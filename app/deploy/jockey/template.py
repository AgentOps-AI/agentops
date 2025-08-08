"""Template rendering utilities for Jockey.

Provides helpers for rendering Jinja2 templates from the templates directory.
"""

from pathlib import Path
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader


TEMPLATES_DIR = Path(__file__).parent / 'templates'


def render_template(template_path: str, template_vars: Dict[str, Any]) -> str:
    """Render a template with the given variables.

    Args:
        template_path: Path to template file relative to templates directory (e.g., 'docker/python-agent.j2')
        template_vars: Dictionary of variables to pass to the template

    Returns:
        str: Rendered template content

    Raises:
        FileNotFoundError: If the template file doesn't exist
    """
    full_template_path = TEMPLATES_DIR / template_path

    if not full_template_path.exists():
        raise FileNotFoundError(f"Template '{template_path}' not found in templates directory")

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template(template_path)

    return template.render(**template_vars)

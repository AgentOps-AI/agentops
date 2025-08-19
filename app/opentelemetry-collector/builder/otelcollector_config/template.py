"""
Template renderer for OpenTelemetry Collector configuration.

This module provides functionality to render Jinja2 templates for the OpenTelemetry Collector
configuration files, particularly for dynamically generating the processors configuration
with model cost data.
"""

from typing import Dict, Any, Optional
import os
import shutil

import jinja2
from agentops.semconv import (
    SpanAttributes,
)

from builder.conf import CONFIG_DIR
from builder.costs import ModelCost, load_model_costs


renderer: jinja2.Environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(CONFIG_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _get_shared_context() -> Dict[str, Any]:
    """Get the shared context for rendering templates."""
    # TODO make sure all of these are populated in AgentOps SDK.
    return {
        "SEMCONV": {
            # meta
            "AGENTOPS_PROJECT_ID": "agentops.project.id",
            # tokens
            "LLM_USAGE_TOTAL_TOKENS": SpanAttributes.LLM_USAGE_TOTAL_TOKENS,
            "LLM_USAGE_PROMPT_TOKENS": SpanAttributes.LLM_USAGE_PROMPT_TOKENS,
            "LLM_USAGE_COMPLETION_TOKENS": SpanAttributes.LLM_USAGE_COMPLETION_TOKENS,
            "LLM_USAGE_CACHE_CREATION_INPUT_TOKENS": SpanAttributes.LLM_USAGE_CACHE_CREATION_INPUT_TOKENS,
            "LLM_USAGE_CACHE_READ_INPUT_TOKENS": SpanAttributes.LLM_USAGE_CACHE_READ_INPUT_TOKENS,
            "LLM_USAGE_REASONING_TOKENS": SpanAttributes.LLM_USAGE_REASONING_TOKENS,
            "LLM_USAGE_STREAMING_TOKENS": SpanAttributes.LLM_USAGE_STREAMING_TOKENS,
            # models
            "LLM_REQUEST_MODEL": SpanAttributes.LLM_REQUEST_MODEL,
            "LLM_RESPONSE_MODEL": SpanAttributes.LLM_RESPONSE_MODEL,
            # cost
            "LLM_USAGE_PROMPT_COST": "gen_ai.usage.prompt_cost",
            "LLM_USAGE_COMPLETION_COST": "gen_ai.usage.completion_cost",
        }
    }


def _render_template(template_name: str, context: Dict[str, Any], output_dir: str) -> None:
    """
    Render a template with the given context.

    Args:
        template_name: Name of the template to render
        context: Dictionary of variables to pass to the template
        output_path: Optional path to write the rendered template
                     If None, the rendered template is only returned
    """
    template = renderer.get_template(template_name)
    output_path = f"{output_dir}/{template_name.replace('.tpl', '')}"

    os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(template.render(**context))

    print(f"Rendered template {template_name} to {output_path}")


def render_base_config(output_dir: Optional[str] = None) -> None:
    """
    Render the base configuration template.

    Args:
        output_path: Optional path to write the rendered template.
                     If None, the rendered template is only returned.
    """
    # wee don't transform this file, so just copy it to the output path
    shutil.copy(
        os.path.join(CONFIG_DIR, "base.yaml"),
        os.path.join(output_dir, "base.yaml"),
    )


def render_processors_config(output_dir: Optional[str] = None) -> None:
    """
    Render the processors.yaml.tpl template with model costs.

    Args:
        output_path: Optional path to write the rendered template.
                     If None, the rendered template is only returned.
    """
    model_costs: list[ModelCost] = load_model_costs()
    context = {
        "MODEL_COSTS": [m.model_dump() for m in model_costs],
        **_get_shared_context(),
    }

    return _render_template("processors.yaml.tpl", context, output_dir)

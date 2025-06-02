#!/usr/bin/env python3
"""
Script to generate integration MDX files from Jupyter notebooks.

This script converts a Jupyter notebook from the examples/ directory into a
corresponding .mdx file in docs/v2/integrations/, including proper frontmatter,
GitHub link, SOURCE_FILE comment, transformed %pip install commands, and
boilerplate scripts.

Usage:
    python examples/generate_integration_mdx.py examples/langchain_examples/langchain_examples.ipynb
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def get_folder_and_title(notebook_path):
    """Extract folder name and generate title from notebook path."""
    folder_name = Path(notebook_path).parent.name
    title = folder_name.replace("_", " ").title()
    if not title.endswith(" Integration"):
        title += " Integration"
    return folder_name, title


def convert_notebook_to_markdown(notebook_path):
    """Convert Jupyter notebook to markdown using jupyter nbconvert."""
    try:
        result = subprocess.run(
            ["jupyter", "nbconvert", "--to", "markdown", "--stdout", notebook_path],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        sys.exit(f"Error: Failed to convert notebook: {e}\nstderr: {e.stderr}")
    except FileNotFoundError:
        sys.exit("Error: jupyter nbconvert not found. Please install jupyter: pip install jupyter")


def transform_pip_installs(markdown_content):
    """Transform %pip install commands to a single CodeGroup format under Installation section."""
    # Extract all %pip install dependencies using regex
    pip_pattern = r"^%pip install (.+)$"
    dependencies = []

    for match in re.finditer(pip_pattern, markdown_content, re.MULTILINE):
        deps = match.group(1).strip()
        dependencies.append(deps)

    if not dependencies:
        return markdown_content

    # Combine all dependencies and clean up flags
    combined_deps = " ".join(dependencies)
    combined_deps = re.sub(r"-U\s+", "", combined_deps).strip()
    if not combined_deps.startswith("-U"):
        combined_deps = "-U " + combined_deps

    # Remove all %pip install lines and their containing code blocks
    # This regex removes code blocks that contain only %pip install commands
    content = re.sub(r"```python\n(?:%pip install[^\n]*\n)+```\n?", "", markdown_content)

    # Remove any remaining standalone %pip install lines
    content = re.sub(r"^%pip install.*$\n?", "", content, flags=re.MULTILINE)

    # Remove empty code blocks
    content = re.sub(r"```python\n\s*```\n?", "", content)

    # Create installation section
    installation_section = f"""## Installation
<CodeGroup>
```bash pip
pip install {combined_deps}
```
```bash poetry
poetry add {combined_deps}
```
```bash uv
uv add {combined_deps}
```
</CodeGroup>

"""

    # Find insertion point (after frontmatter links but before first content)
    lines = content.split("\n")
    insert_index = 0
    for idx, line in enumerate(lines):
        if line.strip() and not line.startswith("_View Notebook") and not line.startswith("{/*"):
            insert_index = idx
            break

    # Insert installation section
    lines.insert(insert_index, installation_section.rstrip())

    return "\n".join(lines)


# MDX template for consistent formatting
MDX_TEMPLATE = """---
title: {title}
description: "Learn how to integrate {integration_name} with AgentOps."
---

_View Notebook on <a href={{'https://github.com/AgentOps-AI/agentops/blob/main/{notebook_path}'}} target={{'_blank'}}>Github</a>_

{{/*  SOURCE_FILE: {notebook_path}  */}}

{content}

<script type="module" src="/scripts/github_stars.js"></script>
<script type="module" src="/scripts/scroll-img-fadein-animation.js"></script>
<script type="module" src="/scripts/button_heartbeat_animation.js"></script>
<script type="css" src="/styles/styles.css"></script>"""


def construct_mdx_content(notebook_path, folder_name):
    """Construct the complete .mdx file content using template."""
    folder_name, title = get_folder_and_title(notebook_path)
    integration_name = title.replace(" Integration", "")

    # Convert notebook and transform pip installs
    markdown_content = convert_notebook_to_markdown(notebook_path)
    processed_content = transform_pip_installs(markdown_content)

    return MDX_TEMPLATE.format(
        title=title, integration_name=integration_name, notebook_path=notebook_path, content=processed_content
    )


def validate_notebook_path(notebook_path):
    """Validate the notebook path and return clean folder name."""
    if not os.path.exists(notebook_path):
        sys.exit(f"Error: Notebook file not found: {notebook_path}")

    if not notebook_path.endswith(".ipynb"):
        sys.exit(f"Error: File must be a Jupyter notebook (.ipynb): {notebook_path}")

    if not notebook_path.startswith("examples/"):
        sys.exit(f"Error: Notebook must be in the examples/ directory: {notebook_path}")

    folder_name = Path(notebook_path).parent.name
    return folder_name.replace("_examples", "")


def main():
    parser = argparse.ArgumentParser(description="Generate integration MDX files from Jupyter notebooks")
    parser.add_argument("notebook_path", help="Path to the Jupyter notebook")

    notebook_path = parser.parse_args().notebook_path
    clean_folder_name = validate_notebook_path(notebook_path)
    output_path = Path(f"docs/v2/integrations/{clean_folder_name}.mdx")

    print(f"Processing: {notebook_path} -> {output_path}")

    # Generate and write MDX content
    mdx_content = construct_mdx_content(notebook_path, clean_folder_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(mdx_content, encoding="utf-8")

    print(f"Successfully generated: {output_path}")


if __name__ == "__main__":
    main()

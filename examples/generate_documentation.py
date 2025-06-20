#!/usr/bin/env python3
"""
Script to generate example MDX files from Jupyter notebooks.

This script converts a Jupyter notebook from the examples/ directory into a
corresponding .mdx file in docs/v2/examples/, matching the exact format and
structure used by the GitHub Actions workflow.

Usage:
    python examples/generate_documentation.py examples/openai/openai_example_sync.ipynb
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Constants
SCRIPT_TAGS = """<script type="module" src="/scripts/github_stars.js"></script>
<script type="module" src="/scripts/scroll-img-fadein-animation.js"></script>
<script type="module" src="/scripts/button_heartbeat_animation.js"></script>
<script type="module" src="/scripts/adjust_api_dynamically.js"></script>"""

# Title overrides to reflect correct names
TITLE_OVERRIDES = {
    "ag2": "AG2",
    "autogen": "AutoGen",
    "crewai": "CrewAI",
    "google_adk": "Google ADK",
    "google_genai": "Google GenAI",
    "langchain": "LangChain",
    "litellm": "LiteLLM",
    "llamaindex": "LlamaIndex",
    "openai": "OpenAI",
    "openai_agents": "OpenAI Agents",
    "watsonx": "WatsonX",
    "xai": "xAI",
}


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


def process_pip_installations(markdown_content):
    """Transform %pip install commands using regex for efficiency."""
    # Extract all packages from pip install commands
    packages = []
    for match in re.finditer(r"%pip install\s+([^\n#]+)", markdown_content):
        packages.extend(match.group(1).strip().split())

    if not packages:
        return markdown_content

    # Deduplicate packages
    unique_packages = " ".join(sorted(set(packages)))

    # Remove code blocks containing pip installs
    content = re.sub(r"```python\n(?:[^`])*?%pip install[^\n]*\n(?:[^`])*?```\n?", "", markdown_content)

    # Find insertion point for installation section
    first_pip_pos = markdown_content.find("%pip install")
    if first_pip_pos == -1:
        return markdown_content

    # Calculate line position and insert installation section
    line_pos = markdown_content[:first_pip_pos].count("\n")
    lines = content.split("\n")

    installation_section = f"""## Installation
<CodeGroup>
  ```bash pip
  pip install {unique_packages}
  ```
  ```bash poetry
  poetry add {unique_packages}
  ```
  ```bash uv
  uv add {unique_packages}
  ```
</CodeGroup>
"""

    lines.insert(line_pos, installation_section)
    return "\n".join(lines)


def get_existing_frontmatter(mdx_path):
    """Extract existing frontmatter if it has special configurations."""
    if not mdx_path.exists():
        return None

    content = mdx_path.read_text(encoding="utf-8")

    # Check for special configurations and extract frontmatter
    if any(config in content for config in ["mode:", "layout:"]):
        if content.startswith("---\n"):
            end_marker = content.find("\n---\n", 4)
            if end_marker != -1:
                return content[4:end_marker]

    return None


def generate_mdx_content(notebook_path, processed_content, frontmatter=None):
    """Generate MDX content with either provided or generated frontmatter."""
    if not frontmatter:
        # Generate new frontmatter
        folder_name = Path(notebook_path).parent.name

        # Check for title override, otherwise use default title case conversion
        if folder_name in TITLE_OVERRIDES:
            base_title = TITLE_OVERRIDES[folder_name]
        else:
            base_title = folder_name.replace("_", " ").title()

        title = f"{base_title}"

        # Extract description from first heading or use default
        description = f"{title} example using AgentOps"
        for line in processed_content.split("\n"):
            if line.startswith("# ") and len(line) > 2:
                description = line[2:].strip()
                break

        frontmatter = f"title: '{title}'\ndescription: '{description}'"

    return f"""---
{frontmatter}
---
{{/*  SOURCE_FILE: {notebook_path}  */}}

_View Notebook on <a href={{'https://github.com/AgentOps-AI/agentops/blob/main/{notebook_path}'}} target={{'_blank'}}>Github</a>_

{processed_content}

{SCRIPT_TAGS}"""


def main():
    parser = argparse.ArgumentParser(description="Generate example MDX files from Jupyter notebooks")
    parser.add_argument("notebook_path", help="Path to the Jupyter notebook")

    notebook_path = parser.parse_args().notebook_path

    # Validate notebook path
    notebook_file = Path(notebook_path)
    if not notebook_file.exists():
        sys.exit(f"Error: Notebook file not found: {notebook_path}")

    if notebook_file.suffix != ".ipynb":
        sys.exit(f"Error: File must be a Jupyter notebook (.ipynb): {notebook_path}")

    if not str(notebook_file).startswith("examples/"):
        sys.exit(f"Error: Notebook must be in the examples/ directory: {notebook_path}")

    # Generate output path
    folder_name = notebook_file.parent.name
    output_path = Path(f"docs/v2/examples/{folder_name}.mdx")

    print(f"Processing: {notebook_path} -> {output_path}")

    # Convert notebook to markdown and process
    markdown_content = convert_notebook_to_markdown(notebook_path)
    processed_content = process_pip_installations(markdown_content)

    # Check for existing special frontmatter
    existing_frontmatter = get_existing_frontmatter(output_path)

    if existing_frontmatter:
        final_content = generate_mdx_content(notebook_path, processed_content, existing_frontmatter)
    else:
        print("Generating new frontmatter and content")
        final_content = generate_mdx_content(notebook_path, processed_content)

    # Write the file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(final_content, encoding="utf-8")

    print(f"Successfully generated: {output_path}")


if __name__ == "__main__":
    main()

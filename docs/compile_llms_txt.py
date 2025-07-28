import os
import re
from pathlib import Path


def clean_html_content(text):
    """Remove HTML tags and clean content for llms.txt compatibility."""
    text = re.sub(r"<[^>]+>", "", text)

    lines = text.split("\n")
    cleaned_lines = []
    in_table = False

    for line in lines:
        stripped = line.strip()

        if "|" in stripped and (stripped.startswith("|") or stripped.count("|") >= 2):
            in_table = True
            continue
        elif in_table and (stripped.startswith("-") or not stripped):
            continue
        else:
            in_table = False

        cleaned_line = re.sub(r"[^\x00-\x7F]+", "", line)

        if cleaned_line.strip() or (cleaned_lines and cleaned_lines[-1].strip()):
            cleaned_lines.append(cleaned_line)

    return "\n".join(cleaned_lines)


def convert_relative_urls(text, base_url="https://github.com/AgentOps-AI/agentops/blob/main"):
    """Convert relative URLs to absolute URLs for llms.txt compliance."""

    def replace_relative_link(match):
        link_text = match.group(1)
        url = match.group(2)

        if url.startswith(("http://", "https://", "mailto:")):
            return match.group(0)

        if url.startswith("#"):
            absolute_url = f"{base_url}/README.md{url}"
            return f"[{link_text}]({absolute_url})"

        if url.startswith("./"):
            url = url[2:]
        elif url.startswith("../"):
            url = url[3:]

        url = re.sub(r"/+", "/", url)
        url = url.strip("/")

        if not url:
            return match.group(0)

        absolute_url = f"{base_url}/{url}"
        return f"[{link_text}]({absolute_url})"

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_relative_link, text)

    return text


def compile_llms_txt():
    """Compile a comprehensive llms.txt file with actual repository content."""

    content = "# AgentOps\n\n"

    content += "> AgentOps is the developer favorite platform for testing, debugging, and deploying AI agents and LLM apps. Monitor, analyze, and optimize your agent workflows with comprehensive observability and analytics.\n\n"

    try:
        with open("../README.md", "r", encoding="utf-8") as f:
            readme_content = f.read()
        cleaned_readme = clean_html_content(readme_content)
        cleaned_readme = convert_relative_urls(cleaned_readme)
        content += "## Repository Overview\n\n"
        content += cleaned_readme + "\n\n"
    except Exception as e:
        print(f"Warning: Could not read README.md: {e}")

    try:
        with open("../CONTRIBUTING.md", "r", encoding="utf-8") as f:
            contributing_content = f.read()
        cleaned_contributing = clean_html_content(contributing_content)
        cleaned_contributing = convert_relative_urls(cleaned_contributing)
        content += "## Contributing Guide\n\n"
        content += cleaned_contributing + "\n\n"
    except Exception as e:
        print(f"Warning: Could not read CONTRIBUTING.md: {e}")

    content += "## Core SDK Implementation\n\n"

    sdk_files = ["../agentops/__init__.py", "../agentops/client/client.py", "../agentops/sdk/decorators/__init__.py"]

    for file_path in sdk_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                relative_path = os.path.relpath(file_path, "..")
                content += f"### {relative_path}\n\n```python\n{file_content}\n```\n\n"
            except Exception as e:
                print(f"Warning: Could not read {file_path}: {e}")

    content += "## Documentation\n\n"

    doc_files = ["v2/introduction.mdx", "v2/quickstart.mdx", "v2/concepts/core-concepts.mdx", "v1/quickstart.mdx"]

    for doc_file in doc_files:
        if os.path.exists(doc_file):
            try:
                with open(doc_file, "r", encoding="utf-8") as f:
                    file_content = f.read()
                cleaned_content = clean_html_content(file_content)
                cleaned_content = convert_relative_urls(cleaned_content)
                content += f"### {doc_file}\n\n{cleaned_content}\n\n"
            except Exception as e:
                print(f"Warning: Could not read {doc_file}: {e}")

    content += "## Instrumentation Architecture\n\n"

    instrumentation_files = [
        "../agentops/instrumentation/__init__.py",
        "../agentops/instrumentation/README.md",
        "../agentops/instrumentation/providers/openai/instrumentor.py",
    ]

    for file_path in instrumentation_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                relative_path = os.path.relpath(file_path, "..")
                if file_path.endswith(".py"):
                    content += f"### {relative_path}\n\n```python\n{file_content}\n```\n\n"
                else:
                    cleaned_content = clean_html_content(file_content)
                    cleaned_content = convert_relative_urls(cleaned_content)
                    content += f"### {relative_path}\n\n{cleaned_content}\n\n"
            except Exception as e:
                print(f"Warning: Could not read {file_path}: {e}")

    content += "## Examples\n\n"

    example_files = [
        "../examples/openai/openai_example_sync.py",
        "../examples/crewai/job_posting.py",
        "../examples/langchain/langchain_examples.py",
        "../examples/README.md",
    ]

    for file_path in example_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                relative_path = os.path.relpath(file_path, "..")
                if file_path.endswith(".py"):
                    content += f"### {relative_path}\n\n```python\n{file_content}\n```\n\n"
                else:
                    cleaned_content = clean_html_content(file_content)
                    cleaned_content = convert_relative_urls(cleaned_content)
                    content += f"### {relative_path}\n\n{cleaned_content}\n\n"
            except Exception as e:
                print(f"Warning: Could not read {file_path}: {e}")

    output_path = Path("../llms.txt")
    output_path.write_text(content, encoding="utf-8")
    print(f"Successfully compiled comprehensive llms.txt to {output_path.absolute()}")
    print(f"Total content length: {len(content)} characters")

    try:
        import llms_txt

        print("SUCCESS: llms-txt package available for validation")

        import re

        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        links = re.findall(link_pattern, content)

        has_h1 = content.startswith("# ")
        has_blockquote = "> " in content[:500]  # Check first 500 chars for summary
        h2_count = content.count("\n## ")

        title_match = re.match(r"^# (.+)$", content.split("\n")[0])
        title = title_match.group(1) if title_match else "Unknown"

        summary_match = re.search(r"> (.+)", content)
        summary = summary_match.group(1) if summary_match else "No summary"

        print("SUCCESS: Manual validation results:")
        print(f"   - Title: {title}")
        print(f"   - Summary: {summary[:100]}{'...' if len(summary) > 100 else ''}")
        print(f"   - H2 sections: {h2_count}")
        print(f"   - Links found: {len(links)}")
        print(f"   - Content size: {len(content)} characters")

        print("SUCCESS: Structure validation:")
        print(f"   - H1 header: {'PASS' if has_h1 else 'FAIL'}")
        print(f"   - Blockquote summary: {'PASS' if has_blockquote else 'FAIL'}")
        print(f"   - Multiple sections: {'PASS' if h2_count > 0 else 'FAIL'}")

        try:
            simple_test = "# Test\n\n> Test summary\n\n## Section\n\nContent here."
            llms_txt.parse_llms_file(simple_test)
            print("SUCCESS: llms-txt library functional (tested with simple content)")
        except Exception as simple_error:
            print(f"WARNING: llms-txt library has parsing issues: {simple_error}")

        print("INFO: For comprehensive content validation, use: https://llmstxtvalidator.dev")

    except ImportError:
        print("WARNING: llms-txt package not available, skipping library validation")
        print("INFO: Install with: pip install llms-txt")


if __name__ == "__main__":
    compile_llms_txt()

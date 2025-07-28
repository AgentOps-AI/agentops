import os
import glob
import re
from pathlib import Path


def clean_html_content(text):
    """Remove HTML tags and clean content for llms.txt compatibility."""
    text = re.sub(r'<[^>]+>', '', text)
    
    lines = text.split('\n')
    cleaned_lines = []
    in_table = False
    
    for line in lines:
        stripped = line.strip()
        
        if '|' in stripped and (stripped.startswith('|') or stripped.count('|') >= 2):
            in_table = True
            continue
        elif in_table and (stripped.startswith('-') or not stripped):
            continue
        else:
            in_table = False
        
        cleaned_line = re.sub(r'[^\x00-\x7F]+', '', line)
        
        if cleaned_line.strip() or (cleaned_lines and cleaned_lines[-1].strip()):
            cleaned_lines.append(cleaned_line)
    
    return '\n'.join(cleaned_lines)

def compile_llms_txt():
    """Compile a comprehensive llms.txt file with actual repository content."""
    
    content = "# AgentOps\n\n"
    
    content += "> AgentOps is the developer favorite platform for testing, debugging, and deploying AI agents and LLM apps. Monitor, analyze, and optimize your agent workflows with comprehensive observability and analytics.\n\n"
    
    try:
        with open("../README.md", "r", encoding="utf-8") as f:
            readme_content = f.read()
        cleaned_readme = clean_html_content(readme_content)
        content += "## Repository Overview\n\n"
        content += cleaned_readme + "\n\n"
    except Exception as e:
        print(f"Warning: Could not read README.md: {e}")
    
    try:
        with open("../CONTRIBUTING.md", "r", encoding="utf-8") as f:
            contributing_content = f.read()
        cleaned_contributing = clean_html_content(contributing_content)
        content += "## Contributing Guide\n\n"
        content += cleaned_contributing + "\n\n"
    except Exception as e:
        print(f"Warning: Could not read CONTRIBUTING.md: {e}")
    
    content += "## Core SDK Implementation\n\n"
    
    sdk_files = [
        "../agentops/__init__.py",
        "../agentops/client/client.py",
        "../agentops/sdk/decorators/__init__.py"
    ]
    
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
    
    doc_files = [
        "v2/introduction.mdx",
        "v2/quickstart.mdx",
        "v2/concepts/core-concepts.mdx",
        "v1/quickstart.mdx"
    ]
    
    for doc_file in doc_files:
        if os.path.exists(doc_file):
            try:
                with open(doc_file, "r", encoding="utf-8") as f:
                    file_content = f.read()
                content += f"### {doc_file}\n\n{file_content}\n\n"
            except Exception as e:
                print(f"Warning: Could not read {doc_file}: {e}")
    
    content += "## Instrumentation Architecture\n\n"
    
    instrumentation_files = [
        "../agentops/instrumentation/__init__.py",
        "../agentops/instrumentation/README.md",
        "../agentops/instrumentation/providers/openai/instrumentor.py"
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
                    content += f"### {relative_path}\n\n{file_content}\n\n"
            except Exception as e:
                print(f"Warning: Could not read {file_path}: {e}")
    
    content += "## Examples\n\n"
    
    example_files = [
        "../examples/openai/openai_example_sync.py",
        "../examples/crewai/job_posting.py",
        "../examples/langchain/langchain_examples.py",
        "../examples/README.md"
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
                    content += f"### {relative_path}\n\n{file_content}\n\n"
            except Exception as e:
                print(f"Warning: Could not read {file_path}: {e}")

    output_path = Path("../llms.txt")
    output_path.write_text(content, encoding="utf-8")
    print(f"Successfully compiled comprehensive llms.txt to {output_path.absolute()}")
    print(f"Total content length: {len(content)} characters")
    
    try:
        import llms_txt
        print("✅ llms-txt package available for validation")
        
        try:
            parsed_content = llms_txt.parse_llms_file(content)
            print("✅ llms.txt content successfully parsed by llms-txt library")
            
            title = getattr(parsed_content, 'title', 'Unknown')
            summary = getattr(parsed_content, 'summary', 'No summary')
            sections = getattr(parsed_content, 'sections', {})
            
            import re
            link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
            links = re.findall(link_pattern, content)
            
            print(f"✅ Validation results:")
            print(f"   - Title: {title}")
            print(f"   - Summary: {summary[:100]}{'...' if len(summary) > 100 else ''}")
            print(f"   - Sections parsed: {len(sections)}")
            print(f"   - Links found: {len(links)}")
            print(f"   - Content size: {len(content)} characters")
            
            has_h1 = content.startswith('# ')
            has_blockquote = '> ' in content[:500]  # Check first 500 chars for summary
            h2_count = content.count('\n## ')
            
            print(f"✅ Structure validation:")
            print(f"   - H1 header: {'✅' if has_h1 else '❌'}")
            print(f"   - Blockquote summary: {'✅' if has_blockquote else '❌'}")
            print(f"   - H2 sections: {h2_count}")
            
        except Exception as parse_error:
            print(f"⚠️  llms-txt parsing error: {parse_error}")
            print("⚠️  Content may not be fully compliant with llms.txt standard")
            
    except ImportError:
        print("⚠️  llms-txt package not available, skipping library validation")
        print("💡 Install with: pip install llms-txt")


if __name__ == "__main__":
    compile_llms_txt()

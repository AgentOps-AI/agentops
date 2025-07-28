import os
from pathlib import Path


def compile_llms_txt():
    """Compile a structured llms.txt file following the official standard."""
    
    content = "# AgentOps\n\n"
    
    content += "> AgentOps is the developer favorite platform for testing, debugging, and deploying AI agents and LLM apps. Monitor, analyze, and optimize your agent workflows with comprehensive observability and analytics.\n\n"
    
    content += "## Core Documentation\n\n"
    content += "- [Introduction](https://docs.agentops.ai/v2/introduction) - Getting started with AgentOps\n"
    content += "- [Quickstart Guide](https://docs.agentops.ai/v1/quickstart) - Start using AgentOps with just 2 lines of code\n"
    content += "- [Core Concepts](https://docs.agentops.ai/v2/concepts/core-concepts) - Understanding AgentOps fundamentals\n"
    content += "- [SDK Reference](https://docs.agentops.ai/v2/usage/sdk-reference) - Complete SDK documentation\n"
    content += "- [Dashboard Guide](https://docs.agentops.ai/v2/usage/dashboard-info) - Using the AgentOps dashboard\n\n"
    
    content += "## Usage & Features\n\n"
    content += "- [Tracking Agents](https://docs.agentops.ai/v2/usage/tracking-agents) - Monitor agent behavior and performance\n"
    content += "- [Recording Operations](https://docs.agentops.ai/v2/usage/recording-operations) - Track operations and workflows\n"
    content += "- [LLM Call Tracking](https://docs.agentops.ai/v2/usage/tracking-llm-calls) - Monitor LLM API calls\n"
    content += "- [Trace Management](https://docs.agentops.ai/v2/usage/manual-trace-control) - Advanced trace control\n"
    content += "- [Context Managers](https://docs.agentops.ai/v2/usage/context-managers) - Python context manager usage\n"
    content += "- [Decorators](https://docs.agentops.ai/v2/concepts/decorators) - Using AgentOps decorators\n\n"
    
    content += "## Integrations\n\n"
    content += "- [OpenAI](https://docs.agentops.ai/v2/integrations/openai) - OpenAI API integration\n"
    content += "- [Anthropic](https://docs.agentops.ai/v2/integrations/anthropic) - Anthropic Claude integration\n"
    content += "- [LangChain](https://docs.agentops.ai/v2/integrations/langchain) - LangChain framework integration\n"
    content += "- [LangGraph](https://docs.agentops.ai/v2/integrations/langgraph) - LangGraph workflow integration\n"
    content += "- [CrewAI](https://docs.agentops.ai/v2/integrations/crewai) - CrewAI multi-agent integration\n"
    content += "- [AutoGen](https://docs.agentops.ai/v2/integrations/autogen) - Microsoft AutoGen integration\n"
    content += "- [AG2](https://docs.agentops.ai/v2/integrations/ag2) - AG2 agent framework integration\n"
    content += "- [OpenAI Agents SDK](https://docs.agentops.ai/v2/integrations/openai_agents_python) - OpenAI Agents SDK integration\n"
    content += "- [LlamaIndex](https://docs.agentops.ai/v2/integrations/llamaindex) - LlamaIndex RAG integration\n"
    content += "- [Google Generative AI](https://docs.agentops.ai/v2/integrations/google_generative_ai) - Google Gemini integration\n\n"
    
    content += "## Examples\n\n"
    content += "- [OpenAI Examples](https://docs.agentops.ai/v2/examples/openai) - OpenAI integration examples\n"
    content += "- [LangChain Examples](https://docs.agentops.ai/v2/examples/langchain) - LangChain usage examples\n"
    content += "- [CrewAI Examples](https://docs.agentops.ai/v2/examples/crewai) - Multi-agent CrewAI examples\n"
    content += "- [AutoGen Examples](https://docs.agentops.ai/v2/examples/autogen) - Microsoft AutoGen examples\n"
    content += "- [Anthropic Examples](https://docs.agentops.ai/v2/examples/anthropic) - Anthropic Claude examples\n"
    content += "- [All Examples](https://docs.agentops.ai/v2/examples/examples) - Complete examples collection\n\n"
    
    content += "## Repository & Community\n\n"
    content += "- [GitHub Repository](https://github.com/AgentOps-AI/agentops) - Source code and issues\n"
    content += "- [Contributing Guide](https://github.com/AgentOps-AI/agentops/blob/main/CONTRIBUTING.md) - How to contribute\n"
    content += "- [Discord Community](https://discord.gg/FagdcwwXRR) - Join our Discord server\n"
    content += "- [AgentOps Dashboard](https://app.agentops.ai/) - Access the web dashboard\n"
    content += "- [Documentation](https://docs.agentops.ai) - Complete documentation site\n\n"

    # Write the structured content to llms.txt in the repository root
    output_path = Path("../llms.txt")
    output_path.write_text(content, encoding="utf-8")
    print(f"Successfully compiled structured llms.txt to {output_path.absolute()}")
    print(f"Total content length: {len(content)} characters")
    print(f"Link count: {content.count('](https://')}")


if __name__ == "__main__":
    compile_llms_txt()

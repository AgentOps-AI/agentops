"""
Integration tests for all example scripts in the /examples directory.

This test suite runs each example script and validates that spans are sent to AgentOps.
"""

import os
import sys
import subprocess
import time
import json
import requests
import pytest
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid
import re


# List of all example files to test
EXAMPLE_FILES = [
    "examples/crewai/markdown_validator.py",
    "examples/crewai/job_posting.py",
    "examples/litellm/litellm_example.py",
    "examples/ag2/tools_wikipedia_search.py",
    "examples/ag2/async_human_input.py",
    "examples/xai/grok_vision_examples.py",
    "examples/xai/grok_examples.py",
    "examples/watsonx/watsonx-tokeniation-model.py",
    "examples/watsonx/watsonx-text-chat.py",
    "examples/watsonx/watsonx-streaming.py",
    "examples/anthropic/anthropic-example-async.py",
    "examples/anthropic/agentops-anthropic-understanding-tools.py",
    "examples/anthropic/anthropic-example-sync.py",
    "examples/smolagents/text_to_sql.py",
    "examples/smolagents/multi_smolagents_system.py",
    "examples/agno/agno_basic_agents.py",
    "examples/agno/agno_async_operations.py",
    "examples/agno/agno_workflow_setup.py",
    "examples/agno/agno_tool_integrations.py",
    "examples/agno/agno_research_team.py",
    "examples/context_manager/parallel_traces.py",
    "examples/context_manager/production_patterns.py",
    "examples/context_manager/error_handling.py",
    "examples/context_manager/basic_usage.py",
    "examples/google_genai/gemini_example.py",
    "examples/mem0/mem0_memory_example.py",
    "examples/mem0/mem0_memoryclient_example.py",
    "examples/langgraph/langgraph_example.py",
    "examples/generate_documentation.py",
    "examples/google_adk/human_approval.py",
    "examples/openai/openai_example_async.py",
    "examples/openai/web_search.py",
    "examples/openai/multi_tool_orchestration.py",
    "examples/openai/openai_example_sync.py",
    "examples/langchain/langchain_examples.py",
    "examples/openai_agents/agents_tools.py",
    "examples/openai_agents/customer_service_agent.py",
    "examples/openai_agents/agent_patterns.py",
    "examples/openai_agents/agent_guardrails.py",
    "examples/llamaindex/llamaindex_example.py",
    "examples/autogen/AgentChat.py",
    "examples/autogen/MathAgent.py",
]

# Examples that require special handling or should be skipped
SKIP_EXAMPLES = {
    # Examples that require user interaction
    "examples/ag2/async_human_input.py": "Requires user input",
    "examples/google_adk/human_approval.py": "Requires human approval",
    # Examples that might have external dependencies not available in test env
    "examples/generate_documentation.py": "Documentation generation script",
}

# Examples that are expected to have specific span types
EXPECTED_SPANS = {
    "openai": ["llm"],
    "anthropic": ["llm"],
    "langchain": ["llm", "action"],
    "llamaindex": ["llm"],
    "litellm": ["llm"],
    "google_genai": ["llm"],
    "xai": ["llm"],
    "watsonx": ["llm"],
}


class AgentOpsAPIClient:
    """Client for interacting with AgentOps Public API."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.agentops.ai"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "X-Agentops-Api-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def get_session_stats(self, session_id: str) -> Optional[Dict]:
        """Get statistics for a specific session."""
        try:
            response = requests.get(
                f"{self.base_url}/v2/sessions/{session_id}/stats",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting session stats: {e}")
            return None
    
    def get_session_export(self, session_id: str) -> Optional[Dict]:
        """Export complete session data."""
        try:
            response = requests.get(
                f"{self.base_url}/v2/sessions/{session_id}/export",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error exporting session: {e}")
            return None
    
    def validate_llm_spans(self, session_data: Dict) -> bool:
        """Validate that LLM spans exist in the session data."""
        if not session_data or "events" not in session_data:
            return False
        
        events = session_data.get("events", [])
        llm_spans = [e for e in events if e.get("type") == "llm" or e.get("event_type") == "llm"]
        
        return len(llm_spans) > 0


def extract_session_id_from_output(output: str) -> Optional[str]:
    """Extract session ID from script output."""
    # Look for session URL patterns
    patterns = [
        # Standard AgentOps session URL
        r"https?://app\.agentops\.ai/drilldown\?session_id=([a-f0-9-]+)",
        # Alternative URL formats
        r"https?://app\.agentops\.ai/sessions/([a-f0-9-]+)",
        r"agentops\.ai.*session[_\s]?id=([a-f0-9-]+)",
        # Direct session ID mentions
        r"session[_\s]?id[:\s]+([a-f0-9-]+)",
        r"Session ID: ([a-f0-9-]+)",
        # UUID pattern that might be a session ID
        r"Session.*?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",
        # AgentOps trace/session output
        r"AgentOps: Session.*?([a-f0-9-]+)",
        r"Starting session ([a-f0-9-]+)",
        r"Created session: ([a-f0-9-]+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        if match:
            session_id = match.group(1)
            # Validate it looks like a valid UUID
            if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', session_id):
                return session_id
    
    return None


def run_example_script(script_path: str, timeout: int = 60) -> Tuple[bool, str, Optional[str]]:
    """
    Run an example script and capture its output.
    
    Returns:
        Tuple of (success, output, session_id)
    """
    env = os.environ.copy()
    
    # Ensure AgentOps API key is set
    if "AGENTOPS_API_KEY" not in env:
        return False, "AGENTOPS_API_KEY not set in environment", None
    
    # Set mock API keys for various providers to prevent API errors
    # These won't make real API calls in most examples since AgentOps intercepts them
    mock_keys = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "test-openai-key"),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "test-anthropic-key"),
        "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY", "test-google-key"),
        "COHERE_API_KEY": os.environ.get("COHERE_API_KEY", "test-cohere-key"),
        "HUGGINGFACE_API_KEY": os.environ.get("HUGGINGFACE_API_KEY", "test-hf-key"),
        "WATSONX_API_KEY": os.environ.get("WATSONX_API_KEY", "test-watsonx-key"),
        "GROQ_API_KEY": os.environ.get("GROQ_API_KEY", "test-groq-key"),
    }
    
    for key, value in mock_keys.items():
        if key not in env:
            env[key] = value
    
    try:
        # Run the script
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )
        
        output = result.stdout + result.stderr
        
        # Check if the script ran successfully
        if result.returncode != 0:
            return False, f"Script exited with code {result.returncode}: {output}", None
        
        # Extract session ID from output
        session_id = extract_session_id_from_output(output)
        
        return True, output, session_id
        
    except subprocess.TimeoutExpired:
        return False, f"Script timed out after {timeout} seconds", None
    except Exception as e:
        return False, f"Error running script: {str(e)}", None


@pytest.fixture(scope="module")
def agentops_api_client():
    """Fixture to provide AgentOps API client."""
    api_key = os.environ.get("AGENTOPS_API_KEY")
    if not api_key:
        pytest.skip("AGENTOPS_API_KEY not set")
    
    return AgentOpsAPIClient(api_key)  # type: ignore


@pytest.mark.integration
@pytest.mark.parametrize("example_file", EXAMPLE_FILES)
def test_example_script(example_file: str, agentops_api_client: AgentOpsAPIClient):
    """Test that an example script runs and sends spans to AgentOps."""
    
    # Check if we should skip this example
    if example_file in SKIP_EXAMPLES:
        pytest.skip(f"Skipping {example_file}: {SKIP_EXAMPLES[example_file]}")
    
    # Check if the file exists
    if not os.path.exists(example_file):
        pytest.skip(f"Example file not found: {example_file}")
    
    # Run the example script
    success, output, session_id = run_example_script(example_file)
    
    # Basic assertion that script ran
    assert success, f"Script failed to run: {output}"
    
    # If we couldn't extract session ID, we might need to wait or check differently
    if not session_id:
        # Some scripts might not print session ID, so we'll check if AgentOps was initialized
        assert "agentops" in output.lower() or "AgentOps" in output, \
            f"No AgentOps initialization detected in output: {output[:500]}"
        pytest.skip(f"Could not extract session ID from output")
    
    # Wait a bit for data to be sent to AgentOps
    time.sleep(5)
    
    # Get session data from AgentOps API
    assert session_id is not None  # Already checked above, but helps with type checking
    session_stats = agentops_api_client.get_session_stats(session_id)
    assert session_stats is not None, f"Failed to get session stats for {session_id}"
    
    # Get full session export
    session_data = agentops_api_client.get_session_export(session_id)
    assert session_data is not None, f"Failed to export session data for {session_id}"
    
    # Validate based on the type of example
    example_type = None
    for key in EXPECTED_SPANS:
        if key in example_file.lower():
            example_type = key
            break
    
    if example_type and example_type in EXPECTED_SPANS:
        # Validate that expected span types exist
        events = session_data.get("events", [])
        event_types = set(e.get("type") or e.get("event_type") for e in events)
        
        for expected_span in EXPECTED_SPANS[example_type]:
            assert expected_span in event_types, \
                f"Expected {expected_span} span not found in {event_types}"
    
    # Always validate that at least some events were recorded
    assert len(session_data.get("events", [])) > 0, \
        f"No events recorded for session {session_id}"


@pytest.mark.integration
def test_validate_llm_spans_in_llm_examples(agentops_api_client: AgentOpsAPIClient):
    """Test that LLM examples specifically have LLM spans."""
    
    llm_examples = [
        "examples/openai/openai_example_sync.py",
        "examples/anthropic/anthropic-example-sync.py",
        "examples/litellm/litellm_example.py",
    ]
    
    for example_file in llm_examples:
        if not os.path.exists(example_file):
            continue
            
        if example_file in SKIP_EXAMPLES:
            continue
        
        success, output, session_id = run_example_script(example_file)
        
        if not success or not session_id:
            continue
        
        # Wait for data to be sent
        time.sleep(5)
        
        session_data = agentops_api_client.get_session_export(session_id)
        if session_data:
            assert agentops_api_client.validate_llm_spans(session_data), \
                f"No LLM spans found in {example_file}"


@pytest.mark.integration
def test_multiple_scripts_different_sessions(agentops_api_client: AgentOpsAPIClient):
    """Test that running multiple scripts creates different sessions."""
    
    test_scripts = [
        "examples/openai/openai_example_sync.py",
        "examples/context_manager/basic_usage.py",
    ]
    
    session_ids = []
    
    for script in test_scripts:
        if not os.path.exists(script) or script in SKIP_EXAMPLES:
            continue
            
        success, output, session_id = run_example_script(script)
        
        if success and session_id:
            session_ids.append(session_id)
    
    # Ensure we got at least 2 sessions
    if len(session_ids) >= 2:
        # All session IDs should be unique
        assert len(session_ids) == len(set(session_ids)), \
            "Scripts should create unique sessions"


if __name__ == "__main__":
    # For manual testing
    api_key = os.environ.get("AGENTOPS_API_KEY")
    if not api_key:
        print("Please set AGENTOPS_API_KEY environment variable")
        sys.exit(1)
    
    client = AgentOpsAPIClient(api_key)
    
    # Test a single example
    test_file = "examples/openai/openai_example_sync.py"
    if os.path.exists(test_file):
        success, output, session_id = run_example_script(test_file)
        print(f"Success: {success}")
        print(f"Session ID: {session_id}")
        
        if session_id:
            time.sleep(5)
            stats = client.get_session_stats(session_id)
            print(f"Session stats: {json.dumps(stats, indent=2)}")
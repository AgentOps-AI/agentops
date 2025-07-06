import os
import re
import time
import pathlib
import subprocess
from typing import List

import pytest  # type: ignore
import requests

# Directory containing example scripts
EXAMPLES_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "examples"

# Regex pattern to extract UUIDs (session IDs)
_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def _list_example_scripts() -> List[str]:
    """Return a sorted list of python example file paths under EXAMPLES_DIR."""
    return sorted(
        str(p)
        for p in EXAMPLES_DIR.rglob("*.py")
        if p.is_file() and not p.name.startswith("__init__")
    )


EXAMPLE_SCRIPTS = _list_example_scripts()


def _extract_session_ids(text: str) -> List[str]:
    """Return all UUIDs found in given text."""
    return _UUID_RE.findall(text)


@pytest.mark.parametrize("script_path", EXAMPLE_SCRIPTS)
def test_example_generates_llm_span(script_path: str):
    """Run an example script and assert that at least one LLM span was recorded.

    The test performs the following steps:
    1. Ensures an AgentOps API key is present via the `AGENTOPS_API_KEY` env var.
    2. Executes the script in a subprocess, capturing stdout/stderr.
    3. Parses the output for an AgentOps Session ID (UUID).
       AgentOps prints a clickable session URL which contains the ID.
    4. Polls the AgentOps public API `/v2/sessions/{session_id}/export` until
       the session is available, and asserts that at least one event with
       `type == "llm"` exists.
    """

    api_key = os.getenv("AGENTOPS_API_KEY")
    if not api_key:
        pytest.skip("Environment variable AGENTOPS_API_KEY not set – skipping integration test.")

    # At this point `api_key` is guaranteed to be a non-empty string
    assert isinstance(api_key, str)

    env = os.environ.copy()
    env["AGENTOPS_API_KEY"] = api_key
    # Make subprocess output unbuffered for timely printing
    env.setdefault("PYTHONUNBUFFERED", "1")

    # Run the script and capture output
    proc = subprocess.run(
        ["python", script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        timeout=600,  # generous timeout (10 minutes)
    )

    # Surface script output for easier debugging on failure
    output = proc.stdout
    if proc.returncode != 0:
        pytest.fail(f"Script {script_path} exited with code {proc.returncode}.\nOutput:\n{output}")

    # Extract session IDs from output; choose the last one printed
    session_ids = _extract_session_ids(output)
    if not session_ids:
        pytest.fail(
            "No AgentOps session ID found in output. "
            "Ensure the script prints the session URL or ID."
        )
    session_id = session_ids[-1]

    # Poll AgentOps public API for up to 60 seconds waiting for data
    headers = {"X-Agentops-Api-Key": api_key}
    url = f"https://api.agentops.ai/v2/sessions/{session_id}/export"
    session_data = None
    for _ in range(30):  # 30 * 2s = 60s max wait
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            session_data = resp.json()
            # ensure events have been ingested
            if session_data.get("events"):
                break
        time.sleep(2)

    if not session_data or not session_data.get("events"):
        pytest.fail("Failed to retrieve session events from AgentOps API within timeout.")

    assert session_data is not None  # for type checkers
    llm_spans = [e for e in session_data["events"] if e.get("type") == "llm"]
    assert llm_spans, "No LLM spans found in session events."
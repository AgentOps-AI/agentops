# AgentOps Development Notes

## Project Setup
When working with the AgentOps project, make sure to:

1. Activate the virtual environment: `. .venv/bin/activate`
2. Install dependencies: `uv install -e '.'`
3. If running tests, install test dependencies:
   ```
   uv install pytest pytest-cov pytest-depends pytest-asyncio pytest-mock pyfakefs pytest-recording vcrpy
   ```

## Running Python

Always use `uv run` to run scripts as it will prepare your virtual environment for you. 
There is a.env file in the project's root that provides API keys for common services. 
The virtual environment has all of the packages that you need, and you will never have to install a package. 

## Testing

Run unit tests:
```bash
uv run pytest tests/unit
uv run pytest tests/unit/test_session_legacy.py
```

Run specific tests with:
```
uv run pytest tests/unit/sdk/test_response_serialization.py -v
```

### Common Module Tests

#### OpenAI Agents Instrumentation
```
# Run specific OpenAI Agents instrumentation tests
uv run pytest tests/unit/instrumentation/test_openai_agents.py -v

# Test with example OpenAI Agents hello world code
uv run examples/agents-example/hello_world.py

# Enable debug logging to see detailed trace and span information
AGENTOPS_LOG_LEVEL=debug uv run examples/agents-example/hello_world.py
```

**Note:** Most examples require an AgentOps API key to run. Check the following locations for environment files:
1. `.env` file in the repository root directory
2. `.agentops` file in your home directory (`~/.agentops`)

If you're debugging trace ID correlation between logs and the AgentOps API, make sure to enable debug logging.

#### Querying the AgentOps API
To investigate trace details directly from the API:

1. Run your example with debug logging to get the trace ID:
   ```
   AGENTOPS_LOG_LEVEL=debug uv run examples/agents-example/hello_world.py
   ```
   Look for the line: `[TRACE] Started: Agent workflow | TRACE ID: <trace_id>`

2. Use the AgentOps API to fetch trace information:
   ```python
   # Using the AgentOps API functions:
   # List recent traces
   mcp__agentops-api__list_traces(AGENTOPS_API_KEY="<your_api_key>")
   
   # Get detailed trace information
   mcp__agentops-api__trace_detail(AGENTOPS_API_KEY="<your_api_key>", trace_id="<trace_id>")
   ```

#### OpenTelemetry Instrumentation
```
# Run OpenTelemetry instrumentation tests
uv run pytest tests/unit/instrumentation/test_openai_completions.py -v
uv run pytest tests/unit/instrumentation/test_openai_responses.py -v
```

#### SDK Core Tests
```
# Test core SDK functionality
uv run pytest tests/unit/sdk/test_core.py -v
uv run pytest tests/unit/sdk/test_instrumentation.py -v
```

If seeing import errors related to missing packages like `agents`, make sure to install appropriate dependencies or modify test code to avoid dependencies on external packages.

## Examples

Run basic examples:
```bash
uv run examples/agents-examples/basic/hello_world.py
uv run examples/crewai-basic.py
```

## Version Management

Check installed versions:
```bash
uv run python -c "import crewai; print(crewai.__version__)"
```

Install specific versions:
```bash
uv pip install "crewai==0.98.0"
uv pip install "crewai==0.100.1"
uv pip install "crewai==0.105.0"
uv pip install "crewai==0.108.0"
```

List available versions:
```bash
pip index versions crewai
```

## Code Exploration

Search for patterns in code:
```bash
grep -r "agentops." /path/to/file/or/directory
grep -A 5 "if agentops:" /path/to/file
grep -r "end_session" /path/to/directory
```

Whenever you need to replace multiple items in a file, use grep or sed. The built-in tools don't allow for finding multiple instances of a string. Be careful with this though, as global search and replace can be risky.

### Modules 

Work on specific modules in specific directories as instructed. Try to stick to that scope unless given explicit instructions to read files outside of that scope.

You'll often find Markdown files inside project directories you're working on. Reference them as they're likely notes made for guidance.

## Development Flow

When modifying backward compatibility code:

1. Run tests to verify current functionality
2. Check and understand the integration pattern
3. Make the necessary code changes
4. Test with multiple versions of the integrated library
5. Document findings for future developers

## CrewAI Compatibility

CrewAI versions we need to support:
- 0.98.0 - Direct integration pattern (spans: 11, root_span_name: session.session)
- 0.100.1, 0.102.0 - Direct integration pattern (spans: 11, root_span_name: Crew Created)
- 0.105.0, 0.108.0 - Event-based integration (spans: 7, root_span_name: crewai.workflow)

## Technologies

### Core Concepts
- **AgentOps**: Platform for monitoring and tracking AI agent performance and behavior
- **OpenTelemetry (OTel)**: Open source observability framework used for instrumentation
- **Instrumentation**: Process of adding monitoring/telemetry capabilities to code
- **Span**: Unit of work in a trace (represents an operation with start/end time)
- **Trace**: Collection of spans forming a tree structure showing a request's path
- **Context Propagation**: Passing trace context between components to maintain hierarchy

### API Formats
- **OpenAI Chat Completions API**: Traditional format with choices array and prompt/completion tokens
- **OpenAI Response API**: Newer format used by Agents SDK with nested output structure and input/output tokens

### Instrumentation Components
- **Instrumentor**: Class that patches target libraries to add telemetry
- **Extractor**: Function that processes specific response formats
- **Semantic Conventions**: Standardized naming for span attributes
   stored in agentops/semconv always reference semantic conventions when working with OpenTelemetry attributes. 

### Development Tools
- **UV**: Fast Python package installer and resolver (replacement for pip)

When running tests, don't truncate the result. Show every line of tests that pass.
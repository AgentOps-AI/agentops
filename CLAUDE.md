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
Run tests with:
```
uv run pytest tests/unit/
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
python examples/agents-examples/basic/hello_world.py
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

### Modules 

I will often direct you to work on specific modules in specific directories. Try to stick to that scope unless I give you explicit instructions to read files outside of that scope. 

You'll often find Markdown files inside the project directories you're working on. Reference them because they're probably notes that you made for yourself. 

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


Whenever you need to replace lots of items in a file, use grep or sed. Your built-in tools don't let you find multiple instances of a string. Be careful with this though, because you know global search and replace is definitely risky, but I think you've got it. 

when you run tests in your interface, don't truncate the result. I want to see every line of the test that passes 
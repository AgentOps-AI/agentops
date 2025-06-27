## AgentOps MCP

1. Run the public API at AgentOps.Next/api.
2. Configure your MCP client.
3. Chat/debug/etc!

## Environment Variables

- `AGENTOPS_API_KEY`: Your AgentOps API key (required for authentication)
- `HOST`: The AgentOps API host (optional, defaults to https://api.agentops.ai)

When `AGENTOPS_API_KEY` is set in the environment, the server will automatically authenticate on startup.

## Configuration Examples

### Windsurf config example (with direct Python):

```json
{
    "mcpServers": {
        "agentops": {
            "command": "uv",
            "args": [
                "--directory", "/path/to/agentops-mcp",
                "run", "server.py"
            ],
            "env": {
                "AGENTOPS_API_KEY": "your-agentops-api-key-here"
            }
        }
    }
}
```

### Docker configuration example:

```json
{
    "mcpServers": {
        "agentops": {
            "command": "docker",
            "args": [
                "run",
                "-i",
                "--rm",
                "-e",
                "AGENTOPS_API_KEY",
                "agentops/agentops-mcp:latest"
            ],
            "env": {
                "AGENTOPS_API_KEY": "your-agentops-api-key-here"
            }
        }
    }
}
```
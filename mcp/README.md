## AgentOps MCP

1. Run the public API at AgentOps.Next/api.
2. Configure your MCP client.
3. Chat/debug/etc!

Windsurf config example:

```
{
    "mcpServers": {
        "agentops": {
            "command": "uv",
            "args": [
                "--directory", "/Users/michi/MCP/DIRECTORY",
                "run", "server.py"
            ]
        }
    }
}
```

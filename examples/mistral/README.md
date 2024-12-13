# AgentOps Monitoring for Mistral AI

![AgentOps Banner](../../docs/images/external/logo/banner-badge.png)

AgentOps supports Mistral's API for building and monitoring powerful AI applications!

To learn more about Mistral AI, visit their [website](https://mistral.ai) or check out their [documentation](https://docs.mistral.ai).

> [!NOTE]
> New to LLMs? Check out our intro guide (coming soon) to learn about key concepts like context management, prompt engineering, and cost optimization!

## Getting Started

Let's get your Mistral monitoring set up in just a few steps:

### 1. Install Required Packages

```bash
pip install agentops mistralai
```

### 2. Set Up Your Environment

```python
from mistralai import Mistral
import agentops
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY") or "<your_mistral_key>"
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "<your_agentops_key>"
```

> [!WARNING]
> Remember to set API keys for both AgentOps and Mistral! Never share your API keys or commit them to version control.

## Integration Examples

### Basic Model Monitoring
Track your Mistral model calls with detailed performance metrics:

```python
# Initialize clients
agentops.init(AGENTOPS_API_KEY)
client = Mistral(MISTRAL_API_KEY)

@agentops.track_agent(name='mistral-agent')
def get_completion(prompt):
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# Example usage
response = get_completion("Explain quantum computing")
```

See our [example notebook](./monitoring_mistral.ipynb) for more advanced examples including:
- Streaming responses with real-time monitoring
- Async operations and parallel request tracking
- Custom event tracking and metadata analysis
- Performance optimization techniques
- Error handling and debugging strategies

## Visual Examples

### Session Overview
Monitor your model's performance and behavior in real-time:

![Session Overview](../../docs/images/external/app_screenshots/session-overview.png)

### Session Replay
Analyze the flow and dependencies of your model interactions:

![Session Replay](../../docs/images/external/app_screenshots/session-replay.png)

### Detailed Analytics
Track performance metrics and model behavior:

![Session Drilldown](../../docs/images/external/app_screenshots/session-drilldown-graphs.png)

## Learn More
- [AgentOps Documentation](https://docs.agentops.ai)
- [Mistral API Documentation](https://docs.mistral.ai)
- [Example Notebook](./monitoring_mistral.ipynb)
- [Join our Discord Community](https://discord.gg/agentops)

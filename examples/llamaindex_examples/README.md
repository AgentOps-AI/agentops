# LlamaIndex AgentOps Integration Example

This example demonstrates how to use AgentOps with LlamaIndex for observability and monitoring of your context-augmented generative AI applications.

## Setup

1. Install required packages:
```bash
pip install agentops llama-index-instrumentation-agentops llama-index python-dotenv
```

2. Set your API keys:
```bash
export AGENTOPS_API_KEY="your_agentops_api_key"
export OPENAI_API_KEY="your_openai_api_key"
```

## Files

- `llamaindex_example.py` - Python script example
- `llamaindex_example.ipynb` - Jupyter notebook example

## Usage

Run the Python script:
```bash
python llamaindex_example.py
```

Or open and run the Jupyter notebook:
```bash
jupyter notebook llamaindex_example.ipynb
```

After running, check your AgentOps dashboard for the recorded session.

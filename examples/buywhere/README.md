# BuyWhere Product Search Example

This example demonstrates using the [BuyWhere](https://buywhere.ai) product catalog API with AgentOps observability.

BuyWhere is an agent-native product catalog API that lets AI agents search 11M+ products across 5 markets (Singapore, United States, Malaysia, Vietnam, Thailand) with real-time pricing and deal discovery.

## What this example shows

- Searching products by keyword across markets
- Fetching current deals and discounts
- Listing product categories
- Finding best prices for specific products
- All traced with AgentOps for observability

## Requirements

- Python 3.10+
- AgentOps API key ([get one free](https://agentops.ai))
- BuyWhere API key (optional — public endpoints work without auth)

## Usage

```bash
export AGENTOPS_API_KEY="your-api-key"
python buywhere_product_search.py
```

The example searches for laptops in Singapore, fetches active deals, and lists product categories — all tracked in your AgentOps dashboard.


"""
BuyWhere Product Search with AgentOps Tracing
==============================================

Demonstrates using the BuyWhere product catalog API with AgentOps observability.
Searches 11M+ products across 5 markets (SG, US, MY, VN, TH) with
real-time pricing and deal discovery.

Installation:
    pip install agentops python-dotenv requests
"""

import os
import json

import agentops
import requests
from dotenv import load_dotenv

load_dotenv()

AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY", "your_agentops_api_key")
BUYWHERE_API_KEY = os.getenv("BUYWHERE_API_KEY", "")
BUYWHERE_BASE_URL = "https://api.buywhere.ai/v1"

agentops.init(
    auto_start_session=True,
    trace_name="BuyWhere Product Search",
    tags=["buywhere", "product-search", "agentops-example"],
)
tracer = agentops.start_trace(
    trace_name="BuyWhere Product Search",
    tags=["buywhere", "product-search", "agentops-example"],
)


def search_products(query: str, market: str = "SG", limit: int = 5):
    """Search products by keyword across a market."""
    headers = {"Authorization": f"Bearer {BUYWHERE_API_KEY}"} if BUYWHERE_API_KEY else {}
    params = {"q": query, "market": market, "limit": limit}
    resp = requests.get(f"{BUYWHERE_BASE_URL}/products/search", headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()


def get_deals(market: str = "SG", limit: int = 5):
    """Get current deals and discounts."""
    headers = {"Authorization": f"Bearer {BUYWHERE_API_KEY}"} if BUYWHERE_API_KEY else {}
    params = {"market": market, "limit": limit}
    resp = requests.get(f"{BUYWHERE_BASE_URL}/products/deals", headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()


def list_categories(market: str = "SG"):
    """List product categories available in a market."""
    headers = {"Authorization": f"Bearer {BUYWHERE_API_KEY}"} if BUYWHERE_API_KEY else {}
    params = {"market": market}
    resp = requests.get(f"{BUYWHERE_BASE_URL}/categories", headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()


def find_best_price(product_id: str):
    """Get pricing history for a specific product."""
    headers = {"Authorization": f"Bearer {BUYWHERE_API_KEY}"} if BUYWHERE_API_KEY else {}
    resp = requests.get(f"{BUYWHERE_BASE_URL}/products/{product_id}/prices", headers=headers)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    print("=== BuyWhere Product Search with AgentOps ===\n")

    products = search_products("laptop", market="SG", limit=3)
    print(f"Found {products.get('total', 0)} laptops in Singapore")
    for item in products.get("data", [])[:3]:
        print(f"  - {item.get('name')}: ${item.get('price')} at {item.get('merchant')}")

    print()
    deals = get_deals(market="SG", limit=3)
    print(f"Top deals in Singapore ({deals.get('total', 0)} available):")
    for deal in deals.get("data", [])[:3]:
        print(f"  - {deal.get('name')}: was ${deal.get('original_price')}, now ${deal.get('price')}")

    print()
    categories = list_categories(market="SG")
    print(f"Product categories ({len(categories.get('data', []))} available):")
    for cat in categories.get("data", [])[:5]:
        print(f"  - {cat.get('name')} ({cat.get('product_count', 0)} products)")

    agentops.end_trace(tracer, end_state="Success")
    print("\n✓ Trace complete — view in AgentOps dashboard")

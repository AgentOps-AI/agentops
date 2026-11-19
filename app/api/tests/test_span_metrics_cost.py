from decimal import Decimal
from types import SimpleNamespace

import pytest

from agentops.api.models.span_metrics import SpanMetricsMixin, _llm_prices_rate


def _cost(model: str, tokens: int, direction: str) -> Decimal:
    # _calculate_cost only reads `model_for_cost`, so a stand-in avoids building a ClickHouse row.
    return SpanMetricsMixin._calculate_cost(SimpleNamespace(model_for_cost=model), tokens, direction)


def test_model_missing_from_tokencost_is_priced_instead_of_booked_at_zero():
    # gpt-5.5 is newer than tokencost's table; this span used to cost $0.
    assert _cost("gpt-5.5", 100_000, "input") == pytest.approx(Decimal("0.5"))  # $5 per 1M input
    assert _cost("gpt-5.5", 5_000, "output") == pytest.approx(Decimal("0.15"))  # $30 per 1M output


def test_claude_model_missing_from_tokencost_is_priced():
    assert _cost("claude-opus-4-7", 100_000, "input") == pytest.approx(Decimal("0.5"))  # $5 per 1M input


def test_model_in_tokencost_keeps_its_tokencost_price():
    assert _cost("gpt-4o", 1_000_000, "input") == pytest.approx(Decimal("2.5"))


def test_unknown_model_still_costs_zero():
    assert _llm_prices_rate("my-local-finetune", "input") is None
    assert _cost("my-local-finetune", 1_000, "input") == Decimal(0)


def test_no_model_costs_zero():
    assert _cost("", 1_000, "input") == Decimal(0)

import pytest
from decimal import Decimal
from pathlib import Path
from builder.costs import ModelCost, get_tokencost_path, load_model_costs

# For direct validator testing
import pydantic


class TestModelCost:
    """Test cases for the ModelCost class."""

    def test_init_with_complete_data(self):
        """Test initializing ModelCost with complete data."""
        model_cost = ModelCost(
            model="gpt-4",
            provider="openai",
            input=Decimal("0.00001"),
            output=Decimal("0.00003"),
            cached=Decimal("0.000005"),
            reasoning=Decimal("0.000015")
        )

        assert model_cost.model == "gpt-4"
        assert model_cost.provider == "openai"
        assert model_cost.input == Decimal("0.00001")
        assert model_cost.output == Decimal("0.00003")
        assert model_cost.cached == Decimal("0.000005")
        assert model_cost.reasoning == Decimal("0.000015")

    def test_init_with_partial_data(self):
        """Test initializing ModelCost with only required data."""
        model_cost = ModelCost(model="gpt-3.5-turbo")

        assert model_cost.model == "gpt-3.5-turbo"
        assert model_cost.provider is None
        assert model_cost.input == Decimal("0")
        assert model_cost.output == Decimal("0") 
        assert model_cost.cached is None
        assert model_cost.reasoning is None

    def test_init_with_mixed_data(self):
        """Test initializing ModelCost with a mix of data types."""
        model_cost = ModelCost(
            model="claude-3",
            provider="anthropic",
            input=0.00002,  # Float instead of Decimal
            output="0.00004",  # String instead of Decimal
            cached=None,
            reasoning=0  # zero value
        )

        assert model_cost.model == "claude-3"
        assert model_cost.provider == "anthropic"
        assert isinstance(model_cost.input, Decimal)
        assert model_cost.input == Decimal("0.00002")
        assert isinstance(model_cost.output, Decimal)
        assert model_cost.output == Decimal("0.00004")
        assert model_cost.cached is None
        # Zero values should be converted to None per the field validator
        assert model_cost.reasoning is None

    def test_model_dump_formats_decimals(self):
        """Test that model_dump properly formats Decimal values."""
        model_cost = ModelCost(
            model="gpt-4",
            provider="openai",
            input=Decimal("0.00001"),
            output=Decimal("0.00003"),
            cached=Decimal("0.000005"),
            reasoning=Decimal("0.000015")
        )

        dumped = model_cost.model_dump()
        
        assert dumped["model"] == "gpt-4"
        assert dumped["provider"] == "openai"
        assert dumped["input"] == "0.00001"
        assert dumped["output"] == "0.00003"
        assert dumped["cached"] == "0.000005"
        assert dumped["reasoning"] == "0.000015"
        
        # Check that trailing zeros are removed
        model_cost = ModelCost(
            model="test",
            input=Decimal("0.001000000")
        )
        dumped = model_cost.model_dump()
        assert dumped["input"] == "0.001"

    def test_from_tokencost_json(self):
        """Test creating a ModelCost from tokencost JSON format."""
        tokencost_data = {
            "litellm_provider": "openai",
            "input_cost_per_token": 0.00001,
            "output_cost_per_token": 0.00003,
            "cache_read_input_token_cost": 0.000005,
            "reasoning_cost_per_token": 0.000015
        }

        model_cost = ModelCost.from_tokencost_json("gpt-4", tokencost_data)

        assert model_cost.model == "gpt-4"
        assert model_cost.provider == "openai"
        assert model_cost.input == Decimal("0.00001")
        assert model_cost.output == Decimal("0.00003")
        assert model_cost.cached == Decimal("0.000005")
        assert model_cost.reasoning == Decimal("0.000015")

    def test_from_tokencost_json_partial_data(self):
        """Test that partial tokencost JSON data with zero input cost raises ValidationError."""
        tokencost_data = {
            "litellm_provider": "openai",
            "input_cost_per_token": 0,  # This will cause validation error as expected
            "output_cost_per_token": 0.00003,
            # Missing cache_read_input_token_cost
            # Missing reasoning_cost_per_token
        }

        # The validator converts 0 to None, which then fails validation for required Decimal fields
        with pytest.raises(pydantic.ValidationError) as exc_info:
            ModelCost.from_tokencost_json("gpt-4", tokencost_data)

        # Verify the error is about the input field
        assert "input" in str(exc_info.value)

    def test_zero_values_in_validator(self):
        """Test that the convert_to_decimal validator handles zero values correctly."""
        # Test the validator method directly without object creation
        result = ModelCost.convert_to_decimal(0)
        assert result is None  # Zero should convert to None

        result = ModelCost.convert_to_decimal(0.0)
        assert result is None  # Float zero should convert to None

        result = ModelCost.convert_to_decimal(None)
        assert result is None  # None should remain None

        result = ModelCost.convert_to_decimal(0.00003)
        assert result == Decimal("0.00003")  # Non-zero values should be converted to Decimal

    def test_zero_value_in_constructor_raises_error(self):
        """Test that providing a zero value to a required Decimal field raises ValidationError."""
        # Create a model with explicit zero value - it should fail validation since the
        # validator converts 0 to None, which is not valid for a required Decimal field
        with pytest.raises(pydantic.ValidationError) as exc_info:
            ModelCost(
                model="test-model",
                input=0,  # This will be converted to None by the validator
                output=Decimal("0.00003")
            )

        # Verify the error is about the input field
        assert "input" in str(exc_info.value)


class TestTokenCostFunctions:
    """Test cases for the tokencost-related functions."""

    def test_validator_methods(self):
        """Test the validator methods directly."""
        # Test that zero values are converted to None
        assert ModelCost.convert_to_decimal(0) is None
        assert ModelCost.convert_to_decimal(0.0) is None
        
        # Test that None remains None
        assert ModelCost.convert_to_decimal(None) is None
        
        # Test that non-zero values are converted to Decimal correctly
        assert ModelCost.convert_to_decimal(0.00003) == Decimal("0.00003")
        
        # Test decimal formatting in model_dump
        model = ModelCost(model="test", input=Decimal("0.001000"))
        dumped = model.model_dump()
        assert dumped["input"] == "0.001"
        
    def test_get_tokencost_path_integration(self):
        """Integration test for get_tokencost_path with the real package."""
        path = get_tokencost_path()
        
        # The function should return a path
        assert path is not None
        assert isinstance(path, Path)
        
        # The path should point to a directory that exists
        assert path.exists()
        
        # The directory should contain model_prices.json
        assert (path / "model_prices.json").exists()
        
    def test_load_model_costs_integration(self):
        """Integration test for load_model_costs with the real package."""
        # Load real model costs from the tokencost package
        costs = load_model_costs()
        
        # We should get a non-empty list of ModelCost objects
        assert costs is not None
        assert isinstance(costs, list)
        assert len(costs) > 0
        
        # Check that every item is a ModelCost object
        for cost in costs:
            assert isinstance(cost, ModelCost)
            assert cost.model is not None
            assert isinstance(cost.model, str)
            
            # Either input or output should have a valid cost
            has_valid_cost = (
                (cost.input is not None and cost.input > 0) or
                (cost.output is not None and cost.output > 0)
            )
            assert has_valid_cost, f"Model {cost.model} has no valid costs"
            
        # Let's also check for some common models that should be present
        # This might need to be adjusted if the package changes significantly
        model_names = [cost.model for cost in costs]
        common_models = ['gpt-3.5-turbo', 'gpt-4', 'claude-3-opus']
        
        # At least one of these common models should be present
        assert any(model in model_names for model in common_models), \
            f"None of the common models {common_models} found in {model_names[:5]}..."
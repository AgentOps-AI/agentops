import importlib.util
import json
from pathlib import Path
from decimal import Decimal
from typing import Optional
from importlib.metadata import distribution
import pydantic


class ModelCost(pydantic.BaseModel):
    """Pydantic model for storing model cost information with Decimal precision."""

    model: str
    provider: Optional[str] = None
    input: Decimal = pydantic.Field(default=Decimal("0"))
    output: Decimal = pydantic.Field(default=Decimal("0"))
    cached: Optional[Decimal] = None
    reasoning: Optional[Decimal] = None

    def model_dump(self, *args, **kwargs) -> dict:
        """
        Override the model_dump method to ensure Decimal values are formatted correctly.
        """

        def _format_decimal(value) -> str:
            """Format Decimal values to string of max 10 decimal places and remove trailing zeros."""
            return ("%.10f" % value).rstrip('0')

        data = super().model_dump(*args, **kwargs)
        for key in ['input', 'output', 'cached', 'reasoning']:
            if key in data and isinstance(data[key], Decimal):
                data[key] = _format_decimal(data[key])
        return data

    @pydantic.field_validator('input', 'output', 'cached', 'reasoning', mode='before')
    @classmethod
    def convert_to_decimal(cls, value: float | None) -> Optional[Decimal]:
        """Convert float values to Decimal for precise currency calculations."""
        if value is None:
            return None

        if value == 0:
            # zero values should not make it into upstream calculations
            return None

        # casting the float to a string first avoids fp noise on the conversion
        return Decimal(str(value))

    @classmethod
    def from_tokencost_json(cls, name: str, data: dict) -> 'ModelCost':
        """
        Create a ModelCost instance from tokencost JSON format.

        Args:
            name: The name of the model
            data: The model data from tokencost's model_prices.json

        Returns:
            ModelCost: A new ModelCost instance with properly converted Decimal values
        """
        return cls(
            model=name,
            provider=data.get("litellm_provider"),
            input=data.get("input_cost_per_token"),
            output=data.get("output_cost_per_token"),
            cached=data.get("cache_read_input_token_cost"),
            reasoning=data.get("reasoning_cost_per_token"),
        )


def get_tokencost_path() -> Path:
    """
    Determine the installation location of the 'tokencost' package.

    Returns:
        Path: The path to the 'tokencost' package directory
    """
    try:
        # this works for locally installed packages
        spec = importlib.util.find_spec("tokencost")
        if spec is not None and spec.origin is not None:
            path = Path(spec.origin)
            if path.is_file():
                path = path.parent  # remove "__init__.py"
            print(f"tokencost package found at {path}")
            return path

        # this works for site-packages
        dist = distribution("tokencost")
        return dist.locate_file("tokencost")

        raise ImportError("tokencost package not found. Please install it first.")
    except (ImportError, ModuleNotFoundError, ValueError):
        # Package is not installed
        return None


def load_model_costs() -> list[ModelCost]:
    """
    Load model costs from the tokencost model_prices.json file.

    Returns:
        Dict[str, ModelCost]: Dictionary of model costs keyed by model name
    """
    json_path = get_tokencost_path() / "model_prices.json"

    if not json_path.exists():
        raise FileNotFoundError(f"model_prices.json not found at {json_path}")

    with open(json_path, "r") as f:
        data = json.load(f)

    costs = []
    for model_name, model_data in data.items():
        try:
            cost = ModelCost.from_tokencost_json(model_name, model_data)
        except pydantic.ValidationError:
            print(f"Model {model_name} has invalid data. Skipping.")
        costs.append(cost)

    print(f"Loaded {len(costs)} model costs from {json_path}")
    return costs

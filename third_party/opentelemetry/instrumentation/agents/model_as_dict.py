"""Helper function to safely convert model objects to dictionaries."""


def model_as_dict(model):
    """Convert a model object to a dictionary safely."""
    if isinstance(model, dict):
        return model
    if hasattr(model, "model_dump"):
        return model.model_dump()
    elif hasattr(model, "dict"):
        return model.dict()
    elif hasattr(model, "parse"):  # Raw API response
        return model_as_dict(model.parse())
    else:
        # Try to use __dict__ as fallback
        try:
            return model.__dict__
        except:
            return model

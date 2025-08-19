from typing import Any
from datetime import datetime, timedelta, timezone
import pydantic


# Free:
#     30 spans in waterfall
#     100 lines of logs
#     one project
#     one seat
#     one org
#     metrics up to one month lookback
#     5,000 spans per month
#     cant view traces older than 3 days other than last 3 traces regardless how old
# Pro:
#     100,000 spans per month included
#     tool costs
#     evals
#     notifications
#     exports
#     custom attributes
#     cost breakdowns by model
# enterprise:
#     whateva you want babyy


def freeplan_clamp_datetime(dt: None | datetime, days: int) -> datetime:
    """
    Clamp a datetime object to a maximum number of days in the past for free plan users.

    If the provided datetime is older than the cutoff date (further in the past),
    returns the cutoff date. Otherwise, returns the original datetime.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return max(dt, cutoff) if dt else cutoff


def freeplan_clamp_start_time(start_time: None | datetime, days: int) -> tuple[datetime, bool]:
    """
    Clamp a start_time datetime for freeplan users and return whether it was modified.

    Args:
        start_time: The original start time (can be None)
        days: Number of days to allow in the past

    Returns:
        tuple[datetime, bool]: (clamped_datetime, was_modified)
            - clamped_datetime: The final datetime to use
            - was_modified: True if the original value was changed for freeplan limits
    """
    clamped = freeplan_clamp_datetime(start_time, days)
    return clamped, (start_time is None or clamped != start_time)


def freeplan_clamp_end_time(end_time: None | datetime, days: int) -> tuple[datetime, bool]:
    """
    Clamp an end_time datetime for freeplan users and return whether it was modified.

    Args:
        end_time: The original end time (can be None)
        days: Number of days to allow in the past

    Returns:
        tuple[datetime, bool]: (clamped_datetime, was_modified)
            - clamped_datetime: The final datetime to use
            - was_modified: True if the original value was changed for freeplan limits
    """
    # If end_time is not provided, we start freeplan users at the current time
    actual_end_time = end_time if end_time is not None else datetime.now(timezone.utc)
    clamped = freeplan_clamp_datetime(actual_end_time, days)
    return clamped, (end_time is None or clamped != actual_end_time)


class FreePlanFilteredResponse(pydantic.BaseModel):
    """
    Base class for responses that need to be filtered for free plan users.

    This class provides three mechanisms to control the data returned to free plan users:
    1. Exclude certain fields from the response (replacing them with empty values)
    2. Truncate list fields to a maximum number of items
    3. Truncate string fields to a maximum number of lines

    When the `freeplan_truncated` flag is set to True, the `model_dump` method will apply
    these restrictions to the response.

    Attributes:
        _freeplan_exclude (tuple[str]): A tuple of field names to be excluded from the response.
        _freeplan_maxitems (dict[str, int]): A dictionary mapping field names to the maximum
            number of items allowed in that list field.
        _freeplan_maxlines (dict[str, int]): A dictionary mapping field names to the maximum
            number of lines allowed in that string field.
        freeplan_truncated (bool): A flag to indicate whether the response should be restricted
            for free plan users.

    Example for field exclusion:

        class MyResponse(FreePlanFilteredResponse):
            _freeplan_exclude = ('field1', 'field2')

            field1: str
            field2: str
            field3: str

        response = MyResponse(field1='value1', field2='value2', field3='value3')
        response.freeplan_truncated = True

        print(response.model_dump())  # {'field3': 'value3', 'field1': '', 'field2': ''}

    Example for item truncation:
        class MyResponse(FreePlanFilteredResponse):
            _freeplan_maxitems = {'list_field': 2}

            list_field: list[str]

        response = MyResponse(list_field=['item1', 'item2', 'item3', 'item4'])
        response.freeplan_truncated = True

        print(response.model_dump())  # {'list_field': ['item1', 'item2']}

    Example for line truncation:

        class MyResponse(FreePlanFilteredResponse):
            _freeplan_maxlines = {'multiline_field': 3}

            multiline_field: str

        response = MyResponse(multiline_field='line1\\nline2\\nline3\\nline4\\nline5')
        response.freeplan_truncated = True

        print(response.model_dump())  # {'multiline_field': 'line1\\nline2\\nline3'}
    """

    # fields to return empty values for in freeplans
    _freeplan_exclude: tuple[str] = ()
    # list fields to return truncated values for in freeplans (limit number of items)
    _freeplan_maxitems: dict[str, int] = {}
    # string fields to return truncated values for in freeplans (limit line length)
    _freeplan_maxlines: dict[str, int] = {}

    freeplan_truncated: bool = False  # flag to activate this filtering

    def _freeplan_get_empty_fields(self) -> dict[str, Any]:
        """Get the fields we're filtering as empty values of the expected type."""
        # we want to always adhere to the schema in the returned data, so we instantiate
        # the fields as empty values of the expected type
        fields = {}

        for field in self._freeplan_exclude:
            field_type = self.__annotations__.get(field)
            fields[field] = field_type() if field_type else None

        return fields

    def model_dump(self, **kwargs):
        """Override model_dump to exclude fields we don't allow with freeplan"""
        if not self.freeplan_truncated:
            # if the flag is not set, just call the default implementation
            return super().model_dump(**kwargs)

        # by default pydantic doesn't call the model_dump method on nested models
        # so we need to do that manually here
        dump = {}
        exclude = kwargs.get('exclude', [])

        def _is_model(obj: Any) -> bool:
            return isinstance(obj, pydantic.BaseModel)

        def _dump_list(value: list) -> list:
            return [item.model_dump(**kwargs) if _is_model(item) else item for item in value]

        def _apply_max_lines(value: str, max_lines: int) -> str:
            """Apply max lines to a string value."""
            return "\n".join(value.splitlines()[:max_lines])

        for field, value in self.__dict__.items():
            if field in exclude:
                continue  # support default behavior of `exclude`

            if field in self._freeplan_exclude:
                continue  # save resources by not serializing skipped fields

            if _is_model(value):
                dump[field] = value.model_dump(**kwargs)
            elif isinstance(value, list):
                dump[field] = _dump_list(value)
            else:
                dump[field] = value

            if field in self._freeplan_maxitems:
                # restrict the field to a maximum number of items
                assert isinstance(dump[field], list), f"Field {field} must be a list to truncate item count"
                max_items: int = self._freeplan_maxitems[field]
                dump[field] = dump[field][:max_items]

            if field in self._freeplan_maxlines:
                # restrict the field to a maximum number of lines
                assert isinstance(dump[field], str), f"Field {field} must be a string to truncate line count"
                max_lines: int = self._freeplan_maxlines[field]
                dump[field] = _apply_max_lines(dump[field], max_lines)

        # overwrite the fields we don't allow with freeplan
        return {**dump, **self._freeplan_get_empty_fields()}

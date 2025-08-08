import asyncio
from typing import TypeVar, ClassVar, Type, Any, Optional, Union, Collection, Tuple, Literal
from datetime import datetime
from uuid import UUID
import abc
import pydantic
from clickhouse_connect.driver.asyncclient import AsyncClient
from agentops.api.db.clickhouse_client import get_async_clickhouse  # type: ignore


TOperation = TypeVar('TOperation', bound='BaseOperation')
TClickhouseModel = TypeVar('TClickhouseModel', bound='ClickhouseModel')
TClickhouseAggregatedModel = TypeVar('TClickhouseAggregatedModel', bound='ClickhouseAggregatedModel')

# Defines the filterable fields on a Model.
FilterDict = dict[str, Tuple[Union[str, Type[TOperation]], str]]  # {field_name: (operator, db_column)}

# Types that can be automatically formatted for ClickHouse queries
FormattableValue = Union[datetime, UUID, str, int, float, bool, None]

# FilterFields is a dictionary of field names to values that can be used in WHERE clauses
FilterFields = dict[str, FormattableValue]  # Filter values for queries

# SelectFields can be a string (like "*"), a list of field names, or a dict mapping
SelectFields = Union[str, Collection[str], dict[str, str]]

# Fields that can be searched with LIKE/ILIKE pattern matching
SearchFields = dict[str, Tuple[Literal["LIKE", "ILIKE"], str]]  # {field_name: (operator, db_column)}
# Search term is simply a string that gets applied to all configured searchable fields

__all__ = [
    'ClickhouseModel',
    'TClickhouseModel',
    'ClickhouseAggregatedModel',
    'TClickhouseAggregatedModel',
    'FilterDict',
    'FilterFields',
    'FormattableValue',
    'SelectFields',
    'SearchFields',
]


def _format_field_value(value: FormattableValue) -> Any:
    """
    Format field values for ClickHouse queries based on their type.

    This method provides a centralized place to handle type conversions
    for different Python types to their ClickHouse-compatible formats.

    Args:
        value: The value to format (datetime, UUID, or basic types)

    Returns:
        The formatted value suitable for ClickHouse queries
    """
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')  # ClickHouse format: 'YYYY-MM-DD HH:MM:SS'

    if isinstance(value, UUID):
        return str(value)

    return value


class BaseOperation(abc.ABC):
    """
    Base class for custom Clickhouse filter operations.
    """

    @staticmethod
    @abc.abstractmethod
    def format(db_field: str, field: str, value: Any) -> tuple[str, dict]: ...


class WithinListOperation(BaseOperation):
    """
    Operation for filtering within a list of values.
    """

    @staticmethod
    def format(db_field: str, field: str, value: list | tuple) -> tuple[str, dict]:
        # multiple ORs are faster than a single IN
        assert isinstance(value, (list, tuple)), f"Expected list or tuple, got {type(value)}"

        params, conditions = {}, []
        for idx, item in enumerate(value):
            conditions.append(f"{db_field} = %({field}_withinlist_{idx})s")
            params[f"{field}_withinlist_{idx}"] = _format_field_value(item)
        return " OR ".join(conditions), params


class ClickhouseModel(abc.ABC, pydantic.BaseModel):
    """Base abstract model for Clickhouse database interactions.

    This model provides a standardized interface for querying Clickhouse tables,
    with support for filtering, field selection, and result pagination. It handles
    parameter binding and query generation automatically based on class attributes.

    Configuration:
    - table_name: The Clickhouse table to query
    - selectable_fields: Fields to SELECT by default (defaults to "*") This
        should be populated as a lookup table for conversion os column names
        to your python attribute names.
        For example:
            selectable_fields = {'Timestamp': 'timestamp'} allows you to refer
            to `timestamp` in your python code.
    - filterable_fields: Dict mapping Python attribute names to tuples of
        (comparison_operator, db_column_name).
        For example:
            {"project_id": ("=", "ProjectId")} enables filtering by project_id
    - searchable_fields: Dict mapping Python attribute names to tuples of
        (search_operator, db_column_name) for string search operations.
        For example:
            {"name": ("ILIKE", "UserName")} enables searching by name
        For models using GROUP BY with HAVING clauses, the db_column_name should
        reference the column alias created in the query, not the original table column.

    Usage example:
    ```python
    class UserModel(ClickhouseModel):
        table_name = "users"
        selectable_fields = {
            "Id": "id",
            "Age": "age",
            "Timestamp": "timestamp",
            "ProjectId": "project_id",
            "UserName": "name",
        }
        filterable_fields = {
            "user_id": ("=", "Id"),
            "min_age": (">=", "Age"),
            "max_age": ("<=", "Age"),
        }
        searchable_fields = {
            "name": ("ILIKE", "UserName"),
        }

    # Get users between ages 18-30
    users = await UserModel.select(filters={"min_age": 18, "max_age": 30})

    # Search for users with names containing 'john'
    users = await UserModel.select(search="john")
    ```

    This is intended to be used to query a single table.
    Override the _get_query method for more complex query customization.
    See `ClickhouseAggregatedModel` for handling multiple models in a single query.
    """

    table_name: ClassVar[Optional[str]] = None
    selectable_fields: ClassVar[SelectFields] = "*"
    filterable_fields: ClassVar[FilterDict] = {
        # field_name: (comparison_operator, db_column_name)
        "id": ("=", "Id"),
        "start_time": (">=", "Timestamp"),
        "end_time": ("<=", "Timestamp"),
    }
    searchable_fields: ClassVar[SearchFields] = {
        # "field_name": ("ILIKE", db_column_name)
    }

    @classmethod
    def _get_select_clause(cls, *, fields: Optional[SelectFields] = None) -> str:
        """
        Get the selectable fields for the model. This allows subclasses to customize
        the selectable fields dynamically if needed.
        Returns:
            SelectFields: The selectable fields for the model, which can be a string, list, or dict.
        """
        if fields is None:
            fields = cls.selectable_fields

        if isinstance(fields, str):  # str like "*" or a single db column name
            return fields

        if isinstance(fields, (tuple, list)):  # list of field names
            return ', '.join(fields)

        if isinstance(fields, dict):  # dict of field names to db column names
            return ', '.join([f"{db_col} as {field}" for db_col, field in fields.items()])

        raise ValueError(f"Invalid fields type: {type(fields)}. Expected str, list, tuple, or dict.")

    @classmethod
    def _get_search_clause(cls, search_term: Optional[str] = None) -> tuple[str, dict]:
        """
        Generate search conditions based on the searchable_fields configuration.

        Arguments:
            search_term: The search term to apply to all searchable fields

        Returns:
            tuple[str, dict]: A tuple containing:
                - clause: The search conditions string (joined with OR), empty string if no conditions
                - params: Dictionary of parameter values for the conditions
        """
        conditions = []
        params = {}

        if search_term is not None:
            for field, (op, db_field) in cls.searchable_fields.items():
                param_name = f"search_{field}"  # avoid collisions with other params
                conditions.append(f"{db_field} {op} %({param_name})s")
                params[param_name] = f"%{search_term}%"

        # Join conditions with OR - this is more intuitive for searches across multiple fields
        # Users expect to see results where ANY field matches, not where ALL fields match
        return " OR ".join(conditions), params

    @classmethod
    def _get_where_clause(cls, **filters: FormattableValue) -> tuple[str, dict]:
        """
        Generate the WHERE clause for the SQL query based on the provided filterable fields.

        Arguments:
            filters: The keyword arguments to filter on. Each key should match a filterable field in the model.

        Returns:
            tuple[str, dict]: A tuple containing:
                - clause: The WHERE clause string (joined with AND), empty string if no conditions
                - params: Dictionary of parameter values for the conditions

        Example:
            (
                "ProjectId = %(project_id)s AND Timestamp >= %(start_time)s",
                {'project_id': 'my_project', 'start_time': '2023-01-01'}
            )
        """
        conditions = []
        params = {}

        for field, (op, db_field) in cls.filterable_fields.items():
            if (value := filters.get(field)) is not None:
                if isinstance(op, type) and issubclass(op, BaseOperation):
                    # dynamic operation
                    _cond, _params = op.format(db_field, field, value)
                    conditions.append(_cond)
                    params.update(_params)
                else:
                    # basic operation
                    conditions.append(f"{db_field} {op} %({field})s")
                    params[field] = _format_field_value(value)

        # Join conditions with AND
        return " AND ".join(conditions), params

    @classmethod
    def _get_select_query(
        cls: Type[TClickhouseModel],
        *,
        fields: Optional[SelectFields] = None,
        filters: Optional[FilterFields] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> tuple[str, dict[str, Any]]:
        """Generate SQL query and parameters for this model.

        This internal method builds the SQL query string and parameters dictionary
        used by the select method. It's commonly overridden by subclasses to
        customize the query logic or structure.

        Args:
            fields: Fields to select (defaults to cls.selectable_fields)
            filters: Filters to apply in the WHERE clause
            search: Search string to apply to all configured searchable fields
            order_by: ORDER BY clause (without the "ORDER BY" prefix)
            offset: OFFSET value for pagination
            limit: LIMIT value to restrict result count

        Returns:
            tuple[str, dict]: A tuple containing:
              - The SQL query string with parameterized values
              - A dictionary of parameter values for safe query execution
        """
        assert cls.table_name, f"table_name must be set for {cls.__name__} to generate SQL queries"

        select_clause = cls._get_select_clause(fields=fields)
        filter_clause, filter_params = cls._get_where_clause(**(filters or {}))
        search_clause, search_params = cls._get_search_clause(search)
        params = {**filter_params, **search_params}

        if filter_clause and search_clause:
            where_clause = f"({filter_clause}) AND ({search_clause})"
        else:
            where_clause = filter_clause or search_clause

        query = f"""
        SELECT {select_clause}
        FROM {cls.table_name}
        {f"WHERE {where_clause}" if where_clause else ""}
        """

        if order_by is not None:
            query += f" ORDER BY {order_by}"

        if limit is not None:
            query += f" LIMIT {limit}"

        if offset is not None:
            query += f" OFFSET {offset}"

        return query, params

    @classmethod
    async def select(
        cls: Type[TClickhouseModel],
        *,
        fields: Optional[SelectFields] = None,
        filters: Optional[FilterFields] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list[TClickhouseModel]:
        """Query the database and return a list of model instances.

        This method builds and executes a SQL query based on the provided parameters and
        class configuration, then converts the query results into model instances.

        Args:
            fields: Optional list of fields to select. Defaults to cls.selectable_fields.
                Example: ["id", "name", "email"]
            filters: Optional dictionary of filters to apply. Keys must be defined in
                cls.filterable_fields to be effective.
                Example: {"project_id": "123", "start_time": "2023-01-01"}
            search: Optional search string to apply to all searchable fields configured in
                cls.searchable_fields. For LIKE/ILIKE searches, wildcards (%)
                are automatically added if not present.
                Example: "authentication" will search all configured fields for "authentication"
            order_by: Optional ORDER BY clause (without the "ORDER BY" prefix).
                Example: "created_at DESC"
            offset: Optional OFFSET value for pagination.
            limit: Optional LIMIT value to restrict the number of results.

        Returns:
            List[TClickhouseModel]: A list of model instances of the exact calling class type,
            with each instance created from a row in the query results. The return type is
            properly typed using generics to preserve the concrete subclass type.

        Example:
            ```python
            # Get last 10 traces for a specific project
            traces = await TraceModel.select(
                filters={"project_id": "abc123"},
                order_by="timestamp DESC",
                limit=10
            )

            # Search for traces with spans containing "authentication"
            traces = await TraceModel.select(
                filters={"project_id": "abc123"},
                search="authentication",
                limit=10
            )

            # Access model properties on the results
            for trace in traces:
                print(f"Trace {trace.trace_id}: {trace.total_tokens} tokens")
            ```
        """
        query, params = cls._get_select_query(
            fields=fields,
            filters=filters,
            search=search,
            order_by=order_by,
            offset=offset,
            limit=limit,
        )
        client: AsyncClient = await get_async_clickhouse()
        result = await client.query(query, parameters=params)
        results = list(result.named_results())
        return [cls(**row) for row in results]


class ClickhouseAggregatedModel(abc.ABC, pydantic.BaseModel):
    """Base model for composing and executing multiple Clickhouse queries in parallel.

    This model allows you to combine results from multiple ClickhouseModel queries
    into a single aggregated model. It executes all queries concurrently for better
    performance and constructs a model instance with the combined results.

    Configuration:
    - aggregated_models: Class variable listing the ClickhouseModel subclasses to query

    How it works:
    1. The select() method takes filters that apply to all underlying models
    2. Queries from each model in aggregated_models are generated and executed in parallel
    3. Results from each query are passed as positional arguments to the constructor
    4. The model can then process and combine data from all queries

    This pattern is useful when you need to:
    - Fetch different types of data in a single request
    - Create aggregated metrics from multiple tables
    - Provide a unified API for related data
    """

    aggregated_models: ClassVar[Collection[Type[ClickhouseModel]]]

    # TODO this can accept all the other query params, too
    @classmethod
    async def select(
        cls: Type[TClickhouseAggregatedModel],
        *,
        fields: Optional[SelectFields] = None,
        filters: Optional[FilterFields] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> TClickhouseAggregatedModel:
        """Execute parallel queries for all aggregated models and return a combined model.

        This method:
        1. Generates a query for each model defined in aggregated_models
        2. Executes all queries concurrently using asyncio.gather
        3. Processes the results into lists of model instances
        4. Passes the processed results to the model's constructor

        When passing arguments:
        It is up to the individual model implementations to accept the arguments
        in their `select` method and process them accordingly.

        Args:
            fields: Optional list of fields to select for each aggregated model.
            filters: Optional dictionary of filters to apply to all aggregated models.
                This should match the filterable fields in each model.
            search: Optional search string to apply to all searchable fields
                configured in each model's searchable_fields.
            order_by: Optional ORDER BY clause (without the "ORDER BY" prefix) to apply to each query.
            offset: Optional OFFSET value for pagination (applies to each query).
            limit: Optional LIMIT value to restrict the number of results for each query.

        Returns:
            An instance of the calling class, initialized with the results
            from all the queries. The exact return type depends on the
            implementation of the subclass's __init__ method. Results are passed
            as positional arguments corresponding to the order of models in
            `aggregated_models`.
        """
        assert cls.aggregated_models, f"{cls.__name__} must define `aggregated_models`"

        client: AsyncClient = await get_async_clickhouse()
        queries: list[str] = []
        params: list[dict] = []

        for model_cls in cls.aggregated_models:
            _query, _params = model_cls._get_select_query(
                fields=fields,
                filters=filters,
                search=search,
                order_by=order_by,
                offset=offset,
                limit=limit,
            )
            queries.append(_query)
            params.append(_params)

        responses: list = await asyncio.gather(
            *[client.query(q, parameters=p) for q, p in zip(queries, params)]
        )

        results: list = []
        for response in responses:
            results.append(list(response.named_results()))

        return cls(*results)

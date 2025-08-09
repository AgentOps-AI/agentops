# Custom Clickhouse ORM Documentation

## Overview

This custom ORM provides a Pydantic-based interface to Clickhouse databases, offering strong typing, async query execution, and flexible query building. It consists of two main model types:

1. `ClickhouseModel` - Base model for single table queries with filtering and search support
2. `ClickhouseAggregatedModel` - Model for executing multiple parallel queries

## `ClickhouseModel`

### Purpose

Provides a standardized interface for querying Clickhouse tables with support for filtering, field selection, and pagination.

### Key Features

- Automatic parameter binding and SQL injection prevention
- Type-safe query results via Pydantic models
- Flexible field selection and filtering
- String-based search functionality across multiple fields
- Clean SQL generation without unnecessary clauses
- Pagination support (limit/offset)
- Async execution

### Configuration

When creating a model that inherits from `ClickhouseModel`, define these class variables:

```python
class MyModel(ClickhouseModel):
    # Required: The Clickhouse table name
    table_name = "my_table"

    # Field mapping: DB column names to Python attribute names
    selectable_fields = {
        "Id": "id",                # Maps DB column "Id" to Python attr "id"
        "Timestamp": "timestamp",
        "ProjectId": "project_id"
    }

    # Filterable fields with operators
    filterable_fields = {
        # Python attr name: (comparison operator, DB column name)
        "project_id": ("=", "ProjectId"),
        "start_time": (">=", "Timestamp"),
        "end_time": ("<=", "Timestamp")
    }

    # Searchable fields (string pattern matching)
    searchable_fields = {
        # Python attr name: (search operator, DB column name)
        "name": ("ILIKE", "UserName"),
        "description": ("ILIKE", "Description")
    }

    # Define model attributes that match your selectable_fields
    id: str
    timestamp: datetime
    project_id: str
```

### Usage Examples

#### Basic Query

```python
# Get all records for a project
results = await MyModel.select(filters={"project_id": "abc123"})
```

#### With Pagination

```python
# Get the first 20 records, ordered by timestamp
results = await MyModel.select(
    filters={"project_id": "abc123"},
    order_by="timestamp DESC",
    limit=20
)

# Get the next 20
results = await MyModel.select(
    filters={"project_id": "abc123"},
    order_by="timestamp DESC",
    limit=20,
    offset=20
)
```

#### With Date Range

```python
# Get records in a date range
results = await MyModel.select(filters={
    "project_id": "abc123",
    "start_time": datetime(2023, 1, 1),
    "end_time": datetime(2023, 1, 31)
})
```

#### With Search

```python
# Search for records containing "authentication" in searchable fields
results = await MyModel.select(
    filters={"project_id": "abc123"},
    search="authentication"
)

# The search is applied to all fields defined in searchable_fields
# Wildcards (%) are automatically added for LIKE/ILIKE searches if not present
# Search conditions are combined with OR (matches any field)
```

#### Combining Filters and Search

```python
# Filter by project and date range, then search within those results
results = await MyModel.select(
    filters={
        "project_id": "abc123",
        "start_time": datetime(2023, 1, 1),
        "end_time": datetime(2023, 1, 31)
    },
    search="error",
    limit=50
)
```

## `ClickhouseAggregatedModel`

### Purpose

Allows combining results from multiple `ClickhouseModel` queries into a single aggregated model. It executes all queries concurrently for better performance.

### Key Features

- Parallel query execution
- Results aggregation into a single model
- Type safety through Pydantic validation

### Configuration

```python
class MyAggregatedModel(ClickhouseAggregatedModel):
    # List of model classes to query
    aggregated_models = (ModelA, ModelB, ModelC)

    # Define how to store the results
    model_a_results: list[ModelA] = pydantic.Field(default_factory=list)
    model_b_results: list[ModelB] = pydantic.Field(default_factory=list)
    model_c_results: list[ModelC] = pydantic.Field(default_factory=list)

    # Custom constructor to handle results from each model
    def __init__(self, model_a_data, model_b_data, model_c_data):
        super().__init__(
            model_a_results=[ModelA(**row) for row in model_a_data],
            model_b_results=[ModelB(**row) for row in model_b_data],
            model_c_results=[ModelC(**row) for row in model_c_data]
        )
```

### Usage Examples

```python
# Get data from multiple models with shared filters and search
aggregate = await MyAggregatedModel.select(
    filters={
        "project_id": "abc123",
        "start_time": datetime(2023, 1, 1),
        "end_time": datetime(2023, 1, 31)
    },
    search="important"
)

# Access the results
for item in aggregate.model_a_results:
    print(item.id)
```

## Extending the ORM

### Custom Field Mappings

For more complex field conversions, use Pydantic validators:

```python
class ModelWithValidation(ClickhouseModel):
    # ... configuration ...

    # Create a status field based on status_code
    @pydantic.field_validator('status_code', check_fields=False, mode='before')
    @classmethod
    def uppercase_status(cls, v: str) -> str:
        return v.upper()

    # Create a computed property
    @property
    def is_error(self) -> bool:
        return self.status_code == "ERROR"
```

## Best Practices

1. **Type Safety**: Always define proper types for model attributes to leverage Pydantic's validation

2. **Query Optimization**: Use appropriate filters and limit results for better performance

3. **Field Selection**: Only select the fields you need

4. **Model Composition**: Use the aggregated model for related data that's frequently queried together

5. **Error Handling**: Handle database exceptions appropriately

```python
try:
    results = await MyModel.select(filters={"project_id": project_id})
except Exception as e:
    # Handle Clickhouse exceptions
    logger.error(f"Database error: {e}")
    raise HttpException(500, "Database error occurred")
```

## SQL Generation

The ORM generates clean SQL without unnecessary clauses:

1. WHERE clauses are only included when conditions exist
2. Search conditions are joined with OR (any field can match)
3. Multiple filter conditions are joined with AND (all conditions must match)

Example SQL generated:

```sql
SELECT Id as id, Name as name, Timestamp as timestamp
FROM users
WHERE ProjectId = %(project_id)s AND Timestamp >= %(start_time)s
ORDER BY timestamp DESC
LIMIT 20
```

With search:

```sql
SELECT Id as id, Name as name, Timestamp as timestamp
FROM users
WHERE (ProjectId = %(project_id)s) AND (Name ILIKE %(search_name)s OR Description ILIKE %(search_description)s)
LIMIT 50
```

## Implementation Details

This ORM uses `clickhouse_connect` for async communication with Clickhouse. Under the hood, it:

1. Converts model definitions to parameterized SQL
2. Executes queries asynchronously
3. Maps result rows to Pydantic model instances
4. Handles type conversion and validation

For advanced use cases, refer to the implementation in `api/agentops/api/db/clickhouse/models.py`.
import re
from typing import ClassVar
from agentops.api.db.clickhouse.models import ClickhouseModel, SelectFields, FilterDict, SearchFields


def normalize_sql(sql: str) -> str:
    """Normalize SQL string for exact comparison.

    This preserves the actual SQL format while handling things like
    trailing semicolons and consistent spacing.
    """
    # Remove extra spaces and newlines
    return re.sub(r'\s+', ' ', sql.strip())


class TestModel(ClickhouseModel):
    """Test model for query builder tests"""

    table_name: ClassVar[str] = "test_table"
    selectable_fields: ClassVar[SelectFields] = {
        "Id": "id",
        "Name": "name",
        "Age": "age",
        "ProjectId": "project_id",
        "Timestamp": "timestamp",
    }
    filterable_fields: ClassVar[FilterDict] = {
        "id": ("=", "Id"),
        "min_age": (">=", "Age"),
        "max_age": ("<=", "Age"),
        "project_id": ("=", "ProjectId"),
        "start_time": (">=", "Timestamp"),
        "end_time": ("<=", "Timestamp"),
    }
    searchable_fields: ClassVar[SearchFields] = {
        "name": ("ILIKE", "Name"),
        "project_id": ("LIKE", "ProjectId"),
    }


class TestModelWithStringFields(ClickhouseModel):
    """Test model with string selectable fields"""

    table_name: ClassVar[str] = "test_table_string"
    selectable_fields: ClassVar[SelectFields] = "*"


class TestModelWithListFields(ClickhouseModel):
    """Test model with list selectable fields"""

    table_name: ClassVar[str] = "test_table_list"
    selectable_fields: ClassVar[SelectFields] = ["Id", "Name", "Age"]


def test_get_select_clause_dict():
    """Test _get_select_clause with dictionary fields"""
    select_clause = TestModel._get_select_clause()
    # The exact order must match the order in the class definition
    expected = "Id as id, Name as name, Age as age, ProjectId as project_id, Timestamp as timestamp"
    assert select_clause == expected


def test_get_select_clause_string():
    """Test _get_select_clause with string fields"""
    select_clause = TestModelWithStringFields._get_select_clause()
    assert select_clause == "*"


def test_get_select_clause_list():
    """Test _get_select_clause with list fields"""
    select_clause = TestModelWithListFields._get_select_clause()
    assert select_clause == "Id, Name, Age"


def test_get_select_clause_override():
    """Test _get_select_clause with overridden fields"""
    select_clause = TestModel._get_select_clause(fields=["Id", "Name"])
    assert select_clause == "Id, Name"


def test_get_where_clause_empty():
    """Test _get_where_clause with empty filters"""
    where_clause, params = TestModel._get_where_clause()
    assert where_clause == ""
    assert params == {}


def test_get_where_clause_single_filter():
    """Test _get_where_clause with a single filter"""
    where_clause, params = TestModel._get_where_clause(id="123")
    assert where_clause == "Id = %(id)s"
    assert params == {"id": "123"}


def test_get_where_clause_multiple_filters():
    """Test _get_where_clause with multiple filters"""
    where_clause, params = TestModel._get_where_clause(project_id="abc", min_age=18, max_age=65)

    # Only the fields we provided should be in the result
    assert where_clause == "Age >= %(min_age)s AND Age <= %(max_age)s AND ProjectId = %(project_id)s"
    assert params == {"min_age": 18, "max_age": 65, "project_id": "abc"}


def test_get_search_clause_empty():
    """Test _get_search_clause with no search term"""
    search_clause, params = TestModel._get_search_clause()
    assert search_clause == ""
    assert params == {}


def test_get_search_clause_with_term():
    """Test _get_search_clause with a search term"""
    search_clause, params = TestModel._get_search_clause(search_term="test")

    # Order based on TestModel.searchable_fields
    assert search_clause == "Name ILIKE %(search_name)s OR ProjectId LIKE %(search_project_id)s"
    assert params == {"search_name": "%test%", "search_project_id": "%test%"}


def test_get_select_query_basic():
    """Test _get_select_query with basic parameters"""
    query, params = TestModel._get_select_query()

    normalized_query = normalize_sql(query)
    # Order matches the order in TestModel.selectable_fields
    expected_query = normalize_sql(
        "SELECT Id as id, Name as name, Age as age, ProjectId as project_id, Timestamp as timestamp FROM test_table"
    )
    assert normalized_query == expected_query
    assert params == {}


def test_get_select_query_string_fields():
    """Test _get_select_query with string selectable fields"""
    query, params = TestModelWithStringFields._get_select_query()

    normalized_query = normalize_sql(query)
    assert normalized_query == "SELECT * FROM test_table_string"
    assert params == {}


def test_get_select_query_list_fields():
    """Test _get_select_query with list selectable fields"""
    query, params = TestModelWithListFields._get_select_query()

    normalized_query = normalize_sql(query)
    assert normalized_query == "SELECT Id, Name, Age FROM test_table_list"
    assert params == {}


def test_get_select_query_with_filters():
    """Test _get_select_query with filters"""
    query, params = TestModel._get_select_query(filters={"id": "123"})

    normalized_query = normalize_sql(query)
    expected_query = normalize_sql(
        "SELECT Id as id, Name as name, Age as age, ProjectId as project_id, Timestamp as timestamp FROM test_table WHERE Id = %(id)s"
    )
    assert normalized_query == expected_query
    assert params == {"id": "123"}


def test_get_select_query_with_search():
    """Test _get_select_query with search term"""
    query, params = TestModel._get_select_query(search="test")

    normalized_query = normalize_sql(query)
    expected_query = normalize_sql(
        "SELECT Id as id, Name as name, Age as age, ProjectId as project_id, Timestamp as timestamp FROM test_table WHERE Name ILIKE %(search_name)s OR ProjectId LIKE %(search_project_id)s"
    )
    assert normalized_query == expected_query
    assert params == {"search_name": "%test%", "search_project_id": "%test%"}


def test_get_select_query_with_filters_and_search():
    """Test _get_select_query with both filters and search"""
    query, params = TestModel._get_select_query(filters={"id": "123"}, search="test")

    normalized_query = normalize_sql(query)
    # Verify the order in both the select fields and the search fields
    expected_query = normalize_sql(
        "SELECT Id as id, Name as name, Age as age, ProjectId as project_id, Timestamp as timestamp FROM test_table WHERE (Id = %(id)s) AND (Name ILIKE %(search_name)s OR ProjectId LIKE %(search_project_id)s)"
    )
    assert normalized_query == expected_query
    assert params == {"id": "123", "search_name": "%test%", "search_project_id": "%test%"}


def test_get_select_query_with_order_by():
    """Test _get_select_query with order_by parameter"""
    query, params = TestModel._get_select_query(order_by="Timestamp DESC")

    normalized_query = normalize_sql(query)
    expected_query = normalize_sql(
        "SELECT Id as id, Name as name, Age as age, ProjectId as project_id, Timestamp as timestamp FROM test_table ORDER BY Timestamp DESC"
    )
    assert normalized_query == expected_query
    assert params == {}


def test_get_select_query_with_limit():
    """Test _get_select_query with limit parameter"""
    query, params = TestModel._get_select_query(limit=10)

    normalized_query = normalize_sql(query)
    expected_query = normalize_sql(
        "SELECT Id as id, Name as name, Age as age, ProjectId as project_id, Timestamp as timestamp FROM test_table LIMIT 10"
    )
    assert normalized_query == expected_query
    assert params == {}


def test_get_select_query_with_offset():
    """Test _get_select_query with offset parameter"""
    query, params = TestModel._get_select_query(offset=20)

    normalized_query = normalize_sql(query)
    expected_query = normalize_sql(
        "SELECT Id as id, Name as name, Age as age, ProjectId as project_id, Timestamp as timestamp FROM test_table OFFSET 20"
    )
    assert normalized_query == expected_query
    assert params == {}


def test_get_select_query_complete():
    """Test _get_select_query with all parameters"""
    query, params = TestModel._get_select_query(
        fields=["Id", "Name", "Age"],
        filters={"project_id": "abc123", "min_age": 21},
        search="test",
        order_by="Age DESC",
        limit=10,
        offset=20,
    )

    normalized_query = normalize_sql(query)
    # Match the exact ordering as defined in the model's class variables
    expected_query = normalize_sql("""
        SELECT Id, Name, Age
        FROM test_table
        WHERE (Age >= %(min_age)s AND ProjectId = %(project_id)s)
        AND (Name ILIKE %(search_name)s OR ProjectId LIKE %(search_project_id)s)
        ORDER BY Age DESC
        LIMIT 10
        OFFSET 20
    """)
    assert normalized_query == expected_query
    assert params == {
        "project_id": "abc123",
        "min_age": 21,
        "search_name": "%test%",
        "search_project_id": "%test%",
    }

# # Text-to-SQL
#
# In this tutorial, we’ll see how to implement an agent that leverages SQL using `smolagents`.
# > Let’s start with the golden question: why not keep it simple and use a standard text-to-SQL pipeline?
#
# A standard text-to-sql pipeline is brittle, since the generated SQL query can be incorrect. Even worse, the query could be incorrect, but not raise an error, instead giving some incorrect/useless outputs without raising an alarm.
#
# Instead, an agent system is able to critically inspect outputs and decide if the query needs to be changed or not, thus giving it a huge performance boost.
#
# Let’s build this agent!
# ## Installation
# We will install the necessary packages for this example. We are going to use `sqlalchemy` to create a database and `smolagents` to build our agent. We will use `litellm` for LLM inference and `agentops` for observability.
# %pip install smolagents
# %pip install sqlalchemy
# %pip install agentops
# ## Setting up the SQL Table
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    Float,
    insert,
    inspect,
    text,
)
from smolagents import tool
import agentops
from dotenv import load_dotenv
import os
from smolagents import CodeAgent, LiteLLMModel

engine = create_engine("sqlite:///:memory:")
metadata_obj = MetaData()

# create city SQL table
table_name = "receipts"
receipts = Table(
    table_name,
    metadata_obj,
    Column("receipt_id", Integer, primary_key=True),
    Column("customer_name", String(16), primary_key=True),
    Column("price", Float),
    Column("tip", Float),
)
metadata_obj.create_all(engine)

rows = [
    {"receipt_id": 1, "customer_name": "Alan Payne", "price": 12.06, "tip": 1.20},
    {"receipt_id": 2, "customer_name": "Alex Mason", "price": 23.86, "tip": 0.24},
    {"receipt_id": 3, "customer_name": "Woodrow Wilson", "price": 53.43, "tip": 5.43},
    {"receipt_id": 4, "customer_name": "Margaret James", "price": 21.11, "tip": 1.00},
]
for row in rows:
    stmt = insert(receipts).values(**row)
    with engine.begin() as connection:
        cursor = connection.execute(stmt)
# ## Build our Agent
# We need to create the table description first because the agent will use it to generate the SQL query.
inspector = inspect(engine)
columns_info = [(col["name"], col["type"]) for col in inspector.get_columns("receipts")]

table_description = "Columns:\\n" + "\\n".join([f"  - {name}: {col_type}" for name, col_type in columns_info])
print(table_description)
# Now we can create the tool that will be used by the agent to perform the SQL query.


@tool
def sql_engine(query: str) -> str:
    """
    Allows you to perform SQL queries on the table. Returns a string representation of the result.
    The table is named 'receipts'. Its description is as follows:
        Columns:
        - receipt_id: INTEGER
        - customer_name: VARCHAR(16)
        - price: FLOAT
        - tip: FLOAT

    Args:
        query: The query to perform. This should be correct SQL.
    """
    output = ""
    with engine.connect() as con:
        rows = con.execute(text(query))
        for row in rows:
            output += "\\n" + str(row)
    return output


# Everything is ready to create the agent. We will use the `CodeAgent` class from `smolagents` to create the agent. `litellm` is used to create the model and the agent will use the `sql_engine` tool to perform the SQL query.
#
# `agentops` is used to track the agents. We will initialize it with our API key, which can be found in the [AgentOps settings](https://app.agentops.ai/settings/projects).

load_dotenv()

os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

agentops.init(auto_start_session=False, trace_name="Smolagents Text-to-SQL")
tracer = agentops.start_trace(
    trace_name="Smolagents Text-to-SQL", tags=["smolagents", "example", "text-to-sql", "agentops-example"]
)
model = LiteLLMModel("openai/gpt-4o-mini")
agent = CodeAgent(
    tools=[sql_engine],
    model=model,
)
agent.run("Can you give me the name of the client who got the most expensive receipt?")
# ## Level 2: Table Joins
# Now let’s make it more challenging! We want our agent to handle joins across multiple tables.
#
# So let’s make a second table recording the names of waiters for each receipt_id!
table_name = "waiters"
receipts = Table(
    table_name,
    metadata_obj,
    Column("receipt_id", Integer, primary_key=True),
    Column("waiter_name", String(16), primary_key=True),
)
metadata_obj.create_all(engine)

rows = [
    {"receipt_id": 1, "waiter_name": "Corey Johnson"},
    {"receipt_id": 2, "waiter_name": "Michael Watts"},
    {"receipt_id": 3, "waiter_name": "Michael Watts"},
    {"receipt_id": 4, "waiter_name": "Margaret James"},
]
for row in rows:
    stmt = insert(receipts).values(**row)
    with engine.begin() as connection:
        cursor = connection.execute(stmt)
# Since we changed the table, we update the `SQLExecutorTool` with this table’s description to let the LLM properly leverage information from this table.
updated_description = """Allows you to perform SQL queries on the table. Beware that this tool's output is a string representation of the execution output.
It can use the following tables:"""

inspector = inspect(engine)
for table in ["receipts", "waiters"]:
    columns_info = [(col["name"], col["type"]) for col in inspector.get_columns(table)]

    table_description = f"Table '{table}':\\n"

    table_description += "Columns:\\n" + "\\n".join([f"  - {name}: {col_type}" for name, col_type in columns_info])
    updated_description += "\\n\\n" + table_description

print(updated_description)
# Now let's update the `SQLExecutorTool` with the updated description and run the agent again.
sql_engine.description = updated_description

agent = CodeAgent(
    tools=[sql_engine],
    model=model,
)

agent.run("Which waiter got more total money from tips?")
# All done! Now we can end the agentops session with a "Success" state. You can also end the session with a "Failure" or "Indeterminate" state, where the "Indeterminate" state is used by default.
agentops.end_trace(tracer, end_state="Success")

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=tracer)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise

# You can view the session in the [AgentOps dashboard](https://app.agentops.ai/sessions) by clicking the link provided after ending the session.

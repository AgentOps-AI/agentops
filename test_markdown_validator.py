import sys
from crewai import Agent, Task
from langchain.tools import tool
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from pymarkdown.api import PyMarkdownApi, PyMarkdownApiException
from io import StringIO
import agentops
from agentops.telemetry import TelemetryManager

# Load environment variables
load_dotenv()

# Configure OpenTelemetry exporters first
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from agentops.telemetry.postgres_exporter import PostgresSpanExporter

# Create and configure the tracer provider
resource = Resource.create({
    SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "agentops"),
    "environment": "test"
})

provider = TracerProvider(resource=resource)

# Set up PostgreSQL exporter
postgres_exporter = PostgresSpanExporter(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    database=os.getenv("POSTGRES_DB", "agentops_test"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    table_name="otel_spans"
)
postgres_processor = BatchSpanProcessor(postgres_exporter)
provider.add_span_processor(postgres_processor)

# Set up OTLP exporter for Jaeger
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
)
otlp_processor = BatchSpanProcessor(otlp_exporter)
provider.add_span_processor(otlp_processor)

# Set as global provider
trace.set_tracer_provider(provider)

# Initialize AgentOps with telemetry disabled since we're using our own provider
agentops.init(
    api_key=os.getenv("AGENTOPS_DEV_API_KEY"),
    default_tags=["crewai", "markdown_validator", "otel-test"],
    endpoint=os.getenv("AGENTOPS_API_ENDPOINT")
)

@tool("markdown_validation_tool")
def markdown_validation_tool(file_path: str) -> str:
    """
    A tool to review files for markdown syntax errors.

    Returns:
    - validation_results: A list of validation results
    and suggestions on how to fix them.
    """

    print("\n\nValidating Markdown syntax...\n\n" + file_path)

    try:
        if not (os.path.exists(file_path)):
            return "Could not validate file. The provided file path does not exist."

        scan_result = PyMarkdownApi().scan_path(file_path.rstrip().lstrip())
        results = str(scan_result)
        return results  # Return the reviewed document
    except PyMarkdownApiException as this_exception:
        print(f"API Exception: {this_exception}", file=sys.stderr)
        return f"API Exception: {str(this_exception)}"

default_llm = ChatOpenAI(
    openai_api_base=os.environ.get("OPENAI_API_BASE_URL", "https://api.openai.com/v1"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.1,
    model_name=os.environ.get("MODEL_NAME", "gpt-3.5-turbo"),
)

filename = "README.md"

general_agent = Agent(
    role="Requirements Manager",
    goal="""Provide a detailed list of the markdown 
                            linting results. Give a summary with actionable 
                            tasks to address the validation results. Write your 
                            response as if you were handing it to a developer 
                            to fix the issues.
                            DO NOT provide examples of how to fix the issues or
                            recommend other tools to use.""",
    backstory="""You are an expert business analyst 
				and software QA specialist. You provide high quality, 
                    thorough, insightful and actionable feedback via 
                    detailed list of changes and actionable tasks.""",
    allow_delegation=False,
    verbose=True,
    tools=[markdown_validation_tool],
    llm=default_llm,
)  # groq_llm)

syntax_review_task = Task(
    description=f"""
        Use the markdown_validation_tool to review 
        the file(s) at this path: {filename}
        
        Be sure to pass only the file path to the markdown_validation_tool.
        Use the following format to call the markdown_validation_tool:
        Do I need to use a tool? Yes
        Action: markdown_validation_tool
        Action Input: {filename}

        Get the validation results from the tool 
        and then summarize it into a list of changes
        the developer should make to the document.
        DO NOT recommend ways to update the document.
        DO NOT change any of the content of the document or
        add content to it. It is critical to your task to
        only respond with a list of changes.
        
        If you already know the answer or if you do not need 
        to use a tool, return it as your Final Answer.""",
    agent=general_agent,
    expected_output="",
)

syntax_review_task.execute_sync()

# End AgentOps session
agentops.end_session("Success") 
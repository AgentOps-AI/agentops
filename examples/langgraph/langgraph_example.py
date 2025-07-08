import os
from typing import Annotated, Literal, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
import agentops
from dotenv import load_dotenv

load_dotenv()

agentops.init(
    os.getenv("AGENTOPS_API_KEY"),
    trace_name="LangGraph Tool Usage Example",
    tags=["langgraph", "tool-usage", "agentops-example"],
)


@tool
def get_weather(location: str) -> str:
    """Get the weather for a given location."""
    weather_data = {
        "New York": "Sunny, 72°F",
        "London": "Cloudy, 60°F",
        "Tokyo": "Rainy, 65°F",
        "Paris": "Partly cloudy, 68°F",
        "Sydney": "Clear, 75°F",
    }
    return weather_data.get(location, f"Weather data not available for {location}")


@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        result = eval(expression)
        return f"The result is: {result}"
    except Exception as e:
        return f"Error calculating expression: {str(e)}"


tools = [get_weather, calculate]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


model = ChatOpenAI(temperature=0, model="gpt-4o-mini").bind_tools(tools)


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"


def call_model(state: AgentState):
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def call_tools(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]

    tool_messages = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        for tool_obj in tools:
            if tool_obj.name == tool_name:
                result = tool_obj.invoke(tool_args)
                tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
                break

    return {"messages": tool_messages}


workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", call_tools)

workflow.set_entry_point("agent")

workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})

workflow.add_edge("tools", "agent")

app = workflow.compile()


def run_example():
    print("=== LangGraph + AgentOps Example ===\n")

    queries = [
        "What's the weather in New York and Tokyo?",
        "Calculate 25 * 4 + 10",
        "What's the weather in Paris? Also calculate 100/5",
    ]

    for query in queries:
        print(f"Query: {query}")
        print("-" * 40)

        messages = [HumanMessage(content=query)]
        result = app.invoke({"messages": messages})

        final_message = result["messages"][-1]
        print(f"Response: {final_message.content}\n")


if __name__ == "__main__":
    run_example()
    print("✅ Check your AgentOps dashboard for the trace!")


# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that we have enough spans tracked properly...")
try:
    # LangGraph doesn't emit LLM spans in the same format, so we just check span count
    result = agentops.validate_trace_spans(trace_context=None, check_llm=False, min_spans=5)
    print(f"\n✅ Success! {result['span_count']} spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise

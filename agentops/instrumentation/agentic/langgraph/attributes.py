from typing import Dict, Any
import json


def ensure_no_none_values(attributes: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in attributes.items() if v is not None}


def set_graph_attributes(span: Any, graph_nodes: list = None, graph_edges: list = None) -> None:
    if graph_nodes:
        span.set_attribute("langgraph.graph.nodes", json.dumps(graph_nodes))
        span.set_attribute("langgraph.graph.node_count", len(graph_nodes))

        for i, node in enumerate(graph_nodes):
            span.set_attribute(f"langgraph.node.{i}.name", node)
            span.set_attribute(f"langgraph.node.{i}.type", "unknown")

    if graph_edges:
        span.set_attribute("langgraph.graph.edges", json.dumps(graph_edges))
        span.set_attribute("langgraph.graph.edge_count", len(graph_edges))

        for i, edge in enumerate(graph_edges):
            parts = edge.split("->")
            if len(parts) == 2:
                span.set_attribute(f"langgraph.edge.{i}.source", parts[0])
                span.set_attribute(f"langgraph.edge.{i}.target", parts[1])


def extract_messages_from_input(input_data: Any) -> list:
    if isinstance(input_data, dict) and "messages" in input_data:
        return input_data["messages"]
    return []


def extract_messages_from_output(output_data: Any) -> list:
    if isinstance(output_data, dict) and "messages" in output_data:
        return output_data["messages"]
    return []


def get_message_content(message: Any) -> str:
    if hasattr(message, "content"):
        return str(message.content)
    return ""


def get_message_role(message: Any) -> str:
    if hasattr(message, "role"):
        return message.role
    elif hasattr(message, "type"):
        return message.type
    elif hasattr(message, "__class__"):
        return message.__class__.__name__.replace("Message", "").lower()
    return "unknown"

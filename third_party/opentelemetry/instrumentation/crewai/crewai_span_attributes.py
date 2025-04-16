"""OpenTelemetry instrumentation for CrewAI."""

import json
import logging
from typing import Any
from opentelemetry.trace import Span

from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.workflow import WorkflowAttributes

# Initialize logger for logging potential issues and operations
logger = logging.getLogger(__name__)

def _parse_tools(tools):
    """Parse tools into a JSON string with name and description."""
    result = []
    for tool in tools:
        res = {}
        if hasattr(tool, "name") and tool.name is not None:
            res["name"] = tool.name
        if hasattr(tool, "description") and tool.description is not None:
            res["description"] = tool.description
        if res:
            result.append(res)
    return json.dumps(result)

def set_span_attribute(span: Span, key: str, value: Any) -> None:
    """Set a single attribute on a span."""
    if value is not None and value != "":
        span.set_attribute(key, value)


class CrewAISpanAttributes:
    """Manages span attributes for CrewAI instrumentation."""

    def __init__(self, span: Span, instance) -> None:
        self.span = span
        self.instance = instance
        self.process_instance()

    def process_instance(self):
        """Process the instance based on its type."""
        instance_type = self.instance.__class__.__name__
        method_mapping = {
            "Crew": self._process_crew,
            "Agent": self._process_agent,
            "Task": self._process_task,
            "LLM": self._process_llm,
        }
        method = method_mapping.get(instance_type)
        if method:
            method()

    def _process_crew(self):
        """Process a Crew instance."""
        for key, value in self.instance.__dict__.items():
            if value is None:
                continue
            if key == "tasks":
                self._parse_tasks(value)
            elif key == "agents":
                self._parse_agents(value)
            elif key == "llms":
                self._parse_llms(value)
            else:
                self._set_attribute(f"crewai.crew.{key}", str(value))

    def _process_agent(self):
        """Process an Agent instance."""
        agent = {}
        for key, value in self.instance.__dict__.items():
            if key == "tools":
                value = _parse_tools(value)
            if value is None:
                continue
            agent[key] = str(value)

        # Set agent attributes using our semantic conventions
        self._set_attribute(AgentAttributes.AGENT_ID, agent.get('id', ''))
        self._set_attribute(AgentAttributes.AGENT_ROLE, agent.get('role', ''))
        self._set_attribute(AgentAttributes.AGENT_NAME, agent.get('name', ''))
        self._set_attribute(AgentAttributes.AGENT_TOOLS, agent.get('tools', ''))
        
        self._set_attribute("crewai.agent.goal", agent.get('goal', ''))
        self._set_attribute("crewai.agent.backstory", agent.get('backstory', ''))
        self._set_attribute("crewai.agent.cache", agent.get('cache', ''))
        self._set_attribute("crewai.agent.allow_delegation", agent.get('allow_delegation', ''))
        self._set_attribute("crewai.agent.allow_code_execution", agent.get('allow_code_execution', ''))
        self._set_attribute("crewai.agent.max_retry_limit", agent.get('max_retry_limit', ''))
        self._set_attribute("crewai.agent.tools_results", agent.get('tools_results', ''))

    def _process_task(self):
        """Process a Task instance."""
        task = {}
        for key, value in self.instance.__dict__.items():
            if value is None:
                continue
            if key == "tools":
                value = _parse_tools(value)
                task[key] = value
            elif key == "agent":
                task[key] = value.role if value else None
            else:
                task[key] = str(value)

        # Set task attributes using our semantic conventions
        self._set_attribute(WorkflowAttributes.WORKFLOW_STEP_NAME, task.get('description', ''))
        self._set_attribute(WorkflowAttributes.WORKFLOW_STEP_TYPE, "task")
        self._set_attribute(WorkflowAttributes.WORKFLOW_STEP_INPUT, task.get('context', ''))
        self._set_attribute(WorkflowAttributes.WORKFLOW_STEP_OUTPUT, task.get('expected_output', ''))
        
        self._set_attribute("crewai.task.id", task.get('id', ''))
        self._set_attribute("crewai.task.agent", task.get('agent', ''))
        self._set_attribute("crewai.task.human_input", task.get('human_input', ''))
        self._set_attribute("crewai.task.output", task.get('output', ''))
        self._set_attribute("crewai.task.processed_by_agents", str(task.get('processed_by_agents', '')))

    def _process_llm(self):
        """Process an LLM instance."""
        llm = {}
        for key, value in self.instance.__dict__.items():
            if value is None:
                continue
            llm[key] = str(value)

        # Set LLM attributes using our semantic conventions
        self._set_attribute(SpanAttributes.LLM_REQUEST_MODEL, llm.get('model_name', ''))
        self._set_attribute(SpanAttributes.LLM_REQUEST_TEMPERATURE, llm.get('temperature', ''))
        self._set_attribute(SpanAttributes.LLM_REQUEST_MAX_TOKENS, llm.get('max_tokens', ''))
        self._set_attribute(SpanAttributes.LLM_REQUEST_TOP_P, llm.get('top_p', ''))

    def _parse_agents(self, agents):
        """Parse agents into a list of dictionaries."""
        for agent in agents:
            if agent is not None:
                agent_data = self._extract_agent_data(agent)
                for key, value in agent_data.items():
                    self._set_attribute(f"crewai.agent.{key}", value)

    def _parse_tasks(self, tasks):
        """Parse tasks into a list of dictionaries."""
        for task in tasks:
            if task is not None:
                task_data = {
                    "agent": task.agent.role if task.agent else None,
                    "description": task.description,
                    "async_execution": task.async_execution,
                    "expected_output": task.expected_output,
                    "human_input": task.human_input,
                    "tools": task.tools,
                    "output_file": task.output_file,
                }
                for key, value in task_data.items():
                    if value is not None:
                        self._set_attribute(f"crewai.task.{key}", str(value))

    def _parse_llms(self, llms):
        """Parse LLMs into a list of dictionaries."""
        for llm in llms:
            if llm is not None:
                llm_data = {
                    "temperature": llm.temperature,
                    "max_tokens": llm.max_tokens,
                    "max_completion_tokens": llm.max_completion_tokens,
                    "top_p": llm.top_p,
                    "n": llm.n,
                    "seed": llm.seed,
                    "base_url": llm.base_url,
                    "api_version": llm.api_version,
                }
                for key, value in llm_data.items():
                    if value is not None:
                        self._set_attribute(f"crewai.llm.{key}", str(value))

    def _extract_agent_data(self, agent):
        """Extract data from an agent."""
        model = getattr(agent.llm, "model", None) or getattr(agent.llm, "model_name", None) or ""

        return {
            "id": str(agent.id),
            "role": agent.role,
            "goal": agent.goal,
            "backstory": agent.backstory,
            "cache": agent.cache,
            "config": agent.config,
            "verbose": agent.verbose,
            "allow_delegation": agent.allow_delegation,
            "tools": agent.tools,
            "max_iter": agent.max_iter,
            "llm": str(model),
        }

    def _set_attribute(self, key, value):
        """Set an attribute on the span."""
        if value is not None and value != "":
            set_span_attribute(self.span, key, value)

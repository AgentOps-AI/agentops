"""OpenTelemetry instrumentation for CrewAI."""

import json
import logging
from typing import Any
from opentelemetry.trace import Span

from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.message import MessageAttributes

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
    return result


def set_span_attribute(span: Span, key: str, value: Any) -> None:
    """Set a single attribute on a span."""
    if value is not None and value != "":
        if hasattr(value, "__str__"):
            value = str(value)
        span.set_attribute(key, value)


class CrewAISpanAttributes:
    """Manages span attributes for CrewAI instrumentation."""

    def __init__(self, span: Span, instance, skip_agent_processing=False) -> None:
        self.span = span
        self.instance = instance
        self.skip_agent_processing = skip_agent_processing
        self.process_instance()

    def process_instance(self):
        """Process the instance based on its type."""
        instance_type = self.instance.__class__.__name__
        self._set_attribute(SpanAttributes.LLM_SYSTEM, "crewai")
        self._set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, instance_type)

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
        crew_id = getattr(self.instance, "id", "")
        self._set_attribute("crewai.crew.id", str(crew_id))
        self._set_attribute("crewai.crew.type", "crewai.crew")
        self._set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, "workflow")

        logger.debug(f"CrewAI: Processing crew with id {crew_id}")

        for key, value in self.instance.__dict__.items():
            if value is None:
                continue

            if key == "tasks":
                if isinstance(value, list):
                    self._set_attribute("crewai.crew.max_turns", str(len(value)))
                    logger.debug(f"CrewAI: Found {len(value)} tasks")
            elif key == "agents":
                if isinstance(value, list):
                    logger.debug(f"CrewAI: Found {len(value)} agents in crew")

                if not self.skip_agent_processing:
                    self._parse_agents(value)
            elif key == "llms":
                self._parse_llms(value)
            elif key == "result":
                self._set_attribute("crewai.crew.final_output", str(value))
                self._set_attribute("crewai.crew.output", str(value))
                self._set_attribute(SpanAttributes.AGENTOPS_ENTITY_OUTPUT, str(value))
            else:
                self._set_attribute(f"crewai.crew.{key}", str(value))

    def _process_agent(self):
        """Process an Agent instance."""
        agent = {}
        self._set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, "agent")

        for key, value in self.instance.__dict__.items():
            if key == "tools":
                parsed_tools = _parse_tools(value)
                for i, tool in enumerate(parsed_tools):
                    tool_prefix = f"crewai.agent.tool.{i}."
                    for tool_key, tool_value in tool.items():
                        self._set_attribute(f"{tool_prefix}{tool_key}", str(tool_value))

                agent[key] = json.dumps(parsed_tools)

            if value is None:
                continue

            if key != "tools":
                agent[key] = str(value)

        self._set_attribute(AgentAttributes.AGENT_ID, agent.get("id", ""))
        self._set_attribute(AgentAttributes.AGENT_ROLE, agent.get("role", ""))
        self._set_attribute(AgentAttributes.AGENT_NAME, agent.get("name", ""))
        self._set_attribute(AgentAttributes.AGENT_TOOLS, agent.get("tools", ""))

        if "reasoning" in agent:
            self._set_attribute(AgentAttributes.AGENT_REASONING, agent.get("reasoning", ""))

        if "goal" in agent:
            self._set_attribute(SpanAttributes.AGENTOPS_ENTITY_INPUT, agent.get("goal", ""))

        self._set_attribute("crewai.agent.goal", agent.get("goal", ""))
        self._set_attribute("crewai.agent.backstory", agent.get("backstory", ""))
        self._set_attribute("crewai.agent.cache", agent.get("cache", ""))
        self._set_attribute("crewai.agent.allow_delegation", agent.get("allow_delegation", ""))
        self._set_attribute("crewai.agent.allow_code_execution", agent.get("allow_code_execution", ""))
        self._set_attribute("crewai.agent.max_retry_limit", agent.get("max_retry_limit", ""))

        if hasattr(self.instance, "llm") and self.instance.llm is not None:
            model_name = (
                getattr(self.instance.llm, "model", None) or getattr(self.instance.llm, "model_name", None) or ""
            )
            temp = getattr(self.instance.llm, "temperature", None)
            max_tokens = getattr(self.instance.llm, "max_tokens", None)
            top_p = getattr(self.instance.llm, "top_p", None)

            self._set_attribute(SpanAttributes.LLM_REQUEST_MODEL, model_name)
            if temp is not None:
                self._set_attribute(SpanAttributes.LLM_REQUEST_TEMPERATURE, str(temp))
            if max_tokens is not None:
                self._set_attribute(SpanAttributes.LLM_REQUEST_MAX_TOKENS, str(max_tokens))
            if top_p is not None:
                self._set_attribute(SpanAttributes.LLM_REQUEST_TOP_P, str(top_p))

            self._set_attribute("crewai.agent.llm", str(model_name))
            self._set_attribute(AgentAttributes.AGENT_MODELS, str(model_name))

    def _process_task(self):
        """Process a Task instance."""
        task = {}
        self._set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, "workflow.step")

        for key, value in self.instance.__dict__.items():
            if value is None:
                continue
            if key == "tools":
                parsed_tools = _parse_tools(value)
                for i, tool in enumerate(parsed_tools):
                    tool_prefix = f"crewai.task.tool.{i}."
                    for tool_key, tool_value in tool.items():
                        self._set_attribute(f"{tool_prefix}{tool_key}", str(tool_value))

                task[key] = json.dumps(parsed_tools)

            elif key == "agent":
                task[key] = value.role if value else None
                if value:
                    agent_id = getattr(value, "id", "")
                    self._set_attribute(AgentAttributes.FROM_AGENT, str(agent_id))
            else:
                task[key] = str(value)

        self._set_attribute("crewai.task.name", task.get("description", ""))
        self._set_attribute("crewai.task.type", "task")
        self._set_attribute("crewai.task.input", task.get("context", ""))
        self._set_attribute("crewai.task.expected_output", task.get("expected_output", ""))

        if "description" in task:
            self._set_attribute(SpanAttributes.AGENTOPS_ENTITY_INPUT, task.get("description", ""))
        if "output" in task:
            self._set_attribute(SpanAttributes.AGENTOPS_ENTITY_OUTPUT, task.get("output", ""))
            self._set_attribute("crewai.task.output", task.get("output", ""))

        if "id" in task:
            self._set_attribute("crewai.task.id", str(task.get("id", "")))

        if "status" in task:
            self._set_attribute("crewai.task.status", task.get("status", ""))

        self._set_attribute("crewai.task.agent", task.get("agent", ""))
        self._set_attribute("crewai.task.human_input", task.get("human_input", ""))
        self._set_attribute("crewai.task.processed_by_agents", str(task.get("processed_by_agents", "")))

        if "tools" in task and task["tools"]:
            try:
                tools = json.loads(task["tools"])
                for i, tool in enumerate(tools):
                    self._set_attribute(MessageAttributes.TOOL_CALL_NAME.format(i=i), tool.get("name", ""))
                    self._set_attribute(
                        MessageAttributes.TOOL_CALL_DESCRIPTION.format(i=i), tool.get("description", "")
                    )
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse tools for task: {task.get('id', 'unknown')}")

    def _process_llm(self):
        """Process an LLM instance."""
        llm = {}
        self._set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, "llm")

        for key, value in self.instance.__dict__.items():
            if value is None:
                continue
            llm[key] = str(value)

        model_name = llm.get("model_name", "") or llm.get("model", "")
        self._set_attribute(SpanAttributes.LLM_REQUEST_MODEL, model_name)
        self._set_attribute(SpanAttributes.LLM_REQUEST_TEMPERATURE, llm.get("temperature", ""))
        self._set_attribute(SpanAttributes.LLM_REQUEST_MAX_TOKENS, llm.get("max_tokens", ""))
        self._set_attribute(SpanAttributes.LLM_REQUEST_TOP_P, llm.get("top_p", ""))

        if "frequency_penalty" in llm:
            self._set_attribute(SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY, llm.get("frequency_penalty", ""))
        if "presence_penalty" in llm:
            self._set_attribute(SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY, llm.get("presence_penalty", ""))
        if "streaming" in llm:
            self._set_attribute(SpanAttributes.LLM_REQUEST_STREAMING, llm.get("streaming", ""))

        if "api_key" in llm:
            self._set_attribute("gen_ai.request.api_key_present", "true")

        if "base_url" in llm:
            self._set_attribute(SpanAttributes.LLM_OPENAI_API_BASE, llm.get("base_url", ""))

        if "api_version" in llm:
            self._set_attribute(SpanAttributes.LLM_OPENAI_API_VERSION, llm.get("api_version", ""))

    def _parse_agents(self, agents):
        """Parse agents into a list of dictionaries."""
        if not agents:
            logger.debug("CrewAI: No agents to parse")
            return

        agent_count = len(agents)
        logger.debug(f"CrewAI: Parsing {agent_count} agents")

        # Pre-process all agents to collect their data first
        agent_data_list = []

        for idx, agent in enumerate(agents):
            if agent is None:
                logger.debug(f"CrewAI: Agent at index {idx} is None, skipping")
                agent_data_list.append(None)
                continue

            logger.debug(f"CrewAI: Processing agent at index {idx}")
            try:
                agent_data = self._extract_agent_data(agent)
                agent_data_list.append(agent_data)
            except Exception as e:
                logger.error(f"CrewAI: Error extracting data for agent at index {idx}: {str(e)}")
                agent_data_list.append(None)

        # Now set all attributes at once for each agent
        for idx, agent_data in enumerate(agent_data_list):
            if agent_data is None:
                continue

            for key, value in agent_data.items():
                if key == "tools" and isinstance(value, list):
                    for tool_idx, tool in enumerate(value):
                        for tool_key, tool_value in tool.items():
                            self._set_attribute(f"crewai.agents.{idx}.tools.{tool_idx}.{tool_key}", str(tool_value))
                else:
                    self._set_attribute(f"crewai.agents.{idx}.{key}", value)

    def _parse_llms(self, llms):
        """Parse LLMs into a list of dictionaries."""
        for idx, llm in enumerate(llms):
            if llm is not None:
                model_name = getattr(llm, "model", None) or getattr(llm, "model_name", None) or ""
                llm_data = {
                    "model": model_name,
                    "temperature": llm.temperature,
                    "max_tokens": llm.max_tokens,
                    "max_completion_tokens": llm.max_completion_tokens,
                    "top_p": llm.top_p,
                    "n": llm.n,
                    "seed": llm.seed,
                    "base_url": llm.base_url,
                    "api_version": llm.api_version,
                }

                self._set_attribute(f"{SpanAttributes.LLM_REQUEST_MODEL}.{idx}", model_name)
                if hasattr(llm, "temperature"):
                    self._set_attribute(f"{SpanAttributes.LLM_REQUEST_TEMPERATURE}.{idx}", str(llm.temperature))
                if hasattr(llm, "max_tokens"):
                    self._set_attribute(f"{SpanAttributes.LLM_REQUEST_MAX_TOKENS}.{idx}", str(llm.max_tokens))
                if hasattr(llm, "top_p"):
                    self._set_attribute(f"{SpanAttributes.LLM_REQUEST_TOP_P}.{idx}", str(llm.top_p))

                for key, value in llm_data.items():
                    if value is not None:
                        self._set_attribute(f"crewai.llms.{idx}.{key}", str(value))

    def _extract_agent_data(self, agent):
        """Extract data from an agent."""
        model = getattr(agent.llm, "model", None) or getattr(agent.llm, "model_name", None) or ""

        tools_list = []
        if hasattr(agent, "tools") and agent.tools:
            tools_list = _parse_tools(agent.tools)

        return {
            "id": str(agent.id),
            "role": agent.role,
            "goal": agent.goal,
            "backstory": agent.backstory,
            "cache": agent.cache,
            "config": agent.config,
            "verbose": agent.verbose,
            "allow_delegation": agent.allow_delegation,
            "tools": tools_list,
            "max_iter": agent.max_iter,
            "llm": str(model),
        }

    def _set_attribute(self, key, value):
        """Set an attribute on the span."""
        if value is not None and value != "":
            set_span_attribute(self.span, key, value)

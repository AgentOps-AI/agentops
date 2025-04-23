"""OpenTelemetry instrumentation for CrewAI."""

import json
import logging
from typing import Any
from opentelemetry.trace import Span

from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.tool import ToolAttributes
from agentops.semconv.message import MessageAttributes
from agentops.instrumentation.common.attributes import AttributeMap

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

        self._set_attribute(AgentAttributes.AGENT_ID, agent.get('id', ''))
        self._set_attribute(AgentAttributes.AGENT_ROLE, agent.get('role', ''))
        self._set_attribute(AgentAttributes.AGENT_NAME, agent.get('name', ''))
        self._set_attribute(AgentAttributes.AGENT_TOOLS, agent.get('tools', ''))
        
        if 'reasoning' in agent:
            self._set_attribute(AgentAttributes.AGENT_REASONING, agent.get('reasoning', ''))
            
        if 'goal' in agent:
            self._set_attribute(SpanAttributes.AGENTOPS_ENTITY_INPUT, agent.get('goal', ''))
        
        self._set_attribute("crewai.agent.goal", agent.get('goal', ''))
        self._set_attribute("crewai.agent.backstory", agent.get('backstory', ''))
        self._set_attribute("crewai.agent.cache", agent.get('cache', ''))
        self._set_attribute("crewai.agent.allow_delegation", agent.get('allow_delegation', ''))
        self._set_attribute("crewai.agent.allow_code_execution", agent.get('allow_code_execution', ''))
        self._set_attribute("crewai.agent.max_retry_limit", agent.get('max_retry_limit', ''))
        
        if hasattr(self.instance, "llm") and self.instance.llm is not None:
            model_name = getattr(self.instance.llm, "model", None) or getattr(self.instance.llm, "model_name", None) or ""
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

        self._set_attribute("crewai.task.name", task.get('description', ''))
        self._set_attribute("crewai.task.type", "task")
        self._set_attribute("crewai.task.input", task.get('context', ''))
        self._set_attribute("crewai.task.expected_output", task.get('expected_output', ''))
        
        if 'description' in task:
            self._set_attribute(SpanAttributes.AGENTOPS_ENTITY_INPUT, task.get('description', ''))
        if 'output' in task:
            self._set_attribute(SpanAttributes.AGENTOPS_ENTITY_OUTPUT, task.get('output', ''))
            self._set_attribute("crewai.task.output", task.get('output', ''))
        
        if 'id' in task:
            self._set_attribute("crewai.task.id", str(task.get('id', '')))
        
        if 'status' in task:
            self._set_attribute("crewai.task.status", task.get('status', ''))
        
        self._set_attribute("crewai.task.agent", task.get('agent', ''))
        self._set_attribute("crewai.task.human_input", task.get('human_input', ''))
        self._set_attribute("crewai.task.processed_by_agents", str(task.get('processed_by_agents', '')))
        
        if 'tools' in task and task['tools']:
            try:
                tools = json.loads(task['tools'])
                for i, tool in enumerate(tools):
                    self._set_attribute(MessageAttributes.TOOL_CALL_NAME.format(i=i), tool.get("name", ""))
                    self._set_attribute(MessageAttributes.TOOL_CALL_DESCRIPTION.format(i=i), tool.get("description", ""))
            except:
                logger.warning(f"Failed to parse tools json: {task['tools']}")

    def _process_llm(self):
        """Process an LLM instance."""
        self._set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, "llm")
        
        # Parse model parameters
        model_name = getattr(self.instance, "model", None) or getattr(self.instance, "model_name", None) or ""
        temp = getattr(self.instance, "temperature", None)
        max_tokens = getattr(self.instance, "max_tokens", None)
        
        self._set_attribute(SpanAttributes.LLM_REQUEST_MODEL, model_name)
        if temp is not None:
            self._set_attribute(SpanAttributes.LLM_REQUEST_TEMPERATURE, str(temp))
        if max_tokens is not None:
            self._set_attribute(SpanAttributes.LLM_REQUEST_MAX_TOKENS, str(max_tokens))
        
        # Add provider info based on class attributes or parent class
        if hasattr(self.instance, 'provider'):
            provider = self.instance.provider
            self._set_attribute(SpanAttributes.LLM_PROVIDER, provider)
            
        # Set additional LLM attributes
        for key, value in self.instance.__dict__.items():
            if value is None:
                continue
            self._set_attribute(f"crewai.llm.{key}", str(value))

    def _parse_agents(self, agents):
        """Process a list of agents for a crew instance."""
        # Track agents in an array
        for i, agent in enumerate(agents):
            if not agent:
                continue
                
            agent_data = self._extract_agent_data(agent)
            
            # Set span attributes for each agent
            agent_prefix = f"crewai.crew.agent.{i}."
            for key, value in agent_data.items():
                self._set_attribute(f"{agent_prefix}{key}", value)
            
            # Process tools if available
            if hasattr(agent, "tools") and agent.tools:
                parsed_tools = _parse_tools(agent.tools)
                for j, tool in enumerate(parsed_tools):
                    tool_prefix = f"{agent_prefix}tool.{j}."
                    for tool_key, tool_value in tool.items():
                        self._set_attribute(f"{tool_prefix}{tool_key}", str(tool_value))
            
            # Process LLM if available
            if hasattr(agent, "llm") and agent.llm:
                llm = agent.llm
                if hasattr(llm, "model") and llm.model:
                    self._set_attribute(f"{agent_prefix}llm.model", str(llm.model))
                elif hasattr(llm, "model_name") and llm.model_name:
                    self._set_attribute(f"{agent_prefix}llm.model", str(llm.model_name))

    def _parse_llms(self, llms):
        """Process a dictionary of LLMs for a crew instance."""
        if not llms or not isinstance(llms, dict):
            return
        
        # Track LLMs in an array
        for i, (role, llm) in enumerate(llms.items()):
            if not llm:
                continue
            
            # Set basic LLM information
            llm_prefix = f"crewai.crew.llm.{i}."
            self._set_attribute(f"{llm_prefix}role", str(role))
            
            # Extract model information
            if hasattr(llm, "model") and llm.model:
                self._set_attribute(f"{llm_prefix}model", str(llm.model))
            elif hasattr(llm, "model_name") and llm.model_name:
                self._set_attribute(f"{llm_prefix}model", str(llm.model_name))
            
            # Extract other important LLM parameters
            for key in ["temperature", "max_tokens", "top_p"]:
                if hasattr(llm, key) and getattr(llm, key) is not None:
                    self._set_attribute(f"{llm_prefix}{key}", str(getattr(llm, key)))

    def _extract_agent_data(self, agent):
        """Extract relevant data from an agent instance."""
        agent_data = {}
        
        # Extract basic agent information
        for key in ["id", "role", "name", "goal", "backstory"]:
            if hasattr(agent, key) and getattr(agent, key):
                agent_data[key] = str(getattr(agent, key))
        
        # Extract configuration settings
        for key in ["allow_delegation", "allow_code_execution", "max_iter", "max_rpm", "verbose"]:
            if hasattr(agent, key) and getattr(agent, key) is not None:
                agent_data[key] = str(getattr(agent, key))
        
        return agent_data

    def _set_attribute(self, key, value):
        """Set an attribute on the span with validation."""
        set_span_attribute(self.span, key, value) 
"""
AgentOps has direct integration with CrewAi and needs to preserve all of these 
interfaces. We need to create tests for all of these cases as well. 

from typing import Optional

from crewai.utilities.events import (
    CrewKickoffCompletedEvent,
    ToolUsageErrorEvent,
    ToolUsageStartedEvent,
)
from crewai.utilities.events.base_event_listener import BaseEventListener
from crewai.utilities.events.crew_events import CrewKickoffStartedEvent
from crewai.utilities.events.task_events import TaskEvaluationEvent

try:
    import agentops

    AGENTOPS_INSTALLED = True
except ImportError:
    AGENTOPS_INSTALLED = False


class AgentOpsListener(BaseEventListener):
    tool_event: Optional["agentops.ToolEvent"] = None
    session: Optional["agentops.Session"] = None

    def __init__(self):
        super().__init__()

    def setup_listeners(self, crewai_event_bus):
        if not AGENTOPS_INSTALLED:
            return

        @crewai_event_bus.on(CrewKickoffStartedEvent)
        def on_crew_kickoff_started(source, event: CrewKickoffStartedEvent):
            self.session = agentops.init()
            for agent in source.agents:
                if self.session:
                    self.session.create_agent(
                        name=agent.role,
                        agent_id=str(agent.id),
                    )

        @crewai_event_bus.on(CrewKickoffCompletedEvent)
        def on_crew_kickoff_completed(source, event: CrewKickoffCompletedEvent):
            if self.session:
                self.session.end_session(
                    end_state="Success",
                    end_state_reason="Finished Execution",
                )

        @crewai_event_bus.on(ToolUsageStartedEvent)
        def on_tool_usage_started(source, event: ToolUsageStartedEvent):
            self.tool_event = agentops.ToolEvent(name=event.tool_name)
            if self.session:
                self.session.record(self.tool_event)

        @crewai_event_bus.on(ToolUsageErrorEvent)
        def on_tool_usage_error(source, event: ToolUsageErrorEvent):
            agentops.ErrorEvent(exception=event.error, trigger_event=self.tool_event)

        @crewai_event_bus.on(TaskEvaluationEvent)
        def on_task_evaluation(source, event: TaskEvaluationEvent):
            if self.session:
                self.session.create_agent(
                    name="Task Evaluator", agent_id=str(source.original_agent.id)
                )


agentops_listener = AgentOpsListener()
"""


import pytest
from .conftest import (
    get_api_requests, 
    get_otel_requests, 
    assert_otel_requests_are_unique, 
    assert_instrumentation_is_loaded, 
)

import agentops
from crewai import Agent, Task, Crew
from crewai.tools import tool

pytestmark = [pytest.mark.vcr]


@pytest.mark.asyncio
async def test_instrumentation_is_loaded():
    assert_instrumentation_is_loaded("crewai")


@pytest.mark.asyncio
async def test_crewai_agent_task_basic(vcr):
    """Test a single agent hello world example with CrewAI"""
    
    agentops.init()
    agent = Agent(
        role="Greeter",
        goal="Provide a friendly greeting message",
        backstory="You are a helpful assistant who specializes in creating warm, concise greetings."
    )
    task = Task(
        description="Generate a warm, friendly greeting that mentions the time of day.",
        agent=agent,
        expected_output="A brief, friendly greeting message."
    )
    crew = Crew(
        agents=[agent],
        tasks=[task]
    )
    
    result = crew.kickoff()
    agentops.end_session("Succeeded")
    
    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert_otel_requests_are_unique(vcr)


@pytest.mark.asyncio
async def test_crewai_agent_with_tool(vcr):
    """Test a CrewAI agent using a tool"""
    
    @tool("Get Weather")
    def get_weather(location: str) -> str:
        """Get the current weather for a location."""
        return f"The weather in {location} is sunny and 72 degrees Fahrenheit."
    
    agentops.init()
    travel_agent = Agent(
        role="Travel Advisor",
        goal="Provide weather-informed travel recommendations",
        backstory="You are a travel advisor who uses weather data to make recommendations.",
        tools=[get_weather]
    )
    travel_task = Task(
        description="Recommend whether someone should pack an umbrella for their trip to Seattle.",
        agent=travel_agent,
        expected_output="A recommendation based on Seattle's weather."
    )
    crew = Crew(
        agents=[travel_agent],
        tasks=[travel_task]
    )
    result = crew.kickoff()
    agentops.end_session("Succeeded")
    
    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert_otel_requests_are_unique(vcr)


@pytest.mark.asyncio
async def test_crewai_agent_with_tool_raises_exception(vcr):
    """Test a CrewAI agent using a tool"""
    
    @tool("Get Weather")
    def get_weather(location: str) -> str:
        """Get the current weather for a location."""
        raise Exception
    
    agentops.init()
    travel_agent = Agent(
        role="Travel Advisor",
        goal="Provide weather-informed travel recommendations",
        backstory="You are a travel advisor who uses weather data to make recommendations.",
        tools=[get_weather]
    )
    travel_task = Task(
        description="Recommend whether someone should pack an umbrella for their trip to Seattle.",
        agent=travel_agent,
        expected_output="A recommendation based on Seattle's weather."
    )
    crew = Crew(
        agents=[travel_agent],
        tasks=[travel_task]
    )
    result = crew.kickoff()
    agentops.end_session("Succeeded")
    
    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert_otel_requests_are_unique(vcr)


@pytest.mark.asyncio
async def test_crewai_multiple_agents(vcr):
    """Test multiple CrewAI agents working together without tools"""
    
    agentops.init()
    writer_agent = Agent(
        role="Content Writer",
        goal="Create engaging and informative content",
        backstory="You are a creative writer who specializes in clear and concise explanations."
    )
    researcher_agent = Agent(
        role="Research Specialist",
        goal="Gather and organize information on various topics",
        backstory="You are skilled at finding and summarizing key information."
    )
    editor_agent = Agent(
        role="Content Editor",
        goal="Review and improve content for clarity and accuracy",
        backstory="You have a keen eye for detail and can improve any text."
    )
    
    research_task = Task(
        description="Research the benefits of regular exercise.",
        agent=researcher_agent,
        expected_output="A summary of exercise benefits."
    )
    writing_task = Task(
        description="Write a short article about exercise benefits for beginners.",
        agent=writer_agent,
        expected_output="A short article about exercise."
    )
    editing_task = Task(
        description="Review and edit the exercise article for clarity.",
        agent=editor_agent,
        expected_output="An improved version of the exercise article."
    )
    
    crew = Crew(
        agents=[researcher_agent, writer_agent, editor_agent],
        tasks=[research_task, writing_task, editing_task]
    )
    result = crew.kickoff()
    agentops.end_session("Succeeded")
    
    req_api = get_api_requests(vcr)
    assert len(req_api) == 1, f"Expected 1 API request got {len(req_api)}"
    
    req_otel = get_otel_requests(vcr)
    assert_otel_requests_are_unique(vcr)


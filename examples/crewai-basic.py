from dotenv import load_dotenv
load_dotenv()

import agentops
from crewai import Agent, Crew, Task
from crewai.tools import tool

agentops.init()


@tool("Get Weather")
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"The weather in {location} is sunny and 72 degrees Fahrenheit."


travel_agent = Agent(
    role="Travel Advisor",
    goal="Provide weather-informed travel recommendations",
    backstory="You are a travel advisor who uses weather data to make recommendations.",
    tools=[get_weather],
)
travel_task = Task(
    description="Recommend whether someone should pack an umbrella for their trip to Seattle.",
    agent=travel_agent,
    expected_output="A recommendation based on Seattle's weather.",
)
crew = Crew(agents=[travel_agent], tasks=[travel_task])

result = crew.kickoff()
agentops.end_session("Succeeded")

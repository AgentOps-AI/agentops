import pytest
from crewai import Agent, Crew, Process, Task
from crewai.crew import CrewOutput, TaskOutput

import agentops


@pytest.mark.vcr
def test_basic_crewai(agentops_session):
    # Define your agents
    researcher = Agent(
        role="Researcher",
        goal="Conduct foundational research",
        backstory="An experienced researcher with a passion for uncovering insights",
    )
    writing_task = Task(description="Compose the report...", agent=researcher, expected_output="Final Report")

    # Form the crew with a sequential process
    report_crew = Crew(agents=[researcher], tasks=[writing_task], process=Process.sequential)

    # Execute the crew
    result = report_crew.kickoff()

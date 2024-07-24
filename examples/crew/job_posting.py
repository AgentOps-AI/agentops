# TO TEST: comment and uncomment agentops code


import os

os.environ["SERPER_API_KEY"] = "..."
os.environ["OPENAI_API_KEY"] = "..."

from crewai import Agent
from crewai_tools.tools import WebsiteSearchTool, SerperDevTool, FileReadTool

web_search_tool = WebsiteSearchTool()
serper_dev_tool = SerperDevTool()
file_read_tool = FileReadTool(
    file_path="job_description_example.md",
    description="A tool to read the job description example file.",
)


class Agents:
    def research_agent(self):
        return Agent(
            role="Research Analyst",
            goal="Analyze the company website and provided description to extract insights on culture, values, and specific needs.",
            tools=[web_search_tool, serper_dev_tool],
            backstory="Expert in analyzing company cultures and identifying key values and needs from various sources, including websites and brief descriptions.",
            verbose=True,
        )

    def writer_agent(self):
        return Agent(
            role="Job Description Writer",
            goal="Use insights from the Research Analyst to create a detailed, engaging, and enticing job posting.",
            tools=[web_search_tool, serper_dev_tool, file_read_tool],
            backstory="Skilled in crafting compelling job descriptions that resonate with the company's values and attract the right candidates.",
            verbose=True,
        )

    def review_agent(self):
        return Agent(
            role="Review and Editing Specialist",
            goal="Review the job posting for clarity, engagement, grammatical accuracy, and alignment with company values and refine it to ensure perfection.",
            tools=[web_search_tool, serper_dev_tool, file_read_tool],
            backstory="A meticulous editor with an eye for detail, ensuring every piece of content is clear, engaging, and grammatically perfect.",
            verbose=True,
        )


from textwrap import dedent
from crewai import Task


class Tasks:
    def research_company_culture_task(self, agent, company_description, company_domain):
        return Task(
            description=dedent(
                f"""\
								Analyze the provided company website and the hiring manager's company's domain {company_domain}, description: "{company_description}". Focus on understanding the company's culture, values, and mission. Identify unique selling points and specific projects or achievements highlighted on the site.
								Compile a report summarizing these insights, specifically how they can be leveraged in a job posting to attract the right candidates."""
            ),
            expected_output=dedent(
                """\
								A comprehensive report detailing the company's culture, values, and mission, along with specific selling points relevant to the job role. Suggestions on incorporating these insights into the job posting should be included."""
            ),
            agent=agent,
        )

    def research_role_requirements_task(self, agent, hiring_needs):
        return Task(
            description=dedent(
                f"""\
								Based on the hiring manager's needs: "{hiring_needs}", identify the key skills, experiences, and qualities the ideal candidate should possess for the role. Consider the company's current projects, its competitive landscape, and industry trends. Prepare a list of recommended job requirements and qualifications that align with the company's needs and values."""
            ),
            expected_output=dedent(
                """\
								A list of recommended skills, experiences, and qualities for the ideal candidate, aligned with the company's culture, ongoing projects, and the specific role's requirements."""
            ),
            agent=agent,
        )

    def draft_job_posting_task(
        self, agent, company_description, hiring_needs, specific_benefits
    ):
        return Task(
            description=dedent(
                f"""\
								Draft a job posting for the role described by the hiring manager: "{hiring_needs}". Use the insights on "{company_description}" to start with a compelling introduction, followed by a detailed role description, responsibilities, and required skills and qualifications. Ensure the tone aligns with the company's culture and incorporate any unique benefits or opportunities offered by the company.
								Specfic benefits: "{specific_benefits}"""
            ),
            expected_output=dedent(
                """\
								A detailed, engaging job posting that includes an introduction, role description, responsibilities, requirements, and unique company benefits. The tone should resonate with the company's culture and values, aimed at attracting the right candidates."""
            ),
            agent=agent,
        )

    def review_and_edit_job_posting_task(self, agent, hiring_needs):
        return Task(
            description=dedent(
                f"""\
								Review the draft job posting for the role: "{hiring_needs}". Check for clarity, engagement, grammatical accuracy, and alignment with the company's culture and values. Edit and refine the content, ensuring it speaks directly to the desired candidates and accurately reflects the role's unique benefits and opportunities. Provide feedback for any necessary revisions."""
            ),
            expected_output=dedent(
                """\
								A polished, error-free job posting that is clear, engaging, and perfectly aligned with the company's culture and values. Feedback on potential improvements and final approval for publishing. Formated in markdown."""
            ),
            agent=agent,
            output_file="job_posting.md",
        )

    def industry_analysis_task(self, agent, company_domain, company_description):
        return Task(
            description=dedent(
                f"""\
								Conduct an in-depth analysis of the industry related to the company's domain: "{company_domain}". Investigate current trends, challenges, and opportunities within the industry, utilizing market reports, recent developments, and expert opinions. Assess how these factors could impact the role being hired for and the overall attractiveness of the position to potential candidates.
								Consider how the company's position within this industry and its response to these trends could be leveraged to attract top talent. Include in your report how the role contributes to addressing industry challenges or seizing opportunities."""
            ),
            expected_output=dedent(
                """\
								A detailed analysis report that identifies major industry trends, challenges, and opportunities relevant to the company's domain and the specific job role. This report should provide strategic insights on positioning the job role and the company as an attractive choice for potential candidates."""
            ),
            agent=agent,
        )


from crewai import Crew
import agentops

agentops.init(tags=["crew-job-posting-example"])

tasks = Tasks()
agents = Agents()

company_description = input("What is the company description?\n")
company_domain = input("What is the company domain?\n")
hiring_needs = input("What are the hiring needs?\n")
specific_benefits = input("What are specific_benefits you offer?\n")

# Create Agents
researcher_agent = agents.research_agent()
writer_agent = agents.writer_agent()
review_agent = agents.review_agent()

# Define Tasks for each agent
research_company_culture_task = tasks.research_company_culture_task(
    researcher_agent, company_description, company_domain
)
industry_analysis_task = tasks.industry_analysis_task(
    researcher_agent, company_domain, company_description
)
research_role_requirements_task = tasks.research_role_requirements_task(
    researcher_agent, hiring_needs
)
draft_job_posting_task = tasks.draft_job_posting_task(
    writer_agent, company_description, hiring_needs, specific_benefits
)
review_and_edit_job_posting_task = tasks.review_and_edit_job_posting_task(
    review_agent, hiring_needs
)

# Instantiate the crew with a sequential process
crew = Crew(
    agents=[researcher_agent, writer_agent, review_agent],
    tasks=[
        research_company_culture_task,
        industry_analysis_task,
        research_role_requirements_task,
        draft_job_posting_task,
        review_and_edit_job_posting_task,
    ],
)

# Kick off the process
result = crew.kickoff()

print("Job Posting Creation Process Completed.")
print("Final Job Posting:")
print(result)

agentops.end_session("Success")

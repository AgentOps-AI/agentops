# Google ADK Example: Automated Approval Workflow with AgentOps
# This notebook demonstrates a complete automated approval workflow using the Google ADK (Agent Development Kit), integrated with AgentOps for observability.
#
# **Key Features:**
# - **Sequential Agent Processing:** The workflow uses multiple agents chained together to handle different stages of the approval process.
# - **External Tool Integration:** An agent interacts with an external tool that provides automated approval decisions based on amount and reason analysis.
# - **Session State Management:** Information is passed between agents and persisted using session state.
# - **AgentOps Observability:** All agent actions, tool calls, and LLM interactions are traced and can be viewed in your AgentOps dashboard.
# - **Automated Decision Making:** The approval system automatically approves or rejects requests based on configurable business rules.
# ## 1. Setup and Dependencies
# First, let's install the necessary libraries if they are not already present and import them.
# %pip install google-adk agentops python-dotenv nest_asyncio asyncio
import json
import os
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field
import nest_asyncio
import agentops
from dotenv import load_dotenv
import asyncio

# ## 2. Configuration and Initialization
# Load environment variables (especially `AGENTOPS_API_KEY` and your Google API key for Gemini) and initialize AgentOps.
# Load environment variables from .env file
load_dotenv()
nest_asyncio.apply()
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "your_agentops_api_key_here"

# Initialize AgentOps - Just 2 lines!
agentops.init(
    AGENTOPS_API_KEY,
    trace_name="adk-automated-approval-notebook",
    auto_start_session=False,
    tags=["google-adk", "automated-approval", "agentops-example"],
)

# Define some constants for our application.
APP_NAME = "automated_approval_app_notebook"
USER_ID = "test_user_notebook_123"
SESSION_ID = "automated_approval_session_notebook_456"
MODEL_NAME = "gemini-1.5-flash"
tracer = agentops.start_trace(trace_name=APP_NAME, tags=["google_adk", "notebook"])


# ## 3. Define Schemas
# Pydantic models are used to define the structure of data for approval requests and decisions. This helps with validation and clarity.
class ApprovalRequest(BaseModel):
    amount: float = Field(description="The amount requiring approval")
    reason: str = Field(description="The reason for the request")


class ApprovalDecision(BaseModel):
    decision: str = Field(description="The approval decision: 'approved' or 'rejected'")
    comments: str = Field(description="Additional comments from the approver")


# ## 4. External Approval Tool (Automated Decision Making)
# This tool automatically makes approval decisions based on configurable business rules. It analyzes the amount and reason to determine whether to approve or reject the request. In a real-world scenario, this could be integrated with more sophisticated rule engines or ML models for decision making.
async def external_approval_tool(amount: float, reason: str) -> str:
    """
    Automated approval system that returns approval decisions based on amount and reason analysis.
    """
    print("🤖 AUTOMATED APPROVAL SYSTEM:")
    print(f"   Amount: ${amount:,.2f}")
    print(f"   Reason: {reason}")

    # Automated decision logic
    decision = ""
    comments = ""

    reason_lower = reason.lower()
    high_priority_keywords = ["critical", "urgent", "emergency", "security", "compliance", "license"]
    business_keywords = ["conference", "training", "team", "software", "equipment", "travel"]

    # Check for high priority keywords first (overrides amount limits)
    if any(keyword in reason_lower for keyword in high_priority_keywords):
        decision = "approved"
        comments = "Auto-approved: High priority business need identified"

    # Auto-approve small amounts
    elif amount <= 1000:
        decision = "approved"
        comments = "Auto-approved: Amount under $1,000 threshold"

    # Auto-reject very large amounts without high priority justification
    elif amount > 10000:
        decision = "rejected"
        comments = "Auto-rejected: Amount exceeds $10,000 limit without high priority justification"

    # Medium amounts: analyze reason keywords
    else:
        if any(keyword in reason_lower for keyword in business_keywords):
            decision = "approved"
            comments = "Auto-approved: Standard business expense"
        else:
            # Default to approval for reasonable amounts with unclear reasons
            decision = "approved"
            comments = "Auto-approved: Amount within reasonable range"

    print(f"   Decision: {decision.upper()}")
    print(f"   Comments: {comments}")
    return json.dumps({"decision": decision, "comments": comments, "amount": amount, "reason": reason})


# Create the approval tool instance
approval_tool = FunctionTool(func=external_approval_tool)

# ## 5. Define Agents
# We define three agents for our workflow:
# 1.  **`PrepareApprovalAgent`**: Extracts details from the user's request.
# 2.  **`RequestHumanApprovalAgent`**: Uses the `external_approval_tool` to get a decision.
# 3.  **`ProcessDecisionAgent`**: Processes the decision and formulates a final response.
# Agent 1: Prepare the approval request
prepare_request = LlmAgent(
    model=MODEL_NAME,
    name="PrepareApprovalAgent",
    description="Extracts and prepares approval request details from user input",
    instruction="""You are an approval request preparation agent.
        Your task:
        1. Extract the amount and reason from the user's request
        2. Store these values in the session state with keys 'approval_amount' and 'approval_reason'
        3. Validate that both amount and reason are provided
        4. Respond with a summary of what will be submitted for approval
    If the user input is missing amount or reason, ask for clarification.
    """,
    output_key="request_prepared",
)

# Agent 2: Request automated approval using the tool
request_approval = LlmAgent(
    model=MODEL_NAME,
    name="RequestAutomatedApprovalAgent",
    description="Calls the external automated approval system with prepared request details",
    instruction="""You are an automated approval request agent.
        Your task:
        1. Get the 'approval_amount' and 'approval_reason' from the session state
        2. Use the external_approval_tool with these values
        3. Store the approval decision in session state with key 'automated_decision'
        4. Respond with the approval status
    Always use the exact values from the session state for the tool call.
    """,
    tools=[approval_tool],
    output_key="approval_requested",
)

# Agent 3: Process the approval decision
process_decision = LlmAgent(
    model=MODEL_NAME,
    name="ProcessDecisionAgent",
    description="Processes the automated approval decision and provides final response",
    instruction="""You are a decision processing agent.
        Your task:
        1. Check the 'automated_decision' from session state
        2. Parse the approval decision JSON
        3. If approved: congratulate and provide next steps
        4. If rejected: explain the rejection and suggest alternatives
        5. Provide a clear, helpful final response to the user

    Be professional and helpful in your response.
    """,
    output_key="final_decision",
)

# ## 6. Create Sequential Workflow
# Combine the agents into a sequential workflow. The `SequentialAgent` ensures that the sub-agents are executed in the specified order.
approval_workflow = SequentialAgent(
    name="AutomatedApprovalWorkflowNotebook",
    description="Complete workflow for processing approval requests with automated decision making",
    sub_agents=[prepare_request, request_approval, process_decision],
)

# ## 7. Session Management and Runner
# Set up an in-memory session service and the workflow runner.
session_service = InMemorySessionService()
# Create runner
workflow_runner = Runner(agent=approval_workflow, app_name=APP_NAME, session_service=session_service)


# ## 8. Helper Function to Run Workflow
# This function encapsulates the logic to run the workflow for a given user request and session ID.
async def run_approval_workflow_notebook(user_request: str, session_id: str):
    """Run the complete approval workflow with a user request in the notebook environment"""
    print(f"{'=' * 60}")
    print(f" Starting Approval Workflow for Session: {session_id}")
    print(f"{'=' * 60}")
    print(f"User Request: {user_request}")
    # Create user message
    user_content = types.Content(role="user", parts=[types.Part(text=user_request)])
    step_count = 0
    final_response = "No response received"
    # Run the workflow
    async for event in workflow_runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=user_content,
    ):
        if event.author and event.content:
            step_count += 1
            print(f"📋 Step {step_count} - {event.author}:")
            if event.content.parts:
                response_text = event.content.parts[0].text
                print(f"   {response_text}")
                if event.is_final_response():
                    final_response = response_text
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )
    print(f"{'=' * 60}")
    print(f"📊 Workflow Complete - Session State ({session_id}):")
    print(f"{'=' * 60}")
    for key, value in session.state.items():
        print(f"   {key}: {value}")
    print(f"🎯 Final Response: {final_response}")
    return final_response


# ## 9. Main Execution Logic
# This cell contains the main logic to run the workflow with a few test cases. Each test case will run in its own session.
async def main_notebook():
    test_requests = [
        "I need approval for $750 for team lunch and celebrations",  # Should auto-approve: under $1,000
        "Please approve $3,000 for a conference ticket and travel expenses",  # Should auto-approve: business keywords
        "I need $12,000 approved for critical software licenses renewal",  # Should auto-approve: high priority keywords despite high amount
        "Please approve $15,000 for office decoration and furniture",  # Should auto-reject: over $10,000 without high priority keywords
        "I need $5,000 for urgent security system upgrade",  # Should auto-approve: high priority keywords
    ]
    for i, request in enumerate(test_requests, 1):
        current_session_id = f"automated_approval_session_notebook_{456 + i - 1}"
        # Create the session before running the workflow
        await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=current_session_id)
        print(f"Created session: {current_session_id}")
        await run_approval_workflow_notebook(request, current_session_id)


try:
    asyncio.run(main_notebook())
    agentops.end_trace(end_state="Success")
except Exception as e:
    print(f"Error: {e}")
    agentops.end_trace(end_state="Error")

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=tracer)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise

"""
OpenAI Assistants API integration for AgentOps.

This module provides integration between OpenAI's Assistants API and AgentOps,
mapping Assistants to Agents, Threads to Sessions, and Runs to Events.
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from openai import OpenAI
from ..event import LLMEvent, ToolEvent, ActionEvent
from ..session import Session
from ..enums import EventType

class AssistantAgent:
    """Wrapper for OpenAI Assistant that maps to AgentOps Agent."""

    def __init__(self, assistant_id: str, session: Session):
        """
        Initialize AssistantAgent.

        Args:
            assistant_id: The OpenAI Assistant ID
            session: AgentOps Session for tracking events
        """
        self.assistant_id = assistant_id
        self.session = session
        self._client = OpenAI()

        # Fetch assistant details
        self._assistant = self._client.beta.assistants.retrieve(assistant_id)
        self.model = self._assistant.model
        self.name = self._assistant.name

    def create_thread(self) -> str:
        """Create new thread and return thread_id."""
        thread = self._client.beta.threads.create()
        self.session.thread_id = thread.id
        return thread.id

    def add_message(self, thread_id: str, content: str) -> str:
        """
        Add a message to the thread and return message_id.

        Args:
            thread_id: The thread to add the message to
            content: The message content
        """
        message = self._client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content
        )
        return message.id

    def run(self, thread_id: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the assistant on a thread and return the result.

        Args:
            thread_id: The thread to run the assistant on
            instructions: Optional override instructions
        """
        # Create run
        run = self._client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant_id,
            instructions=instructions
        )

        # Record initial run event
        self._record_run_event(run)

        # Poll for completion
        while run.status in ['queued', 'in_progress']:
            run = self._client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            self._record_run_event(run)

        # Get messages after completion
        messages = self._client.beta.threads.messages.list(
            thread_id=thread_id
        )

        return {
            'run': run,
            'messages': messages
        }

    def _record_run_event(self, run: Any) -> None:
        """Record run as LLMEvent and tool events if applicable."""
        # Record main LLM interaction
        event = LLMEvent(
            thread_id=UUID(run.thread_id),
            model=run.model,
            completion=str(run.status)
        )
        self.session.record(event)

        # Record tool usage if any
        if run.required_action and run.required_action.type == 'submit_tool_outputs':
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                tool_event = ToolEvent(
                    name=tool_call.function.name,
                    logs={'arguments': tool_call.function.arguments}
                )
                self.session.record(tool_event)

from taskweaver.module.event_emitter import (
    SessionEventHandlerBase,
    SessionEventType,
    RoundEventType,
    PostEventType,
)
import agentops
from agentops.event import ActionEvent, ErrorEvent, ToolEvent
from datetime import datetime, timezone
from typing import Dict, Any
from agentops.log_config import logger

ATTACHMENT_TOOLS = [
    "thought",
    "reply_type",
    "reply_content",
    "verification",
    "code_error",
    "execution_status",
    "execution_result",
    "artifact_paths",
    "revise_message",
    "function",
    "web_exploring_plan",
    "web_exploring_screenshot",
    "web_exploring_link",
]


class TaskWeaverEventHandler(SessionEventHandlerBase):
    def __init__(self):
        super().__init__()
        self._message_buffer: Dict[str, Dict[str, Any]] = {}
        self._attachment_buffer: Dict[str, Dict[str, Any]] = {}
        self._active_agents: Dict[str, str] = {}

    def _get_or_create_agent(self, role: str):
        """Get existing agent ID or create new agent for role+round combination"""
        if role not in self._active_agents:
            agent_id = agentops.create_agent(name=role)
            if agent_id:
                self._active_agents[role] = agent_id
        return self._active_agents.get(role)

    def handle_session(self, type: SessionEventType, msg: str, extra: Any, **kwargs: Any):
        agentops.record(ActionEvent(action_type=type.value, params={"extra": extra, "message": msg}))

    def handle_round(self, type: RoundEventType, msg: str, extra: Any, round_id: str, **kwargs: Any):
        if type == RoundEventType.round_error:
            agentops.record(
                ErrorEvent(error_type=type.value, details={"round_id": round_id, "message": msg, "extra": extra})
            )
            logger.error(f"Could not record the Round event: {msg}")
            self.cleanup_round()
        else:
            agentops.record(
                ActionEvent(
                    action_type=type.value,
                    params={"round_id": round_id, "extra": extra},
                    returns=msg,
                )
            )
            if type == RoundEventType.round_end:
                self.cleanup_round()

    def handle_post(self, type: PostEventType, msg: str, extra: Any, post_id: str, round_id: str, **kwargs: Any):
        role = extra.get("role", "Planner")
        agent_id = self._get_or_create_agent(role=role)

        if type == PostEventType.post_error:
            agentops.record(
                ErrorEvent(
                    error_type=type.value,
                    details={"post_id": post_id, "round_id": round_id, "message": msg, "extra": extra},
                )
            )
            logger.error(f"Could not record the Post event: {msg}")

        elif type == PostEventType.post_start or type == PostEventType.post_end:
            agentops.record(
                ActionEvent(
                    action_type=type.value,
                    params={"post_id": post_id, "round_id": round_id, "extra": extra},
                    returns=msg,
                    agent_id=agent_id,
                )
            )

        elif type == PostEventType.post_status_update:
            agentops.record(
                ActionEvent(
                    action_type=type.value,
                    params={"post_id": post_id, "round_id": round_id, "extra": extra},
                    returns=msg,
                    agent_id=agent_id,
                )
            )

        elif type == PostEventType.post_attachment_update:
            attachment_id = extra["id"]
            attachment_type = extra["type"].value
            is_end = extra["is_end"]

            if attachment_id not in self._attachment_buffer:
                self._attachment_buffer[attachment_id] = {
                    "role": attachment_type,
                    "content": [],
                    "init_timestamp": datetime.now(timezone.utc).isoformat(),
                    "end_timestamp": None,
                }

            self._attachment_buffer[attachment_id]["content"].append(str(msg))

            if is_end:
                self._attachment_buffer[attachment_id]["end_timestamp"] = datetime.now(timezone.utc).isoformat()
                complete_message = "".join(self._attachment_buffer[attachment_id]["content"])

                if attachment_type in ATTACHMENT_TOOLS:
                    agentops.record(
                        ToolEvent(
                            name=type.value,
                            init_timestamp=self._attachment_buffer[attachment_id]["init_timestamp"],
                            end_timestamp=self._attachment_buffer[attachment_id]["end_timestamp"],
                            params={
                                "post_id": post_id,
                                "round_id": round_id,
                                "attachment_id": attachment_id,
                                "attachment_type": self._attachment_buffer[attachment_id]["role"],
                                "extra": extra,
                            },
                            returns=complete_message,
                            agent_id=agent_id,
                        )
                    )
                else:
                    agentops.record(
                        ActionEvent(
                            action_type=type.value,
                            init_timestamp=self._attachment_buffer[attachment_id]["init_timestamp"],
                            end_timestamp=self._attachment_buffer[attachment_id]["end_timestamp"],
                            params={
                                "post_id": post_id,
                                "round_id": round_id,
                                "attachment_id": attachment_id,
                                "attachment_type": self._attachment_buffer[attachment_id]["role"],
                                "extra": extra,
                            },
                            returns=complete_message,
                            agent_id=agent_id,
                        )
                    )

                self._attachment_buffer.pop(attachment_id, None)

        elif type == PostEventType.post_message_update:
            is_end = extra["is_end"]

            if post_id not in self._message_buffer:
                self._message_buffer[post_id] = {
                    "content": [],
                    "init_timestamp": datetime.now(timezone.utc).isoformat(),
                    "end_timestamp": None,
                }

            self._message_buffer[post_id]["content"].append(str(msg))

            if is_end:
                self._message_buffer[post_id]["end_timestamp"] = datetime.now(timezone.utc).isoformat()
                complete_message = "".join(self._message_buffer[post_id]["content"])
                agentops.record(
                    ActionEvent(
                        action_type=type.value,
                        init_timestamp=self._message_buffer[post_id]["init_timestamp"],
                        end_timestamp=self._message_buffer[post_id]["end_timestamp"],
                        params={
                            "post_id": post_id,
                            "round_id": round_id,
                            "extra": extra,
                        },
                        returns=complete_message,
                        agent_id=agent_id,
                    )
                )

                self._message_buffer.pop(post_id, None)

    def cleanup_round(self):
        """Cleanup agents and buffers for a completed round"""
        self._active_agents.clear()
        self._message_buffer.clear()
        self._attachment_buffer.clear()

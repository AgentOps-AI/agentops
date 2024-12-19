from taskweaver.module.event_emitter import (
    SessionEventHandlerBase,
    TaskWeaverEvent,
    EventScope,
    SessionEventType,
    RoundEventType,
    PostEventType,
)
import agentops
from typing import Dict, Optional, Any
from uuid import UUID


class TaskWeaverEventHandler(SessionEventHandlerBase):
    def __init__(self):
        super().__init__()
        self.current_round_id: Optional[str] = None
        self.agent_sessions: Dict[str, Any] = {}
        self._message_buffer: Dict[str, str] = {}
        self._attachment_buffer: Dict[str, Dict[str, Any]] = {}
        self._active_agents: Dict[str, str] = {}  # Maps role_round_id to agent_id

    def _get_or_create_agent(self, role: str) -> str:
        """Get existing agent ID or create new agent for role+round combination"""
        agent_key = f"{role}"
        if agent_key not in self._active_agents:
            agent_id = agentops.create_agent(name=role)
            if agent_id:  # Only store if agent creation was successful
                self._active_agents[agent_key] = agent_id
        return self._active_agents.get(agent_key)

    def handle_session(self, type: SessionEventType, msg: str, extra: Any, **kwargs: Any):
        agentops.record(
            agentops.ActionEvent(action_type=type.value, params={"message": msg}, returns=str(extra) if extra else None)
        )

    def handle_round(self, type: RoundEventType, msg: str, extra: Any, round_id: str, **kwargs: Any):
        if type == RoundEventType.round_start:
            self.current_round_id = round_id
            agentops.record(agentops.ActionEvent(action_type="round_start", params={"round_id": round_id}, returns=msg))

        elif type == RoundEventType.round_error:
            agentops.record(
                agentops.ErrorEvent(error_type="round_error", details={"message": msg, "round_id": round_id})
            )

        elif type == RoundEventType.round_end:
            agentops.record(agentops.ActionEvent(action_type="round_end", params={"round_id": round_id}, returns=msg))
            self.current_round_id = None

    def handle_post(self, type: PostEventType, msg: str, extra: Any, post_id: str, round_id: str, **kwargs: Any):
        role = extra.get("role", "Planner")
        agent_id = self._get_or_create_agent(role=role)

        if type == PostEventType.post_start:
            agentops.record(
                agentops.ActionEvent(
                    action_type="post_start",
                    params={
                        "post_id": post_id,
                        "round_id": round_id,
                        "agent_id": agent_id,
                    },
                    returns=msg,
                )
            )

        elif type == PostEventType.post_message_update:
            is_end = extra.get("is_end", False)
            if not is_end:
                self._message_buffer[post_id] = self._message_buffer.get(post_id, "") + msg
            else:
                agentops.record(
                    agentops.ActionEvent(
                        action_type="post_message_update",
                        params={
                            "post_id": post_id,
                            "round_id": round_id,
                            "agent_id": agent_id,
                            "is_end": is_end,
                            "model": extra.get("model", None),
                        },
                        returns=self._message_buffer.get(post_id, ""),
                    )
                )

            if is_end:
                self._message_buffer.pop(post_id, None)

        elif type == PostEventType.post_attachment_update:
            attachment_id = extra.get("id", "")
            attachment_type = extra.get("type", "")
            is_end = extra.get("is_end", False)

            if attachment_id not in self._attachment_buffer:
                self._attachment_buffer[attachment_id] = {
                    "type": attachment_type,
                    "content": "",
                    "post_id": post_id,
                    "round_id": round_id,
                    "agent_id": agent_id,
                }

                agentops.record(
                    agentops.ActionEvent(
                        action_type="attachment_stream_start",
                        params={
                            "attachment_id": attachment_id,
                            "attachment_type": str(attachment_type),
                            "post_id": post_id,
                            "round_id": round_id,
                            "agent_id": agent_id,
                        },
                    )
                )

            self._attachment_buffer[attachment_id]["content"] += msg

            if is_end:
                buffer = self._attachment_buffer[attachment_id]
                agentops.record(
                    agentops.ToolEvent(
                        name=str(buffer["type"]),
                        params={
                            "post_id": buffer["post_id"],
                            "round_id": buffer["round_id"],
                            "attachment_id": attachment_id,
                        },
                        returns=buffer["content"],
                        agent_id=buffer["agent_id"],
                    )
                )
                self._attachment_buffer.pop(attachment_id)

        elif type == PostEventType.post_error:
            agentops.record(
                agentops.ErrorEvent(
                    error_type="post_error",
                    details={"message": msg, "post_id": post_id, "round_id": round_id},
                )
            )

        elif type == PostEventType.post_end:
            agentops.record(
                agentops.ActionEvent(
                    action_type="post_end",
                    params={"post_id": post_id, "round_id": round_id, "agent_id": agent_id},
                    returns=msg,
                )
            )

    def cleanup_round(self, round_id: str):
        """Cleanup agents and buffers for a completed round"""
        self._active_agents = {k: v for k, v in self._active_agents.items() if not k.endswith(round_id)}
        self._message_buffer.clear()
        self._attachment_buffer.clear()

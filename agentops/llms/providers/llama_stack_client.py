import inspect
import pprint
from typing import Any, AsyncGenerator, Dict, Optional, List, Union
import logging

from agentops.event import LLMEvent, ErrorEvent, ToolEvent
from agentops.session import Session
from agentops.log_config import logger
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from agentops.llms.providers.base import BaseProvider


class LlamaStackClientProvider(BaseProvider):
    original_complete = None
    original_create_turn = None

    def __init__(self, client):
        super().__init__(client)
        self._provider_name = "LlamaStack"

    def handle_response(
        self, response, kwargs, init_timestamp, session: Optional[Session] = None, metadata: Optional[Dict] = {}
    ) -> dict:
        """Handle responses for LlamaStack"""

        try:
            stack = []
            accum_delta = None
            accum_tool_delta = None
            # tool_event = None
            # llm_event = None

            def handle_stream_chunk(chunk: dict):
                nonlocal stack

                # NOTE: prompt/completion usage not returned in response when streaming

                try:
                    nonlocal accum_delta

                    if chunk.event.event_type == "start":
                        llm_event = LLMEvent(init_timestamp=get_ISO_time(), params=kwargs)
                        stack.append({"event_type": "start", "event": llm_event})
                        accum_delta = chunk.event.delta
                    elif chunk.event.event_type == "progress":
                        accum_delta += chunk.event.delta
                    elif chunk.event.event_type == "complete":
                        if (
                            stack[-1]["event_type"] == "start"
                        ):  # check if the last event in the stack is a step start event
                            llm_event = stack.pop().get("event")
                            llm_event.prompt = [
                                {"content": message.content, "role": message.role} for message in kwargs["messages"]
                            ]
                            llm_event.agent_id = check_call_stack_for_agent_id()
                            llm_event.model = kwargs["model_id"]
                            llm_event.prompt_tokens = None
                            llm_event.completion = accum_delta or kwargs["completion"]
                            llm_event.completion_tokens = None
                            llm_event.end_timestamp = get_ISO_time()
                            self._safe_record(session, llm_event)

                except Exception as e:
                    llm_event = LLMEvent(init_timestamp=init_timestamp, end_timestamp=get_ISO_time(), params=kwargs)
                    self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))

                    kwargs_str = pprint.pformat(kwargs)
                    chunk = pprint.pformat(chunk)
                    logger.warning(
                        f"Unable to parse a chunk for LLM call. Skipping upload to AgentOps\n"
                        f"chunk:\n {chunk}\n"
                        f"kwargs:\n {kwargs_str}\n"
                    )

            def handle_stream_agent(chunk: dict):
                # NOTE: prompt/completion usage not returned in response when streaming

                # nonlocal llm_event
                nonlocal stack

                if session is not None:
                    llm_event.session_id = session.session_id

                try:
                    if chunk.event.payload.event_type == "turn_start":
                        logger.debug("turn_start")
                        stack.append({"event_type": chunk.event.payload.event_type, "event": None})
                    elif chunk.event.payload.event_type == "step_start":
                        logger.debug("step_start")
                        llm_event = LLMEvent(init_timestamp=get_ISO_time(), params=kwargs)
                        stack.append({"event_type": chunk.event.payload.event_type, "event": llm_event})
                    elif chunk.event.payload.event_type == "step_progress":
                        if (
                            chunk.event.payload.step_type == "inference"
                            and chunk.event.payload.text_delta_model_response
                        ):
                            nonlocal accum_delta
                            delta = chunk.event.payload.text_delta_model_response

                            if accum_delta:
                                accum_delta += delta
                            else:
                                accum_delta = delta
                        elif chunk.event.payload.step_type == "inference" and chunk.event.payload.tool_call_delta:
                            if chunk.event.payload.tool_call_delta.parse_status == "started":
                                logger.debug("tool_started")
                                tool_event = ToolEvent(init_timestamp=get_ISO_time(), params=kwargs)
                                tool_event.name = "tool_started"

                                stack.append({"event_type": "tool_started", "event": tool_event})

                            elif chunk.event.payload.tool_call_delta.parse_status == "in_progress":
                                nonlocal accum_tool_delta
                                delta = chunk.event.payload.tool_call_delta.content
                                if accum_tool_delta:
                                    accum_tool_delta += delta
                                else:
                                    accum_tool_delta = delta
                            elif chunk.event.payload.tool_call_delta.parse_status == "success":
                                logger.debug("ToolExecution - success")
                                if (
                                    stack[-1]["event_type"] == "tool_started"
                                ):  # check if the last event in the stack is a tool execution event
                                    tool_event = stack.pop().get("event")
                                    tool_event.end_timestamp = get_ISO_time()
                                    tool_event.params["completion"] = accum_tool_delta
                                    self._safe_record(session, tool_event)
                            elif chunk.event.payload.tool_call_delta.parse_status == "failure":
                                logger.warning("ToolExecution - failure")
                                if stack[-1]["event_type"] == "ToolExecution - started":
                                    tool_event = stack.pop().get("event")
                                    tool_event.end_timestamp = get_ISO_time()
                                    tool_event.params["completion"] = accum_tool_delta
                                    self._safe_record(
                                        session,
                                        ErrorEvent(
                                            trigger_event=tool_event, exception=Exception("ToolExecution - failure")
                                        ),
                                    )

                    elif chunk.event.payload.event_type == "step_complete":
                        logger.debug("Step complete event received")

                        if chunk.event.payload.step_type == "inference":
                            logger.debug("Step complete inference")

                            if stack[-1]["event_type"] == "step_start":
                                llm_event = stack.pop().get("event")
                                llm_event.prompt = [
                                    {"content": message["content"], "role": message["role"]}
                                    for message in kwargs["messages"]
                                ]
                                llm_event.agent_id = check_call_stack_for_agent_id()
                                llm_event.model = metadata.get("model_id", "Unable to identify model")
                                llm_event.prompt_tokens = None
                                llm_event.completion = accum_delta or kwargs["completion"]
                                llm_event.completion_tokens = None
                                llm_event.end_timestamp = get_ISO_time()
                                self._safe_record(session, llm_event)
                            else:
                                logger.warning("Unexpected event stack state for inference step complete")
                        elif chunk.event.payload.step_type == "tool_execution":
                            if stack[-1]["event_type"] == "tool_started":
                                logger.debug("tool_complete")
                                tool_event = stack.pop().get("event")
                                tool_event.name = "tool_complete"
                                tool_event.params["completion"] = accum_tool_delta
                                self._safe_record(session, tool_event)
                    elif chunk.event.payload.event_type == "turn_complete":
                        if stack[-1]["event_type"] == "turn_start":
                            logger.debug("turn_start")
                        pass

                except Exception as e:
                    llm_event = LLMEvent(init_timestamp=init_timestamp, end_timestamp=get_ISO_time(), params=kwargs)

                    self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))

                    kwargs_str = pprint.pformat(kwargs)
                    chunk = pprint.pformat(chunk)
                    logger.warning(
                        f"Unable to parse a chunk for LLM call. Skipping upload to AgentOps\n"
                        f"chunk:\n {chunk}\n"
                        f"kwargs:\n {kwargs_str}\n"
                    )

            if kwargs.get("stream", False):

                def generator():
                    for chunk in response:
                        handle_stream_chunk(chunk)
                        yield chunk

                return generator()
            elif inspect.isasyncgen(response):

                async def agent_generator():
                    async for chunk in response:
                        handle_stream_agent(chunk)
                        yield chunk

                return agent_generator()
            elif inspect.isgenerator(response):

                def agent_generator():
                    for chunk in response:
                        handle_stream_agent(chunk)
                        yield chunk

                return agent_generator()
            else:
                llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
                if session is not None:
                    llm_event.session_id = session.session_id

                llm_event.returns = response
                llm_event.agent_id = check_call_stack_for_agent_id()
                llm_event.model = kwargs["model_id"]
                llm_event.prompt = [
                    {"content": message.content, "role": message.role} for message in kwargs["messages"]
                ]
                llm_event.prompt_tokens = None
                llm_event.completion = response.completion_message.content
                llm_event.completion_tokens = None
                llm_event.end_timestamp = get_ISO_time()

                self._safe_record(session, llm_event)
        except Exception as e:
            self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
            kwargs_str = pprint.pformat(kwargs)
            response = pprint.pformat(response)
            logger.warning(
                f"Unable to parse response for LLM call. Skipping upload to AgentOps\n"
                f"response:\n {response}\n"
                f"kwargs:\n {kwargs_str}\n"
            )

        return response

    def _override_complete(self):
        from llama_stack_client.resources import InferenceResource

        global original_complete
        original_complete = InferenceResource.chat_completion

        def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = original_complete(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        # Override the original method with the patched one
        InferenceResource.chat_completion = patched_function

    def _override_create_turn(self):
        from llama_stack_client.lib.agents.agent import Agent

        self.original_create_turn = Agent.create_turn

        def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]

            result = self.original_create_turn(*args, **kwargs)
            return self.handle_response(
                result,
                kwargs,
                init_timestamp,
                session=session,
                metadata={"model_id": args[0].agent_config.get("model")},
            )

        # Override the original method with the patched one
        Agent.create_turn = patched_function

    def override(self):
        self._override_complete()
        self._override_create_turn()

    def undo_override(self):
        if self.original_complete is not None:
            from llama_stack_client.resources import InferenceResource

            InferenceResource.chat_completion = self.original_complete

        if self.original_create_turn is not None:
            from llama_stack_client.lib.agents.agent import Agent

            Agent.create_turn = self.original_create_turn

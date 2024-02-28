from . import Event
from .http import HttpClient
from .helpers import safe_serialize, get_ISO_time
from openai.resources.chat.completions import Completions
from openai import Stream, AsyncStream
from openai.types.chat import ChatCompletionChunk
from openai.resources import AsyncCompletions


class Agent:
    def __init__(self, config, client, name: str, session_id: str):
        self.config = config
        self.name = name
        self._session_id = session_id
        self.client = client
        self.event_stream = None

        payload = {
            "name": name,
            "session_id": session_id
        }

        serialized_payload = \
            safe_serialize(payload).encode("utf-8")
        res = HttpClient.post(f'{self.config.endpoint}/agents',
                              serialized_payload,
                              self.config.api_key)

        # TODO: when we have internal logs, track any non-200 response here
        self.id = res.body.get('id')

    def chat_completion(self, *args, **kwargs):
        init_timestamp = get_ISO_time()

        """Handle responses for OpenAI versions >v1.0.0"""

        response = Completions.create(*args, **kwargs)
        event_stream = None

        def handle_stream_chunk(chunk: ChatCompletionChunk):
            try:
                model = chunk.model
                choices = chunk.choices
                token = choices[0].delta.content
                finish_reason = choices[0].finish_reason
                function_call = choices[0].delta.function_call
                tool_calls = choices[0].delta.tool_calls
                role = choices[0].delta.role

                if self.event_stream == None:
                    self.event_stream = Event(
                        event_type='openai chat completion stream',
                        params=kwargs,
                        result='Success',
                        returns={"finish_reason": None,
                                 "content": token},
                        action_type='llm',
                        model=model,
                        prompt=kwargs["messages"],
                        init_timestamp=init_timestamp
                    )
                else:
                    if token == None:
                        token = ''
                    self.event_stream.returns['content'] += token

                if finish_reason:
                    if not self.event_stream.returns:
                        self.event_stream.returns = {}
                    self.event_stream.returns['finish_reason'] = finish_reason
                    self.event_stream.returns['function_call'] = function_call
                    self.event_stream.returns['tool_calls'] = tool_calls
                    self.event_stream.returns['role'] = role
                    # Update end_timestamp
                    self.event_stream.end_timestamp = get_ISO_time()
                    self.client.record(self.event_stream)
                    self.event_stream = None
            except Exception as e:
                print(
                    f"Unable to parse a chunk for LLM call {kwargs} - skipping upload to AgentOps")

        # if the response is a generator, decorate the generator
        if isinstance(response, Stream):
            def generator():
                for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return generator()

        # For asynchronous AsyncStream
        elif isinstance(response, AsyncStream):
            async def async_generator():
                async for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return async_generator()

        # For async AsyncCompletion
        elif isinstance(response, AsyncCompletions):
            async def async_generator():
                async for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return async_generator()

        # v1.0.0+ responses are objects
        try:
            self.client.record(Event(
                event_type=response.object,
                params=kwargs,
                result='Success',
                returns={
                    # TODO: Will need to make the completion the key for content, splat out the model dump
                    "content": response.choices[0].message.model_dump()},
                action_type='llm',
                agent_id=self.id,
                model=response.model,
                prompt=kwargs['messages'],
                init_timestamp=init_timestamp,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens
            ))
            # Standard response
        except Exception as e:
            print(
                f"Unable to parse a chunk for LLM call {kwargs} - skipping upload to AgentOps")

        return response

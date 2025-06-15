"""Streaming wrapper for Google Generative AI responses.

This module provides specialized streaming wrappers for Google Generative AI's streaming API,
building on the common streaming infrastructure.
"""


from agentops.semconv import SpanAttributes, MessageAttributes
from agentops.instrumentation.common.streaming import StreamingResponseWrapper, create_streaming_wrapper
from agentops.instrumentation.providers.google_genai.attributes.model import get_generate_content_attributes


class GoogleGenAIStreamingWrapper(StreamingResponseWrapper):
    """Streaming wrapper specific to Google Generative AI responses."""

    def __init__(self, span, response, tracer):
        super().__init__(span, response, tracer)
        self._candidates = []
        self._current_candidate_index = 0

    def extract_chunk_content(self, chunk):
        """Extract content from a Google GenAI streaming chunk."""
        if hasattr(chunk, "text"):
            return chunk.text
        elif hasattr(chunk, "candidates") and chunk.candidates:
            # Extract text from the first candidate
            for candidate in chunk.candidates:
                if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                    for part in candidate.content.parts:
                        if hasattr(part, "text"):
                            return part.text
        return None

    def extract_finish_reason(self, chunk):
        """Extract finish reason from a Google GenAI streaming chunk."""
        if hasattr(chunk, "candidates") and chunk.candidates:
            for candidate in chunk.candidates:
                if hasattr(candidate, "finish_reason") and candidate.finish_reason:
                    return str(candidate.finish_reason)
        return None

    def update_span_attributes(self, chunk):
        """Update span attributes based on Google GenAI chunk data."""
        # Handle model information
        if hasattr(chunk, "model"):
            self.span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, chunk.model)

        # Handle usage metadata
        if hasattr(chunk, "usage_metadata"):
            metadata = chunk.usage_metadata
            if hasattr(metadata, "prompt_token_count"):
                self.span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, metadata.prompt_token_count)
            if hasattr(metadata, "candidates_token_count"):
                self.span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, metadata.candidates_token_count)
            if hasattr(metadata, "total_token_count"):
                self.span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, metadata.total_token_count)

        # Handle safety ratings
        if hasattr(chunk, "prompt_feedback") and hasattr(chunk.prompt_feedback, "block_reason"):
            self.span.set_attribute("gen_ai.response.prompt_blocked", True)
            self.span.set_attribute("gen_ai.response.prompt_block_reason", str(chunk.prompt_feedback.block_reason))

        # Handle candidates
        if hasattr(chunk, "candidates") and chunk.candidates:
            for i, candidate in enumerate(chunk.candidates):
                # Update candidate index tracking
                self._current_candidate_index = max(self._current_candidate_index, i)

                # Safety ratings for candidate
                if hasattr(candidate, "safety_ratings"):
                    for rating in candidate.safety_ratings:
                        if hasattr(rating, "category") and hasattr(rating, "probability"):
                            attr_name = f"gen_ai.response.candidates.{i}.safety.{str(rating.category).lower()}"
                            self.span.set_attribute(attr_name, str(rating.probability))

                # Citation metadata
                if hasattr(candidate, "citation_metadata") and candidate.citation_metadata:
                    if hasattr(candidate.citation_metadata, "citations"):
                        self.span.set_attribute(
                            f"gen_ai.response.candidates.{i}.citation_count", len(candidate.citation_metadata.citations)
                        )

    def on_stream_complete(self):
        """Called when streaming is complete."""
        super().on_stream_complete()

        # Set completion metadata
        if self._chunks_received > 0:
            self.span.set_attribute("gen_ai.response.candidate_count", self._current_candidate_index + 1)

        # Set message attributes
        if self._accumulated_content:
            self.span.set_attribute(MessageAttributes.COMPLETION_TYPE.format(i=0), "text")
            self.span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")


def generate_content_stream_wrapper(tracer):
    """Create a wrapper for Google GenAI generate_content_stream."""
    return create_streaming_wrapper(
        GoogleGenAIStreamingWrapper,
        "gemini.generate_content_stream",
        lambda args, kwargs: get_generate_content_attributes(args=args, kwargs=kwargs),
    )


def generate_content_stream_async_wrapper(tracer):
    """Create a wrapper for Google GenAI async generate_content_stream."""
    return create_streaming_wrapper(
        GoogleGenAIStreamingWrapper,
        "gemini.generate_content_stream",
        lambda args, kwargs: get_generate_content_attributes(args=args, kwargs=kwargs),
    )

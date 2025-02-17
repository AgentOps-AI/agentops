from typing import Callable, Collection, Optional

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from typing_extensions import Coroutine

from agentops.instrumentation.context import get_current_session
from agentops.instrumentation.openai.shared.config import Config
from agentops.instrumentation.openai.utils import is_openai_v1

_instruments = ("openai >= 0.27.0",)


class OpenAIInstrumentor(BaseInstrumentor):
    """An instrumentor for OpenAI's client library."""

    def __init__(
        self,
        enrich_assistant: bool = False,
        enrich_token_usage: bool = False,
        exception_logger=None,
        get_common_metrics_attributes: Callable[[], dict] = lambda: {},
        upload_base64_image: Optional[
            Callable[[str, str, str, str], Coroutine[None, None, str]]
        ] = lambda *args: "",
        enable_trace_context_propagation: bool = True,
    ):
        super().__init__()
        Config.enrich_assistant = enrich_assistant
        Config.enrich_token_usage = enrich_token_usage
        Config.exception_logger = exception_logger
        Config.get_common_metrics_attributes = self._wrap_metrics_attributes(get_common_metrics_attributes)
        Config.upload_base64_image = upload_base64_image
        Config.enable_trace_context_propagation = enable_trace_context_propagation

    def _wrap_metrics_attributes(self, original_func: Callable[[], dict]) -> Callable[[], dict]:
        def wrapped_attributes() -> dict:
            attributes = original_func()
            session = get_current_session()
            if session:
                attributes.update({
                    "session.id": str(session.session_id),
                    "session.state": str(session.state),
                })
            return attributes
        return wrapped_attributes

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs):
        if is_openai_v1():
            from agentops.instrumentation.openai.v1 import \
                OpenAIV1Instrumentor

            OpenAIV1Instrumentor().instrument(**kwargs)
        else:
            from agentops.instrumentation.openai.v0 import \
                OpenAIV0Instrumentor

            OpenAIV0Instrumentor().instrument(**kwargs)

    def _uninstrument(self, **kwargs):
        if is_openai_v1():
            from agentops.instrumentation.openai.v1 import \
                OpenAIV1Instrumentor

            OpenAIV1Instrumentor().uninstrument(**kwargs)
        else:
            from agentops.instrumentation.openai.v0 import \
                OpenAIV0Instrumentor

            OpenAIV0Instrumentor().uninstrument(**kwargs)


from typing import Collection
import logging

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer

from opentelemetry.metrics import get_meter

from wrapt import wrap_function_wrapper

from opentelemetry.instrumentation.openai.shared.chat_wrappers import (
    chat_wrapper,
    achat_wrapper,
)
from opentelemetry.instrumentation.openai.shared.completion_wrappers import (
    completion_wrapper,
    acompletion_wrapper,
)
from opentelemetry.instrumentation.openai.shared.embeddings_wrappers import (
    embeddings_wrapper,
    aembeddings_wrapper,
)
from opentelemetry.instrumentation.openai.shared.image_gen_wrappers import (
    image_gen_metrics_wrapper,
)
# Import the wrapper factory functions
from opentelemetry.instrumentation.openai.shared.responses_wrappers import (
    responses_wrapper,
    aresponses_wrapper,
)
from opentelemetry.instrumentation.openai.v1.assistant_wrappers import (
    assistants_create_wrapper,
    runs_create_wrapper,
    runs_retrieve_wrapper,
    runs_create_and_stream_wrapper,
    messages_list_wrapper,
)

from opentelemetry.instrumentation.openai.utils import is_metrics_enabled
from opentelemetry.instrumentation.openai.version import __version__

from agentops.semconv import Meters

_instruments = ("openai >= 1.0.0",)
logger = logging.getLogger(__name__)

class OpenAIV1Instrumentor(BaseInstrumentor):
    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs):
        logger.debug("Starting OpenAI V1 instrumentation setup...")
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, __version__, tracer_provider)

        # meter and counters are inited here
        meter_provider = kwargs.get("meter_provider")
        meter = get_meter(__name__, __version__, meter_provider)

        # Use placeholders for metrics if not enabled, to avoid errors in wrapper calls
        tokens_histogram = None
        chat_choice_counter = None
        duration_histogram = None
        chat_exception_counter = None
        streaming_time_to_first_token = None
        streaming_time_to_generate = None
        embeddings_exception_counter = None
        image_gen_exception_counter = None
        embeddings_vector_size_counter = None

        if is_metrics_enabled():
            logger.debug("Metrics are enabled.")
            tokens_histogram = meter.create_histogram(
                name=Meters.LLM_TOKEN_USAGE,
                unit="token",
                description="Measures number of input and output tokens used",
            )

            chat_choice_counter = meter.create_counter(
                name=Meters.LLM_GENERATION_CHOICES,
                unit="choice",
                description="Number of choices returned by chat completions call",
            )

            duration_histogram = meter.create_histogram(
                name=Meters.LLM_OPERATION_DURATION,
                unit="s",
                description="GenAI operation duration",
            )

            chat_exception_counter = meter.create_counter(
                name=Meters.LLM_COMPLETIONS_EXCEPTIONS,
                unit="time",
                description="Number of exceptions occurred during chat completions",
            )

            streaming_time_to_first_token = meter.create_histogram(
                name=Meters.LLM_STREAMING_TIME_TO_FIRST_TOKEN,
                unit="s",
                description="Time to first token in streaming chat completions",
            )
            streaming_time_to_generate = meter.create_histogram(
                name=Meters.LLM_STREAMING_TIME_TO_GENERATE,
                unit="s",
                description="Time between first token and completion in streaming chat completions",
            )
            embeddings_exception_counter = meter.create_counter(
                name=Meters.LLM_EMBEDDINGS_EXCEPTIONS,
                unit="time",
                description="Number of exceptions occurred during embeddings operation",
            )
            image_gen_exception_counter = meter.create_counter(
                name=Meters.LLM_IMAGE_GENERATIONS_EXCEPTIONS,
                unit="time",
                description="Number of exceptions occurred during image generations operation",
            )
            embeddings_vector_size_counter = meter.create_counter(
                name=Meters.LLM_EMBEDDINGS_VECTOR_SIZE,
                unit="element",
                description="he size of returned vector",
            )

        else:
            logger.debug("Metrics are disabled. Metrics objects will be None.")

        # Existing wrappers
        logger.debug("Wrapping chat completions...")
        wrap_function_wrapper(
            "openai.resources.chat.completions",
            "Completions.create",
            chat_wrapper(
                tracer,
                tokens_histogram,
                chat_choice_counter,
                duration_histogram,
                chat_exception_counter,
                streaming_time_to_first_token,
                streaming_time_to_generate,
            ),
        )
        logger.debug("Wrapped chat completions.")

        logger.debug("Wrapping legacy completions...")
        wrap_function_wrapper(
            "openai.resources.completions",
            "Completions.create",
            completion_wrapper(tracer),
        )
        logger.debug("Wrapped legacy completions.")


        logger.debug("Wrapping embeddings...")
        wrap_function_wrapper(
            "openai.resources.embeddings",
            "Embeddings.create",
            embeddings_wrapper(
                tracer,
                tokens_histogram,
                embeddings_vector_size_counter,
                duration_histogram,
                embeddings_exception_counter,
            ),
        )
        logger.debug("Wrapped embeddings.")

        logger.debug("Wrapping async chat completions...")
        wrap_function_wrapper(
            "openai.resources.chat.completions",
            "AsyncCompletions.create",
            achat_wrapper(
                tracer,
                tokens_histogram,
                chat_choice_counter,
                duration_histogram,
                chat_exception_counter,
                streaming_time_to_first_token,
                streaming_time_to_generate,
            ),
        )
        logger.debug("Wrapped async chat completions.")

        logger.debug("Wrapping async legacy completions...")
        wrap_function_wrapper(
            "openai.resources.completions",
            "AsyncCompletions.create",
            acompletion_wrapper(tracer),
        )
        logger.debug("Wrapped async legacy completions.")

        logger.debug("Wrapping async embeddings...")
        wrap_function_wrapper(
            "openai.resources.embeddings",
            "AsyncEmbeddings.create",
            aembeddings_wrapper(
                tracer,
                tokens_histogram,
                embeddings_vector_size_counter,
                duration_histogram,
                embeddings_exception_counter,
            ),
        )
        logger.debug("Wrapped async embeddings.")

        logger.debug("Wrapping image generation...")
        wrap_function_wrapper(
            "openai.resources.images",
            "Images.generate",
            image_gen_metrics_wrapper(duration_histogram, image_gen_exception_counter),
        )
        logger.debug("Wrapped image generation.")


        # ++ Uncommenting the 'responses' wrapping ++
        logger.debug("Attempting to wrap openai.resources.responses...")
        try:
           logger.debug("Creating sync response hook...")
           # Get the wrapper function by calling the factory
           sync_response_hook = responses_wrapper(
               tracer=tracer,
               duration_histogram=duration_histogram,
               exception_counter=chat_exception_counter, # Use chat_exception_counter or define a specific one
           )
           logger.debug("Attempting to wrap openai.resources.responses.Responses.create...")
           wrap_function_wrapper(
               "openai.resources.responses",
               "Responses.create",
               sync_response_hook, # Pass the inner wrapper function returned by the factory
           )
           logger.debug("Successfully wrapped openai.resources.responses.Responses.create.")

           logger.debug("Creating async response hook...")
           # Get the async wrapper function by calling the factory
           async_response_hook = aresponses_wrapper(
               tracer=tracer,
               duration_histogram=duration_histogram,
               exception_counter=chat_exception_counter, # Use chat_exception_counter or define a specific one
           )
           logger.debug("Attempting to wrap openai.resources.responses.AsyncResponses.create...")
           wrap_function_wrapper(
               "openai.resources.responses",
               "AsyncResponses.create",
               async_response_hook, # Pass the inner async wrapper function returned by the factory
           )
           logger.debug("Successfully wrapped openai.resources.responses.AsyncResponses.create.")
        except (ModuleNotFoundError, AttributeError) as e:
           # This is the expected path if the API doesn't exist in the installed openai package
           logger.warning(f"Skipping instrumentation of openai.resources.responses: {e}")
        except Exception as e:
            # Catch any other unexpected errors during the wrapping process
            logger.error(f"Unexpected error during instrumentation of openai.resources.responses: {e}", exc_info=True)


        # Beta APIs
        try:
            logger.debug("Attempting to wrap beta APIs...")
            wrap_function_wrapper(
                "openai.resources.beta.assistants",
                "Assistants.create",
                assistants_create_wrapper(tracer),
            )
            wrap_function_wrapper(
                "openai.resources.beta.chat.completions",
                "Completions.parse",
                chat_wrapper(
                    tracer,
                    tokens_histogram,
                    chat_choice_counter,
                    duration_histogram,
                    chat_exception_counter,
                    streaming_time_to_first_token,
                    streaming_time_to_generate,
                ),
            )
            wrap_function_wrapper(
                "openai.resources.beta.chat.completions",
                "AsyncCompletions.parse",
                achat_wrapper(
                    tracer,
                    tokens_histogram,
                    chat_choice_counter,
                    duration_histogram,
                    chat_exception_counter,
                    streaming_time_to_first_token,
                    streaming_time_to_generate,
                ),
            )
            wrap_function_wrapper(
                "openai.resources.beta.threads.runs",
                "Runs.create",
                runs_create_wrapper(tracer),
            )
            wrap_function_wrapper(
                "openai.resources.beta.threads.runs",
                "Runs.retrieve",
                runs_retrieve_wrapper(tracer),
            )
            wrap_function_wrapper(
                "openai.resources.beta.threads.runs",
                "Runs.create_and_stream",
                runs_create_and_stream_wrapper(tracer),
            )
            wrap_function_wrapper(
                "openai.resources.beta.threads.messages",
                "Messages.list",
                messages_list_wrapper(tracer),
            )
            logger.debug("Wrapped beta APIs.")
        except (AttributeError, ModuleNotFoundError):
            logger.warning("Skipping instrumentation of some beta APIs (module/attribute not found).")
        except Exception as e:
             logger.error(f"Unexpected error during instrumentation of beta APIs: {e}", exc_info=True)

        logger.debug("OpenAI V1 instrumentation setup complete.")

    def _uninstrument(self, **kwargs):
        logger.debug("Attempting to uninstrument OpenAI V1...")
        # Add actual uninstrumentation logic here if needed using _unwrap(module, name)
        logger.debug("OpenAI V1 uninstrumentation finished (placeholder).")

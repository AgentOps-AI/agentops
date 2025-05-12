import openai
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def test_openai():
    import agentops

    agentops.init(exporter=InMemorySpanExporter())
    agentops.start_session()

    openai.chat.completions.create(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Write a one-line joke"}]
    )


if __name__ == "__main__":
    test_openai()

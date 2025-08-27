import os

import agentops
from haystack.components.generators.chat import AzureOpenAIChatGenerator


def main():
    agentops.init(os.getenv("AGENTOPS_API_KEY"))

    if not os.getenv("AZURE_OPENAI_API_KEY") or not os.getenv("AZURE_OPENAI_ENDPOINT"):
        print("Skipping Azure example: missing AZURE_OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT (CI-safe skip)")
        return

    tracer = agentops.start_trace(
        trace_name="Haystack Azure Chat Example",
        tags=["haystack", "azure", "chat", "agentops-example"],
    )

    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    generator = AzureOpenAIChatGenerator(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=api_version,
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=deployment,
    )

    messages = [{"role": "user", "content": "In one sentence, what is AgentOps?"}]
    result = generator.run(messages=messages)
    replies = result.get("replies") or []
    print("Haystack Azure reply:", replies[0] if replies else "<no reply>")

    print("\n" + "=" * 50)
    print("Now let's verify that our LLM calls were tracked properly...")
    try:
        validation_result = agentops.validate_trace_spans(trace_context=tracer)
        agentops.print_validation_summary(validation_result)
    except agentops.ValidationError as e:
        print(f"\n❌ Error validating spans: {e}")
        raise

    agentops.end_trace(tracer, end_state="Success")


if __name__ == "__main__":
    main()

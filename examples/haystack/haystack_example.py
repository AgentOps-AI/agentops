import os

import agentops
from haystack.components.generators.openai import OpenAIGenerator


def main():
    agentops.init(os.getenv("AGENTOPS_API_KEY"))

    if not os.getenv("OPENAI_API_KEY"):
        print("Skipping OpenAI example: missing OPENAI_API_KEY")
        return

    tracer = agentops.start_trace(
        trace_name="Haystack OpenAI Example",
        tags=["haystack", "openai", "agentops-example"],
    )

    prompt = "In one sentence, what is AgentOps?"
    generator = OpenAIGenerator(model="gpt-4o-mini")
    result = generator.run(prompt=prompt)
    replies = result.get("replies") or []
    print("Haystack reply:", replies[0] if replies else "<no reply>")

    print("\n" + "=" * 50)
    print("Now let's verify that our LLM calls were tracked properly with AgentOps...")
    try:
        validation_result = agentops.validate_trace_spans(trace_context=tracer)
        agentops.print_validation_summary(validation_result)
    except agentops.ValidationError as e:
        print(f"\n❌ Error validating spans: {e}")
        raise

    agentops.end_trace(tracer, end_state="Success")


if __name__ == "__main__":
    main()

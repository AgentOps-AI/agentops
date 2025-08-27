import os

import agentops
from haystack.components.generators.openai import OpenAIGenerator


def main():
    agentops.init(os.getenv("AGENTOPS_API_KEY"))

    prompt = "In one sentence, what is AgentOps?"
    generator = OpenAIGenerator(model="gpt-4o-mini")
    result = generator.run(prompt=prompt)
    replies = result.get("replies") or []
    print("Haystack reply:", replies[0] if replies else "<no reply>")

    agentops.end_session("Success")


if __name__ == "__main__":
    main()

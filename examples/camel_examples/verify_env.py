import os


def verify_environment():
    openai_key = os.getenv("OPENAI_API_KEY")
    agentops_key = os.getenv("AGENTOPS_API_KEY")

    print("Environment Check:")
    print(
        f"OpenAI API Key: {'Set' if openai_key else 'Not Set'}"
        f"{f' (starts with: {openai_key[:10]}...)' if openai_key else ''}"
    )
    print(
        f"AgentOps API Key: {'Set' if agentops_key else 'Not Set'}"
        f"{f' (value: {agentops_key})' if agentops_key else ''}"
    )


if __name__ == "__main__":
    verify_environment()

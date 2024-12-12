import os

def verify_environment():
    openai_key = os.getenv('OPENAI_API_KEY')
    agentops_key = os.getenv('AGENTOPS_API_KEY')
    
    print('Environment Check:')
    print(f'OpenAI API Key: {"Set" if openai_key else "Not Set"} (starts with: {openai_key[:10]}...)')
    print(f'AgentOps API Key: {"Set" if agentops_key else "Not Set"} (value: {agentops_key})')

if __name__ == '__main__':
    verify_environment()

import os

from agentops.client.api import ApiClient

api = ApiClient(endpoint="https://api.agentops.ai")

api.v3.fetch_auth_token(os.environ["AGENTOPS_API_KEY"])

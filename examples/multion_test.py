import multion
from multion.client import MultiOn
from multion.core.request_options import RequestOptions
import os

multion = MultiOn(
    api_key=os.environ.get("MULTION_API_KEY"),
    agentops_api_key=os.environ.get("AGENTOPS_API_KEY"),
)
cmd = "what three things do i get with agentops"
request_options = RequestOptions(
    timeout_in_seconds=60, max_retries=4, additional_headers={"test": "ing"}
)
browse_response = multion.browse(
    cmd="what three things do i get with agentops",
    url="https://www.agentops.ai/",
    max_steps=4,
    include_screenshot=True,
    request_options=request_options,
)

print(browse_response.message)

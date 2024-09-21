### Purpose
# test an edge case where a request is retried after the jwt has expired
import time
from datetime import datetime

### SETUP
# Run the API server locally
# In utils.py -> generate_jwt -> set the jwt expiration to 0.001
# Run this script

### Plan
# The first request should succeed and return a JWT
# We'll manually add a failed request to the DLQ with the expired JWT
# When reattempting, the http_client should identify the expired jwt and reauthorize it before sending again

import agentops
from agentops import ActionEvent
from agentops.helpers import safe_serialize, get_ISO_time
from agentops.http_client import dead_letter_queue, HttpClient

api_key = "492f0ee6-0b7d-40a6-af86-22d89c7c5eea"
agentops.init(
    endpoint="http://localhost:8000",
    api_key=api_key,
    auto_start_session=False,
    default_tags=["dead-letter-queue-test"],
)

# create session
session = agentops.start_session()

# add failed request to DLQ
event = ActionEvent()
event.end_timestamp = get_ISO_time()

failed_request = {
    "url": "http://localhost:8000/v2/create_events",
    "payload": {"events": [event.__dict__]},
    "api_key": str(api_key),
    "parent_key": None,
    "jwt": session.jwt,
    "error_type": "Timeout",
}
# failed_request = safe_serialize(failed_request).encode("utf-8")

dead_letter_queue.add(failed_request)
assert len(dead_letter_queue.get_all()) == 1

# wait for the JWT to expire
time.sleep(3)

# retry
HttpClient()._retry_dlq_requests()
session.end_session(end_state="Success")

# check if the failed request is still in the DLQ
assert dead_letter_queue.get_all() == []

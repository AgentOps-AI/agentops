# API server test
This is a manual test with two files. It checks to make sure that the SDK works in an API environment.

## Running
1. `python server.py`
2. In different terminal, `python client.py`

## Validate
Check in your AgentOps Dashboard that two sessions are created with the `api-server-test` tag.

Each session should have one `LLMEvent` and one `ActionEvent`.

Both sessions should have an end state of `Success`
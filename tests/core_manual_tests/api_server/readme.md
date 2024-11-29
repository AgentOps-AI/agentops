# API server test
This is a manual test with two files. It checks to make sure that the SDK works in an API environment.

## Running the FastAPI Server
You can run FastAPI with:
1. `uvicorn main:app --reload`
2. To test, run `curl http://localhost:8000/completion` in a different terminal.

## Validate
Check in your AgentOps Dashboard 

1. two sessions are created with the `api-server-test` tag.
2. Each session should have one `LLMEvent` and one `ActionEvent`.
3. Both sessions should have an end state of `Success`
4. Neither session should have multiple agents
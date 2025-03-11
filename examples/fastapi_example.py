import asyncio
from fastapi import FastAPI, Depends, Request
from opentelemetry import trace

from agentops.sdk.decorators import session, agent, tool
from agentops.sdk.spans.utils import get_root_span

app = FastAPI()

# Utility function to get session info
def get_session_info():
    session_span = get_root_span()
    if session_span:
        return {
            "name": session_span.name,
            "id": session_span.span_id,
            "state": session_span.state,
            "tags": session_span._tags
        }
    return {"error": "No active session found"}

class RequestProcessor:
    @session(name="api_request", tags=["api", "fastapi"])
    def __init__(self, request_id: str):
        self.request_id = request_id
        # Session span is available as self._session_span
        self._session_span.set_attribute("request.id", request_id)
    
    @agent(name="request_handler", agent_type="api")
    async def process(self):
        # Access session directly
        print(f"Processing request {self.request_id} in session {self._session_span.name}")
        
        # Simulate some processing
        result = await self.fetch_data()
        return {
            "request_id": self.request_id,
            "result": result,
            "session_info": get_session_info()
        }
    
    @tool(name="data_fetcher", tool_type="database")
    async def fetch_data(self):
        # Simulate async database operation
        await asyncio.sleep(0.5)
        
        # Get session info from utility function
        session_info = get_session_info()
        print(f"Fetching data in session: {session_info.get('name')}")
        
        return {"data": "Sample data", "processed_in": session_info}

@app.get("/process/{request_id}")
async def process_request(request_id: str):
    processor = RequestProcessor(request_id)
    return await processor.process()

# For testing without running the server
async def test_request():
    processor = RequestProcessor("test-123")
    return await processor.process()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
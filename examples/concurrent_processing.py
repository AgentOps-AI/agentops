import asyncio
import uuid
from opentelemetry import trace, context
from opentelemetry.context import attach, detach

from agentops.sdk.decorators import session, agent, tool
from agentops.sdk.spans.utils import get_root_span

async def process_item(item, session_id):
    """Process a single item in a concurrent environment."""
    print(f"Processing item {item} for session {session_id}")
    
    # Get the session span
    session_span = get_root_span()
    if session_span:
        print(f"Found session: {session_span.name} (ID: {session_span.span_id})")
        
        # Add an event to the session span
        session_span.add_event(f"Processing item {item}")
    else:
        print(f"No session found for item {item}")
    
    # Simulate processing time
    await asyncio.sleep(0.5)
    return f"Processed {item}"

@session(name="batch_processor", tags=["batch", "async"])
class BatchProcessor:
    def __init__(self, items):
        self.items = items
        self.session_id = str(uuid.uuid4())
        self._session_span.set_attribute("batch.size", len(items))
        self._session_span.set_attribute("batch.id", self.session_id)
    
    @agent(name="batch_agent", agent_type="processor")
    async def process_all(self):
        print(f"Starting batch processing of {len(self.items)} items")
        
        # Process items concurrently
        tasks = []
        for item in self.items:
            # Create a task for each item
            task = asyncio.create_task(self.process_item(item))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        print(f"Batch processing completed")
        return results
    
    @tool(name="item_processor", tool_type="processor")
    async def process_item(self, item):
        # In a real application, you might need to explicitly pass the context
        # to ensure the correct session span is available in the task
        return await process_item(item, self.session_id)

async def main():
    # Create a batch of items to process
    items = [f"item-{i}" for i in range(5)]
    
    # Create and use the batch processor
    processor = BatchProcessor(items)
    results = await processor.process_all()
    
    print("Results:", results)

if __name__ == "__main__":
    asyncio.run(main()) 
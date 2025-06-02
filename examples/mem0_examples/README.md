# Comprehensive Mem0 Example with AgentOps Instrumentation

This example demonstrates all four mem0 memory classes with full AgentOps instrumentation:

##  Memory Classes Covered

1. **Memory** (Sync Local Memory) - Direct memory operations using local vector stores
2. **AsyncMemory** (Async Local Memory) - Asynchronous memory operations with local storage
3. **MemoryClient** (Sync Cloud Client) - Synchronous operations using mem0's cloud service
4. **AsyncMemoryClient** (Async Cloud Client) - Asynchronous operations with mem0 cloud

##  Features Demonstrated

### All Classes Support:
- **ADD** - Store conversations and individual memories
- **SEARCH** - Semantic search through memories
- **GET_ALL** - Retrieve all memories with optional filters
- **GET** - Fetch specific memory by ID
- **UPDATE** - Modify existing memories
- **DELETE** - Remove specific memories
- **DELETE_ALL** - Clear all memories for a user
- **HISTORY** - View memory change history (local classes only)

### AgentOps Instrumentation:
- Complete tracing of all memory operations
-  Detailed span attributes for debugging
-  Async operation support
- Metadata and user tracking
-  Performance metrics

##  Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_mem0_example.txt
```

### 2. Set Environment Variables

Create a `.env` file with the following variables:

```env
# Required
AGENTOPS_API_KEY=your_agentops_api_key
OPENAI_API_KEY=your_openai_api_key

# Optional (for cloud operations)
MEM0_API_KEY=your_mem0_cloud_api_key

# Optional (for alternative LLM providers)
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 4. Run the Example

```bash
python comprehensive_mem0_example.py
```

## 📋 What You'll See

The example will run through four comprehensive demonstrations:

###  Sync Memory (Local)
```
 SYNC MEMORY (Local) OPERATIONS
===========================================================
 Sync Memory initialized successfully

 Adding memories...
   Added conversation: {'message': 'Memory added successfully.'}
   Added preference 1: {'message': 'Memory added successfully.'}
   ...

 Searching memories...
    Query: 'What movies does the user like?'
       Result 1: User strongly prefers sci-fi movies and dislikes thrillers
   ...
```

###  Async Memory (Local)
Shows concurrent operations and async/await patterns:
```
 ASYNC MEMORY (Local) OPERATIONS
===========================================================
 Async Memory initialized successfully

 Adding memories asynchronously...
    Added conversation: {'message': 'Memory added successfully.'}
   ...

 Performing concurrent operations...
    Get result: {'id': 'mem_123...', 'memory': '...'}
    Update result: {'message': 'Memory updated successfully.'}
    History entries: 3
```

### Sync Memory Client (Cloud)
Demonstrates cloud-based memory operations:
```
 SYNC MEMORY CLIENT (Cloud) OPERATIONS
===========================================================
Sync MemoryClient initialized successfully

 Adding memories to cloud...
 Added conversation to cloud: {'id': 'cloud_mem_456...'}
   ...
```

###  Async Memory Client (Cloud)
Shows async cloud operations with concurrent processing:
```
ASYNC MEMORY CLIENT (Cloud) OPERATIONS
===========================================================
Async MemoryClient initialized successfully

Adding memories to cloud asynchronously...
    Added conversation and preferences: 4 items
   ...

Performing concurrent searches...
    Search 1 result: {'results': [...]}
   ...
```

##  Configuration Options

### Local Memory Configuration

```python
local_config = {
    "llm": {
        "provider": "openai",  # or "anthropic", "ollama", etc.
        "config": {
            "model": "gpt-4o-mini",
            "temperature": 0.1,
            "max_tokens": 2000,
            "api_key": "your_api_key",
        }
    },
    "embedder": {
        "provider": "openai",  # or "huggingface", "sentence-transformers"
        "config": {
            "model": "text-embedding-3-small",
            "api_key": "your_api_key",
        }
    },
    "vector_store": {
        "provider": "qdrant",  # or "chromadb", "pinecone"
        "config": {
            "collection_name": "test_collection",
            "host": "localhost",
            "port": 6333,
        }
    }
}
```

### Cloud Client Configuration

```python
# Simply provide your API key
client = MemoryClient(api_key="your_mem0_api_key")
async_client = AsyncMemoryClient(api_key="your_mem0_api_key")
```

##  AgentOps Dashboard

After running the example, check your AgentOps dashboard to see:

- **Spans**: Detailed trace of each memory operation
- **Metrics**: Performance data and operation counts  
- **Attributes**: Memory content, user IDs, metadata
- **Errors**: Any failures with full stack traces

##  Customization

### Add Your Own Operations

```python
# Extend the Mem0Example class
class CustomMem0Example(Mem0Example):
    def custom_memory_workflow(self):
        memory = Memory.from_config(self.local_config)
        
        # Your custom logic here
        result = memory.add("Custom memory content", user_id="custom_user")
        search_results = memory.search("custom query", user_id="custom_user")
        
        return search_results
```

### Use Different Providers

```python
# Anthropic LLM
anthropic_config = {
    "llm": {
        "provider": "anthropic",
        "config": {
            "model": "claude-3-haiku-20240307",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
        }
    }
}

# Hugging Face Embeddings
hf_config = {
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
        }
    }
}
```

##  Learn More
- [Mem0 Documentation](https://docs.mem0.ai/)
- [AgentOps Documentation](https://docs.agentops.ai/)
- [OpenAI API Reference](https://platform.openai.com/docs/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)

## 📄 License

This example is provided under the same license as the AgentOps project. 
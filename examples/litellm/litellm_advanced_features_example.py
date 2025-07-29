"""
LiteLLM Advanced Features Example with AgentOps Integration

This example demonstrates advanced LiteLLM features including:
- Function/tool calling
- Image analysis (vision models)
- Embeddings
- Error handling and retries
- Custom callbacks and logging

Install required packages:
pip install litellm agentops

Set your API keys:
export OPENAI_API_KEY="your-openai-key"
export AGENTOPS_API_KEY="your-agentops-key"
"""

import os
import json
import agentops
import litellm

agentops.init()

tracer = agentops.start_trace("litellm-advanced-features-example")

print("🚀 Starting LiteLLM Advanced Features Example with AgentOps")
print("=" * 60)

def function_calling_example():
    """Demonstrate function/tool calling capabilities."""
    print("\n🛠️  Example 1: Function/Tool Calling")
    print("-" * 40)
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "The temperature unit"
                        }
                    },
                    "required": ["location"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculate_distance",
                "description": "Calculate distance between two cities",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city1": {"type": "string", "description": "First city"},
                        "city2": {"type": "string", "description": "Second city"}
                    },
                    "required": ["city1", "city2"]
                }
            }
        }
    ]
    
    messages = [
        {"role": "user", "content": "What's the weather like in New York and what's the distance between New York and Los Angeles?"}
    ]
    
    try:
        print("🔧 Making completion with function calling...")
        response = litellm.completion(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=300
        )
        
        message = response.choices[0].message
        
        if message.tool_calls:
            print(f"🎯 Function calls detected: {len(message.tool_calls)}")
            for i, tool_call in enumerate(message.tool_calls, 1):
                print(f"  {i}. Function: {tool_call.function.name}")
                print(f"     Arguments: {tool_call.function.arguments}")
        else:
            print(f"📝 Regular response: {message.content}")
        
        print(f"✅ Function calling successful! Tokens: {response.usage.total_tokens}")
        return response
        
    except Exception as e:
        print(f"❌ Function calling failed: {e}")
        raise

def embeddings_example():
    """Demonstrate embeddings generation."""
    print("\n🔢 Example 2: Text Embeddings")
    print("-" * 40)
    
    texts = [
        "The quick brown fox jumps over the lazy dog",
        "Machine learning is a subset of artificial intelligence",
        "Python is a popular programming language for data science"
    ]
    
    try:
        print("🎯 Generating embeddings...")
        
        for i, text in enumerate(texts, 1):
            print(f"  {i}. Processing: {text[:50]}...")
            
            response = litellm.embedding(
                model="text-embedding-ada-002",
                input=text
            )
            
            embedding = response.data[0].embedding
            print(f"     Embedding dimension: {len(embedding)}")
            print(f"     First 5 values: {embedding[:5]}")
        
        print(f"✅ Embeddings generated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Embeddings failed: {e}")
        return False

def error_handling_example():
    """Demonstrate error handling and retry mechanisms."""
    print("\n⚠️  Example 3: Error Handling & Retries")
    print("-" * 40)
    
    print("🎯 Testing error handling with invalid model...")
    
    try:
        response = litellm.completion(
            model="invalid-model-name",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=50
        )
        print("❌ This should not succeed!")
        
    except Exception as e:
        print(f"✅ Expected error caught: {type(e).__name__}")
        print(f"   Error message: {str(e)[:100]}...")
    
    print("\n🎯 Testing with valid model and proper error handling...")
    
    try:
        response = litellm.completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10,
            temperature=0.1
        )
        
        print(f"📝 Response: {response.choices[0].message.content}")
        print(f"✅ Proper request successful!")
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def streaming_with_callbacks_example():
    """Demonstrate streaming with custom callback handling."""
    print("\n📡 Example 4: Streaming with Custom Callbacks")
    print("-" * 40)
    
    messages = [
        {"role": "user", "content": "Write a short poem about technology and nature."}
    ]
    
    try:
        print("🎯 Making streaming completion with callback tracking...")
        
        # Track streaming metrics
        chunk_count = 0
        total_content = ""
        first_chunk_time = None
        
        response = litellm.completion(
            model="gpt-4o-mini",
            messages=messages,
            stream=True,
            max_tokens=200,
            temperature=0.7
        )
        
        print("📡 Streaming response:")
        for chunk in response:
            chunk_count += 1
            
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                total_content += content
                print(content, end="", flush=True)
                
                if first_chunk_time is None:
                    first_chunk_time = chunk_count
        
        print(f"\n\n📊 Streaming metrics:")
        print(f"   • Total chunks: {chunk_count}")
        print(f"   • Content length: {len(total_content)} characters")
        print(f"   • First content chunk: #{first_chunk_time}")
        
        print(f"✅ Streaming with callbacks successful!")
        return True
        
    except Exception as e:
        print(f"❌ Streaming with callbacks failed: {e}")
        return False

def batch_processing_example():
    """Demonstrate batch processing of multiple requests."""
    print("\n📦 Example 5: Batch Processing")
    print("-" * 40)
    
    tasks = [
        {"role": "user", "content": "What is 2+2?"},
        {"role": "user", "content": "Name a color."},
        {"role": "user", "content": "What day comes after Monday?"},
        {"role": "user", "content": "How many legs does a spider have?"}
    ]
    
    try:
        print(f"🎯 Processing {len(tasks)} tasks in batch...")
        
        results = []
        for i, task in enumerate(tasks, 1):
            print(f"  Processing task {i}/{len(tasks)}...")
            
            response = litellm.completion(
                model="gpt-4o-mini",
                messages=[task],
                max_tokens=50,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens
            
            results.append({
                "task": task["content"],
                "response": content,
                "tokens": tokens
            })
        
        print(f"\n📊 Batch results:")
        total_tokens = 0
        for i, result in enumerate(results, 1):
            print(f"  {i}. Q: {result['task']}")
            print(f"     A: {result['response']}")
            print(f"     Tokens: {result['tokens']}")
            total_tokens += result['tokens']
        
        print(f"\n✅ Batch processing successful! Total tokens: {total_tokens}")
        return results
        
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")
        return []

def main():
    """Main function to run all advanced feature examples."""
    try:
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️  Warning: OPENAI_API_KEY not set. Please set your API key.")
        
        examples_run = 0
        examples_successful = 0
        
        # Function calling
        try:
            function_calling_example()
            examples_successful += 1
        except Exception as e:
            print(f"Function calling example failed: {e}")
        examples_run += 1
        
        try:
            if embeddings_example():
                examples_successful += 1
        except Exception as e:
            print(f"Embeddings example failed: {e}")
        examples_run += 1
        
        try:
            if error_handling_example():
                examples_successful += 1
        except Exception as e:
            print(f"Error handling example failed: {e}")
        examples_run += 1
        
        try:
            if streaming_with_callbacks_example():
                examples_successful += 1
        except Exception as e:
            print(f"Streaming callbacks example failed: {e}")
        examples_run += 1
        
        try:
            batch_results = batch_processing_example()
            if batch_results:
                examples_successful += 1
        except Exception as e:
            print(f"Batch processing example failed: {e}")
        examples_run += 1
        
        print("\n" + "=" * 60)
        print(f"🎉 Advanced Features Testing Complete!")
        print(f"📊 Results: {examples_successful}/{examples_run} examples successful")
        
        if examples_successful > 0:
            agentops.end_trace(tracer, end_state="Success")
        else:
            agentops.end_trace(tracer, end_state="Fail")
        
    except Exception as e:
        print(f"\n❌ Advanced features testing failed: {e}")
        agentops.end_trace(tracer, end_state="Fail")
        raise

if __name__ == "__main__":
    main()
    
    print("\n" + "=" * 60)
    print("Now let's verify that our advanced LLM calls were tracked properly...")
    
    try:
        result = agentops.validate_trace_spans(trace_context=tracer)
        agentops.print_validation_summary(result)
    except agentops.ValidationError as e:
        print(f"❌ Error validating spans: {e}")
        raise
    
    print("\n✅ Success! All advanced feature LLM spans were properly recorded in AgentOps.")

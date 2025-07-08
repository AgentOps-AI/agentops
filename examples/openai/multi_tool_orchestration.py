# ### Multi-Tool Orchestration with RAG approach using OpenAI's Responses API
#
# This cookbook guides you through building dynamic, multi-tool workflows using OpenAI's Responses API. It demonstrates how to implement a Retrieval-Augmented Generation (RAG) approach that intelligently routes user queries to the appropriate in-built or external tools. Whether your query calls for general knowledge or requires accessing specific internal context from a vector database (like Pinecone), this guide shows you how to integrate function calls, web searches in-built tool, and leverage document retrieval to generate accurate, context-aware responses.
# # Install required dependencies
# %pip install agentops
# %pip install openai
# %pip install datasets
# %pip install tqdm
# %pip install pandas
# %pip install pinecone
# %pip install python-dotenv
import os
from dotenv import load_dotenv
import time
from tqdm.auto import tqdm
from pandas import DataFrame
from datasets import load_dataset
import random
import string
from openai import OpenAI
import agentops
from pinecone import Pinecone
from pinecone import ServerlessSpec

load_dotenv()

os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
os.environ["PINECONE_API_KEY"] = os.getenv("PINECONE_API_KEY", "your_pinecone_api_key_here")

agentops.init(auto_start_session=True, tags=["openai", "multi-tool", "agentops-example"])
tracer = agentops.start_trace(
    trace_name="OpenAI Multi-Tool Orchestration with RAG",
    tags=["multi-tool-orchestration-rag-demo", "openai-responses", "agentops-example"],
)
client = OpenAI()

# In this example we use a sample medical reasoning dataset from Hugging Face. We convert the dataset into a Pandas DataFrame and merge the “Question” and “Response” columns into a single string. This merged text is used for embedding and later stored as metadata.
# Load the dataset (ensure you're logged in with huggingface-cli if needed)
ds = load_dataset("FreedomIntelligence/medical-o1-reasoning-SFT", "en", split="train[:100]", trust_remote_code=True)
ds_dataframe = DataFrame(ds)

# Merge the Question and Response columns into a single string.
ds_dataframe["merged"] = ds_dataframe.apply(
    lambda row: f"Question: {row['Question']} Answer: {row['Response']}", axis=1
)
print("Example merged text:", ds_dataframe["merged"].iloc[0])

# ### Create a Pinecone Index Based on the Dataset
# Use the dataset itself to determine the embedding dimensionality. For example, compute one embedding from the merged column and then create the index accordingly.
MODEL = "text-embedding-3-small"  # Replace with your production embedding model if needed

# Compute an embedding for the first document to obtain the embedding dimension.
sample_embedding_resp = client.embeddings.create(input=[ds_dataframe["merged"].iloc[0]], model=MODEL)
embed_dim = len(sample_embedding_resp.data[0].embedding)
print(f"Embedding dimension: {embed_dim}")

# Initialize Pinecone using your API key.
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

# Define the Pinecone serverless specification.
AWS_REGION = "us-east-1"
spec = ServerlessSpec(cloud="aws", region=AWS_REGION)

# Create a random index name with lower case alphanumeric characters and '-'
index_name = "pinecone-index-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=10))

# Create the index if it doesn't already exist.
if index_name not in pc.list_indexes().names():
    pc.create_index(index_name, dimension=embed_dim, metric="dotproduct", spec=spec)

# Connect to the index.
index = pc.Index(index_name)
time.sleep(1)
print("Index stats:", index.describe_index_stats())

# #### Upsert the Dataset into Pinecone index
#
# Process the dataset in batches, generate embeddings for each merged text, prepare metadata (including separate Question and Answer fields), and upsert each batch into the index. You may also update metadata for specific entries if needed.
batch_size = 32
for i in tqdm(range(0, len(ds_dataframe["merged"]), batch_size), desc="Upserting to Pinecone"):
    i_end = min(i + batch_size, len(ds_dataframe["merged"]))
    lines_batch = ds_dataframe["merged"][i:i_end]
    ids_batch = [str(n) for n in range(i, i_end)]

    # Create embeddings for the current batch.
    res = client.embeddings.create(input=[line for line in lines_batch], model=MODEL)
    embeds = [record.embedding for record in res.data]

    # Prepare metadata by extracting original Question and Answer.
    meta = []
    for record in ds_dataframe.iloc[i:i_end].to_dict("records"):
        q_text = record["Question"]
        a_text = record["Response"]
        # Optionally update metadata for specific entries.
        meta.append({"Question": q_text, "Answer": a_text})

    # Upsert the batch into Pinecone.
    vectors = list(zip(ids_batch, embeds, meta))
    index.upsert(vectors=vectors)


# ### Query the Pinecone Index
#
# Create a natural language query, compute its embedding, and perform a similarity search on the Pinecone index. The returned results include metadata that provides context for generating answers.
def query_pinecone_index(client, index, model, query_text):
    # Generate an embedding for the query.
    query_embedding = client.embeddings.create(input=query_text, model=model).data[0].embedding

    # Query the index and return top 5 matches.
    res = index.query(vector=[query_embedding], top_k=5, include_metadata=True)
    print("Query Results:")
    for match in res["matches"]:
        print(
            f"{match['score']:.2f}: {match['metadata'].get('Question', 'N/A')} - {match['metadata'].get('Answer', 'N/A')}"
        )
    return res


# Example usage with a different query from the train/test set
query = (
    "A 45-year-old man with a history of alcohol use presents with symptoms including confusion, ataxia, and ophthalmoplegia. "
    "What is the most likely diagnosis and the recommended treatment?"
)
query_pinecone_index(client, index, MODEL, query)

# ### Generate a Response Using the Retrieved Context
#
# Select the best matching result from your query results and use the OpenAI Responses API to generate a final answer by combining the retrieved context with the original question.
# Retrieve and concatenate top 3 match contexts.
matches = index.query(
    vector=[client.embeddings.create(input=query, model=MODEL).data[0].embedding], top_k=3, include_metadata=True
)["matches"]

context = "\n\n".join(
    f"Question: {m['metadata'].get('Question', '')}\nAnswer: {m['metadata'].get('Answer', '')}" for m in matches
)

# Use the context to generate a final answer.
response = client.responses.create(
    model="gpt-4o",
    input=f"Provide the answer based on the context: {context} and the question: {query} as per the internal knowledge base",
)
print("\nFinal Answer:")
print(response.output_text)

# ### Orchestrate Multi-Tool Calls
#
# Now, we'll define the built-in function available through the Responses API, including the ability to invoke the external Vector Store - Pinecone as an example.
#
# *Web Search Preview Tool*: Enables the model to perform live web searches and preview the results. This is ideal for retrieving real-time or up-to-date information from the internet.
#
# *Pinecone Search Tool*: Allows the model to query a vector database using semantic search. This is especially useful for retrieving relevant documents—such as medical literature or other domain-specific content—that have been stored in a vectorized format.
# # Tools definition: The list of tools includes:
# # - A web search preview tool.
# # - A Pinecone search tool for retrieving medical documents.
#
# # Define available tools.
tools = [
    {
        "type": "web_search_preview",
        "user_location": {"type": "approximate", "country": "US", "region": "California", "city": "SF"},
        "search_context_size": "medium",
    },
    {
        "type": "function",
        "name": "PineconeSearchDocuments",
        "description": "Search for relevant documents based on the medical question asked by the user that is stored within the vector database using a semantic query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The natural language query to search the vector database."},
                "top_k": {"type": "integer", "description": "Number of top results to return.", "default": 3},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
]

# # Example queries that the model should route appropriately.
queries = [
    {"query": "Who won the cricket world cup in 1983?"},
    {"query": "What is the most common cause of death in the United States according to the internet?"},
    {
        "query": (
            "A 7-year-old boy with sickle cell disease is experiencing knee and hip pain, "
            "has been admitted for pain crises in the past, and now walks with a limp. "
            "His exam shows a normal, cool hip with decreased range of motion and pain with ambulation. "
            "What is the most appropriate next step in management according to the internal knowledge base?"
        )
    },
]

# # Process each query dynamically.
for item in queries:
    input_messages = [{"role": "user", "content": item["query"]}]
    print("\n🌟--- Processing Query ---🌟")
    print(f"🔍 **User Query:** {item['query']}")

    # Call the Responses API with tools enabled and allow parallel tool calls.
    response = client.responses.create(
        model="gpt-4o",
        input=[
            {
                "role": "system",
                "content": "When prompted with a question, select the right tool to use based on the question.",
            },
            {"role": "user", "content": item["query"]},
        ],
        tools=tools,
        parallel_tool_calls=True,
    )

    print("\n✨ **Initial Response Output:**")
    print(response.output)

    # Determine if a tool call is needed and process accordingly.
    if response.output:
        tool_call = response.output[0]
        if tool_call.type in ["web_search_preview", "function_call"]:
            tool_name = tool_call.name if tool_call.type == "function_call" else "web_search_preview"
            print(f"\n🔧 **Model triggered a tool call:** {tool_name}")

            if tool_name == "PineconeSearchDocuments":
                print("🔍 **Invoking PineconeSearchDocuments tool...**")
                res = query_pinecone_index(client, index, MODEL, item["query"])
                if res["matches"]:
                    best_match = res["matches"][0]["metadata"]
                    result = f"**Question:** {best_match.get('Question', 'N/A')}\n**Answer:** {best_match.get('Answer', 'N/A')}"
                else:
                    result = "**No matching documents found in the index.**"
                print("✅ **PineconeSearchDocuments tool invoked successfully.**")
            else:
                print("🔍 **Invoking simulated web search tool...**")
                result = "**Simulated web search result.**"
                print("✅ **Simulated web search tool invoked successfully.**")

            # Append the tool call and its output back into the conversation.
            input_messages.append(tool_call)
            input_messages.append({"type": "function_call_output", "call_id": tool_call.call_id, "output": str(result)})

            # Get the final answer incorporating the tool's result.
            final_response = client.responses.create(
                model="gpt-4o", input=input_messages, tools=tools, parallel_tool_calls=True
            )
            print("\n💡 **Final Answer:**")
            print(final_response.output_text)
        else:
            # If no tool call is triggered, print the response directly.
            print("💡 **Final Answer:**")
            print(response.output_text)

# As shown above, depending on the query, appropriate tool is invoked in order to determine the optimal response.
#
# For instance, looking at the third example, when the model triggers the tool named "PineconeSearchDocuments", the code calls `query_pinecone_index` with the current query and then extracts the best match (or an appropriate context) as the result. For non health related inqueries or queries where explicit internet search is asked, the code calls the web_search_call function and for other queries, it may choose to not call any tool and rather provide a response based on the question under consideration.
#
# Finally, the tool call and its output are appended to the conversation, and the final answer is generated by the Responses API.
# ### Multi-tool orchestration flow
#
# Now let us try to modify the input query and the system instructions to the responses API in order to follow a tool calling sequence and generate the output.
# # Process one query as an example to understand the tool calls and function calls as part of the response output
item = "What is the most common cause of death in the United States"

# Initialize input messages with the user's query.
input_messages = [{"role": "user", "content": item}]
print("\n🌟--- Processing Query ---🌟")
print(f"🔍 **User Query:** {item}")

# Call the Responses API with tools enabled and allow parallel tool calls.
print("\n🔧 **Calling Responses API with Tools Enabled**")
print("\n🕵️‍♂️ **Step 1: Web Search Call**")
print("   - Initiating web search to gather initial information.")
print("\n📚 **Step 2: Pinecone Search Call**")
print("   - Querying Pinecone to find relevant examples from the internal knowledge base.")

response = client.responses.create(
    model="gpt-4o",
    input=[
        {
            "role": "system",
            "content": "Every time it's prompted with a question, first call the web search tool for results, then call `PineconeSearchDocuments` to find real examples in the internal knowledge base.",
        },
        {"role": "user", "content": item},
    ],
    tools=tools,
    parallel_tool_calls=True,
)

# Print the initial response output.
print("input_messages", input_messages)

print("\n✨ **Initial Response Output:**")
print(response.output)

# # Understand the tool calls and function calls as part of the response output
#
# import pandas as pd
#
# # Create a list to store the tool call and function call details
# tool_calls = []
#
# # Iterate through the response output and collect the details
# for i in response.output:
#     tool_calls.append(
#         {
#             "Type": i.type,
#             "Call ID": i.call_id if hasattr(i, "call_id") else i.id if hasattr(i, "id") else "N/A",
#             "Output": str(i.output) if hasattr(i, "output") else "N/A",
#             "Name": i.name if hasattr(i, "name") else "N/A",
#         }
#     )
#
# # Convert the list to a DataFrame for tabular display
# df_tool_calls = pd.DataFrame(tool_calls)
#
# # Display the DataFrame
# df_tool_calls
tool_call_1 = response.output[0]
print(tool_call_1)
print(tool_call_1.id)

tool_call_2 = response.output[2]
print(tool_call_2)
print(tool_call_2.call_id)

# # append the tool call and its output back into the conversation.
input_messages.append(response.output[2])
input_messages.append({"type": "function_call_output", "call_id": tool_call_2.call_id, "output": str(result)})
print(input_messages)

# # Get the final answer incorporating the tool's result.
print("\n🔧 **Calling Responses API for Final Answer**")

response_2 = client.responses.create(
    model="gpt-4o",
    input=input_messages,
)
print(response_2)

# # print the final answer
print(response_2.output_text)
agentops.end_trace(tracer, end_state="Success")

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=tracer)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise


# Here, we have seen  how to utilize OpenAI's Responses API to implement a Retrieval-Augmented Generation (RAG) approach with multi-tool calling capabilities. It showcases an example where the model selects the appropriate tool based on the input query: general questions may be handled by built-in tools such as web-search, while specific medical inquiries related to internal knowledge are addressed by retrieving context from a vector database (such as Pinecone) via function calls. Additonally, we have showcased how multiple tool calls can be sequentially combined to generate a final response based on our instructions provided to responses API. Happy coding!

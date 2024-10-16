import agentops
import time
import openai

# OpenAI calls take ~0.5-0.8s

# Define the maximum acceptable execution time (in seconds)
MAX_EXECUTION_TIME = 0.5  # Adjust this value as needed

client = openai.OpenAI()

start_time = time.time()
agentops.init(
    api_key="1bbdc836-b95e-4b14-8538-3c2464989f88",
    endpoint="https://api.playground.agentops.ai",
)
end_time = time.time()
init_time = end_time - start_time
client.chat.completions.create(
    model="gpt-4o-mini", messages=[{"role": "user", "content": "Hello!"}]
)
print(f"AgentOps initialization time: {init_time:.4f} seconds")

agentops.end_session("Success")

# total_start_time = time.time()

# # First test
# print("Start of first test")
# start_time = time.time()

# client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "Hello!"}])
# end_time = time.time()
# elapsed_time = end_time - start_time
# print(f"Elapsed time for first test: {elapsed_time:.4f} seconds")
# # agentops.end_session('Success')

# # Second test
# print("Start of second test")
# start_time = time.time()
# client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "Hello!"}])
# end_time = time.time()
# elapsed_time = end_time - start_time
# print(f"Elapsed time for second test: {elapsed_time:.4f} seconds")

# total_end_time = time.time()
# total_elapsed_time = total_end_time - total_start_time
# print(f"Total elapsed time for entire test: {total_elapsed_time:.4f} seconds")

# print("Latency test passed successfully!")

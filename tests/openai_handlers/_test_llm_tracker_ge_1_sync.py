from openai import OpenAI
import agentops
from agentops import record_action
from packaging.version import parse
from importlib import import_module
import sys
from dotenv import load_dotenv

load_dotenv()

agentops.init()

api = "openai"
if api in sys.modules:
    module = import_module(api)
    if api == "openai":
        if hasattr(module, "__version__"):
            module_version = parse(module.__version__)
            print("openai version: ", module_version)


@record_action("openai v1 sync no streaming")
def call_openai_v1_sync_no_streaming():
    client = OpenAI()
    chat_completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert haiku writer"},
            {"role": "user", "content": "write me a haiku about devops"},
        ],
    )

    print(chat_completion)
    # raise ValueError("This is an intentional error for testing.")


@record_action("openai v1 sync with streaming")
def call_openai_v1_sync_streaming():
    client = OpenAI()
    chat_completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert haiku writer"},
            {"role": "user", "content": "write me a haiku about devops"},
        ],
        stream=True,
    )

    for chunk in chat_completion:
        chunk_message = chunk.choices[0].delta.content
        print(chunk_message)

    # raise ValueError("This is an intentional error for testing.")


call_openai_v1_sync_no_streaming()
call_openai_v1_sync_streaming()

agentops.end_session("Success")

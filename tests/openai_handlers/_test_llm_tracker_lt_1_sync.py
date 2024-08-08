from openai import ChatCompletion
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


@record_action("openai v0 sync no streaming")
def call_openai_v0_sync_no_streaming():
    chat_completion = ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert haiku writer"},
            {"role": "user", "content": "write me a haiku about devops"},
        ],
    )

    print(chat_completion)
    # raise ValueError("This is an intentional error for testing.")


@record_action("openai v0 sync with streaming")
def call_openai_v0_sync_with_streaming():
    chat_completion = ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert haiku writer"},
            {"role": "user", "content": "write me a haiku about devops"},
        ],
        stream=True,
    )

    for chunk in chat_completion:
        print(chunk.choices[0])
        chunk_message = chunk.choices[0].delta["content"]
        print(chunk_message)
    # raise ValueError("This is an intentional error for testing.")


call_openai_v0_sync_no_streaming()
call_openai_v0_sync_with_streaming()

agentops.end_session("Success")

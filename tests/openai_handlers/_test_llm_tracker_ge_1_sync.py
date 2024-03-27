from openai import OpenAI
import agentops
from agentops import record_function
from packaging.version import parse
from importlib import import_module
import sys
from dotenv import load_dotenv

load_dotenv()

agentops.init()

api = 'openai'
if api in sys.modules:
    module = import_module(api)
    if api == 'openai':
        if hasattr(module, '__version__'):
            module_version = parse(module.__version__)
            print('openai version: ', module_version)


@record_function('sample function being recorded')
def call_openai():
    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are an expert haiku writer"
            },
            {
                "role": "user",
                "content": "write me a haiku about devops"
            }
        ],
        temperature=0.7,
        max_tokens=64,
        top_p=1
    )

    print(response)
    # raise ValueError("This is an intentional error for testing.")


call_openai()

agentops.end_session('Success')

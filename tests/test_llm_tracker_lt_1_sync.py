import openai
from openai import ChatCompletion
import agentops
from packaging.version import parse
from importlib import import_module
import sys


ao_client = agentops.Client()

api = 'openai'
if api in sys.modules:
    module = import_module(api)
    if api == 'openai':
        if hasattr(module, '__version__'):
            module_version = parse(module.__version__)
            print('openai version: ', module_version)


@ao_client.record_function('sample function being record')
def call_openai():

    message = [{"role": "user", "content": "Hello"},
               {"role": "assistant", "content": "Hi there!"}]

    response = ChatCompletion.create(
        model='gpt-3.5-turbo', messages=message, temperature=0.5)

    print(response)


call_openai()

ao_client.end_session('Success')

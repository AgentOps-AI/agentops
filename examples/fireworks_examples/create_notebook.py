import nbformat as nbf
import os

nb = nbf.v4.new_notebook()

# Create cells
cells = [
    nbf.v4.new_markdown_cell(
        "# Fireworks Example\n\n"
        "We are going to create a simple chatbot that creates stories based on a prompt. "
        "The chatbot will use the Llama-v3 LLM to generate the story using a user prompt.\n\n"
        "We will track the chatbot with AgentOps and see how it performs!"
    ),

    nbf.v4.new_markdown_cell("First let's install the required packages"),

    nbf.v4.new_code_cell(
        "%pip install -U fireworks-ai\n"
        "%pip install -U agentops"
    ),

    nbf.v4.new_markdown_cell("Then import them"),

    nbf.v4.new_code_cell(
        "from fireworks.client import Fireworks\n"
        "import agentops\n"
        "import os\n"
        "from dotenv import load_dotenv"
    ),

    nbf.v4.new_markdown_cell(
        "Next, we'll grab our API keys. You can use dotenv like below or "
        "however else you like to load environment variables"
    ),

    nbf.v4.new_code_cell(
        'load_dotenv()\n'
        'FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY") or "<your_fireworks_key>"\n'
        'AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "<your_agentops_key>"'
    ),

    nbf.v4.new_markdown_cell("Next we initialize the AgentOps client."),

    nbf.v4.new_code_cell(
        'agentops.init(AGENTOPS_API_KEY, default_tags=["fireworks-example"])'
    ),

    nbf.v4.new_markdown_cell(
        "And we are all set! Note the session url above. We will use it to track the chatbot.\n\n"
        "Let's create a simple chatbot that generates stories."
    ),

    nbf.v4.new_code_cell(
        'client = Fireworks(api_key=FIREWORKS_API_KEY)\n\n'
        'system_prompt = """\n'
        'You are a master storyteller, with the ability to create vivid and engaging stories.\n'
        'You have experience in writing for children and adults alike.\n'
        'You are given a prompt and you need to generate a story based on the prompt.\n'
        '"""\n\n'
        'user_prompt = "Write a story about a cyber-warrior trapped in the imperial time period."\n\n'
        'messages = [\n'
        '    {"role": "system", "content": system_prompt},\n'
        '    {"role": "user", "content": user_prompt},\n'
        ']'
    ),

    nbf.v4.new_code_cell(
        'response = client.chat.completions.create(\n'
        '    model="accounts/fireworks/models/llama-v3p1-8b-instruct",\n'
        '    messages=messages,\n'
        ')\n\n'
        'print(response.choices[0].message.content)'
    ),

    nbf.v4.new_markdown_cell(
        "The response is a string that contains the story. We can track this with AgentOps "
        "by navigating to the session url and viewing the run.\n\n"
        "## Streaming Version\n"
        "We will demonstrate the streaming version of the API."
    ),

    nbf.v4.new_code_cell(
        'stream = client.chat.completions.create(\n'
        '    model="accounts/fireworks/models/llama-v3p1-8b-instruct",\n'
        '    messages=messages,\n'
        '    stream=True,\n'
        ')\n\n'
        'for chunk in stream:\n'
        '    print(chunk.choices[0].delta.content or "", end="")'
    ),

    nbf.v4.new_markdown_cell(
        "Note that the response is a generator that yields chunks of the story. "
        "We can track this with AgentOps by navigating to the session url and viewing the run."
    ),

    nbf.v4.new_code_cell(
        'agentops.end_session(end_state="Success", '
        'end_state_reason="The story was generated successfully.")'
    ),

    nbf.v4.new_markdown_cell(
        "We end the session with a success state and a success reason. This is useful if you "
        "want to track the success or failure of the chatbot. In that case you can set the "
        "end state to failure and provide a reason. By default the session will have an "
        "indeterminate end state.\n\n"
        "All done!"
    )
]

nb.cells = cells

# Set the notebook metadata
nb.metadata = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3"
    },
    "language_info": {
        "codemirror_mode": {"name": "ipython", "version": 3},
        "file_extension": ".py",
        "mimetype": "text/x-python",
        "name": "python",
        "nbconvert_exporter": "python",
        "pygments_lexer": "ipython3",
        "version": "3.12"
    }
}

# Write the notebook
notebook_path = os.path.join(os.path.dirname(__file__), 'fireworks_example.ipynb')
with open(notebook_path, 'w') as f:
    nbf.write(nb, f)

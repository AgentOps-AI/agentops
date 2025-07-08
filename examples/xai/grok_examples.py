# XAI Example
#
# This notebook demonstrates how to use XAI with AgentOps via the OpenAI python client.
#
# We are going to use the latest Grok model from XAI to create a transliteration chatbot that can understand the major languages of the world and translate them to a user's native language! We will use AgentOps to track the chatbot's performance.
# First let's install the required packages
# %pip install -U openai
# %pip install -U agentops
# Then import them
from openai import OpenAI
import agentops
import os
from dotenv import load_dotenv

# Next, we'll grab our API keys. You can use dotenv like below or however else you like to load environment variables
load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")

# Next we initialize the AgentOps client.
agentops.init(auto_start_session=False, trace_name="XAI Grok Example", tags=["xai", "grok", "agentops-example"])
tracer = agentops.start_trace(trace_name="XAI Grok Example", tags=["xai-example", "grok", "agentops-example"])

# And we are all set! Note the seesion url above. We will use it to track the chatbot.
#
# Let's initialize the OpenAI client with the XAI API key and base url.
client = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=os.getenv("XAI_API_KEY", "your_xai_api_key_here"),
)

# Now we will set the system and instruction prompts for the chatbot. We will set the native language to Spanish and the user prompt to transliterate an excerpt from Haruki Murakami's "Kafka On The Shore".
SYSTEM_PROMPT = """
You are a highly intelligent, multilingual assistant designed to understand user prompts in English and respond in the user's specified native language. 
Your key responsibilities include:
1. Translating and generating meaningful, contextually appropriate responses in the user's native language.
2. Ensuring the output is accurate, coherent, and in Unicode format for proper display in the specified language.
3. Adhering to the nuances of the specified language's grammar, tone, and cultural context.

When asked to respond in a language, generate the response entirely in that language without using English unless explicitly requested.

If the specified language is unfamiliar or ambiguous, politely ask for clarification in English.
"""

native_language = "Spanish"

USER_PROMPT = """
Sometimes fate is like a small sandstorm that keeps changing directions. You change direction but the sandstorm chases you. 
You turn again, but the storm adjusts. Over and over you play this out, like some ominous dance with death just before dawn. Why? 
Because this storm isn’t something that blew in from far away, something that has nothing to do with you. This storm is you. 
Something inside of you. So all you can do is give in to it, step right inside the storm, closing your eyes and plugging up your ears so the sand doesn’t get in, and walk through it, step by step. 
There’s no sun there, no moon, no direction, no sense of time. Just fine white sand swirling up into the sky like pulverized bones. 
That’s the kind of sandstorm you need to imagine.

And you really will have to make it through that violent, metaphysical, symbolic storm. 
No matter how metaphysical or symbolic it might be, make no mistake about it: it will cut through flesh like a thousand razor blades. People will bleed there, and you will bleed too. 
Hot, red blood. You’ll catch that blood in your hands, your own blood and the blood of others.

And once the storm is over you won’t remember how you made it through, how you managed to survive. You won’t even be sure, in fact, whether the storm is really over. 
But one thing is certain. When you come out of the storm you won’t be the same person who walked in. That’s what this storm’s all about.
"""

INSTRUCTION_PROMPT = f"""
You are a multilingual chatbot. Take the user's prompt: "{USER_PROMPT}" and respond naturally in {native_language}. 
Ensure that the response is in Unicode characters appropriate for {native_language}.
"""

# Now we will use the OpenAI client to generate the response by passing in the system and instruction prompts.
response = client.chat.completions.create(
    model="grok-3-mini",
    messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": INSTRUCTION_PROMPT}],
)

print(f"Original Response:\n{USER_PROMPT}")
generated_response = response.choices[0].message.content
print(f"Response in {native_language}:\n{generated_response}")

# Awesome! We can now transliterate from English to any language! And all of this can be tracked with AgentOps by going to the session url above.
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


# We end the session with a success state and a success reason. This is useful if you want to track the success or failure of the chatbot. In that case you can set the end state to failure and provide a reason. By default the session will have an indeterminate end state.

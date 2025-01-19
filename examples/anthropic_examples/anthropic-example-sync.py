#!/usr/bin/env python
# coding: utf-8

# # Anthropic Sync Example
# 
# We are going to create a program called "Nier Storyteller". In short, it uses a message system similar to Nier Automata's to generate a one sentence summary before creating a short story.
# 
# Example:
# 
# {A foolish doll} {died in a world} {of ended dreams.} turns into "In a forgotten land where sunlight barely touched the ground, a little doll wandered through the remains of shattered dreams. Its porcelain face, cracked and wea..."

# First, we start by importing Agentops and Anthropic

# In[ ]:


get_ipython().run_line_magic('pip', 'install agentops')
get_ipython().run_line_magic('pip', 'install anthropic')


# Setup our generic default statements

# In[4]:


from anthropic import Anthropic, AsyncAnthropic
import agentops
from dotenv import load_dotenv
import os
import random


# And set our API keys.

# In[6]:


load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or "ANTHROPIC KEY HERE"
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "AGENTOPS KEY HERE"


# Now let's set the client as Anthropic and an AgentOps session!

# In[7]:


client = Anthropic(api_key=ANTHROPIC_API_KEY)


# In[ ]:


agentops.init(AGENTOPS_API_KEY, default_tags=["anthropic-example"])

# Remember that story we made earlier? As of writing, claude-3-5-sonnet-20240620 (the version we will be using) has a 150k word, 680k character length. We also get an 8192 context length. This is great because we can actually set an example for the script! 
# 
# Let's assume we have user (the person speaking), assistant (the AI itself) for now and computer (the way the LLM gets references from).
# Let's set a default story as a script!

# In[10]:


defaultstory = "In a forgotten land where sunlight barely touched the ground, a little doll wandered through the remains of shattered dreams. Its porcelain face, cracked and weathered, reflected the emptiness that hung in the air like a lingering fog. The doll's painted eyes, now chipped and dull, stared into the distance, searching for something—anything—that still held life. It had once belonged to a child who dreamt of endless adventures, of castles in the clouds and whispered secrets under starry skies. But those dreams had long since crumbled to dust, leaving behind nothing but a hollow world where even hope dared not tread. The doll, a relic of a life that had faded, trudged through the darkness, its tiny feet stumbling over broken wishes and forgotten stories. Each step took more effort than the last, as if the world itself pulled at the doll's limbs, weary and bitter. It reached a place where the ground fell away into an abyss of despair, the edge crumbling under its weight. The doll paused, teetering on the brink. It reached out, as though to catch a fading dream, but there was nothing left to hold onto. With a faint crack, its brittle body gave way, and the doll tumbled silently into the void. And so, in a world where dreams had died, the foolish little doll met its end. There were no tears, no mourning. Only the soft, empty echo of its fall, fading into the darkness, as the land of ended dreams swallowed the last trace of what once was."


# We are almost done! Let's generate a one sentence story summary by taking 3 random sentence fragments and connecting them!

# In[11]:


# Define the lists
first = [
    "A unremarkable soldier",
    "A lone swordsman",
    "A lone lancer",
    "A lone pugilist",
    "A dual-wielder",
    "A weaponless soldier",
    "A beautiful android",
    "A small android",
    "A double-crossing android",
    "A weapon carrying android",
]

second = [
    "felt despair at this cold world",
    "held nothing back",
    "gave it all",
    "could not get up again",
    "grimaced in anger",
    "missed the chance of a lifetime",
    "couldn't find a weakpoint",
    "was overwhelmed",
    "was totally outmatched",
    "was distracted by a flower",
    "hesitated to land the killing blow",
    "was attacked from behind",
    "fell to the ground",
]

third = [
    "in a dark hole beneath a city",
    "underground",
    "at the enemy's lair",
    "inside an empty ship",
    "at a tower built by the gods",
    "on a tower smiled upon by angels",
    "inside a tall tower",
    "at a peace-loving village",
    "at a village of refugees",
    "in the free skies",
    "below dark skies",
    "in a blood-soaked battlefield",
]

# Generate a random sentence
generatedsentence = (
    f"{random.choice(first)} {random.choice(second)} {random.choice(third)}."
)


# And now to construct a stream/message! We set an example for the assistant now!

# In[ ]:


stream = client.messages.create(
    max_tokens=2400,
    model="claude-3-5-sonnet-20240620",  # Comma added here
    messages=[
        {
            "role": "user",
            "content": "Create a story based on the three sentence fragments given to you, it has been combined into one below.",
        },
        {
            "role": "assistant",
            "content": "{A foolish doll} {died in a world} {of ended dreams.}",
        },
        {"role": "assistant", "content": defaultstory},
        {
            "role": "user",
            "content": "Create a story based on the three sentence fragments  given to you, it has been combined into one below.",
        },
        {"role": "assistant", "content": generatedsentence},
    ],
    stream=True,
)

response = ""
for event in stream:
    if event.type == "content_block_delta":
        response += event.delta.text
    elif event.type == "message_stop":
        print(generatedsentence)
        print(response)


# We can observe the session in the AgentOps dashboard by going to the session URL provided above.
# 
# Now we will end the session with a success message. We can also end the session with a failure or intdeterminate status. By default, the session will be marked as indeterminate.

# In[ ]:


agentops.end_session("Success")


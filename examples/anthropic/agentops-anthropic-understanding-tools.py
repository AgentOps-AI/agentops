# # Anthropic Example for understanding Tools
#
# Anthropic's tool returns are not as simple as getting a few strings! While this system is more complex than those before it, it's also simple enough to be used without problem once you understand how it works!
# To get started, we will import Agentops and Anthropic
# %pip install agentops
# %pip install anthropic
# Setup our generic default statements
import agentops
from anthropic import Anthropic
from dotenv import load_dotenv
import os
import random

# And set our API keys.
load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "your_anthropic_api_key_here")
#
# Now let's set the client as Anthropic and make an AgentOps trace
agentops.init(trace_name="Anthropic Understanding Tools", tags=["anthropic-example-tool-tutorials", "agentops-example"])
client = Anthropic()
# Now to create a simple dummy tool! We are going to make a tool that will tell us about the demon infestation levels for 3 areas. From there, we will have VEGA, our AI determine the best place for the Doom Slayer to attack.
locations = [
    {
        "Name": "Super Gore Nest",
        "Description": "A grotesque mass of demonic growth and organic structures infesting the ruins of an urban area on Earth. The Super Gore Nest serves as a massive, pulsating hive for Hell’s forces, complete with rivers of blood, twisted tendrils, and a dark, organic design that shows how deeply Hell has taken root in the city.",
    },
    {
        "Name": "Exultia",
        "Description": "An ancient, mystical world that holds the ruins of the Night Sentinels' kingdom, with gothic structures and arcane symbols throughout. This realm is filled with epic landscapes, medieval architecture, and hints of the powerful civilization that once defended against Hell’s forces.",
    },
    {
        "Name": "Cultist Base",
        "Description": "A grim fortress hidden within the icy mountains, where a fanatical cult worships demons. Filled with chilling sacrificial chambers, traps, and rituals, the Cultist Base is a hostile stronghold where Doom Slayer must confront the cult leaders aiding Hell's invasion of Earth.",
    },
    {
        "Name": "Taras Nabad",
        "Description": "A war-ravaged city on the homeworld of the Night Sentinels, showcasing grandiose, ancient architecture in the midst of destruction. Taras Nabad's sprawling structures and historical significance reveal glimpses into the Doom Slayer’s past and the once-thriving Sentinel civilization.",
    },
    {
        "Name": "Nekravol",
        "Description": "A hellish, industrial fortress where souls are processed into Argent energy. With conveyor belts moving the damned and a skyline dominated by fire and darkness, Nekravol is a nightmarish facility that powers Hell's armies and embodies the horrific machinery of Hell's cruelty.",
    },
    {
        "Name": "Urdak",
        "Description": "A surreal, high-tech realm that serves as the home of the angelic Maykrs. Urdak’s sleek, pristine architecture and ethereal ambiance sharply contrast with Hell’s brutal landscapes, yet this realm holds its own dark secrets and a critical role in Hell's invasion of Earth.",
    },
    {
        "Name": "UAC Base",
        "Description": "A futuristic military base on Earth controlled by the Union Aerospace Corporation (UAC), filled with high-tech weaponry and security systems. The UAC Base serves as a human foothold in the fight against Hell, though some within its ranks may have darker intentions.",
    },
]

combat_casualties = ["Nonexistent", "Low", "Medium", "High", "Extinction"]

missions = [
    "Locate and confront a key leader of Hell’s invasion forces.",
    "Clear out demonic infestations to secure a strategic foothold.",
    "Disrupt Hell's control over the area by eliminating critical targets.",
    "Enter a critical demonic stronghold to disrupt enemy operations.",
    "Locate and destroy the central power source to weaken enemy forces.",
    "Collect essential resources before the area becomes unstable.",
]


# Now that that's done, we can make a function! We will generate three random missions and pass it off to the AI.
def generate_missions():
    selectedmissions = []
    loop = 0

    while loop < 3:
        location = random.choice(locations)
        casualties = random.choice(combat_casualties)
        mission = random.choice(missions)
        final = (
            f"LocationName: {location['Name']}, "
            f"LocationInfo: {location['Description']}, "
            f"HumanCombatCasualties: {casualties}, "
            f"Mission: {mission}"
        )

        selectedmissions.append(final)
        loop += 1

    # Combine all mission strings into a single string with a separator (e.g., newline or comma)
    missions_string = "\\n".join(missions)  # Or \", \".join(missions) for a comma-separated string
    print(missions_string)
    return missions_string


generate_missions()
# Now to the real core of this; making our message stream! We create this as a function we can call later! I create examples since the LLM's context size can handle it (and it's generally good practice)!
#
# We are also going to take several steps here; we must create an example of the tool being used as context. Next, we must add the generated lines to the messages list once done being generated. Finally, we will parse the text for the format we want and request another line
# Now we make a message! This time around we will skip making an initial message that has too much context, unlike in the past!
# We make our history a separate block to be easier to add to later on! This is essentially our history
initial_messages = [
    {
        "role": "user",
        "content": "You are VEGA, the assistant to the DOOMGUY. Get three missions from the ship's API and tell me which mission is most to least important for quellng the forces of hell.  ",
    }
]
# Now to construct a request!
response = client.messages.create(
    max_tokens=5000,
    model="claude-3-7-sonnet-20250219",
    tools=[
        {
            "name": "generate_missions",
            "description": "Retrieve three missions for the DoomSlayer",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        }
    ],
    messages=initial_messages,
)

print(response.content)
# Having trouble understanding this? The first block given is always Ai dialouge! You can use response.content[0].text to get the AI's text! Let's try it below.
message = response.content[0].text
print(message)
# The code below finds the tool used!
gen_mission_result = ""

# Print response content to see the data
print(response.content)

# Assuming ToolUseBlock is at index 1
tool_use_block = response.content[1]

# Get the tool name and input
tool_name = tool_use_block.name
tool_input = tool_use_block.input

# We don't need to look to extract any inputs since we don't use any

# Check if the tool name is "generate_missions"
if tool_name == "generate_missions":
    # Call the function with the tool creator as an argument
    gen_mission_result = generate_missions()
# Now we add these as context to the LLM through initial messages!
initial_messages.append({"role": "assistant", "content": gen_mission_result})

initial_messages.append(
    {
        "role": "user",
        "content": "Based on these, which location should take priority and why?",
    }
)
# And now to get a response!
response = client.messages.create(
    max_tokens=5000,
    model="claude-3-7-sonnet-20250219",
    tools=[
        {
            "name": "generate_missions",
            "description": "Retrieve three missions for the DoomSlayer",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        }
    ],
    messages=initial_messages,
)

print(response)
# Isolate again!
message = response.content[0].text
print(message)
# Hmmm, what if we wanted to include more tools and add inputs? Let's create two new functions to display this!
#
# One will show the kind of demon we are facing, whereas another one will take our weapon input to determine what the best weapon chain to use is (You heard that right, we believe in quick weapon switches around these parts)
demons = [
    {
        "Name": "Imp",
        "Description": "A fast, agile demon that hurls fireballs and uses its claws to tear apart its prey. Imps are commonly found in Hell’s army, notorious for their quickness and ability to climb walls, making them dangerous adversaries in any environment.",
    },
    {
        "Name": "Cacodemon",
        "Description": "A floating, spherical demon with a large mouth full of teeth and an ability to launch explosive projectiles. Cacodemons are often encountered in open areas, where their aerial agility and relentless attacks pose a constant threat.",
    },
    {
        "Name": "Hell Knight",
        "Description": "A towering, brutish demon with immense strength and durability. The Hell Knight is capable of charging at the Doom Slayer and delivering devastating melee attacks. Its tough hide makes it resistant to most forms of damage.",
    },
    {
        "Name": "Mancubus",
        "Description": "A grotesque, overweight demon that releases powerful fireballs from its massive arm cannons. Mancubus demons are slow-moving but dangerous due to their firepower and the ability to overwhelm enemies with their fiery onslaughts.",
    },
]


weapons = [
    {
        "Name": "Super Shotgun",
        "Description": "A powerful, double-barreled shotgun that delivers devastating close-range damage. Known for its sheer stopping power, the Super Shotgun can tear through enemies with ease, especially when equipped with the Meat Hook attachment, allowing for rapid mobility and devastating hits.",
    },
    {
        "Name": "Rocket Launcher",
        "Description": "A high-powered weapon that fires explosive rockets capable of dealing massive area damage. The Rocket Launcher is invaluable for taking down groups of enemies or dealing significant damage to larger demons, especially when upgraded with the Lock-On Burst mod.",
    },
    {
        "Name": "Chaingun",
        "Description": "A rapid-fire weapon that can unleash a torrent of bullets at a high rate of speed. The Chaingun is perfect for mowing down enemies and can be equipped with the Heat Blast mod, allowing for explosive energy rounds that can clear multiple enemies at once.",
    },
    {
        "Name": "BFG 9000",
        "Description": "One of the most iconic weapons in the *Doom* franchise, the BFG 9000 fires a massive energy beam that obliterates anything in its path. With its massive damage potential, the BFG 9000 is a game-changer, especially in dealing with large groups of enemies or the toughest foes.",
    },
    {
        "Name": "Ice Bomb",
        "Description": "A special grenade that freezes enemies in a wide area, giving the Doom Slayer a chance to deal with multiple foes at once. The Ice Bomb is effective for crowd control, allowing for easy Glory Kills or creating distance from overwhelming enemies.",
    },
]
# Now we can keep the initialmessages from before actually! However let's change the context
initial_messages.append(
    {
        "role": "user",
        "content": "The first priority mission was selected. At the same time, scan for enemies and check inventory to determine the best combat strategy. You should use both tools at once.",
    }
)


# And we of course make functions
def enemyscan(amount):
    enemiesonscene = []
    loop = 0

    while loop < amount + 1:
        scannedenemy = random.choice(demons)

        # Append just the name of the demon to the list
        enemiesonscene.append(scannedenemy["Name"])
        enemiesonscene.append(scannedenemy["Description"])
        loop += 1

    # Combine all mission strings into a single string with a separator (e.g., newline or comma)
    enemies_string = "\\n".join(enemiesonscene)
    print(enemies_string)
    return enemies_string


enemyscan(5)


# And now inventory
def inventoryscan():
    weapons_at_hand = []
    loop = 0

    while loop < 5:
        weapon = random.choice(weapons)

        # Append just the name of the demon to the list
        weapons_at_hand.append(weapon["Name"])
        weapons_at_hand.append(weapon["Description"])
        loop += 1

    # Combine all mission strings into a single string with a separator (e.g., newline or comma)
    weapons_string = "\\n".join(weapons_at_hand)
    print(weapons_string)
    return weapons_string


inventoryscan()
# With that, let's construct our new tools and run this!!
response = client.messages.create(
    max_tokens=5000,
    model="claude-3-7-sonnet-20250219",
    tools=[
        {
            "name": "enemyscan_tool",
            "description": "Retrieve a list of demons currently present in the area.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "integer",
                        "description": "Number of enemies to scan.",
                    }
                },
                "required": ["amount"],
            },
        },
        {
            "name": "inventoryscan_tool",
            "description": "Retrieve a list of weapons the Doom Slayer has at hand.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ],
    messages=initial_messages,
)

print(response)
# Display just the text
message = response.content[0].text
print(message)
initial_messages.append({"role": "assistant", "content": f"{str(response.content[0].text)}"})
# And now to get the information and put it all together! PLEASE read the comments!
inv_scan_res = ""
enemy_scan_res = ""


response_str = str(response)
tool_use_count = response_str.count(
    "ToolUseBlock"
)  # We know the ToolUseBlock will appear once for each tool request so we check how many time it appears


# You can use print(tool_use_count)to validate the ToolBlocks here if you wish

loop = 0

# We do this instead of a (foreach) because we need to skip the first block! This contains the message from the AI, not the tool! This way allows us to reference the item we want as easily as possible without complex logic needed!

while loop < tool_use_count:  # We will get the tools now
    tool_use_block = response.content[loop + 1]  # We start at 1 since 0 holds the AI mesage
    tool_name = tool_use_block.name
    tool_input = tool_use_block.input

    if tool_name == "inventoryscan_tool":
        # Call the inventoryscan function for inventoryscan_tool
        inv_scan_res = inventoryscan()
    elif tool_name == "enemyscan_tool":
        # Get the amount for enemyscan_tool
        amount = tool_input["amount"]
        # Call the enemyscan function with the amount
        enemy_scan_res = enemyscan(amount)

    loop = loop + 1
print(inv_scan_res)
print(enemy_scan_res)
# And now we are basically done! We can give this to th AI and see what we get
initial_messages.append(
    {
        "role": "assistant",
        "content": f"Weapons Inventory Scan Result: {inv_scan_res}\\nEnemy Scans Result: {enemy_scan_res}",
    }
)


initial_messages.append(
    {
        "role": "user",
        "content": "What is the combat plan for killing these demons? Based on the last message, tell me which demons to kill first, in which order and using which weapons as well as any sweakpoints.",
    }
)
response = client.messages.create(
    max_tokens=5000,
    model="claude-3-7-sonnet-20250219",
    tools=[
        {
            "name": "enemyscan_tool",
            "description": "Retrieve a list of demons currently present in the area.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "integer",
                        "description": "Number of enemies to scan.",
                    }
                },
                "required": ["amount"],
            },
        },
        {
            "name": "inventoryscan_tool",
            "description": "Retrieve a list of weapons the Doom Slayer has at hand.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ],
    messages=initial_messages,
)

message = response.content[0].text
print(message)


# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=None)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise

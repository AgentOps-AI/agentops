from openai import OpenAI, AsyncOpenAI
import openai
from openai.resources.chat import completions
import agentops
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

agentops.init(default_tags=["TTD Test", openai.__version__])

try:
    chat_completion_1 = client.chat.completions.create(
        messages=[
            {
                "content": "Come up with a random superpower that isn't time travel. Just return the superpower in the format: 'Superpower: [superpower]'",
                "role": "user",
            }
        ],
        model="gpt-3.5-turbo-0125",
    )
    content1 = chat_completion_1.choices[0].message.content
    print(content1)
    superpower = content1.split("Superpower:")[1].strip()

    chat_completion_2 = client.chat.completions.create(
        messages=[
            {
                "content": "Come up with a superhero name given this superpower: "
                + superpower
                + ". Just return the superhero name in this format: 'Superhero: [superhero name]'",
                "role": "user",
            }
        ],
        model="gpt-3.5-turbo-0125",
    )
    content2 = chat_completion_2.choices[0].message.content
    print(content2)
    superhero = content2.split("Superhero:")[1].strip()

    chat_completion_3 = client.chat.completions.create(
        messages=[
            {
                "content": "Come up with a fictional city for superhero "
                + superhero
                + ". Just return the city name in this format: 'City: [city name]'",
                "role": "user",
            }
        ],
        model="gpt-3.5-turbo-0125",
    )
    content3 = chat_completion_3.choices[0].message.content
    print(content3)
    city = content3.split("City:")[1].strip()

    chat_completion_4 = client.chat.completions.create(
        messages=[
            {
                "content": "Come up with a weakness for superhero "
                + superhero
                + " with superpower "
                + superpower
                + ". Just return the weakness in this format: 'Weakness: [weakness]'",
                "role": "user",
            }
        ],
        model="gpt-3.5-turbo-0125",
    )
    content4 = chat_completion_4.choices[0].message.content
    print(content4)
    weakness = content4.split("Weakness:")[1].strip()

    chat_completion_5 = client.chat.completions.create(
        messages=[
            {
                "content": "Come up with the superpower of superhero "
                + superhero
                + "'s arch nemesis. The superpower cannot be time travel. Just return the superpower in the format: 'Superpower: [superpower]'",
                "role": "user",
            }
        ],
        model="gpt-3.5-turbo-0125",
    )
    content5 = chat_completion_5.choices[0].message.content
    print(content5)
    arch_nemesis_superpower = content5.split("Superpower:")[1].strip()

    chat_completion_6 = client.chat.completions.create(
        messages=[
            {
                "content": "Given the following superpower of a supervillain - "
                + arch_nemesis_superpower
                + " - come up with the supervillain's name. Just return the supervillain's name in this format 'Supervillain: [supervillain name]'",
                "role": "user",
            }
        ],
        model="gpt-3.5-turbo-0125",
    )
    content6 = chat_completion_6.choices[0].message.content
    print(content6)
    supervillain = content6.split("Supervillain:")[1].strip()

    chat_completion_7 = client.chat.completions.create(
        messages=[
            {
                "content": "Write a 100 word superhero story about the feud between superhero "
                + superhero
                + " and his arch nemesis "
                + supervillain
                + " set in "
                + city
                + ". "
                + superhero
                + "'s superpower is "
                + superpower
                + " and his weakness is "
                + weakness
                + "."
                + supervillain
                + "'s superpower is "
                + arch_nemesis_superpower
                + ".",
                "role": "user",
            }
        ],
        model="gpt-3.5-turbo-0125",
    )
    content7 = chat_completion_7.choices[0].message.content
    print(content7)

    agentops.end_session("Success")

# TODO: This just fails more gracefully for the demo but might wanna refactor so split/strip don't except
except (IndexError, AttributeError) as e:
    agentops.logger.warning(f"An error occurred: {e}")
    agentops.end_session("Fail")

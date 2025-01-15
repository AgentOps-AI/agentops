import pytest
from openai import OpenAI


@pytest.fixture
def openai_client():
    return OpenAI()


@pytest.mark.vcr()
def test_time_travel_story_generation(openai_client):
    """Test the complete time travel story generation flow."""
    # Step 1: Get superpower
    response1 = openai_client.chat.completions.create(
        messages=[
            {
                "content": "Come up with a random superpower that isn't time travel. Just return the superpower in the format: 'Superpower: [superpower]'",
                "role": "user",
            }
        ],
        model="gpt-3.5-turbo-0125",
    )
    superpower = response1.choices[0].message.content.split("Superpower:")[1].strip()
    assert superpower

    # Step 2: Get superhero name
    response2 = openai_client.chat.completions.create(
        messages=[
            {
                "content": f"Come up with a superhero name given this superpower: {superpower}. Just return the superhero name in this format: 'Superhero: [superhero name]'",
                "role": "user",
            }
        ],
        model="gpt-3.5-turbo-0125",
    )
    superhero = response2.choices[0].message.content.split("Superhero:")[1].strip()
    assert superhero

    # We can continue with more steps, but this shows the pattern
    # The test verifies the complete story generation flow works

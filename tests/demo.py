import openai
import os
from typing import Dict, List
from dotenv import load_dotenv
import json
import requests

# import agentops

load_dotenv()

# agentops.init()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


# @agentops.record_tool(tool_name="get_weather")
def get_weather(city: str) -> Dict:
    """Get current weather data for a city."""
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": WEATHER_API_KEY, "units": "metric"}  # For Celsius

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": f"Failed to get weather data: {str(e)}"}


def get_initial_itinerary(destination: str) -> Dict:
    """Generate initial travel itinerary using OpenAI."""
    prompt = f"""Create a 3-day travel itinerary for {destination}. 
    Return the response as a JSON object with the following structure:
    {{
        "day1": {{
            "activities": [],
            "restaurants": [],
            "attractions": []
        }},
        "day2": {{
            "activities": [],
            "restaurants": [],
            "attractions": []
        }},
        "day3": {{
            "activities": [],
            "restaurants": [],
            "attractions": []
        }}
    }}"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful travel planner. Always respond with valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},  # Ensure JSON response
    )

    return response.choices[0].message.content


def modify_itinerary(current_itinerary: str, modifications: str) -> Dict:
    """Modify the existing itinerary based on user requests."""
    prompt = f"""Given this current itinerary:

    {current_itinerary}

    Please modify it according to these requests:
    {modifications}

    Return the modified itinerary in the same JSON format as the original."""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful travel planner. Always respond with valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},  # Ensure JSON response
    )

    return response.choices[0].message.content


def main():
    # Get initial destination
    while True:
        destination = input("\nWhere would you like to travel? (or 'quit' to exit): ")

        if destination.lower() == "quit":
            print("\nGoodbye!")
            agentops.end_session("User quit")
            break

        # Get and display weather
        print("\nFetching current weather...")
        weather_data = get_weather(destination)
        print("\nCurrent Weather:")
        print(json.dumps(weather_data, indent=2))

        # Generate initial itinerary
        print("\nGenerating your itinerary...")
        itinerary = get_initial_itinerary(destination)
        print("\nHere's your initial itinerary:")
        print(json.dumps(itinerary, indent=2))  # Pretty print JSON

        # Allow for modifications in a continuous loop
        while True:
            modify = input(
                "\nWould you like to make any changes to this itinerary? (yes/no/new): "
            )
            if modify.lower() == "no":
                break
            elif modify.lower() == "new":
                break  # This will break inner loop and return to destination prompt

            changes = input(
                "\nWhat changes would you like to make? (e.g., 'add more museums', 'make it more budget-friendly'): "
            )
            print("\nUpdating your itinerary...")
            itinerary = modify_itinerary(itinerary, changes)
            print("\nHere's your updated itinerary:")
            print(json.dumps(itinerary, indent=2))  # Pretty print JSON

        if modify.lower() == "no":
            print("\nEnjoy your trip!")
            print("\n" + "=" * 50 + "\n")  # Separator between iterations


if __name__ == "__main__":
    main()

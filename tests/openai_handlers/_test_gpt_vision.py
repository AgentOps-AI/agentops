import requests
import base64
from openai import OpenAI
import openai
from dotenv import load_dotenv
import os
import agentops
load_dotenv()

client = OpenAI()
agentops.init(tags=['vision test', openai.__version__])

response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[
        {
          "role": "user",
          "content": [
              {"type": "text", "text": "What’s in this image?"},
              {
                  "type": "image_url",
                  "image_url": {
                      "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
                  },
              },
          ],
        }
    ],
    max_tokens=300,
)

print(response.choices[0])


# OpenAI API Key
api_key = os.environ['OPENAI_API_KEY']

# Function to encode the image


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


# Path to your image
image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo_for_vision_test.png')

# Getting the base64 string
base64_image = encode_image(image_path)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

payload = {
    "model": "gpt-4-turbo",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What’s in this image?"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
        }
    ],
    "max_tokens": 300
}

response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

print(response.json())

response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[
        {
          "role": "user",
          "content": [
              {
                  "type": "text",
                  "text": "What are in these images? Is there any difference between them?",
              },
              {
                  "type": "image_url",
                  "image_url": {
                      "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
                  },
              },
              {
                  "type": "image_url",
                  "image_url": {
                      "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
                  },
              },
          ],
        }
    ],
    max_tokens=300,
)
print(response.choices[0])

response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[
        {
          "role": "user",
          "content": [
              {"type": "text", "text": "What’s in this image?"},
              {
                  "type": "image_url",
                  "image_url": {
                      "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
                      "detail": "high"
                  },
              },
          ],
        }
    ],
    max_tokens=300,
)

print(response.choices[0].message.content)


agentops.end_session('Success')

import agentops
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv
from agentops import ActionEvent
from openai import OpenAI

load_dotenv()

openai = OpenAI()
agentops.init()
app = FastAPI()


@app.get("/completion")
def completion():

    session = agentops.start_session(tags=["api-server-test"])

    messages = [{"role": "user", "content": "Hello"}]
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.5,
    )

    session.record(
        ActionEvent(
            action_type="Agent says hello",
            params=messages,
            returns=str(response.choices[0].message.content),
        ),
    )

    session.end_session(end_state="Success")

    return {"response": response}


uvicorn.run(app, host="0.0.0.0", port=9696)

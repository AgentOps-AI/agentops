import agentops
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv
from agentops import record_tool
from openai import OpenAI
import time

load_dotenv()

openai = OpenAI()
agentops.init(auto_start_session=False)
app = FastAPI()


@app.get("/completion")
def completion():
    start_time = time.time()

    session = agentops.start_session(tags=["api-server-test"])

    @record_tool(tool_name="foo")
    def foo(x: str):
        print(x)

    foo("Hello")

    session.end_session(end_state="Success")

    end_time = time.time()
    execution_time = end_time - start_time

    return {"response": "Done", "execution_time_seconds": round(execution_time, 3)}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

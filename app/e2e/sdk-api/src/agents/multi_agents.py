from agentops.agent import track_agent
from agentops.event import ErrorEvent
from agentops import record_function
import agentops


@track_agent(name="qa")
class QaAgent:
    async def completion(self, prompt: str, openai_client):
        res = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a qa engineer and only output python code, no markdown tags.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
        )
        return res.choices[0].message.content

    def record_error(self):
        agentops.record(ErrorEvent(details="Test error"))

    @record_function(event_name="add_two_record_action")
    def record_action(self, a: int, b: int):
        return a + b


@track_agent(name="engineer")
class EngineerAgent:
    async def completion(self, prompt: str, openai_client):
        res = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a "
                    "software "
                    "engineer and "
                    "only output "
                    "python code, "
                    "no markdown "
                    "tags.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
        )
        return res.choices[0].message.content

import unittest
from dotenv import load_dotenv
from supabase import Supabase
import os
from constants import Project
import agentops
from agents.multi_agents import QaAgent, EngineerAgent
from openai import AsyncOpenAI
import openai
import time

load_dotenv()


class E2ETests(unittest.IsolatedAsyncioTestCase):

    qa = None
    engineer = None
    db = None

    @classmethod
    def setUpClass(cls):
        # Connect to testing db
        supabase_url: str = os.environ.get("SUPABASE_URL")
        supabase_key: str = os.environ.get("SUPABASE_KEY")
        cls.db = Supabase(supabase_url, supabase_key)
        cls.client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        agentops.init(
            api_key=Project.API_KEY,
            endpoint="http://0.0.0.0:8000",
            tags=["test agent", openai.__version__],
            auto_start_session=False,
        )

    @classmethod
    def setUp(cls):
        agentops.start_session()
        cls.qa = QaAgent()
        cls.engineer = EngineerAgent()

    @classmethod
    async def asyncTearDown(cls):
        agentops.end_session("Success")
        await cls.db.delete("sessions", "project_id", Project.ID)

    async def test_single_completion(self):
        await self.engineer.completion(
            "write a python function that adds two numbers together", self.client
        )

        time.sleep(2)

        llm_calls = await self.db.get(
            "llms", "id", "agent_id", getattr(self.engineer, "agent_ops_agent_id")
        )
        self.assertIsNotNone(llm_calls)

    async def test_record_agent_error(self):
        self.qa.record_error()

        time.sleep(2)
        sessions = await self.db.get("sessions", "id", "project_id", Project.ID)
        errors = await self.db.get("errors", "id", "session_id", sessions[0].get("id"))
        self.assertIsNotNone(errors)

    async def test_record_agent_action(self):
        self.qa.record_action(1, 2)

        time.sleep(2)

        actions = await self.db.get(
            "actions", "id", "agent_id", getattr(self.engineer, "agent_ops_agent_id")
        )
        self.assertIsNotNone(actions)


if __name__ == "__main__":
    unittest.main()

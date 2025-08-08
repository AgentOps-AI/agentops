import unittest
from dotenv import load_dotenv
from supabase import Supabase
import os
import time
from agents.basic_agent import BasicAgent
from constants import Project

load_dotenv()


class E2ETests(unittest.IsolatedAsyncioTestCase):

    agent = None
    db = None

    @classmethod
    def setUp(self):
        # Connect to testing db
        supabase_url: str = os.environ.get("SUPABASE_URL")
        supabase_key: str = os.environ.get("SUPABASE_KEY")
        self.db = Supabase(supabase_url, supabase_key)

        # create test agent
        self.agent = BasicAgent()
        self.agent.start_session()

    @classmethod
    async def asyncTearDown(self):
        self.agent.end_session()
        await self.db.delete("sessions", "project_id", Project.ID)

    async def test_completion(self):
        await self.agent.async_chat_completion()
        time.sleep(2)
        sessions = await self.db.get("sessions", "id", "project_id", Project.ID)
        llm_calls = await self.db.get("llms", "*", "session_id", sessions[0].get("id"))

        self.assertEqual(
            llm_calls[0].get("prompt").get("messages")[0].get("content"),
            "Say this is an async test",
        )
        self.assertIsNotNone(sessions[0].get("id"))

    async def test_stream_completion(self):
        await self.agent.async_chat_completion_stream()
        time.sleep(2)
        sessions = await self.db.get("sessions", "id", "project_id", Project.ID)
        llm_calls = await self.db.get("llms", "*", "session_id", sessions[0].get("id"))

        self.assertEqual(
            llm_calls[0].get("prompt").get("messages")[0].get("content"),
            "Say this is an async stream test",
        )
        self.assertIsNotNone(sessions[0].get("id"))


if __name__ == "__main__":
    unittest.main()

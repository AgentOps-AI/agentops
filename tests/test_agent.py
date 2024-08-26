from unittest import TestCase

from agentops import track_agent
import agentops


class TrackAgentTests(TestCase):
    def test_track_agent_with_class(self):
        agentops.init()

        @track_agent(name="agent_name")
        class TestAgentClass:
            t = "a"
            pass

        obj = TestAgentClass()
        self.assertTrue(isinstance(obj, TestAgentClass))
        self.assertEqual(getattr(obj, "agent_ops_agent_name"), "agent_name")
        self.assertIsNotNone(getattr(obj, "agent_ops_agent_id"))

    def test_track_agent_with_class_name(self):
        agentops.init()

        @track_agent(name="agent_name")
        class TestAgentClass:
            t = "a"
            pass

        obj = TestAgentClass(agentops_name="agent1")
        self.assertTrue(isinstance(obj, TestAgentClass))
        self.assertEqual(getattr(obj, "agent_ops_agent_name"), "agent1")
        self.assertIsNotNone(getattr(obj, "agent_ops_agent_id"))

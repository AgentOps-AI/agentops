from unittest import TestCase

import pytest

from agentops import track_agent


class TrackAgentTests(TestCase):
    def test_track_agent_with_class(self):
        @track_agent(name="agent_name")
        class TestAgentClass:
            t = "a"
            pass

        obj = TestAgentClass()
        self.assertTrue(isinstance(obj, TestAgentClass))
        self.assertEqual(getattr(obj, "agent_ops_agent_name"), "agent_name")
        self.assertIsNotNone(getattr(obj, "agent_ops_agent_id"))

    def test_track_agent_with_class_name(self):
        @track_agent(name="agent_name")
        class TestAgentClass:
            t = "a"
            pass

        obj = TestAgentClass(agentops_name="agent1")
        self.assertTrue(isinstance(obj, TestAgentClass))
        self.assertEqual(getattr(obj, "agent_ops_agent_name"), "agent1")
        self.assertIsNotNone(getattr(obj, "agent_ops_agent_id"))


from uuid import uuid4

from agentops.helpers import AgentOpsDescriptor, check_call_stack_for_agent_id


class TestAgentOpsDescriptor(TestCase):
    def test_agent_property_get_set(self):
        """Test basic get/set functionality of AgentOpsDescriptor"""

        class TestAgent:
            agent_id = AgentOpsDescriptor("agent_id")
            agent_name = AgentOpsDescriptor("agent_name")

        agent = TestAgent()
        test_id = str(uuid4())
        test_name = "TestAgent"

        # Test setting values
        agent._agentops_agent_id = test_id
        agent._agentops_agent_name = test_name

        # Test getting values
        assert agent.agent_id == test_id
        assert agent.agent_name == test_name

        # Test getting non-existent value returns None
        assert TestAgent().agent_id is None

    @pytest.mark.skip(reason="Not planned")
    def test_check_call_stack_agent_detection(self):
        """Test that check_call_stack_for_agent_id correctly identifies agents"""

        class TestAgent:
            agent_ops_agent_id = AgentOpsDescriptor("agent_id")
            agent_ops_agent_name = AgentOpsDescriptor("agent_name")

            def __init__(self):
                self._agentops_agent_id = str(uuid4())
                self._agentops_agent_name = "TestAgent"

            def get_my_id(self):
                # Make self visible in locals()
                agent = self
                return check_call_stack_for_agent_id()

        agent = TestAgent()
        detected_id = agent.get_my_id()
        assert detected_id == agent.agent_ops_agent_id

    @pytest.mark.skip(reason="Not planned")
    def test_check_call_stack_ignores_raw_attributes(self):
        """Test that check_call_stack_for_agent_id ignores non-descriptor attributes"""

        class FakeAgent:
            def __init__(self):
                self._agentops_agent_id = str(uuid4())
                self._agentops_agent_name = "FakeAgent"

            def get_my_id(self):
                # Make self visible in locals()
                agent = self
                return check_call_stack_for_agent_id()

        fake_agent = FakeAgent()
        detected_id = fake_agent.get_my_id()

        assert detected_id is None

    @pytest.mark.skip(reason="Not planned")
    def test_check_call_stack_nested_calls(self):
        """Test that check_call_stack_for_agent_id works through nested function calls"""

        class TestAgent:
            agent_ops_agent_id = AgentOpsDescriptor("agent_id")
            agent_ops_agent_name = AgentOpsDescriptor("agent_name")

            def __init__(self):
                self._agentops_agent_id = str(uuid4())
                self._agentops_agent_name = "TestAgent"

            def nested_call_level_1(self):
                # Make self visible in locals()
                agent = self
                return self.nested_call_level_2()

            def nested_call_level_2(self):
                # Make self visible in locals()
                agent = self
                return check_call_stack_for_agent_id()

        agent = TestAgent()
        detected_id = agent.nested_call_level_1()

        assert detected_id == agent.agent_ops_agent_id

    @pytest.mark.skip(reason="Not planned")
    def test_multiple_agents_in_stack(self):
        """Test that check_call_stack_for_agent_id finds the correct agent when multiple exist"""

        class AgentA:
            agent_ops_agent_id = AgentOpsDescriptor("agent_id")
            agent_ops_agent_name = AgentOpsDescriptor("agent_name")

            def __init__(self):
                self._agentops_agent_id = str(uuid4())
                self._agentops_agent_name = "AgentA"

        class AgentB:
            agent_ops_agent_id = AgentOpsDescriptor("agent_id")
            agent_ops_agent_name = AgentOpsDescriptor("agent_name")

            def __init__(self, other_agent):
                self._agentops_agent_id = str(uuid4())
                self._agentops_agent_name = "AgentB"
                self.other = other_agent

            def check_id(self):
                # Make self visible in locals()
                agent = self
                return check_call_stack_for_agent_id()

        agent_a = AgentA()
        agent_b = AgentB(agent_a)

        detected_id = agent_b.check_id()
        assert detected_id == agent_b.agent_ops_agent_id
        assert detected_id != agent_a.agent_ops_agent_id

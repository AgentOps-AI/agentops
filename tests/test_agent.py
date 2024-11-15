from unittest import TestCase
from uuid import uuid4

from agentops import track_agent
from agentops.descriptor import agentops_property


class TrackAgentTests(TestCase):
    def test_track_agent_with_class(self):
        @track_agent(name="agent_name")
        class TestAgentClass:
            t = "a"
            pass

        obj = TestAgentClass()
        self.assertTrue(isinstance(obj, TestAgentClass))
        self.assertEqual(getattr(obj, "agentops_agent_name", None), "agent_name")
        self.assertIsNotNone(getattr(obj, "agentops_agent_id", None))

    def test_track_agent_with_class_name(self):
        @track_agent(name="agent_name")
        class TestAgentClass:
            t = "a"
            pass

        obj = TestAgentClass(agentops_name="agent1")
        self.assertTrue(isinstance(obj, TestAgentClass))
        self.assertEqual(getattr(obj, "agentops_agent_name"), "agent1")
        self.assertIsNotNone(getattr(obj, "agentops_agent_id"))


class TestAgentOpsDescriptor(TestCase):
    def test_agent_property_get_set(self):
        """Test basic get/set functionality of agentops_property"""

        class TestAgent:
            agent_id = agentops_property()
            agent_name = agentops_property()

        agent = TestAgent()
        test_id = str(uuid4())
        test_name = "TestAgent"

        # Test setting values
        agent.agent_id = test_id
        agent.agent_name = test_name

        # Test getting values
        self.assertEqual(agent.agent_id, test_id)
        self.assertEqual(agent.agent_name, test_name)

        # Test getting non-existent value returns None
        self.assertIsNone(TestAgent().agent_id)

    def test_from_stack_direct_call(self):
        """Test from_stack when called directly from a method with an agent"""

        @track_agent(name="TestAgent")
        class TestAgent:
            def get_my_id(self):
                return agentops_property.from_stack()

        agent = TestAgent()
        detected_id = agent.get_my_id()
        self.assertEqual(detected_id, agent.agentops_agent_id)

    def test_from_stack_nested_call(self):
        """Test from_stack when called through nested function calls"""

        @track_agent(name="TestAgent")
        class TestAgent:
            def get_my_id(self):
                def nested_func():
                    return agentops_property.from_stack()

                return nested_func()

        agent = TestAgent()
        detected_id = agent.get_my_id()
        self.assertEqual(detected_id, agent.agentops_agent_id)

    def test_from_stack_multiple_agents(self):
        """Test from_stack with multiple agents in different stack frames"""

        @track_agent(name="Agent1")
        class Agent1:
            def get_other_agent_id(self, other_agent):
                return other_agent.get_my_id()

        @track_agent(name="Agent2")
        class Agent2:
            def get_my_id(self):
                return agentops_property.from_stack()

        agent1 = Agent1()
        agent2 = Agent2()

        # Should return agent2's ID since it's the closest in the call stack
        detected_id = agent1.get_other_agent_id(agent2)
        self.assertEqual(detected_id, agent2.agentops_agent_id)
        self.assertNotEqual(detected_id, agent1.agentops_agent_id)

    def test_from_stack_no_agent(self):
        """Test from_stack when no agent is in the call stack"""

        class NonAgent:
            def get_id(self):
                return agentops_property.from_stack()

        non_agent = NonAgent()
        self.assertIsNone(non_agent.get_id())

    def test_from_stack_with_exception(self):
        """Test from_stack's behavior when exceptions occur during stack inspection"""

        class ProblemAgent:
            agentops_agent_id = agentops_property()

            @property
            def problematic_attr(self):
                raise Exception("Simulated error")

            def get_id(self):
                return agentops_property.from_stack()

        agent = ProblemAgent()
        # Should return None and not raise exception
        self.assertIsNone(agent.get_id())

    def test_from_stack_inheritance(self):
        """Test from_stack with inheritance hierarchy"""

        @track_agent(name="BaseAgent")
        class BaseAgent:
            def get_id_from_base(self):
                return agentops_property.from_stack()

        @track_agent(name="DerivedAgent")
        class DerivedAgent(BaseAgent):
            def get_id_from_derived(self):
                return agentops_property.from_stack()

        derived = DerivedAgent()
        base_call_id = derived.get_id_from_base()
        derived_call_id = derived.get_id_from_derived()

        self.assertEqual(base_call_id, derived.agentops_agent_id)
        self.assertEqual(derived_call_id, derived.agentops_agent_id)

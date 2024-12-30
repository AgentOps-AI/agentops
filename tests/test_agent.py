from unittest import TestCase
from uuid import uuid4
from typing import Optional

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

    def test_track_agent_with_post_init_name_assignment(self):
        """Test setting agentops_agent_name after initialization"""

        @track_agent()
        class TestAgentClass:
            def __init__(self):
                self.role = "test_role"
                # Simulate post_init behavior like in CrewAI
                self.agentops_agent_name = self.role

        obj = TestAgentClass()
        self.assertEqual(getattr(obj, "agentops_agent_name"), "test_role")
        self.assertIsNotNone(getattr(obj, "agentops_agent_id"))

    def test_track_agent_with_property_override(self):
        """Test overriding agentops properties after initialization"""

        @track_agent()
        class TestAgentClass:
            def __init__(self):
                self.role = "initial_role"
                self.agentops_agent_name = self.role

            @property
            def role(self):
                return self._role

            @role.setter
            def role(self, value):
                self._role = value
                # Update agentops_agent_name when role changes
                if hasattr(self, "agentops_agent_name"):
                    self.agentops_agent_name = value

        # Test initial setting
        obj = TestAgentClass()
        self.assertEqual(getattr(obj, "agentops_agent_name"), "initial_role")

        # Test property update
        obj.role = "updated_role"
        self.assertEqual(getattr(obj, "agentops_agent_name"), "updated_role")
        self.assertIsNotNone(getattr(obj, "agentops_agent_id"))

    def test_track_agent_with_none_values(self):
        """Test handling of None values for agentops properties"""

        @track_agent()
        class TestAgentClass:
            def __init__(self):
                self.role = None
                self.agentops_agent_name = None
                self._model_validate()

            def _model_validate(self):
                # Simulate setting name after validation
                if self.role is not None:
                    self.agentops_agent_name = self.role

        # Test initialization with None
        obj = TestAgentClass()
        self.assertIsNone(getattr(obj, "agentops_agent_name"))
        self.assertIsNotNone(getattr(obj, "agentops_agent_id"))  # ID should still be set

        # Test updating from None
        obj.role = "new_role"
        obj._model_validate()
        self.assertEqual(getattr(obj, "agentops_agent_name"), "new_role")

    def test_track_agent_with_pydantic_model(self):
        """Test setting agentops_agent_name with actual Pydantic BaseModel"""
        try:
            from typing import Optional
            from pydantic import BaseModel, Field, model_validator
        except ImportError:
            self.skipTest("Pydantic not installed, skipping Pydantic model test")

        @track_agent()
        class TestAgentModel(BaseModel):
            role: str = Field(default="test_role")
            agentops_agent_name: Optional[str] = None
            agentops_agent_id: Optional[str] = None

            @model_validator(mode="after")
            def set_agent_name(self):
                # Simulate CrewAI's post_init_setup behavior
                self.agentops_agent_name = self.role
                return self

        # Test basic initialization
        obj = TestAgentModel()
        self.assertEqual(obj.agentops_agent_name, "test_role")
        self.assertIsNotNone(obj.agentops_agent_id)

        # Test with custom role
        obj2 = TestAgentModel(role="custom_role")
        self.assertEqual(obj2.agentops_agent_name, "custom_role")
        self.assertIsNotNone(obj2.agentops_agent_id)

        # Test model update
        obj.role = "updated_role"
        obj.set_agent_name()
        self.assertEqual(obj.agentops_agent_name, "updated_role")


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
                return agentops_property.stack_lookup()

        agent = TestAgent()
        detected_id = agent.get_my_id()
        self.assertEqual(detected_id, agent.agentops_agent_id)

    def test_from_stack_nested_call(self):
        """Test from_stack when called through nested function calls"""

        @track_agent(name="TestAgent")
        class TestAgent:
            def get_my_id(self):
                def nested_func():
                    return agentops_property.stack_lookup()

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
                return agentops_property.stack_lookup()

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
                return agentops_property.stack_lookup()

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
                return agentops_property.stack_lookup()

        agent = ProblemAgent()
        # Should return None and not raise exception
        self.assertIsNone(agent.get_id())

    def test_from_stack_inheritance(self):
        """Test from_stack with inheritance hierarchy"""

        @track_agent(name="BaseAgent")
        class BaseAgent:
            def get_id_from_base(self):
                return agentops_property.stack_lookup()

        @track_agent(name="DerivedAgent")
        class DerivedAgent(BaseAgent):
            def get_id_from_derived(self):
                return agentops_property.stack_lookup()

        derived = DerivedAgent()
        base_call_id = derived.get_id_from_base()
        derived_call_id = derived.get_id_from_derived()

        self.assertEqual(base_call_id, derived.agentops_agent_id)
        self.assertEqual(derived_call_id, derived.agentops_agent_id)

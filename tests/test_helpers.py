import pytest
from agentops.helpers import cached_property


def test_cached_property():
    class TestClass:
        def __init__(self):
            self.compute_count = 0

        @cached_property
        def expensive_computation(self):
            self.compute_count += 1
            return 42

    # Create instance
    obj = TestClass()

    # First access should compute the value
    assert obj.expensive_computation == 42
    assert obj.compute_count == 1

    # Second access should use cached value
    assert obj.expensive_computation == 42
    assert obj.compute_count == 1  # Count shouldn't increase

    # Third access should still use cached value
    assert obj.expensive_computation == 42
    assert obj.compute_count == 1  # Count shouldn't increase


def test_cached_property_different_instances():
    class TestClass:
        def __init__(self):
            self.compute_count = 0

        @cached_property
        def expensive_computation(self):
            self.compute_count += 1
            return id(self)  # Return unique id for each instance

    # Create two different instances
    obj1 = TestClass()
    obj2 = TestClass()

    # Each instance should compute its own value
    val1 = obj1.expensive_computation
    val2 = obj2.expensive_computation

    assert val1 != val2  # Values should be different
    assert obj1.compute_count == 1
    assert obj2.compute_count == 1

    # Accessing again should use cached values
    assert obj1.expensive_computation == val1
    assert obj2.expensive_computation == val2
    assert obj1.compute_count == 1  # Counts shouldn't increase
    assert obj2.compute_count == 1


def test_cached_property_class_access():
    class TestClass:
        @cached_property
        def expensive_computation(self):
            return 42

    # Accessing via class should return the descriptor
    assert isinstance(TestClass.expensive_computation, cached_property)

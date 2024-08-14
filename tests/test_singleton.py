import uuid

from agentops.singleton import singleton, conditional_singleton, clear_singletons


@singleton
class SingletonClass:
    def __init__(self):
        self.id = str(uuid.uuid4())


@conditional_singleton
class ConditionalSingletonClass:
    def __init__(self):
        self.id = str(uuid.uuid4())


class TestSingleton:
    def test_singleton(self):
        c1 = SingletonClass()
        c2 = SingletonClass()

        assert c1.id == c2.id

    def test_conditional_singleton(self):
        c1 = ConditionalSingletonClass()
        c2 = ConditionalSingletonClass()
        noSingleton = ConditionalSingletonClass(use_singleton=False)

        assert c1.id == c2.id
        assert c1.id != noSingleton.id
        assert c2.id != noSingleton.id

    def test_clear_singletons(self):
        c1 = SingletonClass()
        clear_singletons()
        c2 = SingletonClass()

        assert c1.id != c2.id

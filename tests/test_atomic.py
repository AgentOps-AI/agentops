import threading
import time

import pytest

from agentops.decorators import atomic

from agentops.singleton import singleton, conditional_singleton, clear_singletons


class TestAtomicDecorator:
    def test_atomic_basic(self):
        """Test basic atomic operation"""
        counter = 0
        completed = []  # Track completed increments

        @atomic
        def increment():
            nonlocal counter
            current = counter
            threading.Event().wait(0.001)  # Simulate some work
            counter = current + 1
            completed.append(True)  # Mark completion

        threads = []
        for i in range(100):
            t = threading.Thread(target=increment, name=f"Thread-{i}")
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(completed) == 100, "Not all increments completed"
        assert counter == 100, f"Counter should be 100, got {counter}"

    def test_atomic_shared_key(self):
        """Test multiple functions sharing same lock"""
        counter = 0

        @atomic(key="shared")
        def increment1():
            nonlocal counter
            current = counter
            threading.Event().wait(0.001)
            counter = current + 1

        @atomic(key="shared")
        def increment2():
            nonlocal counter
            current = counter
            threading.Event().wait(0.001)
            counter = current + 1

        threads = []
        for _ in range(50):
            t1 = threading.Thread(target=increment1)
            t2 = threading.Thread(target=increment2)
            threads.extend([t1, t2])
            t1.start()
            t2.start()

        for t in threads:
            t.join()

        assert counter == 100

    def test_atomic_reentrant(self):
        """Test reentrant lock behavior"""

        @atomic(key="reentrant", reentrant=True)
        def outer():
            return inner()

        @atomic(key="reentrant", reentrant=True)
        def inner():
            return True

        assert outer() is True

    def test_atomic_not_reentrant(self):
        """Test non-reentrant lock behavior"""

        @atomic(key="non-reentrant")
        def outer():
            return inner()

        @atomic(key="non-reentrant")
        def inner():
            return True

        with pytest.raises(RuntimeError):
            outer()

    def test_atomic_counter_race(self):
        """Test atomic with very short delay to catch races"""
        counter = 0
        iterations = 1000

        @atomic
        def increment():
            nonlocal counter
            current = counter
            counter = current + 1  # No delay to maximize race condition chance

        threads = []
        for _ in range(iterations):
            t = threading.Thread(target=increment)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert counter == iterations, f"Counter should be {iterations}, got {counter}"

    def test_atomic_nested_locks(self):
        """Test nested locks with different keys"""
        counter = 0

        @atomic(key="outer")
        def outer():
            nonlocal counter
            counter += 1
            inner()

        @atomic(key="inner")
        def inner():
            nonlocal counter
            counter += 1

        outer()
        assert counter == 2, "Both increments should succeed with different keys"

    def test_atomic_multiple_instances(self):
        """Test multiple instances of atomic with same key"""
        counter = 0

        def create_incrementor(n):
            @atomic(key="shared_counter")
            def increment():
                nonlocal counter
                current = counter
                threading.Event().wait(0.001)
                counter = current + n

            return increment

        incrementors = [create_incrementor(i) for i in range(1, 4)]
        threads = []

        for _ in range(50):
            for inc in incrementors:
                t = threading.Thread(target=inc)
                threads.append(t)
                t.start()

        for t in threads:
            t.join()

        assert counter == 50 * sum(range(1, 4)), "Counter should reflect all increments"

    def test_atomic_exception_handling(self):
        """Test that locks are properly released when exceptions occur"""
        counter = 0

        @atomic(key="error_test")
        def might_fail(should_fail=False):
            nonlocal counter
            if should_fail:
                raise ValueError("Intentional failure")
            counter += 1

        # First call should fail
        with pytest.raises(ValueError):
            might_fail(should_fail=True)

        # Second call should succeed because lock was released
        might_fail(should_fail=False)
        assert counter == 1, "Counter should be incremented after failed attempt"

    def test_atomic_recursive_reentrant(self):
        """Test deeply nested reentrant locks"""
        counter = 0

        @atomic(key="recursive", reentrant=True)
        def recursive(depth):
            nonlocal counter
            counter += 1
            if depth > 0:
                recursive(depth - 1)

        recursive(5)
        assert counter == 6, "Should count original call plus 5 recursive calls"

    def test_atomic_mixed_reentrant(self):
        """Test mixing reentrant and non-reentrant locks"""
        counter = 0

        @atomic(key="mixed", reentrant=True)
        def reentrant_outer():
            nonlocal counter
            counter += 1
            non_reentrant_inner()

        @atomic(key="mixed")  # non-reentrant
        def non_reentrant_inner():
            nonlocal counter
            counter += 1

        with pytest.raises(RuntimeError):
            reentrant_outer()

    def test_atomic_concurrent_key_creation(self):
        """Test concurrent creation of locks with the same key"""
        results = []

        @atomic(key="concurrent")
        def append_one():
            results.append(1)
            threading.Event().wait(0.001)

        @atomic(key="concurrent")
        def append_two():
            results.append(2)
            threading.Event().wait(0.001)

        # Start many threads simultaneously to stress test lock creation
        threads = []
        for _ in range(100):
            t1 = threading.Thread(target=append_one)
            t2 = threading.Thread(target=append_two)
            threads.extend([t1, t2])
            t1.start()
            t2.start()

        for t in threads:
            t.join()

        # Verify results are in pairs (lock worked)
        for i in range(0, len(results), 2):
            assert results[i : i + 2].count(1) == 1, "Each pair should contain one '1'"
            assert results[i : i + 2].count(2) == 1, "Each pair should contain one '2'"

    def test_atomic_lock_reuse(self):
        """Test that locks are properly reused and not duplicated"""
        initial_locks = len(atomic._locks)
        lock_ids = set()  # Track unique lock object IDs

        # Create multiple decorators with the same key
        for _ in range(100):

            @atomic(key="reused_lock")
            def temp():
                pass

            temp()
            # Store the ID of the lock object
            with atomic._registry_lock:
                lock_ids.add(id(atomic._locks["reused_lock"]))

        # All decorators should have reused the same lock
        assert len(lock_ids) == 1, "Lock was not reused"
        assert len(atomic._locks) == initial_locks + 1, "Extra locks were created"

        # Clean up the test lock
        with atomic._registry_lock:
            atomic._locks.pop("reused_lock", None)

    def test_atomic_inheritance(self):
        """Test atomic works with inherited methods"""

        class Base:
            @atomic(key="inherited", reentrant=True)
            def method(self):
                return 1

        class Child(Base):
            @atomic(key="inherited", reentrant=True)
            def method(self):
                return super().method() + 1

        assert Child().method() == 2, "Should handle inherited methods"

    def test_atomic_async(self):
        """Test atomic works with async functions"""
        import asyncio

        counter = 0

        @atomic(key="async")
        async def increment():
            nonlocal counter
            await asyncio.sleep(0.001)
            counter += 1

        async def run_test():
            tasks = [increment() for _ in range(100)]
            await asyncio.gather(*tasks)

        asyncio.run(run_test())
        assert counter == 100, "Should work with async functions"

    def test_atomic_generator(self):
        """Test atomic works with generators"""
        sequence = []

        @atomic(key="generator")
        def generate_sequence(n):
            for i in range(n):
                sequence.append(i)
                yield i

        threads = []
        for _ in range(10):

            def run_generator():
                for _ in generate_sequence(5):
                    pass

            t = threading.Thread(target=run_generator)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Check sequence is properly ordered within each generator call
        for i in range(0, len(sequence), 5):
            assert sequence[i : i + 5] == list(range(5)), "Generator sequence should be ordered"

    def test_atomic_with_singleton(self):
        """Test atomic works with singleton classes"""

        @singleton
        class Counter:
            def __init__(self):
                self.value = 0

            @atomic(key="singleton_counter")
            def increment(self):
                current = self.value
                threading.Event().wait(0.001)
                self.value = current + 1

        # Create multiple instances (should be the same object)
        counter1 = Counter()
        counter2 = Counter()
        assert counter1 is counter2, "Singleton not working"

        threads = []
        for _ in range(50):
            t1 = threading.Thread(target=counter1.increment)
            t2 = threading.Thread(target=counter2.increment)
            threads.extend([t1, t2])
            t1.start()
            t2.start()

        for t in threads:
            t.join()

        assert counter1.value == 100, "Counter should be thread-safe across singleton instances"
        clear_singletons()

    def test_atomic_with_conditional_singleton(self):
        """Test atomic works with conditional singletons"""

        @conditional_singleton
        class Counter:
            def __init__(self):
                self.value = 0

            @atomic(key="conditional_counter")
            def increment(self):
                current = self.value
                threading.Event().wait(0.001)
                self.value = current + 1

        # Create singleton instance
        counter1 = Counter(use_singleton=True)
        counter2 = Counter(use_singleton=True)
        assert counter1 is counter2, "Conditional singleton (True) not working"

        # Create separate instances
        counter3 = Counter(use_singleton=False)
        counter4 = Counter(use_singleton=False)
        assert counter3 is not counter4, "Conditional singleton (False) not working"

        threads = []
        for _ in range(50):
            t1 = threading.Thread(target=counter1.increment)
            t2 = threading.Thread(target=counter2.increment)
            t3 = threading.Thread(target=counter3.increment)
            t4 = threading.Thread(target=counter4.increment)
            threads.extend([t1, t2, t3, t4])
            for t in [t1, t2, t3, t4]:
                t.start()

        for t in threads:
            t.join()

        assert counter1.value == 100, "Counter should be thread-safe across singleton instances"
        assert counter3.value == 50, "Separate instance should have its own count"
        assert counter4.value == 50, "Separate instance should have its own count"
        clear_singletons()

    def test_atomic_with_class_instances(self):
        """Test atomic behavior across different instances of the same class"""

        class Counter:
            def __init__(self):
                self.value = 0
                self._id = id(self)  # Use object id as unique identifier

            @atomic(key=lambda self: f"instance_counter_{id(self)}")
            def increment(self):
                current = self.value
                threading.Event().wait(0.001)
                self.value = current + 1

            @atomic(key="shared_counter")
            def increment_shared(self):
                current = self.value
                threading.Event().wait(0.001)
                self.value = current + 1

        # Create separate instances
        counter1 = Counter()
        counter2 = Counter()

        threads = []
        # Test instance-specific locks
        for _ in range(50):
            t1 = threading.Thread(target=counter1.increment)
            t2 = threading.Thread(target=counter2.increment)
            threads.extend([t1, t2])
            t1.start()
            t2.start()

        # Test shared lock
        for _ in range(50):
            t1 = threading.Thread(target=counter1.increment_shared)
            t2 = threading.Thread(target=counter2.increment_shared)
            threads.extend([t1, t2])
            t1.start()
            t2.start()

        for t in threads:
            t.join()

        assert counter1.value == 100, "Counter1 should have its own count"
        assert counter2.value == 100, "Counter2 should have its own count"

import unittest
import sys
import os

# Add the parent directory to the path so we can import the test modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import all test modules
from test_traced import TestTracedObject
from test_spanned import TestSpannedBase
from test_factory import TestSpanFactory
from test_core import TestTracingCore, TestImmediateExportProcessor
from test_spans import TestSessionSpan, TestAgentSpan, TestToolSpan, TestLLMSpan, TestCustomSpan
from test_decorators import TestSessionDecorator, TestAgentDecorator, TestToolDecorator, TestLLMDecorator
from test_integration import TestIntegration

if __name__ == "__main__":
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add all test cases
    test_suite.addTest(unittest.makeSuite(TestTracedObject))
    test_suite.addTest(unittest.makeSuite(TestSpannedBase))
    test_suite.addTest(unittest.makeSuite(TestSpanFactory))
    test_suite.addTest(unittest.makeSuite(TestTracingCore))
    test_suite.addTest(unittest.makeSuite(TestImmediateExportProcessor))
    test_suite.addTest(unittest.makeSuite(TestSessionSpan))
    test_suite.addTest(unittest.makeSuite(TestAgentSpan))
    test_suite.addTest(unittest.makeSuite(TestToolSpan))
    test_suite.addTest(unittest.makeSuite(TestLLMSpan))
    test_suite.addTest(unittest.makeSuite(TestCustomSpan))
    test_suite.addTest(unittest.makeSuite(TestSessionDecorator))
    test_suite.addTest(unittest.makeSuite(TestAgentDecorator))
    test_suite.addTest(unittest.makeSuite(TestToolDecorator))
    test_suite.addTest(unittest.makeSuite(TestLLMDecorator))
    test_suite.addTest(unittest.makeSuite(TestIntegration))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with non-zero code if tests failed
    sys.exit(not result.wasSuccessful()) 
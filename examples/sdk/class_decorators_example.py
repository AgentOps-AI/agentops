"""
Example showing how to use AgentOps class decorators.

This demonstrates how to use the session_class and agent_class decorators
to instrument methods in classes.
"""

import time
import random
import agentops
from agentops.sdk.decorators.agentops import session_class, agent_class

# Initialize AgentOps
agentops.init()


# Example agent class with the agent_class decorator
@agent_class(method_name="process", name="text_processor")
class TextProcessor:
    """A class that processes text, with its process method tracked as an agent."""
    
    def __init__(self, language="english"):
        self.language = language
        self.initialized = True
        print(f"TextProcessor initialized with language: {language}")
    
    def process(self, text):
        """Process the input text and return a result."""
        print(f"Processing text in {self.language}: {text}")
        # Simulate processing
        time.sleep(0.5)
        result = f"[{self.language.upper()}] {text.upper()}"
        print(f"Processing result: {result}")
        return result
    
    def validate(self, text):
        """This method isn't decorated by agent_class."""
        valid = len(text) > 0
        print(f"Text validation result: {'valid' if valid else 'invalid'}")
        return valid


# Example session class with the session_class decorator
@session_class(method_name="run", name="workflow_runner")
class WorkflowRunner:
    """A class that runs workflows, with its run method tracked as a session."""
    
    def __init__(self, name):
        self.name = name
        self.steps_completed = 0
        print(f"WorkflowRunner '{name}' initialized")
    
    def run(self, steps):
        """Run the workflow with the given steps."""
        print(f"Starting workflow '{self.name}' with {len(steps)} steps")
        results = []
        
        for i, step in enumerate(steps):
            print(f"Running step {i+1}: {step}")
            # Simulate work
            time.sleep(0.3)
            result = f"Step {i+1} result: {step} completed"
            results.append(result)
            self.steps_completed += 1
        
        print(f"Workflow '{self.name}' completed with {self.steps_completed} steps")
        return results
    
    def reset(self):
        """This method isn't decorated by session_class."""
        self.steps_completed = 0
        print(f"Workflow '{self.name}' reset")


if __name__ == "__main__":
    print("Starting class decorators example")
    
    # Create and use the TextProcessor
    processor = TextProcessor(language="spanish")
    text = "Hello, world!"
    processed_text = processor.process(text)
    
    # Create and use the WorkflowRunner
    workflow = WorkflowRunner(name="data_pipeline")
    steps = [
        "Load data",
        "Clean data",
        "Transform data",
        "Save results"
    ]
    workflow_results = workflow.run(steps)
    
    print("Example complete") 
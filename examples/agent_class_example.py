import agentops
from agentops.sdk.decorators import session, agent

# Initialize AgentOps
agentops.init(api_key="your_api_key_here")

# Create a session class
@session(name="AgentWorkflow")
class AgentWorkflow:
    def __init__(self, workflow_name):
        self.workflow_name = workflow_name
        print(f"Initialized workflow: {workflow_name}")
    
    def run(self):
        print(f"Running workflow: {self.workflow_name}")
        
        # Create and use the agent
        qa_agent = QuestionAnsweringAgent()
        result = qa_agent.answer("What is the capital of France?")
        
        return f"Workflow result: {result}"

# Create an agent class
@agent(name="QAAgent", agent_type="question_answering")
class QuestionAnsweringAgent:
    def __init__(self):
        self.knowledge_base = {
            "france": "Paris",
            "germany": "Berlin",
            "japan": "Tokyo",
            "australia": "Canberra"
        }
        print("QA Agent initialized with knowledge base")
    
    def answer(self, question):
        print(f"Agent processing: {question}")
        
        # Simple parsing logic
        for country, capital in self.knowledge_base.items():
            if country in question.lower():
                return f"The capital of {country.capitalize()} is {capital}."
        
        return "I don't know the answer to that question."
    
    def get_agent_info(self):
        # Access the agent span that was automatically created
        agent_span = self.get_agent_span()
        return f"Agent ID: {agent_span.span.get_span_context().span_id}"

# Create and run the workflow
workflow = AgentWorkflow("Capital Cities")
result = workflow.run()
print(result) 
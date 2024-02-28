class Tool(Event):
    def __init__(self, session_id: str, agent_id: str, name: str, inputs: str, outputs: str, logs: str, ...):
        super().__init__(event_type='tools')
        self.session_id = session_id
        self.agent_id = agent_id
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        self.logs = logs
        ...
    
    def __str__(self):
        return str({**super().__str__(), "session_id": self.session_id, "agent_id": self.agent_id, "name": self.name, ...})

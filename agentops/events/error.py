class Error(Event):
    def __init__(self, session_id: str, event_id: int, event_type: str, type: str, code: str, details: str, logs: str, ...):
        super().__init__(event_type='errors', result='Fail')
        self.session_id = session_id
        self.event_id = event_id
        self.error_type = type
        self.code = code
        self.details = details
        self.logs = logs
        ...
    
    def __str__(self):
        return str({**super().__str__(), "session_id": self.session_id, "event_id": self.event_id, "type": self.error_type, ...})

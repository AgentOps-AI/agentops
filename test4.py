import agentops

agentops.init(auto_start_session=False)


agentops.start_session()


from agentops.event import ActionEvent, Event

ActionEvent(action_type="test", logs="test", screenshot="test", params={"test": "test"})

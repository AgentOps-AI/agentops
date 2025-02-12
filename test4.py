import agentops

agentops.init(auto_start_session=False)


agentops.start_session()


from agentops.event import ActionEvent, Event

event = ActionEvent(
    action_type="test", logs="test", screenshot="test", params={"test": "test"}, init_timestamp="2021-08-19T15:00:00Z"
)


breakpoint()

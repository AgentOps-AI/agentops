import pytest

import agentops
from agentops.client import Client
from agentops.session.session import Session

#
#
# class TestSessionRequiresInitialization:
#
#
#     # @pytest.mark.config_kwargs(auto_init=False)
#     def test_session_requires_initialization(self):
#         # require client .init() to be called before session.start()
#         client = Client()
#         assert not client.initialized, "CLIENT IS NOT SUPPOSED TO BE INITIALIZED"
#         with pytest.raises(Exception):
#             agentops.start_session()
#         client.init()
#         assert isinstance(agentops.start_session(), Session)

pytestmark = [pytest.mark.usefixture("noinstrument")]


class TestSessionStart:
    def test_session_start(self, agentops_config):
        session = agentops.start_session()
        assert session is not None

    def test_session_start_with_tags(self, agentops_config):
        """Test that start_session with tags returns a session directly, not a partial"""
        test_tags = ["test1", "test2"]
        session = agentops.start_session(tags=test_tags)
        assert isinstance(session, Session), "start_session with tags should return a Session instance"
        assert session is not None, "Session should not be None"
        assert session.tags == test_tags

    def test_init_timestamp(self, agentops_session):
        assert agentops_session.init_timestamp is not None, "Session.init_timestamp should be set"


class TestSessionEncoding:
    @pytest.mark.session_kwargs(auto_start=False)
    def test_dict(self, agentops_session):
        """Test that asdict works with Session objects"""
        assert isinstance(agentops_session.dict(), dict)

    @pytest.mark.session_kwargs(auto_start=False)
    def test_json(self, agentops_session):
        """Test that asdict works with Session objects"""
        assert isinstance(agentops_session.json(), str)

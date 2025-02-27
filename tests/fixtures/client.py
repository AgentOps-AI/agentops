import pytest
from pytest_mock import MockerFixture

from agentops import Client


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the client singleton before and after each test"""
    # Reset the Client singleton by resetting its class attributes
    Client._instance = None
    if hasattr(Client, "_init_done"):
        delattr(Client, "_init_done")
    yield
    # Reset again after the test
    Client._instance = None
    if hasattr(Client, "_init_done"):
        delattr(Client, "_init_done")




@pytest.fixture(autouse=True)
def client_init_mock(agentops_config, mocker: MockerFixture):
    # Store the original method
    original_init = Client.init

    # Now patch the init method
    mock_init = mocker.patch("agentops.client.Client.init", autospec=True)

    # Add side effect to merge kwargs with agentops_config.dict()
    def side_effect(self, **kwargs):
        # Only update with config values for keys NOT already in kwargs
        config_dict = agentops_config.dict()
        for key, value in config_dict.items():
            if key not in kwargs:
                kwargs[key] = value

        # Call original init and return its result
        return original_init(self, **kwargs)

    mock_init.side_effect = side_effect

    yield mock_init

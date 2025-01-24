from typing import TYPE_CHECKING, Dict

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(scope="function")
def http_client_spy(mocker: "MockerFixture") -> Dict[str, "MockerFixture"]:
    """
    !!! To be used with integration tests !!!

    Reasoning:

        Unit tests leverage on requests-mock which completely suppress
        any outgoing HTTP requests. In integration tests you usually want
        to let requests go through, hence we spy on the HttpClient without
        interfering with native `requests` library.

    Usage:

        ```python
        def test_my_test(http_client_spy):
            # test code here
            http_client_spy["post"].assert_called_once()
            http_client_spy["get"].assert_called_once()
        ```
    """
    from agentops.http_client import HttpClient

    return {
        "post": mocker.spy(HttpClient, "post"),
        "get": mocker.spy(HttpClient, "get"),
    }

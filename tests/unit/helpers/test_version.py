from unittest.mock import Mock, patch
from importlib.metadata import PackageNotFoundError

from agentops.helpers.version import get_agentops_version, check_agentops_update


class TestGetAgentopsVersion:
    def test_get_agentops_version_success(self):
        """Test successful version retrieval."""
        with patch("agentops.helpers.version.version") as mock_version:
            mock_version.return_value = "1.2.3"

            result = get_agentops_version()

            assert result == "1.2.3"
            mock_version.assert_called_once_with("agentops")

    def test_get_agentops_version_exception(self):
        """Test version retrieval when an exception occurs."""
        test_exception = Exception("Test error")

        with patch("agentops.helpers.version.version") as mock_version:
            mock_version.side_effect = test_exception

            with patch("agentops.helpers.version.logger") as mock_logger:
                result = get_agentops_version()

                assert result is None
                mock_logger.warning.assert_called_once_with("Error reading package version: %s", test_exception)


class TestCheckAgentopsUpdate:
    def test_check_agentops_update_outdated(self):
        """Test update check when a newer version is available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"version": "2.0.0"}}

        with patch("agentops.helpers.version.requests.get", return_value=mock_response):
            with patch("agentops.helpers.version.version", return_value="1.0.0"):
                with patch("agentops.helpers.version.logger") as mock_logger:
                    check_agentops_update()

                    mock_logger.warning.assert_called_once_with(
                        " WARNING: agentops is out of date. Please update with the command: 'pip install --upgrade agentops'"
                    )

    def test_check_agentops_update_current(self):
        """Test update check when current version is up to date."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"version": "1.0.0"}}

        with patch("agentops.helpers.version.requests.get", return_value=mock_response):
            with patch("agentops.helpers.version.version", return_value="1.0.0"):
                with patch("agentops.helpers.version.logger") as mock_logger:
                    check_agentops_update()

                    # Should not log any warning when versions match
                    mock_logger.warning.assert_not_called()

    def test_check_agentops_update_package_not_found(self):
        """Test update check when package is not found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"version": "2.0.0"}}

        with patch("agentops.helpers.version.requests.get", return_value=mock_response):
            with patch("agentops.helpers.version.version", side_effect=PackageNotFoundError("agentops")):
                with patch("agentops.helpers.version.logger") as mock_logger:
                    result = check_agentops_update()

                    assert result is None
                    mock_logger.warning.assert_not_called()

    def test_check_agentops_update_request_failure(self):
        """Test update check when the HTTP request fails."""
        with patch("agentops.helpers.version.requests.get", side_effect=Exception("Network error")):
            with patch("agentops.helpers.version.logger") as mock_logger:
                result = check_agentops_update()

                assert result is None
                mock_logger.debug.assert_called_once_with("Failed to check for updates: Network error")

    def test_check_agentops_update_non_200_status(self):
        """Test update check when the HTTP response is not 200."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch("agentops.helpers.version.requests.get", return_value=mock_response):
            with patch("agentops.helpers.version.logger") as mock_logger:
                check_agentops_update()

                # Should not log any warning when status is not 200
                mock_logger.warning.assert_not_called()

    def test_check_agentops_update_json_error(self):
        """Test update check when JSON parsing fails."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = Exception("JSON error")

        with patch("agentops.helpers.version.requests.get", return_value=mock_response):
            with patch("agentops.helpers.version.logger") as mock_logger:
                result = check_agentops_update()

                assert result is None
                mock_logger.debug.assert_called_once_with("Failed to check for updates: JSON error")

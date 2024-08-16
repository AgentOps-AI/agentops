import unittest
from unittest.mock import patch, mock_open, Mock

from agentops.time_travel import (
    TimeTravel,
    check_time_travel_active,
)


class TestTimeTravel(unittest.TestCase):

    @patch("os.path.dirname")
    @patch("os.path.abspath")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"completion_overrides": {}}',
    )
    def test_init(self, mock_open, mock_abspath, mock_dirname):
        mock_abspath.return_value = "/path/to/script"
        mock_dirname.return_value = "/path/to"
        instance = TimeTravel()
        self.assertEqual(instance._completion_overrides, {})

    @patch("os.path.dirname")
    @patch("os.path.abspath")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"Time_Travel_Debugging_Active": true}',
    )
    def test_check_time_travel_active(self, mock_open, mock_abspath, mock_dirname):
        mock_abspath.return_value = "/path/to/script"
        mock_dirname.return_value = "/path/to"
        result = check_time_travel_active()
        self.assertTrue(result)

import os
import socket
from pathlib import Path

# the root of the repository
REPO_ROOT = Path(__file__).parent.parent.parent.parent
APP_DIR = REPO_ROOT / 'api'

__all__ = [
    'REPO_ROOT',
    'APP_DIR',
    'is_github_actions',
    'get_free_port',
]


def is_github_actions():
    """Check if we're running in GitHub Actions CI."""
    return os.environ.get('GITHUB_ACTIONS') == 'true'


def get_free_port(start_port: int) -> int:
    """Get a free port starting from start_port, incrementing by 1."""
    if is_github_actions():
        # postgres will already be running by the time we get here in CI
        return start_port

    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', start_port))
                return start_port
            except OSError:
                start_port += 1

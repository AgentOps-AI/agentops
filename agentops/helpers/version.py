from importlib.metadata import PackageNotFoundError, version

import requests

from agentops.logging import logger


def get_agentops_version():
    try:
        pkg_version = version("agentops")
        return pkg_version
    except Exception as e:
        logger.warning("Error reading package version: %s", e)
        return None


def check_agentops_update():
    try:
        response = requests.get("https://pypi.org/pypi/agentops/json")

        if response.status_code == 200:
            json_data = response.json()
            latest_version = json_data["info"]["version"]

            try:
                current_version = version("agentops")
            except PackageNotFoundError:
                return None

            if not latest_version == current_version:
                logger.warning(
                    " WARNING: agentops is out of date. Please update with the command: 'pip install --upgrade agentops'"
                )
    except Exception as e:
        logger.debug(f"Failed to check for updates: {e}")
        return None

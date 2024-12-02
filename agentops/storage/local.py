import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import aiofiles
import yaml

from agentops.singleton import singleton


@singleton
class LocalStorage:
    """
    Handles local file storage operations for Agentops.

    This class provides both synchronous and asynchronous methods for reading and writing
    JSON and YAML files. All files are stored in the ~/.agentops directory.

    Methods are prefixed with 'a' to indicate async variants (e.g., read_json vs aread_json).

    Example:
        ```python
        # Synchronous usage
        storage = LocalStorage()
        data = storage.read_json("config.json")

        # Asynchronous usage
        async def load_config():
            storage = LocalStorage()
            data = await storage.aread_json("config.json")
        ```
    """

    def __init__(self):
        """Initialize LocalStorage with base directory at ~/.agentops"""
        self.base_dir = self._get_base_dir()
        self._ensure_base_dir_exists()

    @staticmethod
    def _get_base_dir() -> Path:
        """
        Get the base directory path for Agentops storage.

        Returns:
            Path: The path to ~/.agentops directory
        """
        home = Path.home()
        return home / ".agentops"

    def _ensure_base_dir_exists(self) -> None:
        """Create the base directory if it doesn't exist."""
        os.makedirs(self.base_dir, exist_ok=True)

    def path(self, filename: str) -> Path:
        """
        Get the full path for a storage file.

        Args:
            filename: Name of the file to get path for

        Returns:
            Path: Full path to the file in the Agentops directory
        """
        return self.base_dir / filename

    def read_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Read JSON data from storage synchronously.

        Args:
            filename: Name of the JSON file to read

        Returns:
            Optional[Dict[str, Any]]: The parsed JSON data, or None if file doesn't exist
            or contains invalid JSON
        """
        try:
            with open(self.path(filename), "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as e:
            print(f"Error reading JSON file {filename}: {e}")
            return None

    def write_json(self, filename: str, data: Dict[str, Any]) -> bool:
        """
        Write JSON data to storage synchronously.

        Args:
            filename: Name of the JSON file to write to
            data: Dictionary to be written as JSON

        Returns:
            bool: True if write was successful, False otherwise
        """
        try:
            with open(self.path(filename), "w") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error writing JSON file {filename}: {e}")
            return False

    async def aread_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Read JSON data from storage asynchronously.

        Args:
            filename: Name of the JSON file to read

        Returns:
            Optional[Dict[str, Any]]: The parsed JSON data, or None if file doesn't exist
            or contains invalid JSON
        """
        try:
            async with aiofiles.open(self.path(filename), "r") as f:
                content = await f.read()
                return json.loads(content)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as e:
            print(f"Error reading JSON file {filename}: {e}")
            return None

    async def awrite_json(self, filename: str, data: Dict[str, Any]) -> bool:
        """
        Write JSON data to storage asynchronously.

        Args:
            filename: Name of the JSON file to write to
            data: Dictionary to be written as JSON

        Returns:
            bool: True if write was successful, False otherwise
        """
        try:
            async with aiofiles.open(self.path(filename), "w") as f:
                await f.write(json.dumps(data, indent=4))
            return True
        except Exception as e:
            print(f"Error writing JSON file {filename}: {e}")
            return False

    def read_yaml(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Read YAML data from storage synchronously.

        Args:
            filename: Name of the YAML file to read

        Returns:
            Optional[Dict[str, Any]]: The parsed YAML data, or None if file doesn't exist
            or contains invalid YAML
        """
        try:
            with open(self.path(filename), "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return None
        except yaml.YAMLError as e:
            print(f"Error reading YAML file {filename}: {e}")
            return None

    def write_yaml(self, filename: str, data: Dict[str, Any]) -> bool:
        """
        Write YAML data to storage synchronously.

        Args:
            filename: Name of the YAML file to write to
            data: Dictionary to be written as YAML

        Returns:
            bool: True if write was successful, False otherwise
        """
        try:
            with open(self.path(filename), "w") as f:
                yaml.dump(data, f)
            return True
        except Exception as e:
            print(f"Error writing YAML file {filename}: {e}")
            return False

    async def aread_yaml(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Read YAML data from storage asynchronously.

        Args:
            filename: Name of the YAML file to read

        Returns:
            Optional[Dict[str, Any]]: The parsed YAML data, or None if file doesn't exist
            or contains invalid YAML
        """
        try:
            async with aiofiles.open(self.path(filename), "r") as f:
                content = await f.read()
                return yaml.safe_load(content)
        except FileNotFoundError:
            return None
        except yaml.YAMLError as e:
            print(f"Error reading YAML file {filename}: {e}")
            return None

    async def awrite_yaml(self, filename: str, data: Dict[str, Any]) -> bool:
        """
        Write YAML data to storage asynchronously.

        Args:
            filename: Name of the YAML file to write to
            data: Dictionary to be written as YAML

        Returns:
            bool: True if write was successful, False otherwise
        """
        try:
            async with aiofiles.open(self.path(filename), "w") as f:
                await f.write(yaml.dump(data))
            return True
        except Exception as e:
            print(f"Error writing YAML file {filename}: {e}")
            return False



local_store = LocalStorage()
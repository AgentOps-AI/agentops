from __future__ import annotations
from typing import Optional, Generator
from enum import Enum
from dataclasses import dataclass
import re

import git
from git.exc import GitCommandError

from jockey.backend import (
    get_repository_path,
    ensure_namespace_directory,
    cleanup_namespace_directory,
)
from jockey.backend.event import BaseEvent, EventStatus, register_event


class RepositoryEventStep(Enum):
    """Specific steps in repository operations."""

    INITIALIZING = "initializing"
    CLONING = "cloning"
    CHECKOUT = "checkout"
    COMPLETED = "completed"


class RepositoryEvent(BaseEvent):
    """Event for repository operations."""

    event_type = "repository"
    step: Optional[RepositoryEventStep]

    def format_message(self) -> str:
        """Dynamically format the message based on step and status."""
        if self.status == EventStatus.STARTED:
            return "Starting repository clone"
        elif self.status == EventStatus.PROGRESS:
            match self.step:
                case RepositoryEventStep.INITIALIZING:
                    return "Initializing clone directory"
                case RepositoryEventStep.CLONING:
                    return "Cloning repository..."
                case RepositoryEventStep.CHECKOUT:
                    return "Checking out branch"
                case _:
                    return "Processing repository..."
        elif self.status == EventStatus.COMPLETED:
            return "Repository clone completed"
        elif self.status == EventStatus.ERROR:
            if self.exception:
                return f"Repository clone failed: {self.exception}"
            return "Repository clone failed"

        # Fallback
        return f"Repository: {self.status.value}"


register_event(RepositoryEvent)


@dataclass
class Repository:
    """Model for managing Git repositories.

    Handles repository cloning, checkout, and cleanup in namespace-isolated directories.
    """

    url: str
    namespace: str  # Required for directory isolation
    branch: str = "main"  # Branch or commit hash to checkout
    local_name: Optional[str] = None  # Directory name, defaults to repo name
    github_access_token: Optional[str] = None  # GitHub access token for private repos

    @property
    def repository_name(self) -> str:
        """Extract repository name from URL using regex."""
        if self.local_name:
            return self.local_name

        # Use regex to extract repo name from various Git URL formats:
        # https://github.com/user/repo.git
        # git@github.com:user/repo.git
        # https://gitlab.com/user/repo
        # /path/to/local/repo
        pattern = r'[/:]([^/]+?)(?:\.git)?/?$'
        match = re.search(pattern, self.url)

        if match:
            return match.group(1)
        else:
            raise ValueError(f"Unable to extract repository name from URL: {self.url}")

    @property
    def local_path(self) -> str:
        """Get the full local path where repository will be cloned."""
        return str(get_repository_path(self.namespace, self.repository_name))

    def _get_authenticated_url(self) -> str:
        """Get the repository URL with authentication token if available."""
        if not self.github_access_token:
            return self.url

        # Transform https://github.com/user/repo.git to https://token@github.com/user/repo.git
        return self.url.replace('https://github.com/', f'https://{self.github_access_token}@github.com/')

    def clone(self) -> Generator[RepositoryEvent, None, str]:
        """Clone the repository with progress events.

        Yields:
            RepositoryEvent: Status events during cloning

        Returns:
            str: Local path to the cloned repository
        """
        try:
            yield RepositoryEvent(EventStatus.STARTED)
            yield RepositoryEvent(EventStatus.PROGRESS, step=RepositoryEventStep.INITIALIZING)
            cleanup_namespace_directory(self.namespace)
            ensure_namespace_directory(self.namespace)

            yield RepositoryEvent(EventStatus.PROGRESS, step=RepositoryEventStep.CLONING)
            repo = git.Repo.clone_from(
                self._get_authenticated_url(),
                self.local_path,
            )

            yield RepositoryEvent(EventStatus.PROGRESS, step=RepositoryEventStep.CHECKOUT)
            repo.git.checkout(self.branch)

            yield RepositoryEvent(EventStatus.COMPLETED)
            return self.local_path

        except GitCommandError as e:
            yield RepositoryEvent(EventStatus.ERROR, exception=e)
        except Exception as e:
            yield RepositoryEvent(EventStatus.ERROR, exception=e)
        finally:
            cleanup_namespace_directory(self.namespace)

    def clone_sync(self) -> str:
        """Clone the repository synchronously (convenience method).

        Returns:
            str: Local path to the cloned repository
        """
        for event in self.clone():
            if event.status == EventStatus.COMPLETED:
                return self.local_path
        return self.local_path

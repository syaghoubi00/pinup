"""Base Container class implementation."""

import logging

from pinup.utils.container.runtime import detect_container_runtime

logger = logging.getLogger(__name__)


class Runtime:
    """Handles container runtime specific operations."""

    def __init__(self, runtime_path: str | None) -> None:
        """Initialize the runtime with a path.

        Args:
            runtime_path: Path to the container runtime binary

        """
        self._runtime_path = runtime_path

    @property
    def is_available(self) -> bool:
        """Check if this container runtime is available.

        Returns:
            bool: True if the runtime is available, False otherwise

        """
        return self._runtime_path is not None

    @property
    def path(self) -> str | None:
        """Return the runtime binary path.

        Returns:
            Optional[str]: Path to the runtime binary or None if not available

        """
        return self._runtime_path


class Container:
    """Handles interaction with container runtimes like Docker and Podman."""

    def __init__(self) -> None:
        """Initialize the container runtime."""
        runtime_path = detect_container_runtime()
        self._runtime = Runtime(runtime_path)

    @property
    def runtime(self) -> Runtime:
        """Access the container runtime.

        Returns:
            Runtime: The container runtime instance

        """
        return self._runtime

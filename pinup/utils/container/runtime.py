"""Detects how to interacted with the container runtime (Docker or Podman)."""

import logging
import shutil

logger = logging.getLogger(__name__)


def detect_container_runtime() -> str | None:
    """Detect available container engine (Docker or Podman).

    Returns:
        str: Path to the container runtime binary
        None: If no container runtime is found

    """
    # Check for Docker and Podman
    for runtime in ("docker", "podman"):
        if path := shutil.which(runtime):
            logger.debug("Found container runtime: %s at %s", runtime, path)
            return path

    # No container engine found
    logger.debug("No container runtime found")
    return None

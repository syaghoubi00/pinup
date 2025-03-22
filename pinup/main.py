"""PinUp - Update Pinned Package Versions in Containerfiles."""

import logging
import os
import shutil
from pathlib import Path

import docker

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_container_runtime_socket() -> str | None:
    """Return the path to the container runtime socket."""
    for runtime in ("docker", "podman"):
        if path := shutil.which(runtime):
            logger.info("Found container runtime: %s", path)

            uid = os.getuid()

            if "docker" in path:
                # Try rootless user socket first
                if Path(f"/run/user/{uid}/docker.sock").exists():
                    return f"unix://run/user/{uid}/docker.sock"
                # Try rootful socket next
                if Path("/var/run/docker.sock").exists():
                    return "unix://var/run/docker.sock"
            if "podman" in path:
                if Path(f"/run/user/{uid}/podman/podman.sock").exists():
                    return f"unix://run/user/{uid}/podman/podman.sock"
                if Path("/var/run/podman/podman.sock").exists():
                    return "unix://var/run/podman/podman.sock"

    msg = "No container runtime socket found"
    raise FileNotFoundError(msg)


if __name__ == "__main__":
    socket = get_container_runtime_socket()
    logger.info("Using container runtime socket: %s", socket)

    client = docker.DockerClient(base_url=socket)

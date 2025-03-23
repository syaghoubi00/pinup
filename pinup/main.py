"""PinUp - Update Pinned Package Versions in Containerfiles."""

import argparse
import logging
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import docker

from pinup.utils import parsers

logger = logging.getLogger(__name__)


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


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Update package versions in container files.",
    )

    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default="Containerfile",
        help="Path to the container file.",
    )
    parser.add_argument(
        "--socket",
        type=Path,
        help="Path to the container runtime socket.",
    )
    parser.add_argument(
        "--verbosity",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="WARNING",
        help="Set logging level.",
    )

    return parser.parse_args()


@dataclass
class PackageManager:
    """Represents a package manager for a specific base image."""

    package_manager: str  # Package manager for this base image
    check_update_command: str  # Command to check for package updates


def get_package_manager(base_image: str) -> PackageManager:
    """Determine the package manager based on the base image."""
    image_lower = base_image.lower()
    if any(distro in image_lower for distro in ["fedora", "centos", "rhel"]):
        return PackageManager(
            package_manager="dnf",
            check_update_command="dnf repoquery --quiet --latest-limit=1 --queryformat='%{name}=%{version}\n'",
        )
    if any(distro in image_lower for distro in ["ubuntu", "debian"]):
        return PackageManager(package_manager="apt-get", check_update_command="update")
    if "alpine" in image_lower:
        return PackageManager(package_manager="apk", check_update_command="update")

    msg = f"Unknown base image type: {base_image}, cannot determine package manager"
    raise RuntimeError(msg)


def get_new_package_versions(
    stage_content: str,
    pkg_manager: PackageManager,
    client: docker.DockerClient,
) -> None:
    """Update package versions in a container stage.

    Args:
        stage_content: Content of the container stage
        pkg_manager: PackageManager object for this stage
        client: Docker client object

    """
    packages = []
    command = ""

    # NOTE: This is a placeholder implementation for DNF package manager
    out_pattern = ""
    result = ""

    if pkg_manager.package_manager == "dnf":
        # pattern = r"([a-zA-Z0-9_-]+)-[\d.:]+(?=-*\d*\s|$)"
        pattern = r"([a-zA-Z0-9_-]+)=\S+"
        # out_pattern = r"([a-zA-Z0-9_-]+)-0:([\d\.]+)"

        # Matches package names
        packages = {match.group(1) for match in re.finditer(pattern, stage_content)}

        command = f"{pkg_manager.check_update_command} {' '.join(packages)}"

    if not packages:
        logger.info("No pinned packages found in stage %d", stage.index)
        return

    logger.info("Pinned packages in stage %d: %s", stage.index, packages)

    if command:
        try:
            # TODO: Create temp dir to store package manager cache and pass as volume
            container = client.containers.run(
                image=stage.base_image,
                command=command,
                detach=True,
            )

            # TODO: Add timeout handling
            # Wait for the container to finish
            container.wait()

            # Get the output from the container
            result = container.logs().decode("utf-8").strip()

            # Clean up the container
            container.remove()

            logger.info("Result:\n%s", result)

        except docker.errors.APIError:
            logger.exception("Error checking for updates: %s")
            raise

    new_package_versions = result.strip().split("\n")

    logger.info(
        "New package versions in stage %d: %s",
        stage.index,
        new_package_versions,
    )


if __name__ == "__main__":
    args = parse_args()

    # Set logging level
    log_level = getattr(logging, args.verbosity)
    logging.basicConfig(level=log_level)

    # If socket is not provided, try to find one
    socket = get_container_runtime_socket() if not args.socket else args.socket
    logger.info("Using container runtime socket: %s", socket)

    # Initialize Docker client only once
    client = docker.DockerClient(base_url=socket)

    # Parse the container file into stages
    try:
        # Initialize Parser object with the containerfile
        parse = parsers.ContainerfileParser(containerfile_path=args.file)

        stages = parse.containerfile()
        logger.info("Found %d build stages", len(stages))

        for stage in stages:
            logger.info(
                "Stage %d (%s) using base image: %s",
                stage.index,
                stage.name or "unnamed",
                stage.base_image,
            )

            parsed_stage = parse.stage(
                stage=stage,
                all_stages=stages,
            )

            logger.info("Stage content:\n%s", parsed_stage)

            # Determine package manager for this stage
            pkg_manager = get_package_manager(stage.base_image)
            logger.info("Stage uses package manager: %s", pkg_manager.package_manager)

            # Process this stage
            get_new_package_versions(
                stage_content=parsed_stage,
                pkg_manager=pkg_manager,
                client=client,
            )

    except FileNotFoundError:
        logger.exception("Container file not found: %s", args.file)
        raise
    except Exception:
        logger.exception("Error parsing container file: %s")
        raise

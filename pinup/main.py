"""PinUp - Update Pinned Package Versions in Containerfiles."""

import argparse
import logging
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import docker

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
class BuildStage:
    """Represents a build stage in a containerfile."""

    index: int  # Position in multi-stage build
    name: str | None  # Name after AS directive, if any
    base_image: str  # Base image for this stage
    start_line: int  # Line number where this stage begins


def parse_containerfile(containerfile: Path) -> list[BuildStage]:
    """Parse a container file into build stages.

    Args:
        containerfile: Path to the Containerfile/Dockerfile

    Returns:
        List of BuildStage objects representing each stage in the build

    Example:
        >>> stages = parse_containerfile(Path("Containerfile"))
        >>> for stage in stages:
        ...     print(f"Stage {stage.index}: {stage.name or 'unnamed'} using {stage.base_image}")
        Stage 0: builder using python:3.9-slim
        Stage 1: unnamed using alpine:3.14

    """
    stages = []
    current_line = ""
    line_number = 0
    stage_count = 0

    with containerfile.open() as f:
        for line in f:
            line_number += 1
            # Handle line continuations
            line = line.strip()
            if line.endswith("\\"):
                current_line += line[:-1].strip() + " "
                continue
            else:
                current_line += line

            # Remove comments (preserving # in image tags)
            line_without_comments = ""
            in_image_tag = False
            for i, char in enumerate(current_line):
                if char == "#" and i > 0 and current_line[i - 1] != ":":
                    break
                if (
                    char == "/"
                    and i < len(current_line) - 1
                    and current_line[i + 1] == "/"
                ):
                    break
                if char == ":":
                    in_image_tag = True
                if char == " ":
                    in_image_tag = False
                line_without_comments += char

            parts = line_without_comments.split()
            if not parts:
                current_line = ""
                continue

            if parts[0].lower() == "from":
                if len(parts) >= 2:
                    image = parts[1]
                    stage_name = None

                    # Check for AS clause
                    remaining_parts = [p.lower() for p in parts[2:]]
                    if "as" in remaining_parts:
                        as_index = remaining_parts.index("as") + 2
                        stage_name = parts[as_index]
                        # Everything between FROM and AS is the image name
                        image = " ".join(parts[1:as_index])

                    stage = BuildStage(
                        index=stage_count,
                        name=stage_name,
                        base_image=image,
                        start_line=line_number,
                    )
                    stages.append(stage)
                    stage_count += 1

            current_line = ""

    return stages


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


def parse_stage(
    stage: BuildStage,
    all_stages: list[BuildStage],
    containerfile: Path,
) -> str:
    """Parse the container stage content from the containerfile."""
    # Determine the end line for the current stage
    current_index = stage.index
    end_line = None

    # Find the next stage's start line to use as our end boundary
    for other_stage in all_stages:
        if other_stage.index == current_index + 1:
            end_line = other_stage.start_line - 1
            break

    # Read the containerfile content
    with containerfile.open() as f:
        all_lines = f.readlines()

    # Extract only the portion for the current stage
    if end_line:
        stage_content = "".join(all_lines[stage.start_line - 1 : end_line])
    else:
        # If this is the last stage, read until the end of file
        stage_content = "".join(all_lines[stage.start_line - 1 :])

    return stage_content


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
        stages = parse_containerfile(args.file)
        logger.info("Found %d build stages", len(stages))

        for stage in stages:
            logger.info(
                "Stage %d (%s) using base image: %s",
                stage.index,
                stage.name or "unnamed",
                stage.base_image,
            )

            pasrsed_stage = parse_stage(
                stage,
                all_stages=stages,
                containerfile=args.file,
            )

            logger.info("Stage content:\n%s", pasrsed_stage)

            # Determine package manager for this stage
            pkg_manager = get_package_manager(stage.base_image)
            logger.info("Stage uses package manager: %s", pkg_manager.package_manager)

            # Process this stage
            get_new_package_versions(
                stage_content=pasrsed_stage,
                pkg_manager=pkg_manager,
                client=client,
            )

    except FileNotFoundError:
        logger.exception("Container file not found: %s", args.file)
        raise
    except Exception:
        logger.exception("Error parsing container file: %s")
        raise

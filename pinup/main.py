"""PinUp - Update Pinned Package Versions in Containerfiles."""

import argparse
import logging
import os
import shutil
from pathlib import Path
from dataclasses import dataclass

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


def get_package_manager(base_image: str) -> str:
    """Determine the package manager based on the base image."""
    image_lower = base_image.lower()
    if any(distro in image_lower for distro in ["fedora", "centos", "rhel"]):
        return "dnf"
    if any(distro in image_lower for distro in ["ubuntu", "debian"]):
        return "apt"
    if "alpine" in image_lower:
        return "apk"

    logger.warning(
        "Unknown base image type: %s, cannot determine package manager",
        base_image,
    )
    return "unknown"


if __name__ == "__main__":
    args = parse_args()

    # Set logging level
    log_level = getattr(logging, args.verbosity)
    logging.basicConfig(level=log_level)

    # If socket is not provided, try to find one
    socket = get_container_runtime_socket() if not args.socket else args.socket
    logger.info("Using container runtime socket: %s", socket)

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

            # Determine package manager for this stage
            pkg_manager = get_package_manager(stage.base_image)
            logger.info("Stage uses package manager: %s", pkg_manager)

    except FileNotFoundError:
        logger.exception("Container file not found: %s", args.file)
        raise
    except Exception as e:
        logger.exception("Error parsing container file: %s", e)
        raise

    client = docker.DockerClient(base_url=socket)

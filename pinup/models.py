"""Dataclasses."""

from dataclasses import dataclass


@dataclass
class BuildStage:
    """Represents a build stage in a containerfile."""

    index: int  # Position in multi-stage build
    name: str | None  # Name after AS directive, if any
    base_image: str  # Base image for this stage
    start_line: int  # Line number where this stage begins


@dataclass
class PackageManager:
    """Represents a package manager for a specific base image."""

    package_manager: str  # Package manager for this base image
    check_update_command: str  # Command to check for package updates

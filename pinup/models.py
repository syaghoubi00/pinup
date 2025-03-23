"""Dataclasses."""

from dataclasses import dataclass


@dataclass
class BuildStage:
    """Represents a build stage in a containerfile."""

    index: int  # Position in multi-stage build
    name: str | None  # Name after AS directive, if any
    base_image: str  # Base image for this stage
    start_line: int  # Line number where this stage begins

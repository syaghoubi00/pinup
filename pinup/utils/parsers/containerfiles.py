"""Parser Utils for Pinup."""

from pathlib import Path

from pinup.models import BuildStage


class ContainerfileParser:
    """Parser for Containerfiles/Dockerfiles."""

    def __init__(self, containerfile_path: Path) -> None:
        """Initialize the parser with a containerfile.

        Args:
            containerfile_path: Path to the Containerfile/Dockerfile

        """
        self.containerfile_path = containerfile_path
        self.containerfile_content = self.containerfile_path.read_text()

    def stage(
        self,
        stage: BuildStage,
        all_stages: list[BuildStage],
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
        with self.containerfile_path.open() as f:
            all_lines = f.readlines()

        # Extract only the portion for the current stage
        if end_line:
            stage_content = "".join(all_lines[stage.start_line - 1 : end_line])
        else:
            # If this is the last stage, read until the end of file
            stage_content = "".join(all_lines[stage.start_line - 1 :])

        return stage_content

    def containerfile(self) -> list[BuildStage]:
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

        with self.containerfile_path.open() as f:
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

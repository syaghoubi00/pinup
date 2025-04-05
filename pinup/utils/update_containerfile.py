"""Update the containerfile with new package versions."""

import difflib
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def update_containerfile(
    pattern: str,
    packages: list,
    content: str,
) -> str:
    """Update the containerfile with new package versions.

    Args:
        pattern: Regex pattern to match package versions
        packages: List of packages with new versions
        content: current stage being processed

    """
    updated_content = content

    for match in re.finditer(pattern, content):
        logger.info("Found match: %s", match.group(0))
        package_name = match.group(1)

        for pkg in packages:
            if pkg.startswith(f"{package_name}"):
                new_version = pkg.split("=")[1]
                old_version = match.group(0)
                updated_content = updated_content.replace(
                    old_version,
                    # NOTE: Different distros may require different version strings
                    # tested and working on Fedora, 'package-version'
                    f"{package_name}-{new_version}",
                )
                logger.info("updating %s to %s", package_name, new_version)
    logger.info("Updated content:\n%s", updated_content)

    return updated_content


def containerfile_diff(
    content: str,
    updated_content: str,
    file_path: Path,
) -> None:
    """Generate a diff between the old and new Containerfile."""
    if updated_content != content:
        diff = "\n".join(
            difflib.unified_diff(
                content.splitlines(),
                updated_content.splitlines(),
                fromfile=f"{file_path} (old)",
                tofile=f"{file_path} (new)",
            ),
        )
        logger.info("\n%s", diff)
        response = input(f"Update {file_path}? (y/N): ").strip().lower()
        if response != "y":
            logger.info("Skipping update for %s", file_path)
            return
        file_path.write_text(updated_content)
        logger.info("Updated %s: ", file_path)

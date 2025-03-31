import logging
import re

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
            if pkg.startswith(f"{package_name}="):
                new_version = pkg.split("=")[1]
                old_version = match.group(0)
                updated_content = updated_content.replace(
                    old_version,
                    f"{package_name}={new_version}",
                )
                logger.info("updating %s to %s", package_name, new_version)
    logger.info("Updated content:\n%s", updated_content)

    return updated_content

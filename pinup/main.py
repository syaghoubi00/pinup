"""Pinup - Container Pinned Version Updater.

Reads Containerfiles and updates the pinned versions within them.
"""

import logging

from pinup.utils import Container

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the main application logic."""
    container = Container()

    if not container.runtime.is_available:
        logger.error("No container runtime found.")
        return

    logger.info(container.runtime.path)


if __name__ == "__main__":
    main()

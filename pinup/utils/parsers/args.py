"""Arguement Parser for the PinUp Package."""

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Update package versions in container files.",
    )

    parser.add_argument(
        "file",
        type=Path,
        nargs="?",
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
    parser.add_argument(
        "--no-prompt",
        "-y",
        action="store_true",
        help="Skip prompting for confirmation before writing changes",
    )

    return parser.parse_args()

# PinUp - Update Pinned Package Versions in Containerfiles

PinUp is a command-line tool that helps you keep pinned package versions in your Containerfiles (Dockerfiles) up-to-date. It analyzes your Containerfiles, detects pinned packages, and checks for available updates by running commands in temporary containers based on your base images.

This was created as tools like Dependabot only update pinned base images and not pinned package versions within the Containerfiles.

## Features

- **Multi-stage build support**: Analyzes all stages in Containerfiles with multi-stage builds
- **Multiple package managers**: Currently supports DNF, with more coming soon
- **Docker and Podman compatible**: Works with both Docker and Podman container runtimes
- **Automatic socket detection**: Finds the appropriate container runtime socket

<!--## Installation-->
<!---->
<!--```bash-->
<!--pip install pinup-->
<!--```-->

## Usage

Basic usage:

```bash
python3 pinup/main.py /path/to/Containerfile
```

With options:

```bash
pinup --socket unix://var/run/docker.sock --verbosity DEBUG /path/to/Containerfiles
```

## How It Works

1. Parses the Containerfile into build stages
2. For each stage:
   - Identifies the base image and appropriate package manager
   - Detects pinned packages (e.g., `package=1.2.3`)
   - Creates a temporary container using the base image
   - Runs package manager commands to check for available updates
   - Reports the results

## Example

Given a Containerfile with:

```dockerfile
FROM fedora:35

RUN dnf install -y \
    python3=3.9.5 \
    nginx=1.20.1 \
    curl=7.76.1
```

PinUp will:

1. Parse the Containerfile and identify the pinned packages
2. Run a container based on `fedora:35`
3. Execute the appropriate DNF commands to check for updates
4. Report available package updates

## Requirements

- Python >=3.11
- Docker or Podman

<!--### Setting up development environment-->
<!---->
<!--```bash-->
<!--# Clone the repository-->
<!--git clone https://github.com/yourusername/pinup.git-->
<!--cd pinup-->
<!---->
<!--# Create and activate a virtual environment-->
<!--python -m venv venv-->
<!--source venv/bin/activate  # On Windows: venv\Scripts\activate-->
<!---->
<!--# Install development dependencies-->
<!--pip install -e ".[dev]"-->
<!--```-->

## Current Limitations

- Only supports DNF package manager currently
- No support for version range specifications
- Requires container runtime access

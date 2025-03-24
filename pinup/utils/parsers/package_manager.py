"""Module for determining the package manager based on the base image."""

from pinup.models import PackageManager


def get_package_manager(base_image: str) -> PackageManager:
    """Determine the package manager based on the base image."""
    image_lower = base_image.lower()
    if any(distro in image_lower for distro in ["fedora", "centos", "rhel"]):
        return PackageManager(
            package_manager="dnf",
            check_update_command="dnf repoquery --quiet --latest-limit=1 --queryformat='%{name}=%{version}\n'",
        )
    # if any(distro in image_lower for distro in ["ubuntu", "debian"]):
    #     return PackageManager(package_manager="apt-get", check_update_command="update")
    # if "alpine" in image_lower:
    #     return PackageManager(package_manager="apk", check_update_command="update")

    msg = f"Unknown base image type: {base_image}, cannot determine package manager"
    raise RuntimeError(msg)

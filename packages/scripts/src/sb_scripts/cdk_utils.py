"""CDK deployment utilities for Second Brain."""

from pathlib import Path


def find_project_root() -> Path:
    """Find the project root directory.

    Returns:
        Path to project root (where .git or pyproject.toml exists)

    Raises:
        RuntimeError: If project root cannot be found
    """
    current = Path(__file__).resolve()

    # Walk up the directory tree looking for project markers
    while current != current.parent:
        # Check for git root or root pyproject.toml
        if (current / ".git").exists() or (
            (current / "pyproject.toml").exists() and (current / "packages").exists()
        ):
            return current
        current = current.parent

    raise RuntimeError(
        "Could not find project root. " "Ensure .git or pyproject.toml exists in project root."
    )


def find_bedrock_dockerfile_parent() -> Path:
    """Find the parent directory of bedrock Dockerfile.

    Returns:
        Absolute POSIX path to packages/bedrock directory

    Raises:
        RuntimeError: If bedrock Dockerfile cannot be found
    """
    project_root = find_project_root()
    bedrock_dir = project_root / "packages" / "bedrock"
    dockerfile = bedrock_dir / "Dockerfile"

    if not dockerfile.exists():
        raise RuntimeError(
            f"Bedrock Dockerfile not found at {dockerfile}. "
            f"Ensure packages/bedrock/Dockerfile exists."
        )

    # Return as POSIX path for cross-platform compatibility
    return bedrock_dir.resolve()


def find_packages_directory() -> Path:
    """Find the packages directory.

    Returns:
        Absolute POSIX path to packages directory

    Raises:
        RuntimeError: If packages directory cannot be found
    """
    project_root = find_project_root()
    packages_dir = project_root / "packages"

    if not packages_dir.exists():
        raise RuntimeError(
            f"Packages directory not found at {packages_dir}. " f"Ensure packages directory exists."
        )

    # Return as POSIX path for cross-platform compatibility
    return packages_dir.resolve()


def find_project_root_for_context() -> Path:
    """Get project root for CDK context variable.

    Returns:
        Absolute POSIX path to project root

    Raises:
        RuntimeError: If project root cannot be found
    """
    project_root = find_project_root()
    if not project_root.exists():
        raise RuntimeError(f"Project root not found at {project_root}.")
    return project_root.resolve()

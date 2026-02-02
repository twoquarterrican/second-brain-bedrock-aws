#!/usr/bin/env python3
"""Wrapper to run agentcore invoke from any directory."""

import subprocess
import sys

from sb_scripts.utils import find_project_root


def main():
    """Run agentcore invoke in the bedrock package directory."""
    project_root = find_project_root()
    bedrock_dir = project_root / "packages" / "bedrock"

    if not bedrock_dir.exists():
        print(f"Error: packages/bedrock directory not found at {bedrock_dir}", file=sys.stderr)
        sys.exit(1)

    # Run agentcore invoke in the bedrock directory with all arguments passed through
    result = subprocess.run(
        ["agentcore", "invoke", *sys.argv[1:]],
        cwd=bedrock_dir,
    )

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

"""Shared deployment utilities for Second Brain."""

import subprocess
from pathlib import Path
from typing import List

import click


def check_tools(tools: List[str]) -> bool:
    """Check if required tools are installed.

    Args:
        tools: List of tool names to check (e.g., ['npm', 'aws', 'cdk'])

    Returns:
        True if all tools found, False otherwise
    """
    missing = []

    for tool in tools:
        result = subprocess.run(
            ["which", tool],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            missing.append(tool)

    if missing:
        click.secho(f"✗ Missing required tools: {', '.join(missing)}", fg="red")
        return False

    return True


def show_install_instructions(tools_info: dict) -> None:
    """Show installation instructions for missing tools.

    Args:
        tools_info: Dict mapping tool name to install instructions
    """
    click.echo("Install via:")
    for tool, instruction in tools_info.items():
        click.echo(f"  - {tool}: {instruction}")


def get_project_root() -> Path:
    """Get the project root directory.

    Returns:
        Path to project root
    """
    return Path(__file__).parent.parent


def run_command(
    cmd: List[str],
    cwd: Path = None,
    capture_output: bool = False,
    description: str = None,
) -> subprocess.CompletedProcess:
    """Run a command and handle output.

    Args:
        cmd: Command to run as list
        cwd: Working directory
        capture_output: Whether to capture output
        description: Description for user display

    Returns:
        CompletedProcess result
    """
    if description:
        click.echo(description, nl=False)

    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture_output,
        text=True,
    )

    if description:
        if result.returncode == 0:
            click.secho(" ✓", fg="green")
        else:
            click.secho(" ✗", fg="red")
            if result.stderr:
                click.echo(result.stderr)

    return result

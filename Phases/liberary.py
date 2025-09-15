#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path
from .cli import is_auto_yes

def run_command(command: list[str], *, capture_output: bool = False, input_text: str | None = None) -> str | None:
    """
    Run a system command safely.

    Why this exists:
    - Some callers need to feed scripted input to commands (e.g., fdisk). Use input_text for that.
    - Some callers need the command output (e.g., genfstab). Use capture_output to get stdout as a string.

    Parameters:
    - command: list of strings, the argv style command.
    - capture_output: when True, returns stdout as a string (stderr still printed on failure).
    - input_text: optional string to send to the command's stdin.

    Returns:
    - stdout string when capture_output is True, otherwise None.
    """
    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,              # Treat stdin/stdout/stderr as text
            input=input_text,       # Provide scripted input when needed
            capture_output=capture_output,  # Capture stdout when requested
        )
        return result.stdout if capture_output else None
    except subprocess.CalledProcessError as error:
        # Print helpful diagnostics so the user knows what failed and why
        stdout = getattr(error, "stdout", "") or ""
        stderr = getattr(error, "stderr", "") or ""
        print(f"Command failed: {' '.join(command)}\nExit code: {error.returncode}")
        if stdout:
            print(f"\n--- stdout ---\n{stdout}")
        if stderr:
            print(f"\n--- stderr ---\n{stderr}")
        sys.exit(error.returncode)

def confirm(prompt: str) -> bool:
    """Prompt the user to confirm an action.

    If the --yes flag is active (Phases.cli.is_auto_yes()), automatically
    return True to support non-interactive runs with --config.
    """
    if is_auto_yes():
        return True
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}

def write_file(path: Path, content: str, mode: int = 0o755):
    """Create parent directories, write text content, and chmod to the given mode."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        os.chmod(path, mode)
    except Exception as e:
        print(f"Error writing file {path}: {e}")
        sys.exit(1)
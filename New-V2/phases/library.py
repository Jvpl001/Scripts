#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

def run_command(command: list[str], input_text: str | None = None) -> None:
    """Run a command and exit on failure.

    Args:
        command: Command and arguments to execute.
        input_text: Optional stdin text to pass to the process.
    """
    try:
        subprocess.run(
            command,
            check=True,
            input=input_text,
            text=True if input_text is not None else False,
        )
    except FileNotFoundError as e:
        print(f"Command not found: {command[0]} ({e})")
        sys.exit(127)
    except subprocess.CalledProcessError as error:
        joined = " ".join(command)
        print(f"Command failed: {joined}\nExit code: {error.returncode}")
        sys.exit(error.returncode)

def confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}

def write_file(path: Path, content: str, mode: int = 0o755) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        os.chmod(path, mode)
    except Exception as e:
        print(f"Error writing file {path}: {e}")
        sys.exit(1)

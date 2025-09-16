#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

def run_command(command: list[str]):
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as error:
        print(f"Command failed: {' '.join(command)}\nExit code: {error.returncode}")
        sys.exit(error.returncode)

def confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def write_file(path: Path, content: str, mode: int = 0o755):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        os.chmod(path, mode)
    except Exception as e:
        print(f"Error writing file {path}: {e}")
        sys.exit(1)
#!/usr/bin/env python3
import argparse

# Module-level flag to auto-confirm prompts when desired
_AUTO_YES = False


def set_auto_yes(value: bool) -> None:
    global _AUTO_YES
    _AUTO_YES = bool(value)


def is_auto_yes() -> bool:
    return _AUTO_YES


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    --config PATH: JSON file with installation values. When provided,
                   the installer will use values from this file and only
                   prompt for any missing/invalid fields.
    """
    parser = argparse.ArgumentParser(description="Arch installer")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a JSON config file (e.g., default_config.json)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-confirm prompts (use with --config for non-interactive runs)",
    )
    return parser.parse_args(argv)

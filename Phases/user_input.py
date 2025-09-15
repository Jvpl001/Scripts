#!/usr/bin/env python3
import getpass
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class InstallConfig:
    country: str
    username: str
    host_name: str
    user_pass: str
    root_pass: str
    timezone: str
    gpu: str


# --- Helper validators ---
def _prompt_nonempty(prompt: str) -> str:
    """Prompt until a non-empty trimmed string is provided."""
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("Input cannot be empty. Please try again.")


def _valid_username(name: str) -> bool:
    # Matches typical Linux username rules
    return bool(re.fullmatch(r"[a-z_][a-z0-9_-]*", name)) and len(name) <= 32


def _prompt_username() -> str:
    while True:
        name = input("Enter username: ").strip()
        if _valid_username(name):
            return name
        print("Invalid username. Use lowercase letters, digits, '-', '_', start with a letter or '_', max 32 chars.")


def _valid_hostname(name: str) -> bool:
    # Single-label hostname validation (RFC 1123 label)
    return bool(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", name))


def _prompt_hostname() -> str:
    while True:
        host = input("Enter the hostname: ").strip()
        if _valid_hostname(host):
            return host
        print("Invalid hostname label. Use letters, digits, optional '-', 1-63 chars, cannot start/end with '-'.")


def _prompt_timezone() -> str:
    while True:
        tz = input("Enter your timezone (example->Asia/Tehran): ").strip()
        # Validate against zoneinfo database present on the live system
        if tz and Path("/usr/share/zoneinfo").joinpath(tz).exists():
            return tz
        print("Timezone not found in /usr/share/zoneinfo. Please try again (e.g., Europe/Berlin, Asia/Tehran).")


def _prompt_password(label: str) -> str:
    while True:
        pw = getpass.getpass(f"Enter {label} password: ")
        if len(pw) < 1:
            print("Password cannot be empty. Please try again.")
            continue
        confirm = getpass.getpass(f"Re-enter {label} password: ")
        if pw != confirm:
            print("Passwords do not match. Please try again.")
            continue
        return pw


def _prompt_gpu_choice() -> str:
    prompt = (
        "Select the graphics driver.\n"
        "0 -> mesa (open-source)\n"
        "1 -> new open nvidia (nvidia-open-dkms)\n"
        "2 -> proprietary Nvidia (nvidia-dkms)\n"
        "3 -> intel\n"
        "4 -> VirtualBox\n"
        "Enter choice [0-4]: "
    )
    while True:
        choice = input(prompt).strip()
        if choice in {"0", "1", "2", "3", "4"}:
            return choice
        print("Invalid choice. Please enter a number between 0 and 4.")


def _load_config_from_path(config_path: str | None) -> dict:
    """Load a JSON config by explicit path or default_config.json one level up.

    Returns an empty dict if no file is present.
    """
    # Try explicit path first
    if config_path:
        p = Path(config_path)
        if not p.exists():
            print(f"Warning: --config path not found: {p}. Falling back to interactive prompts.")
            return {}
        try:
            return json.loads(p.read_text())
        except Exception as e:
            print(f"Warning: Failed to read JSON config {p}: {e}. Falling back to interactive prompts.")
            return {}

    # Try default_config.json located one level up from this file (project root)
    default_path = Path(__file__).resolve().parents[1] / "default_config.json"
    if default_path.exists():
        try:
            return json.loads(default_path.read_text())
        except Exception as e:
            print(f"Warning: Failed to read default config {default_path}: {e}. Ignoring.")
            return {}
    return {}


def get_install_config(config_path: str | None = None) -> InstallConfig:
    """Collect installation inputs with validation, using JSON config when provided.

    - If a config file is provided (via --config) or default_config.json is found,
      values from the file are used.
    - Any missing or invalid fields will be interactively prompted.
    """
    raw = _load_config_from_path(config_path)

    # Country
    country = str(raw.get("country", "")).strip() or _prompt_nonempty("Enter your country (example->Iran): ")

    # Username
    ru = str(raw.get("username", "")).strip()
    username = ru if ru and _valid_username(ru) else _prompt_username()

    # Hostname
    rh = str(raw.get("host_name", "")).strip()
    host_name = rh if rh and _valid_hostname(rh) else _prompt_hostname()

    # Passwords: if not provided or set to placeholder, prompt
    up = str(raw.get("user_pass", "")).strip()
    user_pass = up if up and up != "CHANGE_ME" else _prompt_password("user")

    rp = str(raw.get("root_pass", "")).strip()
    root_pass = rp if rp and rp != "CHANGE_ME" else _prompt_password("root")

    # Timezone
    tz = str(raw.get("timezone", "")).strip()
    timezone = tz if tz and Path("/usr/share/zoneinfo").joinpath(tz).exists() else _prompt_timezone()

    # GPU choice
    g = str(raw.get("gpu", "")).strip()
    gpu = g if g in {"0", "1", "2", "3", "4"} else _prompt_gpu_choice()

    return InstallConfig(
        country=country,
        username=username,
        host_name=host_name,
        user_pass=user_pass,
        root_pass=root_pass,
        timezone=timezone,
        gpu=gpu,
    )

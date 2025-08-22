#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys


def ensure_command_exists(command_name: str) -> None:
    if shutil.which(command_name) is None:
        print(f"Error: required command '{command_name}' not found in PATH.")
        sys.exit(1)


def run_command(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as error:
        print(f"Command failed: {' '.join(command)}\nExit code: {error.returncode}")
        sys.exit(error.returncode)


def require_root() -> None:
    if os.geteuid() != 0:
        print("This script must be run as root. Try: sudo python3 lucks_script.py")
        sys.exit(1)


def main() -> None:
    require_root()

    # Show block devices (equivalent to lsblk)
    ensure_command_exists("lsblk")
    run_command(["lsblk"])

    # Inputs
    usb_target = input("entre sdX: ").strip()
    usb_name = input("enter your usb name: ").strip()
    vg_name = input("enter your Volume Group name: ").strip()
    usb_size = input("enter the size of your usb(example 16G): ").strip()
    # Note: usb_size is prompted in the original script but not used by any command

    # Ensure dependencies
    for dependency in [
        "cryptsetup",
        "pvcreate",
        "vgcreate",
    ]:
        ensure_command_exists(dependency)

    # Commands from the original shell script (preserving order)
    # 1) LUKS format target device
    run_command(["cryptsetup", "luksFormat", f"/dev/{usb_target}"])

    # 2) Open the LUKS device with the given name
    run_command(["cryptsetup", "luksOpen", f"/dev/{usb_target}", usb_name])

    # 3) Initialize LVM PV on the opened mapper device
    run_command(["pvcreate", f"/dev/mapper/{usb_name}"])

    # 4) Create a VG
    run_command(["vgcreate", vg_name, f"/dev/mapper/{usb_name}"])

    # 5) The original script repeats luksFormat again; we preserve this behavior
    run_command(["cryptsetup", "luksFormat", f"/dev/{usb_target}"])

    print("All steps completed successfully.")


if __name__ == "__main__":
    main()
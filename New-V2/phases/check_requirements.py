#!/usr/bin/env python3
import os
import shutil
import sys

def checkUEFI():
    if not os.path.exists("/sys/firmware/efi"):
        print("Error: This script requires UEFI boot mode.")
        print("Your system appears to be booted in BIOS/Legacy mode.")
        print("Please ensure your system is booted in UEFI mode and try again.")
        print("You may need to:")
        print("1. Enter your BIOS/UEFI settings during boot")
        print("2. Enable UEFI boot mode")
        print("3. Disable CSM (Compatibility Support Module) if present")
        print("4. Save and reboot")
        sys.exit(1)

def _ensure_command_exists(command_name: str) -> None:
    if shutil.which(command_name) is None:
        print(f"Error: required command '{command_name}' not found in PATH.")
        sys.exit(1)

def require_root():
    if os.geteuid() != 0:
        print("This script must be run as root. Try: sudo python3 main.py")
        sys.exit(1)

def ensure_dependencies() -> None:
    for dependency in [
        "reflector",
        "pacman",
        "pacman-key",
        "lsblk",
        "fdisk",
        "mkfs.fat",
        "mkswap",
        "swapon",
        "mkfs.btrfs",
        "mount",
        "btrfs",
        "umount",
        "mkdir",
        "pacstrap",
        "genfstab",
        "arch-chroot",
        "ln",
        "hwclock",
        "sed",
        "locale-gen",
        "chpasswd",
        "systemctl",
        "useradd",
        "grub-install",
        "grub-mkconfig",
    ]:
        _ensure_command_exists(dependency)
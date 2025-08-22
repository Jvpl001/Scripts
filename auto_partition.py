#!/usr/bin/env python3

import os
import re
import shutil
import subprocess
import sys
from typing import List


FDISK_TEMPLATE = """
# Create new GPT
g
# Partition 1: EFI System (256MB)
n
1

+256M
# Partition 2: swap (4G)
n
2

+4G
# Partition 3: root (rest of disk)
n
3


# Type for p1 -> EFI (1)
t
1
1
# Type for p2 -> Linux swap (19)
t
2
19
# Type for p3 -> Linux filesystem (20)
t
3
20
# Print and write
p
w
""".lstrip()


def require_root() -> None:
	if os.geteuid() != 0:
		print("This script must be run as root. Try: sudo python3 auto_partition.py")
		sys.exit(1)


def ensure_command_exists(name: str) -> None:
	if shutil.which(name) is None:
		print(f"Error: required command '{name}' not found in PATH.")
		sys.exit(1)


def run(command: List[str], input_text: str | None = None) -> None:
	try:
		subprocess.run(command, input=(input_text.encode() if input_text else None), check=True)
	except subprocess.CalledProcessError as e:
		print(f"Command failed: {' '.join(command)} (exit {e.returncode})")
		sys.exit(e.returncode)


def confirm(prompt: str) -> bool:
	answer = input(f"{prompt} [y/N]: ").strip().lower()
	return answer in {"y", "yes"}


def list_disks() -> None:
	print("Available disks:")
	subprocess.run(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT"], check=False)


def validate_disk_name(name: str) -> bool:
	# Basic validation to avoid /dev/null, etc.
	return re.fullmatch(r"[a-zA-Z0-9]+", name) is not None


def main() -> None:
	require_root()
	ensure_command_exists("fdisk")
	ensure_command_exists("lsblk")

	print("This will DESTROY ALL DATA on the selected disk.")
	list_disks()
	disk_base = input("Enter target disk base name (e.g., sda or nvme0n1): ").strip()
	if not validate_disk_name(disk_base):
		print("Invalid disk name.")
		sys.exit(1)
	disk_path = f"/dev/{disk_base}"

	# Show current partition table for confirmation
	print(f"\nCurrent partition table for {disk_path}:")
	subprocess.run(["fdisk", "-l", disk_path], check=False)

	if not confirm(f"Proceed to create GPT with 256MB EFI, 4G swap, and rest root on {disk_path}?"):
		print("Aborted.")
		sys.exit(0)

	# Feed fdisk with our script
	print("\nPartitioning...")
	run(["fdisk", disk_path], input_text=FDISK_TEMPLATE)

	print("\nResulting partition table:")
	subprocess.run(["fdisk", "-l", disk_path], check=False)

	# Print next steps
	print("\nNext steps (example):")
	if disk_base.startswith("nvme"):
		p1, p2, p3 = f"{disk_path}p1", f"{disk_path}p2", f"{disk_path}p3"
	else:
		p1, p2, p3 = f"{disk_path}1", f"{disk_path}2", f"{disk_path}3"
	print(f"mkfs.fat -F32 {p1}")
	print(f"mkswap {p2} && swapon {p2}")
	print(f"mkfs.btrfs {p3}")

	print("\nDone.")


if __name__ == "__main__":
	main()

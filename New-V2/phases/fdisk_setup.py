#!/usr/bin/env python3
import subprocess
import sys
import re

from .library import confirm
from .library import run_command

FDISK_TEMPLATE = """
g
n
1

+256M
n
2

+4G
n
3


t
1
1
t
2
19
t
3
20
p
w
""".lstrip()

def list_disks():
    print("Available disks:")
    subprocess.run(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT"], check=False)


def run_fdisk():

    while True:
        name = input("Enter the installation drive (e.g., sda or nvme0n1): ").strip().lower()
        if re.fullmatch(r"sd[a-z]", name) or re.fullmatch(r"nvme\d+n\d+", name):
            break
        else:
            print("The drive name was incorrect, try again.")
    disk_path = f"/dev/{name}"

    print(f"\nCurrent partition table for {disk_path}:")
    subprocess.run(["fdisk", "-l", disk_path], check=False)

    if not confirm(f"Proceed to create GPT with 256MB EFI, 4G swap, and rest root on {disk_path}?"):
        print("Aborted.")
        sys.exit(0)

    print("\nPartitioning...")
    run_command(["fdisk", disk_path], input_text=FDISK_TEMPLATE)

    print("\nResulting partition table:")
    subprocess.run(["fdisk", "-l", disk_path], check=False)

    if re.fullmatch("sd.", name):
        part1 = f"{disk_path}1"
        part2 = f"{disk_path}2"
        part3 = f"{disk_path}3"
    else:
        part1 = f"{disk_path}p1"
        part2 = f"{disk_path}p2"
        part3 = f"{disk_path}p3"
    print(f"\nUsing partitions: {part1}, {part2}, {part3}")
    
    run_command(["mkfs.fat", "-F32", part1])
    run_command(["mkswap", part2])
    run_command(["swapon", part2])
    run_command(["mkfs.btrfs", part3])

    run_command(["mount", part3, "/mnt"])
    run_command(["btrfs", "subvolume", "create", "/mnt/@"])
    run_command(["btrfs", "subvolume", "create", "/mnt/@home"])
    run_command(["btrfs", "subvolume", "create", "/mnt/@var"])
    run_command(["btrfs", "subvolume", "create", "/mnt/@snapshots"])
    run_command(["umount", "/mnt"])

    run_command(["mount", "-o", "noatime,compress=lzo,space_cache=v2,subvol=@", part3, "/mnt"])
    run_command(["mkdir", "-p", "/mnt/boot", "/mnt/var", "/mnt/home", "/mnt/.snapshots"])
    run_command(["mount", "-o", "noatime,compress=lzo,space_cache=v2,subvol=@home", part3, "/mnt/home"])
    run_command(["mount", "-o", "noatime,compress=lzo,space_cache=v2,subvol=@var", part3, "/mnt/var"])
    run_command(["mount", "-o", "noatime,compress=lzo,space_cache=v2,subvol=@snapshots", part3, "/mnt/.snapshots"])
    run_command(["mount", part1, "/mnt/boot"])
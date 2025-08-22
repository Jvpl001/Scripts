#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
import re
import getpass
from typing import List
from pathlib import Path

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


def validate_username(username: str) -> bool:
    # Username validation (alphanumeric, underscore, hyphen, 3-32 chars)
    return re.fullmatch(r"[a-z_][a-z0-9_-]*", username) is not None and 3 <= len(username) <= 32


def validate_hostname(hostname: str) -> bool:
    # Hostname validation (alphanumeric, hyphen, 2-63 chars)
    return re.fullmatch(r"[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?", hostname) is not None and 2 <= len(hostname) <= 63


def require_root() -> None:
    if os.geteuid() != 0:
        print("This script must be run as root. Try: sudo python3 arch_install_v1.py")
        sys.exit(1)
    
    # Check if system is booted in UEFI mode
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


def write_file(path: Path, content: str, mode: int = 0o755) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        os.chmod(path, mode)
    except Exception as e:
        print(f"Error writing file {path}: {e}")
        sys.exit(1)


def main() -> None:
    require_root()

    # Ensure essential tools exist
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
        ensure_command_exists(dependency)

    print("btrfs + hyprland arch install")

    print("This will DESTROY ALL DATA on the selected disk.")
    list_disks()
    
    # Get and validate disk selection
    while True:
        disk_base = input("Enter target disk base name (e.g., sda or nvme0n1): ").strip()
        if validate_disk_name(disk_base):
            break
        print("Invalid disk name. Please use only alphanumeric characters.")
    
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

    # Get user credentials with validation
    while True:
        username = input("Enter username: ").strip()
        if validate_username(username):
            break
        print("Invalid username. Use 3-32 characters, lowercase letters, numbers, underscore, or hyphen. Must start with a letter or underscore.")
    
    user_pass = getpass.getpass("Enter the user password: ")
    if not user_pass:
        print("Error: Password cannot be empty.")
        sys.exit(1)
    
    root_pass = getpass.getpass("Enter root password: ")
    if not root_pass:
        print("Error: Root password cannot be empty.")
        sys.exit(1)
    
    while True:
        host_name = input("Enter the hostname: ").strip()
        if validate_hostname(host_name):
            break
        print("Invalid hostname. Use 2-63 characters, alphanumeric and hyphens only.")
    
    country = input("Enter your country (example->Iran): ").strip()
    timezone = input("Enter your timezone (example->Asia/Tehran): ").strip()

    # Use the same disk_base variable throughout
    part1 = f"{disk_base}1"
    part2 = f"{disk_base}2"
    part3 = f"{disk_base}3"

    print(f"\nUsing partitions: {part1}, {part2}, {part3}")

    # Try to update mirrorlist with reflector, but don't quit if it fails
    try:
        subprocess.run(["reflector", "-c", country, "--sort", "rate", "--save", "/etc/pacman.d/mirrorlist"], check=True)
        print("✓ Mirrorlist updated successfully")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f" Warning: Failed to update mirrorlist with reflector: {e}")
        print("This could affect download speeds, but the installation can continue.")
        if not confirm("Do you want to continue with the installation?"):
            print("Aborted.")
            sys.exit(0)
        print("Continuing with installation...")
    
    run_command(["pacman", "-Syy"])
    run_command(["pacman-key", "--init"])
    run_command(["pacman-key", "--populate"])

    run_command(["mkfs.fat", "-F32", f"/dev/{part1}"])
    run_command(["mkswap", f"/dev/{part2}"])
    run_command(["swapon", f"/dev/{part2}"])
    run_command(["mkfs.btrfs", f"/dev/{part3}"])

    run_command(["mount", f"/dev/{part3}", "/mnt"])
    run_command(["btrfs", "su", "cr", "/mnt/@"])
    run_command(["btrfs", "su", "cr", "/mnt/@home"])
    run_command(["btrfs", "su", "cr", "/mnt/@var"])
    run_command(["btrfs", "su", "cr", "/mnt/@snapshots"])
    run_command(["umount", "/mnt"])

    run_command(["mount", "-o", "noatime,compress=lzo,space_cache=v2,subvol=@", f"/dev/{part3}", "/mnt"])
    run_command(["mkdir", "-p", "/mnt/boot", "/mnt/var", "/mnt/home", "/mnt/.snapshots"])
    run_command(["mount", "-o", "noatime,compress=lzo,space_cache=v2,subvol=@home", f"/dev/{part3}", "/mnt/home"])
    run_command(["mount", "-o", "noatime,compress=lzo,space_cache=v2,subvol=@var", f"/dev/{part3}", "/mnt/var"])
    run_command(["mount", "-o", "noatime,compress=lzo,space_cache=v2,subvol=@snapshots", f"/dev/{part3}", "/mnt/.snapshots"])
    run_command(["mount", f"/dev/{part1}", "/mnt/boot"])

    run_command(["pacstrap", "/mnt", "base", "linux", "linux-firmware", "nano", "neovim", "sof-firmware", "base-devel", "grub", "grub-btrfs", "efibootmgr", "networkmanager", "snapper"])
    
    # Generate fstab
    run_command(["genfstab", "-U", "/mnt", "-f", "/mnt/etc/fstab"])

    # Create chroot script content
    chroot_script = f"""
#!/usr/bin/env bash

ln -sf /usr/share/zoneinfo/{timezone} /etc/localtime
hwclock --systohc
sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" >> /etc/locale.conf
echo "{host_name}" >> /etc/hostname
echo root:{root_pass} | chpasswd

cat <<EOF > /etc/hosts
127.0.0.1 localhost
::1       localhost
127.0.1.1	{host_name}.localdomain	{host_name}
EOF

pacman -S mtools libva-mesa-driver vulkan-nouveau cmake docker xf86-video-nouveau xorg-server xorg-xinit yt-dlp python3 fastfetch whois zsh mesa-utils git dosfstools man less xclip linux-headers reflector hyprland sddm kitty kate 7zip firefox btop vlc smplayer unrar pipewire pipewire-alsa dolphin pipewire-pulse --noconfirm --needed
systemctl enable sddm
systemctl enable NetworkManager
systemctl enable snapper-timeline.timer
systemctl enable snapper-cleanup.timer
systemctl enable grub-btrfsd.service

useradd -m -G wheel,storage,power,audio,video {username}
sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers
echo {username}:{user_pass} | chpasswd

grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg

echo "-------------------------------------------------"
echo "Install Complete, You can reboot now"
echo "-------------------------------------------------"
""".lstrip()

    chroot_path = Path("/mnt/chroot.sh")
    write_file(chroot_path, chroot_script, mode=0o755)

    run_command(["arch-chroot", "/mnt", "sh", "/chroot.sh"])

    print("Arch installation steps completed.")


if __name__ == "__main__":
    main()

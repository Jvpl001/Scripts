#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
import re
import getpass
import argparse
import secrets
import string
from pathlib import Path

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

def ensure_command_exists(command_name: str) -> None:
    """Exit early if a required command is missing from PATH."""
    if shutil.which(command_name) is None:
        print(f"Error: required command '{command_name}' not found in PATH.")
        sys.exit(1)


def run_command(command: list[str], input_text: str | bytes | None = None) -> None:
    """Run a command and exit on failure. Optionally pass stdin input."""
    try:
        if isinstance(input_text, str):
            input_bytes = input_text.encode()
        else:
            input_bytes = input_text
        subprocess.run(command, input=input_bytes, check=True)
    except subprocess.CalledProcessError as error:
        print(f"Command failed: {' '.join(command)}\nExit code: {error.returncode}")
        sys.exit(error.returncode)


def run_capture(command: list[str]) -> str:
    """Run a command and return stdout as text, raising on failure."""
    result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout.decode()


def confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def list_disks() -> None:
    """Display available disks to help the user choose the target device."""
    print("Available disks:")
    subprocess.run(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT"], check=False)


def validate_disk_name(name: str) -> bool:
    """Basic validation for disk base name (e.g., sda, nvme0n1)."""
    return re.fullmatch(r"[a-zA-Z0-9]+", name) is not None


def validate_username(username: str) -> bool:
    """Username must start with a letter/underscore, 3-32 chars, allowed -, _ and digits."""
    return re.fullmatch(r"[a-z_][a-z0-9_-]*", username) is not None and 3 <= len(username) <= 32


def validate_hostname(hostname: str) -> bool:
    """Validate a single-label hostname: 2-63 alphanumeric chars with optional internal hyphens."""
    return re.fullmatch(r"[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?", hostname) is not None and 2 <= len(hostname) <= 63


def compute_partition_names(disk_base: str) -> tuple[str, str, str]:
    """Handle nvme-style names that require a 'p' before the partition number."""
    suffix = "p" if disk_base[-1].isdigit() else ""
    return (f"{disk_base}{suffix}1", f"{disk_base}{suffix}2", f"{disk_base}{suffix}3")


def require_root() -> None:
    """Ensure the script is run as root and system is booted in UEFI mode."""
    if os.geteuid() != 0:
        print("This script must be run as root. Try: sudo python3 Arch-Install-V2.py")
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
    """Write text to a file ensuring parent directories exist and set mode."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        os.chmod(path, mode)
    except Exception as e:
        print(f"Error writing file {path}: {e}")
        sys.exit(1)


def random_password(length: int = 16) -> str:
    """Generate a reasonably strong random password for unattended installs."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> None:
    require_root()

    # CLI arguments for silent/defaulted automation
    parser = argparse.ArgumentParser(description="Arch Linux Installer V2 (btrfs + hyprland)")
    parser.add_argument("--silent", action="store_true", help="Run unattended with default values where possible")
    parser.add_argument("--disk", help="Target disk base name (e.g., sda or nvme0n1)")
    parser.add_argument("--username", default="archuser", help="Username to create (default: archuser)")
    parser.add_argument("--user-pass", dest="user_pass_arg", help="Password for the user (omit to autogenerate in --silent)")
    parser.add_argument("--root-pass", dest="root_pass_arg", help="Password for root (omit to autogenerate in --silent)")
    parser.add_argument("--hostname", default="archlinux", help="System hostname (default: archlinux)")
    parser.add_argument("--country", default="United States", help="Country for reflector (default: United States)")
    parser.add_argument("--timezone", default="UTC", help="Timezone like Region/City (default: UTC)")
    args = parser.parse_args()

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

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    Arch Linux Installer V2                   ║")
    print("║                  btrfs + hyprland Edition                    ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    print("This will DESTROY ALL DATA on the selected disk.")
    list_disks()

    # Get and validate disk selection
    if args.silent and args.disk:
        disk_base = args.disk
        if not validate_disk_name(disk_base):
            print("Invalid --disk name. Use only alphanumeric characters.")
            sys.exit(1)
    else:
        while True:
            provided = args.disk or input("Enter target disk base name (e.g., sda or nvme0n1): ").strip()
            if validate_disk_name(provided):
                disk_base = provided
                break
            print("Invalid disk name. Please use only alphanumeric characters.")

    disk_path = f"/dev/{disk_base}"

    # Ensure target device exists
    if not os.path.exists(disk_path):
        print(f"Error: device {disk_path} does not exist.")
        sys.exit(1)

    # Show current partition table for confirmation
    print(f"\nCurrent partition table for {disk_path}:")
    subprocess.run(["fdisk", "-l", disk_path], check=False)

    if not args.silent:
        if not confirm(f"Proceed to create GPT with 256MB EFI, 4G swap, and rest root on {disk_path}?"):
            print("Aborted.")
            sys.exit(0)

    # Feed fdisk with our script
    print("\nPartitioning...")
    run_command(["fdisk", disk_path], input_text=FDISK_TEMPLATE)

    print("\nResulting partition table:")
    subprocess.run(["fdisk", "-l", disk_path], check=False)

    # Get user credentials with validation
    if args.silent:
        username = args.username
        if not validate_username(username):
            print("Error: --username is invalid.")
            sys.exit(1)
        user_pass = args.user_pass_arg or random_password()
        root_pass = args.root_pass_arg or random_password()
        host_name = args.hostname
        if not validate_hostname(host_name):
            print("Error: --hostname is invalid.")
            sys.exit(1)
        country = args.country
        timezone = args.timezone
        print("Running in silent mode with defaults and generated passwords.")
    else:
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

    # Partition device paths (support nvme style names e.g., nvme0n1p1)
    part1, part2, part3 = compute_partition_names(disk_base)

    print(f"\nUsing partitions: {part1}, {part2}, {part3}")

    # Try to update mirrorlist with reflector, but don't quit if it fails
    try:
        subprocess.run(["reflector", "-c", country, "--sort", "rate", "--save", "/etc/pacman.d/mirrorlist"], check=True)
        print("Mirrorlist updated successfully")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f" Warning: Failed to update mirrorlist with reflector: {e}")
        print("This could affect download speeds, but the installation can continue.")
        if not args.silent:
            if not confirm("Do you want to continue with the installation?"):
                print("Aborted.")
                sys.exit(0)
        print("Continuing with installation...")
    
    run_command(["pacman", "-Syy"])
    run_command(["pacman-key", "--init"])
    run_command(["pacman-key", "--populate"])

    # Track whether we mounted/swapped to cleanup on failure
    mounted = False
    swapped = False
    try:
        run_command(["mkfs.fat", "-F32", f"/dev/{part1}"])
        run_command(["mkswap", f"/dev/{part2}"])
        run_command(["swapon", f"/dev/{part2}"])
        swapped = True
        run_command(["mkfs.btrfs", f"/dev/{part3}"])

        run_command(["mount", f"/dev/{part3}", "/mnt"])
        mounted = True

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
    
        # Generate fstab (capture and write, as genfstab doesn't take an output path)
        fstab = run_capture(["genfstab", "-U", "/mnt"])
        write_file(Path("/mnt/etc/fstab"), fstab, mode=0o644)

        # Create chroot script content (no passwords here for security)
        chroot_script = f"""
#!/usr/bin/env bash
set -euo pipefail

ln -sf /usr/share/zoneinfo/{timezone} /etc/localtime
hwclock --systohc
sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf
echo "{host_name}" > /etc/hostname

cat <<EOF > /etc/hosts
127.0.0.1 localhost
::1       localhost
127.0.1.1 {host_name}.localdomain {host_name}
EOF

pacman -S mtools mesa libva-mesa-driver vulkan-nouveau cmake docker xf86-video-nouveau xorg-server xorg-xinit yt-dlp python3 fastfetch whois zsh mesa-utils git dosfstools man less xclip linux-headers reflector hyprland sddm kitty kate 7zip firefox btop vlc smplayer unrar pipewire pipewire-alsa dolphin pipewire-pulse --noconfirm --needed
systemctl enable sddm
systemctl enable NetworkManager
systemctl enable snapper-timeline.timer
systemctl enable snapper-cleanup.timer
systemctl enable grub-btrfsd.service

useradd -m -G wheel,storage,power,audio,video {username}
sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers

grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg

""".lstrip()

        chroot_path = Path("/mnt/chroot.sh")
        write_file(chroot_path, chroot_script, mode=0o755)

        # Execute the chroot script
        run_command(["arch-chroot", "/mnt", "sh", "/chroot.sh"])

        # Set passwords securely via stdin (not written to disk)
        run_command(["arch-chroot", "/mnt", "chpasswd"], input_text=f"root:{root_pass}\n")
        run_command(["arch-chroot", "/mnt", "chpasswd"], input_text=f"{username}:{user_pass}\n")

    finally:
        # Cleanup mounts/swaps on failure or after completion
        try:
            if mounted:
                subprocess.run(["umount", "-R", "/mnt"], check=False)
        finally:
            if swapped:
                subprocess.run(["swapoff", f"/dev/{part2}"], check=False)

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    Installation Complete!                    ║")
    print("╚══════════════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()

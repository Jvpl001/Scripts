#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
from pathlib import Path


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
        print("This script must be run as root. Try: sudo python3 arch_install_v1.py")
        sys.exit(1)


def write_file(path: Path, content: str, mode: int = 0o755) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    os.chmod(path, mode)


def main() -> None:
    require_root()

    # Ensure essential tools exist
    for dependency in [
        "reflector",
        "pacman",
        "pacman-key",
        "lsblk",
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

    username = input("enter username: ").strip()
    user_pass = input("enter the user password: ").strip()
    root_pass = input("enter root password: ").strip()
    host_name = input("enter the hostname: ").strip()
    country = input("enter you country(example->Iran): ").strip()
    timezone = input("enter you time zone(example->Asia/Tehran): ").strip()

    run_command(["reflector", "-c", country, "--sort", "rate", "--save", "/etc/pacman.d/mirrorlist"])
    run_command(["pacman", "-Syy"])
    run_command(["pacman-key", "--init"])
    run_command(["pacman-key", "--populate"])

    run_command(["lsblk"])
    install_drive = input("enter sdX: ").strip()

    part1 = f"{install_drive}1"
    part2 = f"{install_drive}2"
    part3 = f"{install_drive}3"

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
    run_command(["genfstab", "-U", "/mnt"],)

    # Append fstab into /mnt/etc/fstab
    with open("/mnt/etc/fstab", "a", encoding="utf-8") as fstab_out:
        subprocess.run(["genfstab", "-U", "/mnt"], check=True, stdout=fstab_out)

    # Create chroot script content
    chroot_script = f"""
#!/usr/bin/env bash

ln -sf /usr/share/zoneinfo/{timezone} /etc/localtime
hwclock --systohc
sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" >> /etc/locale.conf
echo "ArchMachine" >> /etc/hostname
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
#!/usr/bin/env python3
import subprocess
import sys
import crypt
from pathlib import Path

from .liberary import confirm
from .liberary import run_command
from .liberary import write_file

def base_install(country: str):

    try:
        subprocess.run(["reflector", "-c", country, "--sort", "rate", "--save", "/etc/pacman.d/mirrorlist"], check=True)
        print("Mirrorlist updated successfully")
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
    run_command(["pacstrap", "/mnt", "base", "linux", "linux-firmware", "nano", "neovim", "sof-firmware", "base-devel", "grub", "grub-btrfs", "efibootmgr", "networkmanager", "snapper"])
    # Instead, capture genfstab output and write it to the target file.
    fstab_content = run_command(["genfstab", "-U", "/mnt"], capture_output=True) or ""
    write_file(Path("/mnt/etc/fstab"), fstab_content, mode=0o644)

def chroot_config(username: str, host_name: str, user_pass: str, root_pass: str, timezone: str, gpu: str):
    chroot_script = f"""
#!/usr/bin/env bash

set -euo pipefail

ln -sf /usr/share/zoneinfo/{timezone} /etc/localtime
hwclock --systohc
sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" >> /etc/locale.conf
echo "{host_name}" >> /etc/hostname
# Note: root password is set after this script runs to avoid storing it on disk.

cat <<EOF > /etc/hosts
127.0.0.1 localhost
::1       localhost
127.0.1.1	{host_name}.localdomain	{host_name}
EOF

pacman -S mtools cmake docker yt-dlp python fastfetch whois zsh git dosfstools man less xclip linux-headers reflector hyprland sddm kitty kate p7zip firefox btop vlc smplayer unrar pipewire pipewire-alsa dolphin pipewire-pulse --noconfirm --needed

# Detect CPU vendor and install only the relevant microcode package.
# This avoids installing both intel-ucode and amd-ucode unnecessarily.
if grep -qi 'GenuineIntel' /proc/cpuinfo; then
  pacman -S intel-ucode --noconfirm --needed
elif grep -qi 'AuthenticAMD' /proc/cpuinfo; then
  pacman -S amd-ucode --noconfirm --needed
else
  echo "Warning: Unknown CPU vendor; skipping microcode installation."
fi

gpu="{gpu}"
case "$gpu" in
  0)
    # Mesa drivers
    pacman -S libva-mesa-driver vulkan-nouveau xf86-video-nouveau xorg-server xorg-xinit mesa-utils mesa --noconfirm --needed ;;
  1)
    # New open kernel Nvidia
    pacman -S dkms libva-nvidia-driver nvidia-open-dkms xorg-server xorg-xinit --noconfirm --needed ;;
  2)
    # Proprietary Nvidia
    pacman -S dkms libva-nvidia-driver nvidia-dkms xorg-server xorg-xinit --noconfirm --needed ;;
  3)
    # Intel
    pacman -S intel-media-driver libva-intel-driver mesa vulkan-intel xorg-server xorg-xinit --noconfirm --needed ;;
  4)
    # VirtualBox
    pacman -S mesa xorg-server xorg-xinit --noconfirm --needed ;;
  *)
    echo "No GPU driver was installed." ;;
esac
systemctl enable sddm
systemctl enable NetworkManager
systemctl enable snapper-timeline.timer
systemctl enable snapper-cleanup.timer
systemctl enable grub-btrfsd.service
systemctl enable docker

useradd -m -G wheel,storage,power,audio,video,docker {username}
sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers
# Note: user password is set after this script runs to avoid storing it on disk.

grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg

    """.lstrip()

    chroot_path = Path("/mnt/chroot.sh")
    write_file(chroot_path, chroot_script, mode=0o755)

    # Run the chroot configuration script first (no passwords inside it)
    run_command(["arch-chroot", "/mnt", "bash", "/chroot.sh"])
    
    # Now set passwords securely using hashed values with chpasswd -e.
    # Using crypt with SHA-512 ensures no plaintext password crosses stdin.
    root_hash = crypt.crypt(root_pass, crypt.mksalt(crypt.METHOD_SHA512))
    user_hash = crypt.crypt(user_pass, crypt.mksalt(crypt.METHOD_SHA512))
    run_command(["arch-chroot", "/mnt", "chpasswd", "-e"], input_text=f"root:{root_hash}\n")
    run_command(["arch-chroot", "/mnt", "chpasswd", "-e"], input_text=f"{username}:{user_hash}\n")
    run_command(["rm", "-f", "/mnt/chroot.sh"])

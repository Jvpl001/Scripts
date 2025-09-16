#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

from .library import confirm
from .library import run_command
from .library import write_file

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
    # Generate fstab and write to file
    try:
        result = subprocess.run(["genfstab", "-U", "/mnt"], check=True, capture_output=True, text=True)
        etc_fstab = Path("/mnt/etc/fstab")
        etc_fstab.parent.mkdir(parents=True, exist_ok=True)
        etc_fstab.write_text(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error generating fstab: {e}")
        sys.exit(1)

def chroot_config(username: str, host_name: str, user_pass: str, root_pass: str, timezone: str, gpu: str):
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

pacman -S mtools cmake docker yt-dlp python3 fastfetch whois zsh git dosfstools man less xclip linux-headers reflector hyprland sddm kitty kate 7zip firefox btop vlc smplayer unrar pipewire pipewire-alsa dolphin pipewire-pulse --noconfirm --needed
#mesa drivers
if [ {gpu} -eq 0 ]; then
    pacman -S libva-mesa-driver vulkan-nouveau xf86-video-nouveau xorg-server xorg-xinit mesa-utils mesa --noconfirm --needed
#new open kernel Nvidia
elif [ {gpu} -eq 1 ]; then
    pacman -S dkms libva-nvidia-driver nvidia-dkms xorg-server xorg-xinit --noconfirm --needed
#Proprietary Nvidia
elif [ {gpu} -eq 2 ]; then
    pacman -S dkms libva-nvidia-driver nvidia-open-dkms xorg-server xorg-xinit --noconfirm --needed
#intel
elif [ {gpu} -eq 3 ]; then
    pacman -S intel-media-driver libva-intel-driver mesa vulkan-intel xorg-server xorg-xinit --noconfirm --needed
#VirtualBox
elif [ {gpu} -eq 4 ]; then
    pacman -S mesa xorg-server xorg-xinit --noconfirm --needed
else
    echo "no gpu driver was installed."
fi
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

""".lstrip()

    chroot_path = Path("/mnt/chroot.sh")
    write_file(chroot_path, chroot_script, mode=0o755)

    run_command(["arch-chroot", "/mnt", "sh", "/chroot.sh"])
    run_command(["rm", "-f", "/mnt/chroot.sh"])
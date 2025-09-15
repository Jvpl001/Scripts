## Features

- GPT partitioning (EFI 256MB, swap 4GB, Btrfs root)
- Btrfs subvolumes with `compress=zstd` for: `@`, `@home`, `@var`, `@snapshots`
- Hyprland + SDDM, NetworkManager, pipewire, base install
- GPU driver selection (Mesa, Nvidia open/proprietary, Intel, VirtualBox)
- Optional resume-from-swap setup (GRUB + mkinitcpio)

## Requirements

- Booted in UEFI mode
- Running as root
- Network access

## Quick Start

### 1. Download and Boot
```bash
# Download the latest Arch Linux ISO
# Boot from USB/DVD in UEFI mode
```

### 2. Run the Installer
- From another USB (example):
```bash
mkdir /mnt/usb && mount /dev/sdX1 /mnt/usb
cp -r /mnt/usb/scripts /root/
```

- From the web:
```bash
git clone https://github.com/Jvpl001/Scripts.git
```

### Prerequisites
```bash
# Verify internet connection
ping archlinux.org

# Update system clock
timedatectl set-ntp true
```

### Install dependencies on the ISO
The Arch ISO usually includes most tools. Ensure Python and Reflector are available:
```bash
pacman -Sy python git --noconfirm --needed
```

### Running the installer
Make the script executable and run it:
```bash
chmod +x /root/scripts/main.py
python3 /root/scripts/main.py
```


- `gpu` options:
  - `0` → Mesa (open-source)
  - `1` → Nvidia open (nvidia-open-dkms)
  - `2` → Nvidia proprietary (nvidia-dkms)
  - `3` → Intel
  - `4` → VirtualBox

Notes:
- If `user_pass` or `root_pass` is absent or set to `CHANGE_ME`, you will be prompted.
- Invalid values (e.g., timezone not found in `/usr/share/zoneinfo`) will trigger a prompt.

## What the installer does

1. `check_requirements`: Ensures UEFI, root, and required commands exist.
2. `user_input`: Collects config values from JSON and/or interactive prompts.
3. `fdisk_setup`:
   - Shows disks
   - Confirms target and partitions (256MB EFI, 4GB swap, rest Btrfs root)
   - Creates Btrfs subvolumes and mounts with `compress=zstd`
4. `base_install`:
   - Sync keys, install base packages and desktop
   - Generate `/mnt/etc/fstab`
   - Writes a `chroot.sh` and runs it inside `arch-chroot` for system config
   - Sets passwords only after `chroot.sh` via `chpasswd` stdin (not stored on disk)
5. `resume_setup` (optional):
   - Detects swap UUID
   - Adds `resume=UUID=...` to GRUB
   - Ensures `resume` + `btrfs` in `mkinitcpio` hooks
   - Rebuilds initramfs and regenerates GRUB config
6. Reboot confirmation

## Troubleshooting

- Reflector fails: The installer will warn and allow you to continue using existing mirrors.
- Missing packages/commands: Ensure your live environment includes all required tools listed above.
- Hibernation not resuming: Ensure you have a swap partition and that `resume_setup` ran (check GRUB cmdline and mkinitcpio hooks).

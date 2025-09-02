# 🐧 Arch Linux Installer V2

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Arch Linux](https://img.shields.io/badge/Arch%20Linux-rolling-blue.svg)](https://archlinux.org/)

Automated Arch Linux installation script with Btrfs filesystem and Hyprland desktop. Supports interactive and fully unattended installs.

## ✨ Features

- 🚀 **Automated Installation** - Interactive and unattended modes
- 💾 **Btrfs Filesystem** - Advanced filesystem with snapshots and compression
- 🖥️ **Hyprland Desktop** - Modern, tiling Wayland compositor
- 🔒 **UEFI Boot Support** - Secure boot with GPT partitioning
- 📦 **Pre-configured Software** - Essential tools and applications included
- 🎯 **Smart Partitioning** - Optimized partition layout (EFI + Swap + Root)
- 🌍 **Mirror Optimization** - Automatic mirror selection for faster downloads
- 🛡️ **Security Features** - Proper user setup with sudo privileges
- 📸 **Snapshot Support** - Btrfs snapshots with Snapper integration

## 🆕 What’s New

- __Silent mode (`--silent`)__ with sensible defaults and optional overrides
- __CLI flags__ for disk, username, passwords, hostname, country, timezone
- __NVMe-aware partitions__ (handles `nvme0n1p1` naming automatically)
- __Secure password handling__ (set via stdin, not written to disk)
- __Correct fstab generation__ (writes output of `genfstab -U /mnt` to `/mnt/etc/fstab`)
- __Cleanup on failure__ (`umount -R /mnt` and `swapoff`) to avoid dirty state

## 🎯 What It Does

This script performs a complete Arch Linux installation including:

1. **System Validation** - Checks UEFI boot mode and root privileges
2. **Disk Partitioning** - Creates GPT table with EFI, swap, and root partitions
3. **Filesystem Setup** - Configures Btrfs with subvolumes (@, @home, @var, @snapshots)
4. **Base Installation** - Installs core system packages
5. **Desktop Environment** - Sets up Hyprland with SDDM display manager
6. **User Configuration** - Creates user account with proper permissions
7. **Bootloader Setup** - Installs and configures GRUB for UEFI
8. **System Services** - Enables essential systemd services
9. **Software Suite** - Installs productivity and entertainment applications

## 📋 Requirements

### System Requirements
- **Arch Linux Live ISO** (latest version recommended)
- **UEFI Boot Mode** (BIOS/Legacy mode not supported)
- **Internet Connection** (for package downloads)
- **Target Disk** (all data will be erased)

### Hardware Requirements
- **Architecture**: x86_64 (64-bit)
- **RAM**: Minimum 2GB, recommended 4GB+
- **Storage**: Minimum 20GB, recommended 50GB+
- **Graphics**: Only Nouveau(Mesa) drivers included

### Software Dependencies
The script checks for these commands and exits early if missing:
- `reflector`, `pacman`, `pacman-key`
- `lsblk`, `fdisk`, `mkfs.fat`, `mkswap`
- `mkfs.btrfs`, `mount`, `btrfs`, `umount`
- `pacstrap`, `genfstab`, `arch-chroot`
- `grub-install`, `grub-mkconfig`

## 🚀 Quick Start

### 1. Download and Boot
```bash
# Download the latest Arch Linux ISO
# Boot from USB/DVD in UEFI mode
```

### 2. Get the Installer

- From another USB (example):
```bash
mkdir /mnt/usb && mount /dev/sdX1 /mnt/usb
cp /mnt/usb/Arch-Install-V2.py /root/
```

- From the web:
```bash
curl -o /root/Arch-Install-V2.py 'https://raw.githubusercontent.com/Jvpl001/Scripts/refs/heads/main/Arch-Install-V2.py'
```

- Manual paste:
```bash
nano /root/Arch-Install-V2.py
# paste file content, then save and exit
```

### Prerequisites
```bash
# Ensure you're booted in UEFI mode
[ -d /sys/firmware/efi ] && echo UEFI || echo BIOS

# Verify internet connection
ping archlinux.org

# Update system clock
timedatectl set-ntp true
```

### Install dependencies on the ISO
The Arch ISO usually includes most tools. Ensure Python and Reflector are available:
```bash
pacman -Sy python reflector --noconfirm --needed
```

### Running the installer (interactive)
Make the script executable and run it:
```bash
chmod +x /root/Arch-Install-V2.py
python3 /root/Arch-Install-V2.py
```

### 3. Follow the Prompts
The script will guide you through:
- Disk selection
- Username and password setup
- Hostname configuration
- Country and timezone selection

## 📖 Detailed Usage

### Command-line options

```
--silent                 Run unattended with defaults (no prompts)
--disk DISK              Target disk base (e.g., sda, nvme0n1)
--username NAME          Username to create (default: archuser)
--user-pass PASS         User password (omit in --silent to autogenerate)
--root-pass PASS         Root password (omit in --silent to autogenerate)
--hostname NAME          Hostname (default: archlinux)
--country NAME           Country for reflector (default: United States)
--timezone ZONE          Timezone like Region/City (default: UTC)
```

### Unattended examples

```bash
# Fully unattended with defaults (prompts suppressed)
python3 /root/Arch-Install-V2.py --silent --disk nvme0n1

# Unattended with custom values
python3 /root/Arch-Install-V2.py \
  --silent \
  --disk sda \
  --username alice \
  --hostname myarch \
  --country Iran \
  --timezone Asia/Tehran

# Unattended with explicit passwords
python3 /root/Arch-Install-V2.py --silent --disk sda --user-pass 'P@ssw0rd!' --root-pass 'R00t!Pass'
```

Notes:
- In `--silent` mode, if passwords are not provided, strong random ones are generated internally.
- The script does not print generated passwords by default.

### Installation Process

1. **Disk Selection**: Choose your target disk (e.g., `sda`, `nvme0n1`)
2. **Confirmation**: Review partition layout before proceeding
3. **User Setup**: Enter username, passwords, and hostname
4. **Localization**: Specify country and timezone
5. **Automated Installation**: Script handles everything else

### What Gets Installed

#### Core System
- Base system packages
- Linux kernel and firmware
- Development tools
- Network management

#### Desktop Environment

- **Hyprland** - Modern tiling Wayland compositor
- **SDDM** - Display manager
- **Kitty** - Terminal emulator
- **Dolphin** - File manager

#### Applications

- **Firefox** - Web browser
- **VLC** - Media player
- **Kate** - Text editor
- **Btop** - System monitor
- **7-Zip** - Archive manager (package: 7zip)

#### Development Tools

- **Git** - Version control
- **Docker** - Containerization
- **CMake** - Build system
- **Python3** - Programming language

#### Graphics
- **Mesa** - Open-source graphics stack
- **Nouveau** - Open-source NVIDIA driver (xf86-video-nouveau + vulkan-nouveau)

## 🔧 Customization

### Modify Package Selection
Edit the `chroot_script` in `Arch-Install-V2.py` to add/remove packages:

```python
pacman -S your-package-here --noconfirm --needed
```

### Change Filesystem Options
Modify Btrfs mount options for different performance characteristics:

```python
# Current: noatime,compress=lzo,space_cache=v2
# Alternative: noatime,compress=zstd,space_cache=v2
```

### Adjust Partition Sizes
Modify the `FDISK_TEMPLATE` in `Arch-Install-V2.py` for different partition layouts:

```python
# EFI: +256M (current)
# Swap: +4G (current)
# Root: rest of disk (current)
```

## 🚨 Important Notes

### ⚠️ Data Loss Warning
**This script will completely erase the target disk. Ensure you have backups of any important data.**

### 🔒 Security Considerations
- Must run as root and in UEFI mode
- Passwords are set via stdin to `chpasswd` (not written to disk)
- User is added to `wheel` with sudo access
- Proper file permissions are set on generated files

### 🐛 Troubleshooting

#### Common Issues
1. **UEFI Mode Required**: Ensure your system boots in UEFI mode
2. **Network Issues**: Check internet connection and mirror availability
3. **Disk Space**: Ensure sufficient space on target disk
4. **Permission Errors**: Script must run with sudo/root privileges

## 📚 Learning Resources

- [Arch Linux Wiki](https://wiki.archlinux.org/)
- [Hyprland Documentation](https://wiki.hyprland.org/)
- [Btrfs Filesystem](https://btrfs.wiki.kernel.org/)
- [UEFI Boot](https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### Development Setup
```bash
# Clone the repository
git clone https://github.com/Jvpl001/Scripts.git
cd Scripts
```

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Arch Linux Team](https://archlinux.org/) for the amazing distribution
- [Hyprland Community](https://github.com/hyprwm/Hyprland) for the desktop environment
- [Btrfs Team](https://btrfs.wiki.kernel.org/) for the filesystem
- All contributors and users of this project

**⭐ If this project helped you, please give it a star!**

*Made with ❤️ for the Arch Linux community*

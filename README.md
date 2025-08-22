# Scripts
## Arch Install Script

A script to automate parts of an Arch Linux setup

> Warning: These scripts will format and modify disks. Double-check targets with `lsblk` and proceed only if you understand the implications.


### Partitioning assumptions (important)
The installer script expects you to have already created three partitions on your target disk:
- 1: EFI System Partition (FAT32)
- 2: swap
- 3: Linux data (Btrfs)

### Requirements
- Run from the official Arch Linux live ISO (UEFI mode recommended).
- Internet connection (Ethernet or Wi‑Fi).
- Root privileges (you are root by default on the live ISO).

### Get the scripts onto the live system
Use one of the following methods after booting the Arch ISO:

- From USB (example):
```bash
mkdir /mnt/usb && mount /dev/sdX1 /mnt/usb
cp /mnt/usb/arch_install_v1.py /root/
```

- From the web (if you host the file):
```bash
curl -o /root/arch_install_v1.py 'https://raw.githubusercontent.com/Jvpl001/Scripts/refs/heads/test/Arch-Install-v1.py'
```

- Manual paste:
```bash
nano /root/arch_install_v1.py
# paste file content, then save and exit
```

- Enable NTP:
```bash
timedatectl set-ntp true
```

### Install dependencies on the ISO
The Arch ISO usually includes most tools. Ensure Python and Reflector are available:
```bash
pacman -Sy python reflector --noconfirm
```

### Running the installer
Make the script executable and run it:
```bash
chmod +x /root/arch_install_v1.py
python3 /root/arch_install_v1.py
```

The script will:
- Format partition 1 as FAT32 for EFI, partition 2 as swap, partition 3 as Btrfs.
- Create Btrfs subvolumes: `@`, `@home`, `@var`, `@snapshots`.
- Mount them with sensible options and proceed with base installation and configuration.

Create the partitions first using `fdisk`, `cgdisk`, or `parted` (GPT). When prompted for `sdX` during the script, enter the disk base (e.g., `sda` or `nvme0n1`). The script uses `X1`, `X2`, and `X3` automatically for the EFI, swap, and Btrfs partitions.

### What the installer configures
- Mirrors via `reflector`
- Base packages via `pacstrap` (including `grub`, `efibootmgr`, `networkmanager`, `snapper`)
- `genfstab` written into `/mnt/etc/fstab`
- Timezone, locale, hostname, hosts
- `sddm`, `NetworkManager`, `snapper` timers, and `grub-btrfsd` enabled
- Creates a user and sets passwords for root and the user
- Installs and configures GRUB for UEFI

### Troubleshooting
- If a command is missing, the scripts will exit with a helpful message. Install the missing tool with `pacman -Sy <package> --noconfirm`.
- Ensure you are booted in UEFI mode (required for `grub-install --target=x86_64-efi`).
- Verify the correct target disk with `lsblk` before proceeding.

### License
See `LICENSE` for details.

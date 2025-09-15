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

Interactive mode:

```bash
python3 main.py
```

Config-driven (prompts only for missing/invalid values):

```bash
python3 main.py --config default_config.json
```

Fully non-interactive (use config and auto-confirm confirmations like partitioning and reboot):

```bash
python3 main.py --config default_config.json --yes
```

## Configuration File

`default_config.json` example:

```json
{
  "country": "Iran",
  "username": "user",
  "host_name": "arch-host",
  "user_pass": "CHANGE_ME",
  "root_pass": "CHANGE_ME",
  "timezone": "Asia/Tehran",
  "gpu": "0"
}
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

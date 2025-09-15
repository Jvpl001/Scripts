# Arch Installer (New-V2)

Fast, opinionated Arch Linux installer with Btrfs subvolumes, Hyprland + SDDM, Docker, and optional resume-from-swap configuration. This directory contains the new installer. The `Scripts-main/` directory is the legacy repository.

## Features

- GPT partitioning (EFI 256MB, swap 4GB, Btrfs root)
- Btrfs subvolumes with `compress=zstd` for: `@`, `@home`, `@var`, `@snapshots`
- Base system install with `pacstrap`
- Hyprland + SDDM desktop, NetworkManager, common utilities
- GPU driver selection (Mesa, Nvidia open/proprietary, Intel, VirtualBox)
- CPU microcode auto-detect (Intel/AMD)
- Optional resume-from-swap setup (GRUB + mkinitcpio)
- Secure password handling (no plaintext passwords written to disk)
- Config-driven installs via `--config` JSON
- Non-interactive confirmations via `--yes`

## Layout

```
New-V2/
  main.py                        # entry point
  default_config.json            # example configuration
  Phases/
    __init__.py
    base_install.py              # base system + chroot config
    check_requirements.py        # root/UEFI/dependencies checks
    cli.py                       # CLI parser ( --config, --yes )
    fdisk_setup.py               # disk selection, partitioning, btrfs mounts
    liberary.py                  # common helpers: run_command, confirm, write_file
    resume_setup.py              # resume-from-swap configuration inside chroot
    user_input.py                # interactive + config-backed prompts
```

## Requirements

- Booted in UEFI mode
- Running as root
- Network access
- Arch ISO or an Arch-based live environment with the following tools available:
  - `reflector`, `pacman`, `pacman-key`, `lsblk`, `fdisk`, `mkfs.fat`, `mkswap`, `swapon`, `mkfs.btrfs`, `mount`, `btrfs`, `umount`, `mkdir`, `pacstrap`, `genfstab`, `arch-chroot`, `ln`, `hwclock`, `sed`, `locale-gen`, `chpasswd`, `systemctl`, `useradd`, `grub-install`, `grub-mkconfig`

The script verifies these via `Phases/check_requirements.py`.

## Warning

This script partitions and formats disks. Double-check the target drive and read prompts carefully. Use at your own risk.

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

## Security

- Passwords are not embedded in any file on disk. They are applied after chroot via `arch-chroot /mnt chpasswd`, using stdin only.
- Consider using hashes and `chpasswd -e` if you need to avoid plaintext over stdin as well.

## Troubleshooting

- Reflector fails: The installer will warn and allow you to continue using existing mirrors.
- Missing packages/commands: Ensure your live environment includes all required tools listed above.
- GPU drivers: If unsure, use `0` (Mesa) for most open-source drivers. Nvidia users may try `1` (new open kernel) first; fallback to `2` (proprietary) if issues arise.
- Hibernation not resuming: Ensure you have a swap partition and that `resume_setup` ran (check GRUB cmdline and mkinitcpio hooks).

## Migrating from Scripts-main

`Scripts-main/` contains your old installer. This `New-V2/` directory is a cleaner, modular rewrite with improved safety, configuration, and defaults. Prefer `New-V2/` going forward.

## License

MIT (same as original repository unless otherwise specified).

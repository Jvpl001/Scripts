#!/usr/bin/env python3
from pathlib import Path
from .liberary import run_command, write_file


def configure_resume():
    """
    Set up kernel resume-from-swap inside the target system.

    This will:
    - Detect the first swap partition UUID
    - Add resume=UUID=... to GRUB_CMDLINE_LINUX in /etc/default/grub
    - Ensure 'resume' and 'btrfs' exist in mkinitcpio HOOKS
    - Rebuild initramfs and regenerate GRUB config

    Implemented via a short script executed in arch-chroot to keep changes contained.
    """
    script = """
#!/usr/bin/env bash
set -euo pipefail

# Find a swap UUID
SWAP_UUID=$(blkid -t TYPE=swap -o value -s UUID | head -n1 || true)
if [[ -z "${SWAP_UUID}" ]]; then
  echo "No swap UUID detected; skipping resume configuration."
  exit 0
fi

echo "Detected swap UUID: ${SWAP_UUID}"

# Update GRUB_CMDLINE_LINUX to include resume parameter
# If resume already exists, replace its value; otherwise append it.
if grep -q '^GRUB_CMDLINE_LINUX=' /etc/default/grub; then
  if grep -q 'resume=UUID=' /etc/default/grub; then
    sed -i -E "s#resume=UUID=[^\" ]+#resume=UUID=${SWAP_UUID}#" /etc/default/grub
  else
    sed -i -E "s#^(GRUB_CMDLINE_LINUX=\".*)\"$#\1 resume=UUID=${SWAP_UUID}\"#" /etc/default/grub
  fi
else
  echo "GRUB_CMDLINE_LINUX=\"resume=UUID=${SWAP_UUID}\"" >> /etc/default/grub
fi

# Ensure 'resume' and 'btrfs' are present in mkinitcpio HOOKS before 'filesystems'
if grep -q '^HOOKS=' /etc/mkinitcpio.conf; then
  # Normalize to a single line for sed processing
  sed -i -E 's/\s+/ /g' /etc/mkinitcpio.conf
  # Insert btrfs if missing
  if ! grep -qE 'HOOKS=.*\bbtrfs\b' /etc/mkinitcpio.conf; then
    sed -i -E 's/(HOOKS=\(.*)( filesystems)/\1 btrfs\2/' /etc/mkinitcpio.conf
  fi
  # Insert resume if missing
  if ! grep -qE 'HOOKS=.*\bresume\b' /etc/mkinitcpio.conf; then
    sed -i -E 's/(HOOKS=\(.*)( filesystems)/\1 resume\2/' /etc/mkinitcpio.conf
  fi
fi

# Rebuild initramfs and regenerate GRUB config
mkinitcpio -P
grub-mkconfig -o /boot/grub/grub.cfg
""".lstrip()

    path = Path("/mnt/resume_setup.sh")
    write_file(path, script, mode=0o755)

    # Execute inside chroot and then remove the script
    run_command(["arch-chroot", "/mnt", "bash", "/resume_setup.sh"])
    run_command(["rm", "-f", "/mnt/resume_setup.sh"])

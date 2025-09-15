#!/usr/bin/env python3

from Phases.check_requirements import require_root
from Phases.check_requirements import ensure_dependencies
from Phases.check_requirements import checkUEFI

from Phases.liberary import run_command
from Phases.liberary import confirm

from Phases.fdisk_setup import list_disks
from Phases.fdisk_setup import run_fdisk

from Phases.base_install import base_install
from Phases.base_install import chroot_config
from Phases.user_input import get_install_config
from Phases.resume_setup import configure_resume
from Phases.cli import parse_args, set_auto_yes

def  main():
    # Parse CLI options (e.g., --config PATH) and load config if provided
    args = parse_args()
    # If --yes is passed, auto-confirm confirmation prompts
    set_auto_yes(getattr(args, 'yes', False))

    checkUEFI()
    require_root()
    ensure_dependencies()
    
    config = get_install_config(args.config)

    list_disks()
    run_fdisk()
    base_install(config.country)
    chroot_config(config.username, config.host_name, config.user_pass, config.root_pass, config.timezone, config.gpu)
    # Configure kernel resume-from-swap (hibernation). Safe to run even if no swap is present.
    configure_resume()
    if confirm("Do you want to reboot?"):
            run_command(["reboot"])

if __name__ == "__main__":
    main()
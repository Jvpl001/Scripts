#!/usr/bin/env python3

from phases.check_requirements import require_root
from phases.check_requirements import ensure_dependencies
from phases.check_requirements import checkUEFI

from phases.library import run_command
from phases.library import confirm

from phases.fdisk_setup import list_disks
from phases.fdisk_setup import run_fdisk

from phases.base_install import base_install
from phases.base_install import chroot_config
from phases.user_inputs import prompt_user_inputs

def main() -> None:
    
    checkUEFI()
    require_root()
    ensure_dependencies()
    
    country, username, host_name, user_pass, root_pass, timezone, gpu = prompt_user_inputs()

    list_disks()
    run_fdisk()
    base_install(country)
    chroot_config(username, host_name, user_pass, root_pass, timezone, gpu)
    if confirm("Do you want to reboot?"):
        run_command(["reboot"])

if __name__ == "__main__":
    main()
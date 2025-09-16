#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import re
import getpass
from typing import List
from pathlib import Path

from check_requirements import require_root
from check_requirements import ensure_command_exists
from check_requirements import checkUEFI

from liberary import run_command
from liberary import confirm

from fdisk_setup import list_disks
from fdisk_setup import run_fdisk

from base_install import base_install
from base_install import chroot_config

def  main():
    
    checkUEFI()
    require_root()
    ensure_command_exists()
    
    country=input("Enter your country (example->Iran): ").strip()
    username=input("Enter username: ").strip()
    host_name=input("Enter the hostname: ").strip()
    user_pass = getpass.getpass("Enter the user password: ")
    root_pass = getpass.getpass("Enter root password: ")
    timezone=input("Enter your timezone (example->Asia/Tehran): ").strip()
    gpu=input("select the graphics driver.\n0->mesa\n1->new open nvidia\n2->proprietary Nvidia\n3->intel\n4->VirtualBox").strip()

    list_disks()
    run_fdisk()
    base_install(country)
    chroot_config(username, host_name, user_pass, root_pass, timezone, gpu)
    if confirm("Do you want to reboot?"):
            run_command(["reboot"])

if __name__ == "__main__":
    main()
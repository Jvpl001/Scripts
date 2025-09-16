#!/usr/bin/env python3
import getpass


def prompt_user_inputs():
    """Prompt the user for all required installation inputs.

    Returns:
        tuple: (country, username, host_name, user_pass, root_pass, timezone, gpu)
    """
    country = input("Enter your country (e.g., Iran): ").strip()
    username = input("Enter username: ").strip()
    host_name = input("Enter the hostname: ").strip()
    user_pass = getpass.getpass("Enter the user password: ")
    root_pass = getpass.getpass("Enter root password: ")
    timezone = input("Enter your timezone (e.g., Asia/Tehran): ").strip()
    gpu = input(
        "Select the graphics driver (0-4):\n"
        "0 -> Mesa (open-source)\n"
        "1 -> NVIDIA (open kernel)\n"
        "2 -> NVIDIA (proprietary)\n"
        "3 -> Intel\n"
        "4 -> VirtualBox\n"
        "Your choice: "
    ).strip()

    return country, username, host_name, user_pass, root_pass, timezone, gpu

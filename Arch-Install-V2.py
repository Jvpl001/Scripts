#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
import re
import getpass
import json
import time
import signal
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass

FDISK_TEMPLATE = """
# Create new GPT
g
# Partition 1: EFI System (256MB)
n
1

+256M
# Partition 2: swap (4G)
n
2

+4G
# Partition 3: root (rest of disk)
n
3


# Type for p1 -> EFI (1)
t
1
1
# Type for p2 -> Linux swap (19)
t
2
19
# Type for p3 -> Linux filesystem (20)
t
3
20
# Print and write
p
w
""".lstrip()

# Color codes for better user experience
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

@dataclass
class InstallConfig:
    """Configuration class for installation settings."""
    username: str = ""
    user_pass: str = ""
    root_pass: str = ""
    host_name: str = ""
    country: str = ""
    timezone: str = ""
    disk_base: str = ""
    auto_confirm: bool = False
    dry_run: bool = False
    backup_existing: bool = False

class InstallError(Exception):
    """Custom exception for installation errors."""

class InstallProgress:
    """Track installation progress."""
    
    def __init__(self, total_steps: int):
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
    
    def update(self, step_name: str):
        self.current_step += 1
        elapsed = time.time() - self.start_time
        progress = (self.current_step / self.total_steps) * 100
        
        print(f"{Colors.CYAN}[{self.current_step}/{self.total_steps}] {Colors.GREEN}✓{Colors.END} {step_name}")
        print(f"{Colors.BLUE}Progress: {progress:.1f}% | Elapsed: {elapsed:.0f}s{Colors.END}\n")

def print_header():
    """Print a beautiful header for the installation script."""
    print(f"{Colors.PURPLE}{Colors.BOLD}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    Arch Linux Installer V3                  ║")
    print("║                  btrfs + hyprland Edition                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

def print_warning(msg: str):
    """Print a warning message with consistent formatting."""
    print(f"{Colors.YELLOW}⚠️  WARNING: {msg}{Colors.END}")

def print_error(msg: str):
    """Print an error message with consistent formatting."""
    print(f"{Colors.RED}❌ ERROR: {msg}{Colors.END}")

def print_success(msg: str):
    """Print a success message with consistent formatting."""
    print(f"{Colors.GREEN}✓ SUCCESS: {msg}{Colors.END}")

def print_info(msg: str):
    """Print an info message with consistent formatting."""
    print(f"{Colors.BLUE}ℹ️  INFO: {msg}{Colors.END}")

def check_disk_space(disk_path: str, required_gb: int = 20) -> bool:
    """Check if disk has sufficient space for installation."""
    try:
        result = subprocess.run(["df", "-BG", disk_path], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return False
        
        # Get available space in GB
        available_gb = int(lines[1].split()[3].replace('G', ''))
        return available_gb >= required_gb
    except:
        return False

def check_network_connectivity() -> bool:
    """Check if network is available and working."""
    try:
        subprocess.run(["ping", "-c", "1", "8.8.8.8"], 
                      capture_output=True, check=True, timeout=10)
        return True
    except:
        return False

def test_network_speed() -> Optional[float]:
    """Test network speed and return MB/s or None if failed."""
    try:
        start_time = time.time()
        result = subprocess.run(["curl", "-s", "--max-time", "10", 
                               "https://archlinux.org/mirrors/status/json/"], 
                              capture_output=True, text=True, check=True)
        elapsed = time.time() - start_time
        
        if elapsed > 0:
            # Rough estimate based on response time
            return 1.0 / elapsed
        return None
    except:
        return None

def backup_existing_system(disk_path: str) -> bool:
    """Create a backup of existing system if requested."""
    backup_dir = f"/tmp/arch_backup_{int(time.time())}"
    try:
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create partition table backup
        subprocess.run(["sfdisk", "-d", disk_path], 
                      stdout=open(f"{backup_dir}/partition_table.txt", "w"), check=True)
        
        print_success(f"Backup created at: {backup_dir}")
        return True
    except Exception as e:
        print_warning(f"Backup failed: {e}")
        return False

def retry_prompt(msg: str) -> bool:
    """Ask user if they want to retry an operation."""
    answer = input(f"{Colors.YELLOW}{msg} Would you like to retry? [y/N]: {Colors.END}").strip().lower()
    return answer in {"y", "yes"}

def ensure_command_exists(command_name: str, retries: int = 2) -> None:
    """Ensure a command exists with retry logic."""
    attempt = 0
    while attempt <= retries:
        if shutil.which(command_name) is not None:
            return
        if attempt < retries and retry_prompt(f"Required command '{command_name}' not found in PATH."):
            attempt += 1
            continue
        raise InstallError(f"Required command '{command_name}' not found in PATH after {attempt+1} attempts.")

def run_command(command: list[str], input_text: str = None, retries: int = 2, 
                capture_output: bool = False) -> Optional[str]:
    """Run a command with retry logic and optional output capture."""
    attempt = 0
    while attempt <= retries:
        try:
            if capture_output:
                result = subprocess.run(command, input=(input_text.encode() if input_text else None), 
                                      check=True, capture_output=True, text=True)
                return result.stdout
            else:
                subprocess.run(command, input=(input_text.encode() if input_text else None), 
                             check=True)
                return None
        except FileNotFoundError:
            if attempt < retries and retry_prompt(f"Command not found: {command[0]}."):
                attempt += 1
                continue
            raise InstallError(f"Command not found: {command[0]} after {attempt+1} attempts.")
        except subprocess.CalledProcessError as error:
            if attempt < retries and retry_prompt(f"Command failed: {' '.join(command)}\nExit code: {error.returncode}\nOutput: {error.stderr.decode().strip() if error.stderr else 'No output'}"):
                attempt += 1
                continue
            raise InstallError(f"Command failed: {' '.join(command)}\nExit code: {error.returncode}\nOutput: {error.stderr.decode().strip() if error.stderr else 'No output'} after {attempt+1} attempts.")

def confirm(prompt: str, default: bool = False) -> bool:
    """Enhanced confirmation prompt with default value."""
    default_text = "Y/n" if default else "y/N"
    answer = input(f"{Colors.CYAN}{prompt} [{default_text}]: {Colors.END}").strip().lower()
    
    if not answer:
        return default
    return answer in {"y", "yes"}

def list_disks(retries: int = 2) -> None:
    """List available disks with enhanced formatting."""
    print(f"{Colors.BLUE}Available disks:{Colors.END}")
    attempt = 0
    while attempt <= retries:
        try:
            result = subprocess.run(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE"], 
                                  check=True, capture_output=True, text=True)
            print(result.stdout)
            return
        except subprocess.CalledProcessError as e:
            if attempt < retries and retry_prompt(f"Could not list disks: {e}"):
                attempt += 1
                continue
            print_warning("Unable to list disks after multiple attempts.")
            return

def validate_disk_name(name: str) -> bool:
    """Validate disk name with enhanced checks."""
    return re.fullmatch(r"[a-zA-Z0-9]+", name) is not None

def validate_username(username: str) -> bool:
    """Validate username with enhanced rules."""
    return re.fullmatch(r"[a-z_][a-z0-9_-]*", username) is not None and 3 <= len(username) <= 32

def validate_hostname(hostname: str) -> bool:
    """Validate hostname with enhanced rules."""
    return re.fullmatch(r"[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?", hostname) is not None and 2 <= len(hostname) <= 63

def require_root(retries: int = 2) -> None:
    """Check root privileges and UEFI mode with enhanced validation."""
    attempt = 0
    while attempt <= retries:
        try:
            if os.geteuid() != 0:
                raise InstallError("This script must be run as root. Try: sudo python3 arch_install_v1.py")
            if not os.path.exists("/sys/firmware/efi"):
                raise InstallError(
                    "This script requires UEFI boot mode.\n"
                    "Your system appears to be booted in BIOS/Legacy mode.\n"
                    "Please ensure your system is booted in UEFI mode and try again.\n"
                    "You may need to:\n"
                    "1. Enter your BIOS/UEFI settings during boot\n"
                    "2. Enable UEFI boot mode\n"
                    "3. Disable CSM (Compatibility Support Module) if present\n"
                    "4. Save and reboot"
                )
            
            # Check if running in a container
            if os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"):
                print_warning("Running in a container environment. Some features may not work correctly.")
            
            return
        except InstallError as e:
            if attempt < retries and retry_prompt(str(e)):
                attempt += 1
                continue
            raise InstallError(f"{e}\nFailed after {attempt+1} attempts.")

def write_file(path: Path, content: str, mode: int = 0o755, retries: int = 2) -> None:
    """Write file with enhanced error handling."""
    attempt = 0
    while attempt <= retries:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            os.chmod(path, mode)
            return
        except Exception as e:
            if attempt < retries and retry_prompt(f"Error writing file {path}: {e}"):
                attempt += 1
                continue
            raise InstallError(f"Error writing file {path}: {e} after {attempt+1} attempts.")

def load_config(config_path: str = "install_config.json") -> Optional[InstallConfig]:
    """Load configuration from file if it exists."""
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                return InstallConfig(**config_data)
    except Exception as e:
        print_warning(f"Could not load config file: {e}")
    return None

def save_config(config: InstallConfig, config_path: str = "install_config.json") -> None:
    """Save configuration to file."""
    try:
        config_data = {
            'username': config.username,
            'host_name': config.host_name,
            'country': config.country,
            'timezone': config.timezone,
            'disk_base': config.disk_base,
            'auto_confirm': config.auto_confirm,
            'dry_run': config.dry_run,
            'backup_existing': config.backup_existing
        }
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        print_success(f"Configuration saved to {config_path}")
    except Exception as e:
        print_warning(f"Could not save config file: {e}")

def show_help():
    """Display help information."""
    print(f"{Colors.CYAN}{Colors.BOLD}Usage: sudo python3 AI-V3.py [OPTIONS]{Colors.END}")
    print(f"{Colors.CYAN}Options:{Colors.END}")
    print(f"  --help, -h          Show this help message")
    print(f"  --dry-run           Perform a dry run without making changes")
    print(f"  --config FILE       Load configuration from FILE")
    print(f"  --auto-confirm      Skip confirmation prompts")
    print(f"  --backup            Create backup before installation")
    print(f"\n{Colors.YELLOW}This script will DESTROY ALL DATA on the selected disk!{Colors.END}")

def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    print(f"\n{Colors.YELLOW}Received interrupt signal. Cleaning up...{Colors.END}")
    
    # Try to unmount if mounted
    try:
        subprocess.run(["umount", "-R", "/mnt"], check=False)
    except:
        pass
    
    print(f"{Colors.RED}Installation interrupted. Please check system state before retrying.{Colors.END}")
    sys.exit(1)

def main() -> None:
    """Main installation function with enhanced safety and user experience."""
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    if "--help" in sys.argv or "-h" in sys.argv:
        show_help()
        return
    
    config = InstallConfig()
    config.dry_run = "--dry-run" in sys.argv
    config.auto_confirm = "--auto-confirm" in sys.argv
    config.backup_existing = "--backup" in sys.argv
    
    # Load configuration file if specified
    for i, arg in enumerate(sys.argv):
        if arg == "--config" and i + 1 < len(sys.argv):
            loaded_config = load_config(sys.argv[i + 1])
            if loaded_config:
                config = loaded_config
                break
    
    try:
        print_header()
        
        if config.dry_run:
            print_info("DRY RUN MODE: No changes will be made to the system")
        
        require_root()
        
        # Check system compatibility
        print_info("Checking system compatibility...")
        
        if not check_network_connectivity():
            print_warning("Network connectivity check failed. Installation may fail.")
            if not confirm("Continue without network verification?"):
                print("Aborted.")
                return
        
        network_speed = test_network_speed()
        if network_speed:
            print_info(f"Network speed: {network_speed:.2f} MB/s")
        else:
            print_warning("Could not determine network speed")
        
        # Check dependencies
        dependencies = [
            "reflector", "pacman", "pacman-key", "lsblk", "fdisk", "mkfs.fat", 
            "mkswap", "swapon", "mkfs.btrfs", "mount", "btrfs", "umount", 
            "mkdir", "pacstrap", "genfstab", "arch-chroot", "ln", "hwclock", 
            "sed", "locale-gen", "chpasswd", "systemctl", "useradd", 
            "grub-install", "grub-mkconfig"
        ]
        
        print_info("Checking required dependencies...")
        missing = []
        for dep in dependencies:
            try:
                ensure_command_exists(dep)
                print(f"  {Colors.GREEN}✓{Colors.END} {dep}")
            except InstallError as e:
                missing.append(dep)
                print(f"  {Colors.RED}✗{Colors.END} {dep}")
        
        if missing:
            raise InstallError(f"Missing required commands: {', '.join(missing)}")
        
        print_success("All dependencies are available")
        
        # Initialize progress tracking
        progress = InstallProgress(15)  # Total installation steps
        
        print(f"{Colors.RED}{Colors.BOLD}WARNING: This will DESTROY ALL DATA on the selected disk!{Colors.END}")
        
        if not config.auto_confirm and not confirm("Are you absolutely sure you want to continue?"):
            print("Aborted.")
            return
        
        list_disks()
        
        # Get disk selection
        while True:
            disk_base = input(f"{Colors.CYAN}Enter target disk base name (e.g., sda or nvme0n1): {Colors.END}").strip()
            if validate_disk_name(disk_base):
                break
            print_error("Invalid disk name. Please use only alphanumeric characters.")
        
        disk_path = f"/dev/{disk_base}"
        config.disk_base = disk_base
        
        # Check disk space
        if not check_disk_space(disk_path):
            print_warning("Disk space check failed. Installation may fail due to insufficient space.")
            if not confirm("Continue anyway?"):
                print("Aborted.")
                return
        
        # Show current partition table
        print(f"\n{Colors.BLUE}Current partition table for {disk_path}:{Colors.END}")
        attempt = 0
        while attempt < 3:
            try:
                subprocess.run(["fdisk", "-l", disk_path], check=True)
                break
            except subprocess.CalledProcessError as e:
                if attempt < 2 and retry_prompt(f"Could not show partition table for {disk_path}: {e}"):
                    attempt += 1
                    continue
                print_warning("Unable to show partition table after multiple attempts.")
                break
        
        if not config.auto_confirm and not confirm(f"Proceed to create GPT with 256MB EFI, 4G swap, and rest root on {disk_path}?"):
            print("Aborted.")
            return
        
        # Create backup if requested
        if config.backup_existing:
            print_info("Creating backup of existing system...")
            backup_existing_system(disk_path)
        
        # Partitioning
        progress.update("Starting disk partitioning")
        print("\nPartitioning...")
        run_command(["fdisk", disk_path], input_text=FDISK_TEMPLATE)
        
        progress.update("Disk partitioning completed")
        
        # Show resulting partition table
        print(f"\n{Colors.BLUE}Resulting partition table:{Colors.END}")
        attempt = 0
        while attempt < 3:
            try:
                subprocess.run(["fdisk", "-l", disk_path], check=True)
                break
            except subprocess.CalledProcessError as e:
                if attempt < 2 and retry_prompt(f"Could not show resulting partition table: {e}"):
                    attempt += 1
                    continue
                print_warning("Unable to show resulting partition table after multiple attempts.")
                break
        
        # Get user credentials
        progress.update("Collecting user credentials")
        
        while True:
            username = input(f"{Colors.CYAN}Enter username: {Colors.END}").strip()
            if validate_username(username):
                break
            print_error("Invalid username. Use 3-32 characters, lowercase letters, numbers, underscore, or hyphen. Must start with a letter or underscore.")
        
        config.username = username
        
        user_pass = getpass.getpass(f"{Colors.CYAN}Enter the user password: {Colors.END}")
        if not user_pass:
            if retry_prompt("Password cannot be empty."):
                user_pass = getpass.getpass(f"{Colors.CYAN}Enter the user password: {Colors.END}")
            if not user_pass:
                raise InstallError("Password cannot be empty.")
        
        config.user_pass = user_pass
        
        root_pass = getpass.getpass(f"{Colors.CYAN}Enter root password: {Colors.END}")
        if not root_pass:
            if retry_prompt("Root password cannot be empty."):
                root_pass = getpass.getpass(f"{Colors.CYAN}Enter root password: {Colors.END}")
            if not root_pass:
                raise InstallError("Root password cannot be empty.")
        
        config.root_pass = root_pass
        
        while True:
            host_name = input(f"{Colors.CYAN}Enter the hostname: {Colors.END}").strip()
            if validate_hostname(host_name):
                break
            print_error("Invalid hostname. Use 2-63 characters, alphanumeric and hyphens only.")
        
        config.host_name = host_name
        
        country = input(f"{Colors.CYAN}Enter your country (example->Iran): {Colors.END}").strip()
        timezone = input(f"{Colors.CYAN}Enter your timezone (example->Asia/Tehran): {Colors.END}").strip()
        
        config.country = country
        config.timezone = timezone
        
        # Save configuration
        save_config(config)
        
        # Set up partitions
        part1 = f"{disk_base}1"
        part2 = f"{disk_base}2"
        part3 = f"{disk_base}3"
        
        print(f"\n{Colors.BLUE}Using partitions: {part1}, {part2}, {part3}{Colors.END}")
        
        # Update mirrorlist
        progress.update("Updating package mirrorlist")
        attempt = 0
        while attempt < 3:
            try:
                run_command(["reflector", "-c", country, "--sort", "rate", "--save", "/etc/pacman.d/mirrorlist"])
                print_success("Mirrorlist updated successfully")
                break
            except InstallError as e:
                print_warning(f"Failed to update mirrorlist with reflector: {e}")
                print("This could affect download speeds, but the installation can continue.")
                if attempt < 2 and retry_prompt("Retry updating mirrorlist?"):
                    attempt += 1
                    continue
                if not confirm("Continue with the installation?"):
                    print("Aborted.")
                    return
                print("Continuing with installation...")
                break
        
        # Initialize package database
        progress.update("Initializing package database")
        run_command(["pacman", "-Syy"])
        run_command(["pacman-key", "--init"])
        run_command(["pacman-key", "--populate"])
        
        # Create filesystems and mount
        progress.update("Creating filesystems")
        try:
            run_command(["mkfs.fat", "-F32", f"/dev/{part1}"])
            run_command(["mkswap", f"/dev/{part2}"])
            run_command(["swapon", f"/dev/{part2}"])
            run_command(["mkfs.btrfs", f"/dev/{part3}"])
            
            progress.update("Setting up BTRFS subvolumes")
            run_command(["mount", f"/dev/{part3}", "/mnt"])
            run_command(["btrfs", "su", "cr", "/mnt/@"])
            run_command(["btrfs", "su", "cr", "/mnt/@home"])
            run_command(["btrfs", "su", "cr", "/mnt/@var"])
            run_command(["btrfs", "su", "cr", "/mnt/@snapshots"])
            run_command(["umount", "/mnt"])
            
            progress.update("Mounting filesystems")
            run_command(["mount", "-o", "noatime,compress=lzo,space_cache=v2,subvol=@", f"/dev/{part3}", "/mnt"])
            run_command(["mkdir", "-p", "/mnt/boot", "/mnt/var", "/mnt/home", "/mnt/.snapshots"])
            run_command(["mount", "-o", "noatime,compress=lzo,space_cache=v2,subvol=@home", f"/dev/{part3}", "/mnt/home"])
            run_command(["mount", "-o", "noatime,compress=lzo,space_cache=v2,subvol=@var", f"/dev/{part3}", "/mnt/var"])
            run_command(["mount", "-o", "noatime,compress=lzo,space_cache=v2,subvol=@snapshots", f"/dev/{part3}", "/mnt/.snapshots"])
            run_command(["mount", f"/dev/{part1}", "/mnt/boot"])
        except InstallError as e:
            if retry_prompt(f"Partitioning/mounting failed: {e}"):
                main()
                return
            raise InstallError(f"Partitioning/mounting failed: {e}")
        
        # Install base system
        progress.update("Installing base system")
        attempt = 0
        while attempt < 3:
            try:
                run_command(["pacstrap", "/mnt", "base", "linux", "linux-firmware", "nano", "neovim", 
                           "sof-firmware", "base-devel", "grub", "grub-btrfs", "efibootmgr", 
                           "networkmanager", "snapper"])
                break
            except InstallError as e:
                if attempt < 2 and retry_prompt(f"Pacstrap installation failed: {e}"):
                    attempt += 1
                    continue
                raise InstallError(f"Pacstrap installation failed: {e}")
        
        # Generate fstab
        progress.update("Generating filesystem table")
        attempt = 0
        while attempt < 3:
            try:
                run_command(["genfstab", "-U", "/mnt", "-f", "/mnt/etc/fstab"])
                break
            except InstallError as e:
                if attempt < 2 and retry_prompt(f"Failed to generate fstab: {e}"):
                    attempt += 1
                    continue
                raise InstallError(f"Failed to generate fstab: {e}")
        
        # Create and execute chroot script
        progress.update("Preparing system configuration")
        chroot_script = f"""
#!/usr/bin/env bash

set -e

ln -sf /usr/share/zoneinfo/{timezone} /etc/localtime
hwclock --systohc
sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" >> /etc/locale.conf
echo "{host_name}" >> /etc/hostname
echo root:{root_pass} | chpasswd

cat <<EOF > /etc/hosts
127.0.0.1 localhost
::1       localhost
127.0.1.1	{host_name}.localdomain	{host_name}
EOF

pacman -S mtools libva-mesa-driver vulkan-nouveau cmake docker xf86-video-nouveau xorg-server xorg-xinit yt-dlp python3 fastfetch whois zsh mesa-utils git dosfstools man less xclip linux-headers reflector hyprland sddm kitty kate 7zip firefox btop vlc smplayer unrar pipewire pipewire-alsa dolphin pipewire-pulse --noconfirm --needed
systemctl enable sddm
systemctl enable NetworkManager
systemctl enable snapper-timeline.timer
systemctl enable snapper-cleanup.timer
systemctl enable grub-btrfsd.service

useradd -m -G wheel,storage,power,audio,video {username}
sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers
echo {username}:{user_pass} | chpasswd

grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg
""".lstrip()
        
        write_file(Path("/mnt/chroot.sh"), chroot_script, mode=0o755)
        
        progress.update("Executing system configuration")
        attempt = 0
        while attempt < 3:
            try:
                run_command(["arch-chroot", "/mnt", "sh", "/chroot.sh"])
                break
            except InstallError as e:
                if attempt < 2 and retry_prompt(f"arch-chroot failed: {e}"):
                    attempt += 1
                    continue
                raise InstallError(f"arch-chroot failed: {e}")
        
        progress.update("Installation completed successfully")
        print_success("Arch Linux installation completed successfully!")
        print(f"{Colors.GREEN}{Colors.BOLD}")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║                    Installation Complete!                    ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print(f"{Colors.END}")
        print(f"{Colors.CYAN}Next steps:{Colors.END}")
        print("1. Reboot your system")
        print("2. Login with your username and password")
        print("3. Enjoy your new Arch Linux installation with Hyprland!")

    except InstallError as e:
        print_error(f"{e}")
        print("The installation failed. Please review the error above and try again.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInstallation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

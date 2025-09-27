# Arch Btrfs + Hyprland Installer (C Version)

This repository contains `Test.c`, a C program that automates an Arch Linux installation using a Btrfs layout and Hyprland desktop packages. It mirrors the logic of the Python implementation under `New-V2/` but runs natively in C on the Arch live ISO.

IMPORTANT: This program performs destructive disk operations (partitioning, formatting, mounting). Run only on the intended target in an Arch live environment, as root, and after double-checking the selected disk.


## Contents
- `Test.c` — the installer program
- `ArchInstall-v1.sh` — the original Bash script (reference)
- `New-V2/` — the Python rewrite (reference)


## High-level Overview
`Test.c` prompts for installation inputs, validates them, provisions the disk using `fdisk` (EFI + swap + root), formats partitions, creates Btrfs subvolumes, installs packages with `pacstrap`, generates `fstab`, writes a `chroot.sh` to configure the system (locale, hostname, users, GPU drivers, services), runs it via `arch-chroot`, then cleans up.


## Function-by-Function Documentation (Test.c)
Below, names reference functions in `Test.c`.

- `trim_newline(char* s)`
  - Removes trailing `\n`/`\r` from an input buffer read via `fgets`.
  - Keeps string parsing consistent. Avoids stray newlines entering shell commands.

- `run_cmd(const char* fmt, ...)`
  - Formats a shell command into a buffer and executes it with `system()`.
  - Prints the command, returns the exit code, and reports failures.
  - Defined with a printf-style interface for performance and convenience; avoids heap allocation by using a fixed-size stack buffer.

- `path_exists(const char* path)`
  - Uses `stat` to check existence of files/directories.
  - Used for UEFI detection (`/sys/firmware/efi`).

- `which_exists(const char* cmd)`
  - Checks if a required binary exists in `PATH` using `command -v`.
  - Ensures early failure if a dependency is missing.

- `require_root()`
  - Exits unless the effective UID is 0.
  - Many operations (partitioning, mounting) require root. Early check saves time.

- `check_uefi()`
  - Verifies that the system booted in UEFI mode by checking `/sys/firmware/efi`.
  - The installer configures GRUB for UEFI; BIOS mode is not supported here.

- `ensure_dependencies()`
  - Verifies presence of all required tools (`reflector`, `pacman`, `fdisk`, `mkfs.btrfs`, `arch-chroot`, etc.).
  - Fails fast with a clear error if something is missing.

- `confirm_prompt(const char* prompt)`
  - Simple `[y/N]` confirmation helper. Returns true only for `y`/`yes`.
  - Prevents accidental destructive steps (e.g., re-partitioning).

- `get_password(const char* prompt, char* out, size_t out_sz)`
  - Reads a password from TTY with echo disabled using `termios`.
  - Prevents secrets from appearing on screen or in scrollback.

- Validators:
  - `validate_username(const char* s)` — allows `[A-Za-z0-9_-]`, length 1..32.
  - `validate_hostname(const char* s)` — simple RFC-1035-ish hostname validation.
  - `validate_country(const char* s)` — letters/spaces only, length 1..64.
  - `validate_timezone(const char* s)` — allows `[A-Za-z0-9_/-]` and requires at least one `/`.
  - `validate_gpu_choice(const char* s)` — must be a single digit `0..4`.
  - `validate_disk_name(const char* name)` — allows `sd[a-z]` or `nvme<d>n<d>`.
  - These reduce bad inputs and injection risk.

- `shell_escape_single_quotes(const char* in, char* out, size_t out_sz)`
  - Escapes single quotes for inclusion in single-quoted shell strings (`'` -> `'\''`).
  - Used when embedding user-provided strings (hostname, passwords) into the generated `chroot.sh` script.

- `main(void)`
  - Overall coordinator. See the next section for a detailed flow.


## Why functions are designed this way
- __Stack buffers over heap__: The program primarily uses fixed-size stack buffers for inputs and commands. This avoids heap allocations and keeps the program simple, fast, and less error-prone.
- __Fail-fast checks__: `require_root`, `check_uefi`, and `ensure_dependencies` ensure the environment is correct before any destructive actions.
- __Minimal shell surface__: All shell executions are funneled through `run_cmd`, and sensitive inputs embedded into scripts are escaped with `shell_escape_single_quotes` and piped to `chpasswd` via `printf` to avoid interpretation issues.
- __Validation-first__: Inputs are validated immediately after reading to catch mistakes early.
- __Heredoc for fdisk__: Using a heredoc to feed `fdisk` avoids tricky quoting with `printf` and is robust against content changes.


## Memory Management
- __No manual heap allocation__: The code uses fixed-size arrays (stack) for user input and commands.
- __Kernel-managed pipes/files__: `popen` and `fopen` are used to read `genfstab` output and write `/mnt/chroot.sh`. These are closed with `pclose`/`fclose` as soon as possible to avoid leaks.
- __No global state requiring cleanup__: Beyond closing descriptors and generated files (`/mnt/chroot.sh`), there is no dynamic memory to free.


## How `main()` works (step-by-step)
1. __Environment checks__
   - Calls `require_root()`, `check_uefi()`, and `ensure_dependencies()`.
2. __Prompt and validate inputs__
   - Country, username, hostname, masked user/root passwords, timezone, GPU choice (0..4).
   - Validation rejects malformed input and exits with a clear message.
3. __Mirrorlist and keyring setup__
   - Tries `reflector` to update mirrors; on failure, asks user to continue.
   - Runs `pacman -Syy`, `pacman-key --init`, `pacman-key --populate`.
4. __Disk partitioning__
   - Shows disks (`lsblk`).
   - Prompts for device (validated `sdX` or `nvmeXnY`).
   - Shows current `fdisk -l` and asks for confirmation.
   - Feeds GPT template to `fdisk` (EFI 256M, swap 4G, rest root) using a heredoc.
5. __Formatting and subvolumes__
   - Formats EFI (`mkfs.fat -F32`), enables swap (`mkswap`, `swapon`), creates Btrfs on root.
   - Mounts root, creates subvolumes `@`, `@home`, `@var`, `@snapshots`, then remounts with `subvol=@` and mounts the others.
6. __Base install and fstab__
   - `pacstrap` base packages.
   - Captures `genfstab -U /mnt` output and writes to `/mnt/etc/fstab`.
7. __System configuration in chroot__
   - Writes `/mnt/chroot.sh` with:
     - Timezone, `hwclock`, locale generation, `LANG`, hostname, root password.
     - `/etc/hosts` with the chosen hostname.
     - Common desktop packages and GPU-specific drivers based on selection (0..4).
     - Enables services: `sddm`, `NetworkManager`, Snapper timers, `grub-btrfsd`.
     - Creates user, enables sudo for `wheel`, sets user password.
     - Installs and configures GRUB (UEFI).
   - Runs `arch-chroot /mnt sh /chroot.sh` and then deletes the script.
8. __Completion__
   - Prints a final success message.


## Security Hardening Measures
- __Root and UEFI checks__ prevent misconfiguration.
- __Dependency verification__ ensures known-safe tool paths.
- __Input validation__ for username, hostname, timezone, country, GPU choice, and disk name reduces malformed or malicious inputs.
- __Password handling__ uses TTY echo-off and avoids exposing passwords in process args or logs.
- __Shell injection resistance__ via single-quote escaping and `printf | chpasswd` piping.
- __Confirmation prompts__ before destructive operations.


## How to Compile and Run (Arch live ISO)
1. Boot into the Arch Linux live ISO in UEFI mode and connect to the internet.
2. Ensure `gcc` is installed:
   ```bash
   pacman -Sy --noconfirm gcc
   ```
3. Copy `Test.c` to the live environment (via USB or download).
4. Compile with warnings and optimizations:
   ```bash
   gcc -O2 -Wall -Wextra -std=c17 Test.c -o Test
   ```
   Optional syntax-only check:
   ```bash
   gcc -fsyntax-only -Wall -Wextra -std=c17 Test.c
   ```
5. Run the installer:
   ```bash
   sudo ./Test
   ```
6. Follow prompts and confirm partitioning only after verifying the target disk.


## Pros and Cons
- Pros
  - __Fast and minimal__: Single static binary; minimal overhead.
  - __Explicit validation__: Fewer ways to shoot yourself in the foot.
  - __Robust fdisk feeding__: Heredoc is resilient to quoting pitfalls.
  - __Security-conscious__: Masked passwords, escaping, and safe piping.
  - __Parity with Python flow__: Mirrors `New-V2/` logic closely.
- Cons
  - __Portability__: Requires GNU/Linux (Arch live ISO) and specific tools.
  - __Destructive__: Mistakes in disk selection are costly (mitigated with validation/confirmations).
  - __Limited dynamic checks__: Country/timezone validity isn’t verified against actual zoneinfo or ISO lists.
  - __Limited error recovery__: Fails fast; does not roll back partial installs.


## How You Can Improve This Code
- __Add password confirmation__ prompts to detect typos.
- __Verify timezone exists__ by checking `/usr/share/zoneinfo/<tz>` and re-prompt on failure.
- __Whitelist country codes__ for `reflector` or map names -> ISO codes.
- __Better nvme parsing__ using sysfs enumeration instead of regex-like checks.
- __Non-interactive mode__ (flags or env vars) for automation/CI.
- __Logging to a file__ with timestamps for troubleshooting.
- __Safer command execution__ using `fork/execvp` instead of `system()` where feasible.
- __Unit tests__ for validators and escaping helpers.


## Structure and Execution Flow

- Call Graph (simplified)
```
main
 ├─ require_root
 ├─ check_uefi
 ├─ ensure_dependencies ── which_exists
 ├─ Input + validation
 │   ├─ get_password
 │   ├─ validate_username / validate_hostname / validate_country
 │   ├─ validate_timezone / validate_gpu_choice
 ├─ run_cmd("reflector" …) [optional continue]
 ├─ run_cmd("pacman …") x3
 ├─ Disk setup
 │   ├─ run_cmd("lsblk …")
 │   ├─ run_cmd("fdisk -l …")
 │   └─ run_cmd("fdisk < heredoc")
 ├─ Filesystems + subvolumes (run_cmd …)
 ├─ Base install (run_cmd pacstrap)
 ├─ fstab (popen genfstab → fopen write)
 ├─ Write chroot.sh (fopen → fprintf) using shell_escape_single_quotes
 ├─ run_cmd("arch-chroot …")
 ├─ run_cmd("rm /mnt/chroot.sh")
 └─ print completion
```

- Execution Steps (line-by-line style, condensed)
  1. Headers and helpers are compiled.
  2. `main()` executes: environment checks → input prompts + validation.
  3. Mirrors/keyring setup commands run.
  4. Disk selection prompt; prints current partition table; confirmation.
  5. Partition creation via `fdisk` heredoc.
  6. Filesystem creation and Btrfs subvolume setup.
  7. `pacstrap` packages and generate `/mnt/etc/fstab`.
  8. Generate `chroot.sh` with safe-escaped values and GPU logic.
  9. `arch-chroot` runs the script; `chroot.sh` is removed.
  10. Final message printed.


## Safety Checklist Before Running
- You are on the Arch live ISO and in UEFI mode.
- Target disk is correct and not holding data you need.
- Network is up, or you’ve accepted reflector fallback.
- You understand this will format and install Arch on the selected disk.

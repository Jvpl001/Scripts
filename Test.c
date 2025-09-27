#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdbool.h>
#include <sys/stat.h>
#include <unistd.h>
#include <termios.h>
#include <ctype.h>

#define CMD_BUF 4096

static void trim_newline(char *s) {
    if (!s) return;
    size_t n = strlen(s);
    if (n && (s[n-1] == '\n' || s[n-1] == '\r')) s[--n] = '\0';
    if (n && (s[n-1] == '\r')) s[--n] = '\0';
}

// ===== Validation and escaping helpers =====
static bool validate_username(const char *s) {
    size_t n = strlen(s);
    if (n == 0 || n > 32) return false;
    for (size_t i = 0; i < n; ++i) {
        if (!(isalnum((unsigned char)s[i]) || s[i] == '-' || s[i] == '_')) return false;
    }
    return true;
}

static bool validate_hostname(const char *s) {
    size_t n = strlen(s);
    if (n == 0 || n > 253) return false;
    int label_len = 0;
    bool new_label = true;
    for (size_t i = 0; i < n; ++i) {
        unsigned char uc = (unsigned char)s[i];
        char c = (char)tolower(uc);
        if (c == '.') {
            if (label_len == 0) return false;
            if (s[i-1] == '-') return false;
            new_label = true;
            label_len = 0;
        } else if (isalnum((unsigned char)c) || c == '-') {
            if (new_label && c == '-') return false;
            new_label = false;
            if (++label_len > 63) return false;
        } else {
            return false;
        }
    }
    if (label_len == 0) return false;
    if (s[n-1] == '-') return false;
    return true;
}

static bool validate_country(const char *s) {
    size_t n = strlen(s);
    if (n == 0 || n > 64) return false;
    for (size_t i = 0; i < n; ++i) {
        if (!(isalpha((unsigned char)s[i]) || s[i] == ' ')) return false;
    }
    return true;
}

static bool validate_timezone(const char *s) {
    size_t n = strlen(s);
    if (n == 0 || n > 128) return false;
    bool has_slash = false;
    for (size_t i = 0; i < n; ++i) {
        unsigned char uc = (unsigned char)s[i];
        char c = (char)uc;
        if (!(isalnum(uc) || c == '_' || c == '/' || c == '-')) return false;
        if (c == '/') has_slash = true;
    }
    return has_slash;
}

static bool validate_gpu_choice(const char *s) {
    return (strlen(s) == 1 && s[0] >= '0' && s[0] <= '4');
}

static bool validate_disk_name(const char *name) {
    size_t len = strlen(name);
    if (len == 3 && name[0]=='s' && name[1]=='d' && (name[2]>='a' && name[2]<='z')) return true;
    if (strncmp(name, "nvme", 4) == 0) {
        const char *p = name + 4;
        if (!isdigit((unsigned char)*p)) return false;
        while (isdigit((unsigned char)*p)) p++;
        if (*p != 'n') return false;
        p++;
        if (!isdigit((unsigned char)*p)) return false;
        while (isdigit((unsigned char)*p)) p++;
        return *p == '\0';
    }
    return false;
}

// Escape for embedding inside a single-quoted shell string: ' -> '\''
static void shell_escape_single_quotes(const char *in, char *out, size_t out_sz) {
    size_t j = 0;
    for (size_t i = 0; in[i] != '\0' && j + 4 < out_sz; ++i) {
        if (in[i] == '\'') {
            if (j + 4 >= out_sz) break;
            out[j++] = '\'';  // end quote
            out[j++] = '\\';  // backslash
            out[j++] = '\'';  // single quote
            out[j++] = '\'';  // start quote
        } else {
            out[j++] = in[i];
        }
    }
    if (j < out_sz) out[j] = '\0'; else out[out_sz-1] = '\0';
}

static int run_cmd(const char *fmt, ...) {
    char cmd[CMD_BUF];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(cmd, sizeof(cmd), fmt, ap);
    va_end(ap);

    printf("\n=> %s\n", cmd);
    int rc = system(cmd);
    if (rc != 0) {
        fprintf(stderr, "Command failed with code %d: %s\n", rc, cmd);
    }
    return rc;
}

static bool path_exists(const char *path) {
    struct stat st;
    return stat(path, &st) == 0;
}

static bool which_exists(const char *cmd) {
    char buf[CMD_BUF];
    snprintf(buf, sizeof(buf), "bash -lc 'command -v %s >/dev/null 2>&1'", cmd);
    int rc = system(buf);
    return rc == 0;
}

static void require_root(void) {
    if (geteuid() != 0) {
        fprintf(stderr, "This program must be run as root.\n");
        exit(1);
    }
}

static void check_uefi(void) {
    if (!path_exists("/sys/firmware/efi")) {
        fprintf(stderr, "Error: This program requires UEFI boot mode.\n");
        exit(1);
    }
}

static void ensure_dependencies(void) {
    const char *deps[] = {
        "reflector","pacman","pacman-key","lsblk","fdisk","mkfs.fat","mkswap","swapon",
        "mkfs.btrfs","mount","btrfs","umount","mkdir","pacstrap","genfstab","arch-chroot",
        "ln","hwclock","sed","locale-gen","chpasswd","systemctl","useradd","grub-install",
        "grub-mkconfig", NULL
    };
    for (int i = 0; deps[i]; ++i) {
        if (!which_exists(deps[i])) {
            fprintf(stderr, "Error: required command '%s' not found in PATH.\n", deps[i]);
            exit(127);
        }
    }
}

static bool confirm_prompt(const char *prompt) {
    char ans[16];
    printf("%s [y/N]: ", prompt);
    if (!fgets(ans, sizeof(ans), stdin)) return false;
    trim_newline(ans);
    for (char *p = ans; *p; ++p) if (*p >= 'A' && *p <= 'Z') *p = *p - 'A' + 'a';
    return (strcmp(ans, "y") == 0 || strcmp(ans, "yes") == 0);
}

static void get_password(const char *prompt, char *out, size_t out_sz) {
    struct termios oldt, newt;
    printf("%s", prompt);
    fflush(stdout);
    if (tcgetattr(STDIN_FILENO, &oldt) == 0) {
        newt = oldt;
        newt.c_lflag &= ~ECHO;
        tcsetattr(STDIN_FILENO, TCSANOW, &newt);
    }
    if (!fgets(out, out_sz, stdin)) {
        out[0] = '\0';
    }
    if (tcgetattr(STDIN_FILENO, &oldt) == 0) {
        tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
    }
    printf("\n");
    trim_newline(out);
}

int main(void) {
    require_root();
    check_uefi();
    ensure_dependencies();

    char country[128];
    char username[128];
    char host_name[256];
    char user_pass[256];
    char root_pass[256];
    char timezone[256];
    char gpu_choice[16];

    printf("btrfs + hyprland Arch install (C, New-V2 parity)\n");

    printf("Enter your country (e.g., Iran): ");
    if (!fgets(country, sizeof(country), stdin)) return 1; trim_newline(country);
    if (!validate_country(country)) { fprintf(stderr, "Invalid country string. Letters and spaces only.\n"); return 1; }
    printf("Enter username: ");
    if (!fgets(username, sizeof(username), stdin)) return 1; trim_newline(username);
    if (!validate_username(username)) { fprintf(stderr, "Invalid username. Use a-z, 0-9, -, _.\n"); return 1; }
    printf("Enter the hostname: ");
    if (!fgets(host_name, sizeof(host_name), stdin)) return 1; trim_newline(host_name);
    if (!validate_hostname(host_name)) { fprintf(stderr, "Invalid hostname.\n"); return 1; }
    get_password("Enter the user password: ", user_pass, sizeof(user_pass));
    get_password("Enter root password: ", root_pass, sizeof(root_pass));
    printf("Enter your timezone (e.g., Asia/Tehran): ");
    if (!fgets(timezone, sizeof(timezone), stdin)) return 1; trim_newline(timezone);
    if (!validate_timezone(timezone)) { fprintf(stderr, "Invalid timezone.\n"); return 1; }
    printf("Select the graphics driver (0-4):\n0 -> Mesa (open-source)\n1 -> NVIDIA (open kernel)\n2 -> NVIDIA (proprietary)\n3 -> Intel\n4 -> VirtualBox\nYour choice: ");
    if (!fgets(gpu_choice, sizeof(gpu_choice), stdin)) return 1; trim_newline(gpu_choice);
    if (!validate_gpu_choice(gpu_choice)) { fprintf(stderr, "Invalid GPU choice.\n"); return 1; }

    // Mirrorlist and keyring setup with graceful fallback on reflector
    if (run_cmd("reflector -c %s --sort rate --save /etc/pacman.d/mirrorlist", country) != 0) {
        printf(" Warning: Failed to update mirrorlist with reflector. This may affect download speeds.\n");
        if (!confirm_prompt("Do you want to continue with the installation?")) {
            printf("Aborted.\n");
            return 0;
        }
        printf("Continuing with installation...\n");
    }
    if (run_cmd("pacman -Syy")) return 1;
    if (run_cmd("pacman-key --init")) return 1;
    if (run_cmd("pacman-key --populate")) return 1;

    // Disk listing and partitioning via fdisk template
    run_cmd("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT");
    char name[128];
    while (1) {
        printf("Enter the installation drive (e.g., sda or nvme0n1): ");
        if (!fgets(name, sizeof(name), stdin)) return 1; trim_newline(name);
        if (validate_disk_name(name)) break;
        printf("The drive name was incorrect, try again.\n");
    }
    char disk_path[256]; snprintf(disk_path, sizeof(disk_path), "/dev/%s", name);
    run_cmd("fdisk -l %s", disk_path);
    if (!confirm_prompt("Proceed to create GPT with 256MB EFI, 4G swap, and rest root on the selected disk?")) {
        printf("Aborted.\n");
        return 0;
    }
    const char *fdisk_template =
        "g\n"
        "n\n1\n\n+256M\n"
        "n\n2\n\n+4G\n"
        "n\n3\n\n\n"
        "t\n1\n1\n"
        "t\n2\n19\n"
        "t\n3\n20\n"
        "p\n"
        "w\n";
    // Pipe template into fdisk using a heredoc to avoid quoting issues
    if (run_cmd("bash -lc 'cat <<\"EOF\" | fdisk %s\n%s\nEOF'", disk_path, fdisk_template)) return 1;
    run_cmd("fdisk -l %s", disk_path);

    char part1[256], part2[256], part3[256];
    if (strncmp(name, "sd", 2) == 0 && strlen(name) == 3) {
        snprintf(part1, sizeof(part1), "%s1", disk_path);
        snprintf(part2, sizeof(part2), "%s2", disk_path);
        snprintf(part3, sizeof(part3), "%s3", disk_path);
    } else {
        snprintf(part1, sizeof(part1), "%sp1", disk_path);
        snprintf(part2, sizeof(part2), "%sp2", disk_path);
        snprintf(part3, sizeof(part3), "%sp3", disk_path);
    }
    printf("Using partitions: %s, %s, %s\n", part1, part2, part3);

    if (run_cmd("mkfs.fat -F32 %s", part1)) return 1;
    if (run_cmd("mkswap %s", part2)) return 1;
    if (run_cmd("swapon %s", part2)) return 1;
    if (run_cmd("mkfs.btrfs %s", part3)) return 1;

    if (run_cmd("mount %s /mnt", part3)) return 1;
    if (run_cmd("btrfs subvolume create /mnt/@")) return 1;
    if (run_cmd("btrfs subvolume create /mnt/@home")) return 1;
    if (run_cmd("btrfs subvolume create /mnt/@var")) return 1;
    if (run_cmd("btrfs subvolume create /mnt/@snapshots")) return 1;
    if (run_cmd("umount /mnt")) return 1;

    if (run_cmd("mount -o noatime,compress=lzo,space_cache=v2,subvol=@ %s /mnt", part3)) return 1;
    if (run_cmd("mkdir -p /mnt/boot /mnt/var /mnt/home /mnt/.snapshots")) return 1;
    if (run_cmd("mount -o noatime,compress=lzo,space_cache=v2,subvol=@home %s /mnt/home", part3)) return 1;
    if (run_cmd("mount -o noatime,compress=lzo,space_cache=v2,subvol=@var %s /mnt/var", part3)) return 1;
    if (run_cmd("mount -o noatime,compress=lzo,space_cache=v2,subvol=@snapshots %s /mnt/.snapshots", part3)) return 1;
    if (run_cmd("mount %s /mnt/boot", part1)) return 1;

    // Base install
    if (run_cmd("pacstrap /mnt base linux linux-firmware nano neovim sof-firmware base-devel grub grub-btrfs efibootmgr networkmanager snapper")) return 1;

    // Generate fstab by capturing output
    FILE *pf = popen("genfstab -U /mnt", "r");
    if (!pf) { perror("popen genfstab"); return 1; }
    if (system("bash -lc 'mkdir -p /mnt/etc'")) { pclose(pf); return 1; }
    FILE *ff = fopen("/mnt/etc/fstab", "w");
    if (!ff) { perror("fopen /mnt/etc/fstab"); pclose(pf); return 1; }
    char line[8192];
    while (fgets(line, sizeof(line), pf)) fputs(line, ff);
    pclose(pf);
    fclose(ff);

    // Write chroot script matching New-V2 logic
    const char *chroot_path = "/mnt/chroot.sh";
    FILE *f = fopen(chroot_path, "w");
    if (!f) { perror("fopen /mnt/chroot.sh"); return 1; }
    // Prepare escaped values for safe single-quoted embedding
    char esc_root_pass[1024]; shell_escape_single_quotes(root_pass, esc_root_pass, sizeof(esc_root_pass));
    char esc_user_pass[1024]; shell_escape_single_quotes(user_pass, esc_user_pass, sizeof(esc_user_pass));
    char esc_host[1024]; shell_escape_single_quotes(host_name, esc_host, sizeof(esc_host));

    fprintf(f,
        "#!/usr/bin/env bash\n"
        "set -e\n"
        "ln -sf /usr/share/zoneinfo/%s /etc/localtime\n"
        "hwclock --systohc\n"
        "sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen\n"
        "locale-gen\n"
        "echo \"LANG=en_US.UTF-8\" >> /etc/locale.conf\n"
        "echo '%s' > /etc/hostname\n"
        "printf '%%s' 'root:%s' | chpasswd\n"
        "cat <<EOF > /etc/hosts\n"
        "127.0.0.1 localhost\n"
        "::1       localhost\n"
        "127.0.1.1\t%s.localdomain\t%s\n"
        "EOF\n"
        "pacman -S mtools cmake docker yt-dlp python3 fastfetch whois zsh git dosfstools man less xclip linux-headers reflector hyprland sddm kitty kate 7zip firefox btop vlc smplayer unrar pipewire pipewire-alsa dolphin pipewire-pulse --noconfirm --needed\n"
        "# GPU drivers\n"
        "if [ %s -eq 0 ]; then\n"
        "  pacman -S libva-mesa-driver vulkan-nouveau xf86-video-nouveau xorg-server xorg-xinit mesa-utils mesa --noconfirm --needed\n"
        "elif [ %s -eq 1 ]; then\n"
        "  pacman -S dkms libva-nvidia-driver nvidia-dkms xorg-server xorg-xinit --noconfirm --needed\n"
        "elif [ %s -eq 2 ]; then\n"
        "  pacman -S dkms libva-nvidia-driver nvidia-open-dkms xorg-server xorg-xinit --noconfirm --needed\n"
        "elif [ %s -eq 3 ]; then\n"
        "  pacman -S intel-media-driver libva-intel-driver mesa vulkan-intel xorg-server xorg-xinit --noconfirm --needed\n"
        "elif [ %s -eq 4 ]; then\n"
        "  pacman -S mesa xorg-server xorg-xinit --noconfirm --needed\n"
        "else\n"
        "  echo \"no gpu driver was installed.\"\n"
        "fi\n"
        "systemctl enable sddm\n"
        "systemctl enable NetworkManager\n"
        "systemctl enable snapper-timeline.timer\n"
        "systemctl enable snapper-cleanup.timer\n"
        "systemctl enable grub-btrfsd.service\n"
        "useradd -m -G wheel,storage,power,audio,video %s\n"
        "sed -i 's/^# %%%%wheel ALL=(ALL:ALL) ALL/%%%%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers\n"
        "printf '%%s' '%s:%s' | chpasswd\n"
        "grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB\n"
        "grub-mkconfig -o /boot/grub/grub.cfg\n",
        timezone,
        esc_host,
        esc_root_pass,
        host_name, host_name,
        gpu_choice, gpu_choice, gpu_choice, gpu_choice, gpu_choice,
        username,
        username, esc_user_pass
    );
    fclose(f);
    // Ensure executable perms
    chmod(chroot_path, 0755);

    if (run_cmd("arch-chroot /mnt sh /chroot.sh")) return 1;
    run_cmd("rm -f /mnt/chroot.sh");

    printf("All steps completed. You may reboot now.\n");
    return 0;
}

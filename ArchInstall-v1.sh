#!/usr/bin/env bash

echo "btrfs + hyprland arch install"
echo "enter username:"
read username
echo "enter the user password:"
read user_pass
echo "enter root password:"
read root_pass
echo "enter the hostname:"
read host_name
echo "enter you country(example->Iran):"
read country
echo "enter you time zone(example->Asia/Tehran):"
read timezone

reflector -c $country --sort rate --save /etc/pacman.d/mirrorlist
pacman -Syy
pacman-key --init
pacman-key --populate

lsblk
echo "enter sdX:"
read Install_drive

num1="1"
num2="2"
num3="3"
part1="${Install_drive}${num1}"
part2="${Install_drive}${num2}"
part3="${Install_drive}${num3}"

mkfs.fat -F32 /dev/$part1
mkswap /dev/$part2
swapon /dev/$part2
mkfs.btrfs /dev/$part3

mount /dev/$part3 /mnt
btrfs su cr /mnt/@
btrfs su cr /mnt/@home
btrfs su cr /mnt/@var
btrfs su cr /mnt/@snapshots
umount /mnt

mount -o noatime,compress=lzo,space_cache=v2,subvol=@ /dev/$part3 /mnt
mkdir -p /mnt/{boot,var,home,.snapshots}
mount -o noatime,compress=lzo,space_cache=v2,subvol=@home /dev/$part3 /mnt/home
mount -o noatime,compress=lzo,space_cache=v2,subvol=@var /dev/$part3 /mnt/var
mount -o noatime,compress=lzo,space_cache=v2,subvol=@snapshots /dev/$part3 /mnt/.snapshots
mount /dev/$part1 /mnt/boot

pacstrap /mnt base linux linux-firmware nano neovim sof-firmware base-devel grub grub-btrfs efibootmgr networkmanager snapper
genfstab -U /mnt >> /mnt/etc/fstab

cat <<REALEND >/mnt/mnt/chroot.sh

ln -sf /usr/share/zoneinfo/$timezone /etc/localtime
hwclock --systohc
sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" >> /etc/locale.conf
echo "ArchMachine" >> /etc/hostname
echo root:$root_pass | chpasswd

cat <<EOF > /etc/hosts
127.0.0.1 localhost
::1       localhost
127.0.1.1	$host_name.localdomain	$host_name
EOF

pacman -S mtools libva-mesa-driver vulkan-nouveau cmake docker xf86-video-nouveau xorg-server xorg-xinit yt-dlp python3 fastfetch whois zsh mesa-utils git dosfstools man less xclip linux-headers reflector hyprland sddm kitty kate 7zip firefox btop vlc smplayer unrar pipewire pipewire-alsa dolphin pipewire-pulse --noconfirm --needed
systemctl enable sddm
systemctl enable NetworkManager
systemctl enable snapper-timeline.timer
systemctl enable snapper-cleanup.timer
systemctl enable grub-btrfsd.service

useradd -m -G wheel,storage,power,audio,video $username
sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers
echo $username:$user_pass | chpasswd

grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB 
grub-mkconfig -o /boot/grub/grub.cfg

echo "-------------------------------------------------"
echo "Install Complete, You can reboot now"
echo "-------------------------------------------------"
REALEND

arch-chroot /mnt sh /mnt/chroot.sh

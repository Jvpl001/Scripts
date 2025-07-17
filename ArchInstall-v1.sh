#!/usr/bin/env bash

echo "btrfs + KDE arch install"
read -p "enter username:" -a username
read -p "enter root password:" -a root_pass
read -p "enter user password:" -a user_pass
read -p "enter you country(example->Iran):" -a country
read -p "enter you time zone(example->Asia/Tehran):" -a timezone

reflector -c $country --sort rate --save /etc/pacman.d/mirrorlist
pacman -Syy
pacman-key --init
pacman-key --populate

lsblk

read -p "enster sdX:" -a Install_drive

num1="1"
num2="2"
num3="3"
part1="${Install_drive}${num1}"
part2="${Install_drive}${num2}"
part3="${Install_drive}${num3}"

(
  echo g
  echo n
  echo ""
  echo ""
  echo "+256M"
  echo t
  echo 1
  echo n
  echo ""
  echo ""
  echo "+4G"
  echo t
  echo 2
  echo swap
  echo n
  echo ""
  echo ""
  echo ""
  echo w
) | fdisk /dev/$(echo $Install_drive)

mkfs.fat -F32 /dev/$(echo $part1)
mkswap /dev/$(echo $part2)
swapon /dev/$(echo $part2)
mkfs.btrfs /dev/$(echo $part3)

mount /dev/$(echo $part3) /mnt
btrfs su cr /mnt/@
btrfs su cr /mnt/@home
btrfs su cr /mnt/@var
btrfs su cr /mnt/@snapshots
umount /mnt

mkdir -p /mnt/{boot,var,home,.snapshots}
mount -o noatime,compress=lzo,space_cache,subvol=@ /dev/$(echo $part3) /mnt
mount -o noatime,compress=lzo,space_cache,subvol=@home /dev/$(echo $part3) /mnt/home
mount -o noatime,compress=lzo,space_cache,subvol=@var /dev/$(echo $part3) /mnt/var
mount -o noatime,compress=lzo,space_cache,subvol=@snapshots /dev/$(echo $part3) /mnt/.snapshots
mount /dev/$(echo $part1) /mnt/boot

pacstrap /mnt base linux linux-firmware nano neovim sof-firmware base-devel grub grub-btrfs efibootmgr networkmanager snapper
genfstab -U /mnt >>/mnt/etc/fstab

cat <<REALEND >chroot.sh

ln -sf /usr/share/zoneinfo/$timezone /etc/localtime
hwclock --systohc
sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" >> /etc/locale.conf
echo "ArchMachine" >> /etc/hostname
passwd; echo $root_pass; echo $root_pass

cat <<EOF > /etc/hosts
127.0.0.1 localhost
::1       localhost
127.0.1.1	ArchMachine.localdomain	ArchMachine
EOF

pacman -S mtools zsh mesa-utils git dosfstools man less linux-headers reflector plasma sddm kitty kate 7zip firefox btop vlc smplayer unrar pipewire pipewire-alsa pipewire-pulse --noconfirm --needed
systemctl enable sddm
systemctl enable NetworkManager

useradd -m -G wheel,storage,power,audio,video -s /bin/zsh $username
passwd $username; echo $user_pass; echo $user_pass
sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers

grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB 
grub-mkconfig -o /boot/grub/grub.cfg

echo "Snapper config"
umount /.snapshots/
rm -rf /.snapshots/
snapper -c root create-config /
sed -i 's/^ALLOW_USERS=""/ALLOW_USERS="'$username'"/' /etc/snapper/configs/root
echo "I don't know how to edit the time line cleanup values"
chmod a+rx /.snapshots/

systmctl enable snapper-timeline.timer
systmctl enable snapper-cleanup.timer
systmctl enable grub-btrfsd.service

systmctl start snapper-timeline.timer
systmctl start snapper-cleanup.timer
systmctl start grub-btrfsd.service

cd /home/$username/git
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si
cd /

su $username; cd ~; bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

echo "-------------------------------------------------"
echo "Install Complete, You can reboot now"
echo "-------------------------------------------------"
REALEND

arch-chroot /mnt sh chroot.sh

#!/usr/bin/env bash

username=$USER
echo "Snapper config enter root password"
su -
umount /.snapshots/
rm -rf /.snapshots/
snapper -c root create-config /
sed -i 's/^ALLOW_USERS=""/ALLOW_USERS="'$username'"/' /etc/snapper/configs/root
echo "I don't know how to edit the time line cleanup values"
chmod a+rx /.snapshots/

su $username
cd /home/$username/git
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si
cd ~

sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

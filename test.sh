cat <<REALEND >/mnt/mnt/chroot.sh

echo "-------------------------------------------------"
echo "Install Complete, You can reboot now"
echo "-------------------------------------------------"
REALEND

arch-chroot /mnt sh /mnt/chroot.sh

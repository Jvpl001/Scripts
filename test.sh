cat <<REALEND >chroot.sh

echo "-------------------------------------------------"
echo "Install Complete, You can reboot now"
echo "-------------------------------------------------"
REALEND

arch-chroot /mnt sh chroot.sh

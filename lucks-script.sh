#!/usr/bin/env bash

lsblk

echo "entre sdX:"
read USB_TARGET
echo "enter your usb name:"
read USB_NAME
echo "enter your Volume Group name:"
read VG_NAME
echo "enter the size of your usb(example 16G):"
read USB_SIZE

cryptsetup luksFormat /dev/$USB_TARGET
cryptsetup luksOpen /dev/$USB_TARGET $USB_NAME
pvcreate /dev/mapper/$USB_NAME
vgcreate $VG_NAME /dev/mapper/$USB_NAME
cryptsetup luksFormat /dev/$USB_TARGET

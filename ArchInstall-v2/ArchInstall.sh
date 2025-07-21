#!/usr/bin/env bash
echo "enter username:"
read username
echo "enter the username password:"
read user_pass
echo "enter the root password:"
read root_pass
lsblk
echo "enter the installation drive(sdX):"
read drive
echo "enter the host name:"
read host_name

user_pass_en=$(mkpasswd -m yescrypt $user_pass)
root_pass_en=$(mkpasswd -m yescrypt $root_pass)


sed -i 's/^            "username": "username"/            "username": "'$username'"/' user_credentials.json
sed -i 's/^    "root_enc_password": "rootpass",/    "root_enc_password": "'$root_pass_en'",/' user_credentials.json
sed -i 's/^            "enc_password": "userpasss",/            "enc_password": "'$user_pass_en'",/' user_credentials.json

sed -i 's/^                "device": "\/dev\/sda",/                "device": "\/dev\/'$drive'",/' user_configuration.json
sed -i 's/^    "hostname": "Archmachine",/    "hostname": "'$host_name'",/' user_configuration.json

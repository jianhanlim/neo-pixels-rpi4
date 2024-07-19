#!/bin/bash

# Check if the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

CONFIG_FILE="/boot/config.txt"

# Check if /boot/config.txt exists
if [ ! -f "$CONFIG_FILE" ]; then
  echo "$CONFIG_FILE does not exist. Exiting."
  exit 1
fi

# Check current dtparam=audio setting
if grep -q "^dtparam=audio=on" "$CONFIG_FILE"; then
  echo "Audio is currently enabled. Disabling it now..."
  sed -i 's/^dtparam=audio=on/dtparam=audio=off/' "$CONFIG_FILE"
  echo "Audio has been disabled in $CONFIG_FILE."
  echo "A reboot is required to apply the changes. Do you want to reboot now? (y/n)"
  read -r response
  if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
    reboot
  else
    echo "Please reboot manually to apply the changes."
  fi
elif grep -q "^dtparam=audio=off" "$CONFIG_FILE"; then
  echo "Audio is already disabled."
else
  echo "dtparam=audio setting not found. Adding it to disable audio..."
  echo "dtparam=audio=off" >> "$CONFIG_FILE"
  echo "Audio has been disabled in $CONFIG_FILE."
  echo "A reboot is required to apply the changes. Do you want to reboot now? (y/n)"
  read -r response
  if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
    reboot
  else
    echo "Please reboot manually to apply the changes."
  fi
fi

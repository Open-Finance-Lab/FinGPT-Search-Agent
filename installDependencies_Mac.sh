#!/bin/bash

set -e  # Exit immediately on any error

# Check if pip is installed; install if missing
if ! command -v pip &> /dev/null
then
    echo "pip could not be found. Installing pip..."
    sudo apt update
    sudo apt install -y python3-pip
fi

# (Optional) Upgrade pip to the latest version
echo "Upgrading pip..."
pip install --upgrade pip

# Make sure requirements.txt exists
if [ ! -f "requirements_mac.txt" ]
then
    echo "Error: requirements_mac.txt not found in the current directory."
    exit 1
fi

# Install dependencies listed in requirements.txt
echo "Installing dependencies from requirements.txt..."
pip install -r requirements_mac.txt

echo "All dependencies have been installed successfully."

#!/bin/bash
# Setup script for Betafly Optical Position Stabilization
# Run this script on your Raspberry Pi Zero

set -e

echo "================================================"
echo "Betafly Stabilization System - Setup Script"
echo "================================================"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "[1/6] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "[2/6] Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-setuptools \
    git

# Enable SPI
echo "[3/6] Enabling SPI interface..."
if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
    echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
    echo "SPI enabled (reboot required)"
    REBOOT_REQUIRED=1
else
    echo "SPI already enabled"
fi

# Install Python dependencies
echo "[4/6] Installing Python packages..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Make scripts executable
echo "[5/6] Setting file permissions..."
chmod +x betafly_stabilizer.py

# Test installation
echo "[6/6] Testing installation..."
python3 -c "import spidev; print('✓ spidev installed')"
python3 -c "from optical_flow_sensor import PMW3901; print('✓ optical_flow_sensor OK')"
python3 -c "from position_stabilizer import StabilizationController; print('✓ position_stabilizer OK')"

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""

if [ "$REBOOT_REQUIRED" = "1" ]; then
    echo "⚠️  REBOOT REQUIRED to enable SPI interface"
    echo ""
    read -p "Reboot now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo reboot
    fi
else
    echo "✓ All set! You can now run:"
    echo "  ./betafly_stabilizer.py --help"
fi

echo ""

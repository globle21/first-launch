#!/bin/bash
set -e

echo "Starting dependency installation..."

# Navigate to backend directory
cd /home/ubuntu/first-launch/backend

# Create Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

deactivate

# Ensure Nginx is installed and enabled
echo "Ensuring Nginx is installed..."
sudo apt install -y nginx
sudo systemctl enable nginx

echo "Dependencies installed successfully"
exit 0

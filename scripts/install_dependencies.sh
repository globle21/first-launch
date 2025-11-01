#!/bin/bash
set -e

echo "Starting dependency installation..."

# Ensure proper ownership of the application directory
sudo chown -R ubuntu:ubuntu /home/ubuntu/first-launch

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

# Run DB migrations (baseline)
echo "Running database migrations..."
if [ -f /home/ubuntu/first-launch/.env ]; then
    set -a
    source /home/ubuntu/first-launch/.env
    set +a
fi
alembic upgrade 0001 || {
    echo "Alembic upgrade failed. Attempting to stamp base then upgrade..."
    alembic stamp base && alembic upgrade 0001
}

deactivate

# Ensure Nginx is installed and enabled
echo "Ensuring Nginx is installed..."
sudo apt install -y nginx
sudo systemctl enable nginx

# Ensure proper permissions for all files
sudo chown -R ubuntu:ubuntu /home/ubuntu/first-launch

echo "Dependencies installed successfully"
exit 0

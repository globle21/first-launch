#!/bin/bash
set -e

echo "Starting application deployment..."

# Ensure proper ownership
sudo chown -R ubuntu:ubuntu /home/ubuntu/first-launch

# Stop any existing processes
pkill -f "uvicorn main:app" || true

# Wait for processes to stop
sleep 2

# Navigate to backend directory
cd /home/ubuntu/first-launch/backend

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f /home/ubuntu/first-launch/.env ]; then
    export $(cat /home/ubuntu/first-launch/.env | grep -v '^#' | xargs)
fi

# Start FastAPI application in background
echo "Starting FastAPI backend on port 8000..."
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /home/ubuntu/first-launch/backend/server.log 2>&1 &

# Wait for backend to start
sleep 3

# Copy frontend files to Nginx web root
echo "Deploying frontend files to Nginx..."
sudo rm -rf /var/www/html/*
sudo cp -r /home/ubuntu/first-launch/frontend/* /var/www/html/

# Copy src folder if it exists and is needed by frontend
if [ -d /home/ubuntu/first-launch/src ]; then
    echo "Copying src folder to web root..."
    sudo cp -r /home/ubuntu/first-launch/src /var/www/html/
fi

# Set proper permissions for web files
sudo chown -R www-data:www-data /var/www/html
sudo chmod -R 755 /var/www/html

# Restart Nginx
echo "Restarting Nginx..."
sudo systemctl restart nginx

echo "Application started successfully!"
echo "Frontend: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "Backend API: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/api/"

exit 0

#!/bin/bash
set -e

echo "=========================================="
echo "Starting application deployment..."
echo "=========================================="

# Ensure proper ownership
echo "Setting proper file permissions..."
sudo chown -R ubuntu:ubuntu /home/ubuntu/first-launch

# Stop any existing processes
echo "Stopping any existing backend processes..."
pkill -f "uvicorn main:app" || true

# Wait for processes to stop
sleep 2

# Navigate to backend directory
echo "Navigating to backend directory..."
cd /home/ubuntu/first-launch/backend

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Verify Python and packages
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

# Check if uvicorn is installed
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "ERROR: uvicorn not installed. Installing now..."
    pip install uvicorn
fi

# Check if fastapi is installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "ERROR: fastapi not installed. Installing now..."
    pip install fastapi
fi

# Load environment variables
echo "Loading environment variables..."
if [ -f /home/ubuntu/first-launch/.env ]; then
    set -a  # automatically export all variables
    source /home/ubuntu/first-launch/.env
    set +a
    echo "Environment variables loaded"
else
    echo "WARNING: .env file not found at /home/ubuntu/first-launch/.env"
fi

# Test if main.py exists and is valid
echo "Checking main.py..."
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found!"
    exit 1
fi

# Try to import main.py to check for syntax errors
echo "Validating main.py syntax..."
python -c "import main" || {
    echo "ERROR: main.py has import or syntax errors"
    echo "Trying to show the error:"
    python main.py || true
    exit 1
}

# Start FastAPI application in background (Gunicorn+Uvicorn optional upgrade later)
echo "Starting FastAPI backend on port 8000..."
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /home/ubuntu/first-launch/backend/server.log 2>&1 &

# Get the PID
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait a moment and check if it's still running
sleep 5

if ps -p $BACKEND_PID > /dev/null; then
    echo "✅ Backend is running successfully"
else
    echo "❌ ERROR: Backend failed to start. Check logs:"
    cat /home/ubuntu/first-launch/backend/server.log
    exit 1
fi

# Test if backend is responding
echo "Testing backend..."
sleep 2
curl -f http://localhost:8000/ || {
    echo "WARNING: Backend not responding on port 8000"
    echo "Last 20 lines of server log:"
    tail -20 /home/ubuntu/first-launch/backend/server.log
}

echo "Skipping Nginx configuration (handled separately)."

# Get EC2 public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo "Unable to get public IP")

echo "=========================================="
echo "✅ Application started successfully!"
echo "=========================================="
echo "Frontend: http://$PUBLIC_IP/"
echo "Backend API (proxied): http://$PUBLIC_IP/api/"
echo "Backend Docs: http://$PUBLIC_IP/api/docs"
echo ""
echo "Logs:"
echo "  Backend: /home/ubuntu/first-launch/backend/server.log"
echo "  Nginx: /var/log/nginx/error.log"
echo "=========================================="

exit 0

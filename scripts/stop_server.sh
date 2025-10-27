#!/bin/bash
# Stop any running FastAPI/Uvicorn processes

echo "Stopping existing Uvicorn processes..."
pkill -f "uvicorn main:app" || true

# If using systemd service (optional)
# sudo systemctl stop first-launch-backend || true

echo "Server stopped successfully"
exit 0

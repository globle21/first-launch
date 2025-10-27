#!/bin/bash
# Stop any running FastAPI/Uvicorn processes

echo "Stopping existing Uvicorn processes..."
pkill -f "uvicorn main:app" || true

echo "Server stopped successfully"
exit 0


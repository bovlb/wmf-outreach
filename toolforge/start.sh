#!/bin/bash
# Toolforge webservice startup script

set -e

# Use the PORT environment variable provided by Toolforge
PORT=${PORT:-8000}

# Start uvicorn with the FastAPI app
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"

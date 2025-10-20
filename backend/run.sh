#!/bin/bash

# KIBA Backend Startup Script

echo "🚀 Starting KIBA Procurement AI Backend..."

# Check if .env.local exists
if [ ! -f .env.local ]; then
    echo "⚠️  Warning: .env.local not found!"
    echo "Creating from .env.example..."
    cp .env.example .env.local
    echo ""
    echo "❌ Please edit backend/.env.local and add your OPENAI_API_KEY"
    exit 1
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3.11 or higher"
    exit 1
fi

# Load environment variables
export $(cat .env.local | xargs)

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY is not set in .env.local"
    exit 1
fi

# Check if uvicorn is installed
if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    python3 -m pip install -r requirements.txt
fi

# Create logs directory
mkdir -p logs

echo "✅ Backend configuration OK"
echo "🌐 Starting server on http://localhost:8000"
echo ""

# Start the server
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload

#!/bin/bash

# KIBA3 KPA One-Flow Local Deployment Script
echo "🚀 Deploying KIBA3 with KPA One-Flow Integration"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "backend/server.py" ] || [ ! -f "frontend-new/package.json" ]; then
    echo "❌ Error: Please run this script from the KIBA3 root directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f "backend/.env" ]; then
    echo "❌ Error: backend/.env file not found"
    echo "Please add your OpenAI API key to backend/.env:"
    echo "OPENAI_API_KEY=your_api_key_here"
    exit 1
fi

# Check if API key is set
if ! grep -q "OPENAI_API_KEY=sk-" backend/.env; then
    echo "❌ Error: OpenAI API key not properly set in backend/.env"
    exit 1
fi

echo "✅ Environment check passed"

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Backend dependency installation failed"
    exit 1
fi
cd ..

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend-new
npm install
if [ $? -ne 0 ]; then
    echo "❌ Frontend dependency installation failed"
    exit 1
fi
cd ..

echo "✅ Dependencies installed successfully"

# Create logs directory
mkdir -p backend/logs

echo ""
echo "🎉 Deployment ready!"
echo ""
echo "To start the application:"
echo "1. Backend:  cd backend && python server.py"
echo "2. Frontend: cd frontend-new && npm run dev"
echo "3. Open:     http://localhost:5173"
echo ""
echo "The KPA One-Flow integration is ready to use!"

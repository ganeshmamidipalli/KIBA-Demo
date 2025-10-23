#!/bin/bash

# KIBA3 Local Development Startup Script

echo "🚀 Starting KIBA3 Local Development Environment"

# Check if .env files exist
if [ ! -f "backend/.env" ]; then
    echo "⚠️  Backend .env file not found. Please create it with your OPENAI_API_KEY"
    echo "   Example: echo 'OPENAI_API_KEY=your-key-here' > backend/.env"
fi

if [ ! -f "frontend-new/.env.development" ]; then
    echo "⚠️  Frontend .env.development file not found. Creating default..."
    echo "VITE_API_BASE=http://localhost:8001" > frontend-new/.env.development
fi

# Start backend
echo "🔧 Starting Backend Server..."
cd backend
python server.py &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 3

# Start frontend
echo "🎨 Starting Frontend Server..."
cd frontend-new
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ KIBA3 is running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
wait

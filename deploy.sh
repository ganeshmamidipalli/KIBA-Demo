#!/bin/bash

# KIBA3 Complete Deployment Script
echo "🚀 Starting KIBA3 Complete Deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${YELLOW}⚠️  Port $1 is already in use${NC}"
        return 1
    else
        return 0
    fi
}

# Function to kill processes on specific ports
kill_port() {
    echo -e "${YELLOW}🔄 Stopping existing services on ports $1...${NC}"
    lsof -ti:$1 | xargs kill -9 2>/dev/null || true
    sleep 2
}

# Stop existing services
echo -e "${BLUE}🛑 Stopping existing services...${NC}"
kill_port 8000
kill_port 5173

# Check if .env files exist
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}⚠️  Backend .env file not found. Creating template...${NC}"
    echo "OPENAI_API_KEY=your-openai-api-key-here" > backend/.env
    echo -e "${RED}❌ Please edit backend/.env and add your OpenAI API key${NC}"
    echo -e "${RED}   Then run this script again${NC}"
    exit 1
fi

# Start Backend
echo -e "${BLUE}🔧 Starting Backend Server...${NC}"
cd backend
if check_port 8000; then
    python server.py &
    BACKEND_PID=$!
    echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}❌ Port 8000 is already in use${NC}"
    exit 1
fi

# Wait for backend to start
echo -e "${BLUE}⏳ Waiting for backend to initialize...${NC}"
sleep 5

# Test backend
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Backend is healthy${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
    exit 1
fi

# Start Frontend
echo -e "${BLUE}🎨 Starting Frontend Server...${NC}"
cd ../frontend-new

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
    npm install
fi

if check_port 5173; then
    npm run dev &
    FRONTEND_PID=$!
    echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}❌ Port 5173 is already in use${NC}"
    exit 1
fi

# Wait for frontend to start
echo -e "${BLUE}⏳ Waiting for frontend to initialize...${NC}"
sleep 8

# Test frontend
if curl -s http://localhost:5173 > /dev/null; then
    echo -e "${GREEN}✅ Frontend is running${NC}"
else
    echo -e "${RED}❌ Frontend health check failed${NC}"
    exit 1
fi

# Success message
echo ""
echo -e "${GREEN}🎉 KIBA3 Deployment Successful!${NC}"
echo ""
echo -e "${BLUE}📱 Frontend:${NC} http://localhost:5173"
echo -e "${BLUE}🔧 Backend:${NC} http://localhost:8000"
echo -e "${BLUE}📚 API Docs:${NC} http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo -e "   • Open http://localhost:5173 in your browser"
echo -e "   • Check API documentation at http://localhost:8000/docs"
echo -e "   • Press Ctrl+C to stop all services"
echo ""

# Keep script running and show logs
echo -e "${BLUE}📊 Monitoring services... (Press Ctrl+C to stop)${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    kill_port 8000
    kill_port 5173
    echo -e "${GREEN}✅ Services stopped${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for user interrupt
wait

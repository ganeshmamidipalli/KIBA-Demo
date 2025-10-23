#!/bin/bash

# KIBA3 Status Check Script
echo "🔍 KIBA3 Status Check"
echo "===================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check Backend
echo -e "${BLUE}🔧 Backend Status:${NC}"
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Backend is running on http://localhost:8000${NC}"
    curl -s http://localhost:8000/health | jq . 2>/dev/null || curl -s http://localhost:8000/health
else
    echo -e "${RED}❌ Backend is not responding${NC}"
fi

echo ""

# Check Frontend
echo -e "${BLUE}🎨 Frontend Status:${NC}"
if curl -s http://localhost:5173 > /dev/null; then
    echo -e "${GREEN}✅ Frontend is running on http://localhost:5173${NC}"
else
    echo -e "${RED}❌ Frontend is not responding${NC}"
fi

echo ""

# Check API Connection
echo -e "${BLUE}🔗 API Connection Test:${NC}"
if curl -s http://localhost:8000/api/suggest-vendors -X POST -H "Content-Type: application/json" -d '{"product": "test"}' > /dev/null; then
    echo -e "${GREEN}✅ API endpoints are working${NC}"
else
    echo -e "${RED}❌ API endpoints are not responding${NC}"
fi

echo ""

# Show running processes
echo -e "${BLUE}📊 Running Processes:${NC}"
echo "Backend processes:"
ps aux | grep "python server.py" | grep -v grep || echo "No backend processes found"

echo ""
echo "Frontend processes:"
ps aux | grep "vite" | grep -v grep || echo "No frontend processes found"

echo ""
echo -e "${GREEN}🎯 Access URLs:${NC}"
echo "• Frontend: http://localhost:5173"
echo "• Backend: http://localhost:8000"
echo "• API Docs: http://localhost:8000/docs"

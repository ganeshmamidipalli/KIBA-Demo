#!/bin/bash

# KIBA3 Debug Script
echo "🔍 KIBA3 Debug Information"
echo "=========================="

# Check if services are running
echo -e "\n📊 Service Status:"
echo "Backend (8000): $(curl -s http://localhost:8000/health > /dev/null && echo '✅ Running' || echo '❌ Not responding')"
echo "Frontend (5173): $(curl -s http://localhost:5173 > /dev/null && echo '✅ Running' || echo '❌ Not responding')"

# Check for JavaScript errors in the HTML
echo -e "\n🔍 Frontend Content Check:"
if curl -s http://localhost:5173 | grep -q "DOCTYPE html"; then
    echo "✅ HTML is being served"
    echo "✅ React app structure looks good"
else
    echo "❌ HTML structure issue"
fi

# Check API connectivity
echo -e "\n🔗 API Connectivity:"
if curl -s http://localhost:8000/api/suggest-vendors -X POST -H "Content-Type: application/json" -d '{"product": "test"}' > /dev/null; then
    echo "✅ API endpoints working"
else
    echo "❌ API endpoints not responding"
fi

# Check for common issues
echo -e "\n🐛 Common Issues Check:"
echo "• CORS: Backend should allow frontend origin"
echo "• API Base URL: Should be http://localhost:8000"
echo "• Dependencies: All npm packages installed"

echo -e "\n💡 If you see a blank screen:"
echo "1. Open browser developer tools (F12)"
echo "2. Check Console tab for JavaScript errors"
echo "3. Check Network tab for failed requests"
echo "4. Try refreshing the page (Ctrl+F5)"

echo -e "\n🎯 Access URLs:"
echo "• Frontend: http://localhost:5173"
echo "• Backend: http://localhost:8000"
echo "• API Docs: http://localhost:8000/docs"

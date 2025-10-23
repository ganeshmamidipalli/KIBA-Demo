# KIBA3 Local Deployment Guide

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- OpenAI API Key

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key-here"
python server.py
```

### Frontend Setup
```bash
cd frontend-new
npm install
npm run dev
```

### Access
- Frontend: http://localhost:5173
- Backend: http://localhost:8001

## Environment Variables
- `OPENAI_API_KEY`: Required for AI functionality
- `PORT`: Backend port (default: 8001)
- `VITE_API_BASE`: Frontend API base URL

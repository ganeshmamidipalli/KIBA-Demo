# KIBA3 Backend Testing Script
Write-Host ""
Write-Host "KIBA3 Backend Services Test" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan
Write-Host ""

# Check .env file
$envFile = ".\\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "Creating .env template..." -ForegroundColor Yellow
    @"
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_CHAT_MODEL=gpt-4o-2024-08-06
MAX_FILE_MB=10
MAX_TOTAL_MB=30
"@ | Out-File -FilePath $envFile -Encoding UTF8
    Write-Host "Created .env file. Please add your OpenAI API key." -ForegroundColor Green
    Write-Host "Edit backend\.env and replace 'sk-your-api-key-here' with your real key" -ForegroundColor Yellow
    Write-Host "Get key from: https://platform.openai.com/api-keys" -ForegroundColor Cyan
    exit 1
}

# Activate venv
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & .\venv\Scripts\Activate.ps1
}

# Run tests
Write-Host "Running test suite..." -ForegroundColor Cyan
Write-Host ""
python test_services.py

Write-Host ""
Write-Host "Tests complete!" -ForegroundColor Green



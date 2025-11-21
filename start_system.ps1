# UniSoftware Assistant - System Startup Script
# PowerShell Version

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "UniSoftware Assistant - System Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to project directory
Set-Location "D:\Python Project\RAG Project\rag-openrouter"

# Step 1: Check and kill existing processes on port 8000
Write-Host "[1/3] Checking if port 8000 is free..." -ForegroundColor Yellow
$port8000 = netstat -ano | Select-String ":8000"
if ($port8000) {
    Write-Host "Port 8000 is in use. Killing existing process..." -ForegroundColor Yellow
    $port8000 | ForEach-Object {
        $line = $_.Line
        if ($line -match '\s+(\d+)$') {
            $pid = $matches[1]
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 2
}
Write-Host "Port 8000 is free!" -ForegroundColor Green
Write-Host ""

# Step 2: Start Backend API Server
Write-Host "[2/3] Starting Backend API Server..." -ForegroundColor Yellow
$backendJob = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'D:\Python Project\RAG Project\rag-openrouter'; python src/api_openrouter.py" -PassThru
Write-Host "Backend starting (PID: $($backendJob.Id))..." -ForegroundColor Green
Write-Host "Waiting for backend to initialize (15 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15
Write-Host ""

# Step 3: Start Frontend Streamlit
Write-Host "[3/3] Starting Frontend Streamlit..." -ForegroundColor Yellow
$frontendJob = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'D:\Python Project\RAG Project\rag-openrouter'; streamlit run src/frontend_streamlit.py" -PassThru
Write-Host "Frontend starting (PID: $($frontendJob.Id))..." -ForegroundColor Green
Write-Host "Waiting for frontend to start (8 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 8
Write-Host ""

# Verify system health
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Verifying System Health..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

try {
    $health = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    if ($health.StatusCode -eq 200) {
        Write-Host "[OK] Backend API is healthy!" -ForegroundColor Green
        $healthData = $health.Content | ConvertFrom-Json
        Write-Host "     Documents: $($healthData.documents)" -ForegroundColor Gray
        Write-Host "     Chunks: $($healthData.total_chunks)" -ForegroundColor Gray
    }
} catch {
    Write-Host "[WARN] Backend API not responding yet. Please wait..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "System Started Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "Frontend UI: http://localhost:8501" -ForegroundColor White
Write-Host ""
Write-Host "Opening browser in 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Open browser
Start-Process "http://localhost:8501"

Write-Host ""
Write-Host "System is running in separate windows." -ForegroundColor Cyan
Write-Host "Close those windows to stop the system." -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

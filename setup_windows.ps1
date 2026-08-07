Write-Host "Setting up Loan Management System for Windows..." -ForegroundColor Cyan

# 1. Check Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python is not installed or not in PATH! Please install Python 3.14+." -ForegroundColor Red
    Write-Host "You can install it via Microsoft Store or python.org" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "Python detected." -ForegroundColor Green
}

# 2. Check and Install uv
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing 'uv' (Fast Python package manager)..." -ForegroundColor Yellow
    Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1" | Invoke-Expression
    
    # Temporarily add to path for this session
    $env:Path += ";$HOME\.local\bin;$HOME\.cargo\bin"
    
    if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "uv was installed but is not in the current PATH. Please restart your terminal and run this script again." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "'uv' is already installed." -ForegroundColor Green
}

# 3. Install dependencies using uv
Write-Host "Installing project dependencies..." -ForegroundColor Yellow
uv sync

# 4. Check for .env
if (!(Test-Path .env)) {
    Write-Host "WARNING: .env file not found." -ForegroundColor Red
    Write-Host "Please make sure to create a .env file with your database and redis configuration." -ForegroundColor Yellow
} else {
    Write-Host ".env file found." -ForegroundColor Green
}

# 5. Run Migrations
Write-Host "Running database migrations..." -ForegroundColor Yellow
uv run manage.py migrate

# 6. Redis setup for Windows
Write-Host "Checking for Redis (Required for Celery tasks)..." -ForegroundColor Yellow
if (!(Get-Command redis-server -ErrorAction SilentlyContinue) -and !(Get-Command memurai -ErrorAction SilentlyContinue)) {
    Write-Host "--------------------------------------------------------" -ForegroundColor Red
    Write-Host "Redis is required for this project but not detected!" -ForegroundColor Red
    Write-Host "On Windows, you must use one of the following to run Redis:" -ForegroundColor White
    Write-Host "1. Install Memurai (Native Windows Redis port): " -NoNewline; Write-Host "winget install Memurai.MemuraiDeveloper" -ForegroundColor Cyan
    Write-Host "2. Run Redis via Docker: " -NoNewline; Write-Host "docker run -d -p 6379:6379 redis" -ForegroundColor Cyan
    Write-Host "3. Run Redis inside WSL (Windows Subsystem for Linux)" -ForegroundColor White
    Write-Host "--------------------------------------------------------" -ForegroundColor Red
} else {
    Write-Host "Redis/Memurai seems to be available." -ForegroundColor Green
}

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "To start the application servers, open two terminals and run:" -ForegroundColor Cyan
Write-Host "Terminal 1 (Django Server):"
Write-Host "  uv run manage.py runserver" -ForegroundColor White
Write-Host "`nTerminal 2 (Celery Worker):"
Write-Host "  uv run celery -A config worker --loglevel=INFO --pool=threads" -ForegroundColor White
Write-Host "  (Note: --pool=threads is used on Windows because Celery's default prefork pool is unsupported on Windows)" -ForegroundColor Yellow

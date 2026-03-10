# push-to-github.ps1
# Run with: Right-click → "Run with PowerShell"
# Or from terminal: powershell -ExecutionPolicy Bypass -File push-to-github.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Pushing IDN-StockNews to GitHub" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

Set-Location -Path "C:\Users\Muhammad Fadli\Documents\Side Project\market-briefing"

# Initialize git if not already done
if (-Not (Test-Path ".git")) {
    git init
    Write-Host "Git repo initialized." -ForegroundColor Yellow
}

# Stage everything
git add .

# Commit
git commit -m "feat: scaffold full project structure with docs, infra, tests, and workflows"

# Connect to GitHub (remove + re-add to avoid duplicate remote errors)
git remote remove origin 2>$null
git remote add origin https://github.com/Fadliirjiyansy/IDN-StockNews.git

# Push to main
git branch -M main
git push -u origin main --force

Write-Host ""
Write-Host "✅ Done! Check: https://github.com/Fadliirjiyansy/IDN-StockNews" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to close"

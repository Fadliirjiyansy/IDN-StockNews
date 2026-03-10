@echo off
echo Initializing Git repository for market-briefing...

cd /d "C:\Users\Muhammad Fadli\Documents\Side Project\market-briefing"

git init
git add .
git commit -m "Initial commit: Add test workflow and project structure"

echo.
echo ✅ Git repo initialized locally!
echo.
echo Next steps to push to GitHub:
echo   1. Go to https://github.com/new and create a new repo named "market-briefing"
echo   2. Then run the following commands:
echo.
echo   git remote add origin https://github.com/YOUR_USERNAME/market-briefing.git
echo   git branch -M main
echo   git push -u origin main
echo.
pause

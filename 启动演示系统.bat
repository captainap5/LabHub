@echo off
chcp 65001 >nul
title LabHub - Lab Equipment Reservation System
cd /d "%~dp0app"

echo ==========================================
echo   LabHub  Lab Equipment Reservation System
echo ==========================================
echo.
echo   URL      : http://127.0.0.1:8080
echo   Admin    : admin / admin123
echo   Teacher  : teacher1 / 123456
echo   Student  : stu001 / 123456
echo   LowCredit: stu002 / 123456
echo.
echo   Press Ctrl+C to stop the server.
echo ==========================================
echo.

start "" http://127.0.0.1:8080
python server.py 8080
pause

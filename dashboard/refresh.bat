@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File refresh.ps1
start "" security.html

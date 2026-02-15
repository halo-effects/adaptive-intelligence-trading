@echo off
echo === Gee Gee Voice Assistant Setup ===
set PYTHON=C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe

echo.
echo Installing dependencies...
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install -r requirements.txt

echo.
echo Generating chime sound...
%PYTHON% generate_chime.py

echo.
echo Downloading faster-whisper model (tiny ~39MB)...
%PYTHON% -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"

echo.
echo Setup complete! Run 'run.bat' to start the assistant.
pause

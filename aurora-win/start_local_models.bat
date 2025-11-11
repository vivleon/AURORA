@echo off
setlocal
set MODELS_DIR=models\llm
set BIN=models\bin\llama-server.exe

echo Starting Main model server (Port 8081)...
REM [FIX] Removed invalid argument: --batch 256
REM [FIX] Added cmd /K to keep the window open on error.
start "Main Model (8081)" cmd /K "%BIN% -m ""%MODELS_DIR%\main.gguf"" --port 8081 --ctx-size 4096 --threads 8 --parallel 2 --alias main"

echo Starting Intent model server (Port 8082)...
REM [FIX] Removed invalid argument: --batch 256
REM [FIX] Added cmd /K to keep the window open on error.
start "Intent Model (8082)" cmd /K "%BIN% -m ""%MODELS_DIR%\intent.gguf"" --port 8082 --ctx-size 2048 --threads 8 --parallel 2 --alias intent"

echo Both AI servers are starting in separate windows.
endlocal
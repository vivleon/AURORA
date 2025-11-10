@echo off
setlocal
set MODELS_DIR=models\llm
set BIN=models\bin\llama-server.exe

REM main model
"%BIN%" -m "%MODELS_DIR%\main.gguf" --port 8081 --ctx-size 4096 --embedding 0 --threads 8 --batch 256 --parallel 2 --alias main
endlocal

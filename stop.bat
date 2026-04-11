@echo off
echo 停止 x-reader 服务...

:: 停止后端
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /PID %%a /F > nul 2>&1 && echo 已停止后端 (PID: %%a)
)

:: 停止前端
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /PID %%a /F > nul 2>&1 && echo 已停止前端 (PID: %%a)
)

echo 完成
pause

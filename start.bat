@echo off
setlocal

set SCRIPT_DIR=%~dp0
set BACKEND_PORT=8000
set FRONTEND_PORT=5173

echo =========================================
echo   x-reader 服务启动
echo =========================================

:: 检查虚拟环境
if not exist "%SCRIPT_DIR%..\..\.venv\Scripts\activate.bat" (
    echo 错误: 虚拟环境不存在
    exit /b 1
)

:: 启动后端
echo 启动后端 (端口 %BACKEND_PORT%)...
start "x-reader backend" cmd /k "cd /d %SCRIPT_DIR%backend && call %SCRIPT_DIR%..\..\.venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"

:: 等待后端启动
echo 等待后端启动...
timeout /t 5 /nobreak > nul

:: 启动前端
echo 启动前端 (端口 %FRONTEND_PORT%)...
start "x-reader frontend" cmd /k "cd /d %SCRIPT_DIR%frontend && npm run dev"

echo.
echo =========================================
echo   x-reader 服务已启动
echo =========================================
echo   前端: http://localhost:%FRONTEND_PORT%
echo   后端: http://localhost:%BACKEND_PORT%
echo =========================================
echo.
echo 关闭窗口停止服务
echo.

pause

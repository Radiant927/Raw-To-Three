@echo off
chcp 65001 >nul
REM Raw-To-Three 展示平台一键启动（演示 / Mock 模式，Windows）
REM 用法：双击本文件，或在 cmd 里运行 start.bat
REM 依赖：Python 3、Node.js。首次会自动安装前后端依赖。
setlocal
set "HERE=%~dp0"
set "BACKEND_PORT=8010"
set "FRONTEND_PORT=3000"

where python >nul 2>nul || (echo [ERROR] 未找到 Python 3 & exit /b 1)
where node   >nul 2>nul || (echo [ERROR] 未找到 Node.js & exit /b 1)

echo [1/3] 安装后端依赖...
python -m pip install -q -r "%HERE%backend\requirements.txt" || (echo [ERROR] 后端依赖安装失败 & exit /b 1)

echo [2/3] 安装前端依赖...
pushd "%HERE%frontend"
call npm install --silent || (echo [ERROR] 前端依赖安装失败 & popd & exit /b 1)
popd

echo [3/3] 启动服务...
REM 后端（Mock 模式，用 mock_data 占位模型，不需要 GPU）
start "RT backend (Mock)" /d "%HERE%backend" cmd /k "python main.py --mock --port %BACKEND_PORT%"
timeout /t 3 >nul

REM 前端
start "RT frontend" /d "%HERE%frontend" cmd /k "set NEXT_PUBLIC_API_URL=http://localhost:%BACKEND_PORT% && npm run dev"

echo.
echo ========================================
echo   前端:  http://localhost:%FRONTEND_PORT%
echo   后端:  http://localhost:%BACKEND_PORT%
echo   演示说明: 上传 20 张以上 JPG/PNG，走完流程会返回占位模型
echo   关闭弹出的两个窗口即可停止
echo ========================================
endlocal

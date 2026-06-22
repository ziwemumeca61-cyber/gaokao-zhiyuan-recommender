@echo off
chcp 65001 >nul
title 高考志愿推荐系统
cd /d "%~dp0"

rem 兼容两种放置方式：打包版 app.py 与本脚本同级；源码版脚本在 packaging\ 内，app.py 在上一级
if not exist "app.py" if exist "..\app.py" cd ..

rem 优先用随包内嵌的便携 Python；没有则用系统 Python
set "PY=%~dp0runtime\python.exe"
if not exist "%PY%" set "PY=python"
set "LOG=%CD%\启动日志.txt"

rem 跳过 Streamlit 首次运行的"邮箱"引导提示（避免客户双击后卡住）
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit" >nul 2>nul
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    > "%USERPROFILE%\.streamlit\credentials.toml" echo [general]
    >> "%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

rem ===== 环境自检：关键库能否导入（捕获缺 DLL / 依赖不全等问题）=====
"%PY%" -c "import streamlit, pandas, numpy, plotly" 2>"%LOG%"
if errorlevel 1 (
    echo [启动失败] 运行环境有问题。最常见原因：本机缺少 Visual C++ 运行库。
    echo.
    echo   解决：下载安装微软运行库后重试（约 1 分钟）：
    echo   https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo.
    echo 详细错误如下（也已保存到 启动日志.txt，可截图发给技术支持）：
    echo ------------------------------------------------
    type "%LOG%"
    echo ------------------------------------------------
    pause
    exit /b 1
)

echo ============================================
echo    高考志愿推荐系统  正在启动，请稍候...
echo    首次启动较慢（约 10~30 秒），稍等浏览器会自动打开
echo    若没自动打开，手动访问： http://127.0.0.1:8501
echo    使用期间请不要关闭本黑色窗口
echo ============================================
echo.

rem 后台延时打开浏览器（用 PowerShell，独立进程、不影响主程序；127.0.0.1 规避360内网拦截）
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 12; Start-Process 'http://127.0.0.1:8501'" >nul 2>nul

rem 启动服务（前台运行；输出同时留存到 启动日志.txt 便于排错）
"%PY%" -m streamlit run app.py --server.headless true --server.port 8501 --browser.gatherUsageStats false 2>>"%LOG%"

echo.
echo 程序已退出。若启动异常，请把同目录的 “启动日志.txt” 截图发技术支持。
pause >nul

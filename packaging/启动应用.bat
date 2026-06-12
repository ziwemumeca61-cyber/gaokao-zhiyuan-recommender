@echo off
chcp 65001 >nul
title 高考志愿推荐系统
cd /d "%~dp0"

rem 兼容两种放置方式：打包版 app.py 与本脚本同级；源码版本脚本在 packaging\ 内，app.py 在上一级
if not exist "app.py" if exist "..\app.py" cd ..

rem 优先用随包内嵌的便携 Python；没有则用系统 Python
set "PY=%~dp0runtime\python.exe"
if not exist "%PY%" set "PY=python"

rem 跳过 Streamlit 首次运行的"邮箱"引导提示（避免客户双击后卡住）
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit" >nul 2>nul
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    > "%USERPROFILE%\.streamlit\credentials.toml" echo [general]
    >> "%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

echo ============================================
echo    高考志愿推荐系统  正在启动，请稍候...
echo    启动后会自动打开浏览器（约 5~10 秒）
echo    使用期间请不要关闭本黑色窗口
echo ============================================
echo.

rem 延迟几秒后自动打开浏览器
start "" /b cmd /c "timeout /t 6 >nul & start http://localhost:8501"

"%PY%" -m streamlit run app.py --server.headless true --server.port 8501 --browser.gatherUsageStats false

echo.
echo 程序已退出。按任意键关闭窗口。
pause >nul

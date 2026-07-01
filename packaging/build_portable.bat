@echo off
chcp 65001 >nul
title Build portable package
setlocal enabledelayedexpansion

rem Run this on an ONLINE Windows PC to build a distributable portable package.
rem Output goes to dist\ ; zip that folder and send it. The end user just
rem double-clicks the launcher inside, no install needed.
rem IMPORTANT: CLOSE the running app (its black console window) before building,
rem otherwise the runtime files are locked and cleanup will fail.

cd /d "%~dp0\.."
set "PYVER=3.11.9"
set "DIST=dist\高考志愿推荐系统"
set "MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple"

echo [1/6] Cleaning output folder...
if exist "%DIST%" (
    rmdir /s /q "%DIST%" 2>nul
    if exist "%DIST%" (
        echo.
        echo [ERROR] Cannot delete the old output folder.
        echo         The app is probably still running and locking files.
        echo         Close the running app window first, then run this script again.
        echo         [ 请先关闭正在运行的程序窗口, 再重新运行本脚本 ]
        echo.
        pause
        exit /b 1
    )
)
mkdir "%DIST%" || goto :err

echo [2/6] Downloading embedded Python (%PYVER%)...
powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip -OutFile py_embed.zip" || goto :err
powershell -Command "Expand-Archive -Force py_embed.zip '%DIST%\runtime'" || goto :err
del py_embed.zip

echo [3/6] Enabling site-packages in embedded Python...
powershell -Command "(Get-Content '%DIST%\runtime\python311._pth') -replace '#import site','import site' | Set-Content '%DIST%\runtime\python311._pth'"
echo Lib\site-packages>> "%DIST%\runtime\python311._pth"

echo [4/6] Installing pip and dependencies (Tsinghua mirror)...
powershell -Command "Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py" || goto :err
"%DIST%\runtime\python.exe" get-pip.py -i %MIRROR% || goto :err
del get-pip.py
"%DIST%\runtime\python.exe" -m pip install -r requirements.txt -i %MIRROR% || goto :err

echo [5/6] Copying program files...
copy /y app.py "%DIST%\" >nul
copy /y requirements.txt "%DIST%\" >nul
copy /y README.md "%DIST%\" >nul
xcopy /e /i /y src "%DIST%\src" >nul
xcopy /e /i /y pages "%DIST%\pages" >nul
xcopy /e /i /y data "%DIST%\data" >nul
if exist .streamlit xcopy /e /i /y .streamlit "%DIST%\.streamlit" >nul
copy /y "packaging\启动应用.bat" "%DIST%\启动应用.bat" >nul
if exist "怎么打开.txt" copy /y "怎么打开.txt" "%DIST%\怎么打开.txt" >nul

echo [6/6] Done.
echo.
echo   Package folder: %CD%\%DIST%
echo   Zip it and send. End user double-clicks "启动应用.bat" to run.
echo   First run on a NEW PC needs vc_redist.x64.exe (see 怎么打开.txt).
echo.
pause
exit /b 0

:err
echo.
echo [ERROR] A step failed. Check your internet connection and retry
echo         (downloading Python / dependencies needs internet).
pause
exit /b 1

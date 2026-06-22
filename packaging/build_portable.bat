@echo off
chcp 65001 >nul
title 打包：生成开箱即用绿色版
setlocal enabledelayedexpansion

rem 在一台联网的 Windows 上运行本脚本，生成可分发的绿色版。
rem 产物在 dist 目录下，压成 zip 发给客户；客户双击其中的 启动应用.bat 即可，无需安装。
rem 注意：打包前请先关闭正在运行的程序（黑色窗口），否则会占用文件导致清理失败。

cd /d "%~dp0\.."
set "PYVER=3.11.9"
set "DIST=dist\高考志愿推荐系统"
set "MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple"

echo [1/6] 清理并创建输出目录...
if exist "%DIST%" (
    rmdir /s /q "%DIST%" 2>nul
    if exist "%DIST%" (
        echo.
        echo [出错] 无法删除旧的输出目录，通常是程序正在运行、占用了文件。
        echo        请先关闭正在运行的"高考志愿推荐系统"黑色窗口，再重新双击本脚本。
        echo.
        pause
        exit /b 1
    )
)
mkdir "%DIST%" || goto :err

echo [2/6] 下载 Python 内嵌版 (%PYVER%)...
powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip -OutFile py_embed.zip" || goto :err
powershell -Command "Expand-Archive -Force py_embed.zip '%DIST%\runtime'" || goto :err
del py_embed.zip

echo [3/6] 开启 site-packages（让内嵌 Python 能加载第三方库）...
powershell -Command "(Get-Content '%DIST%\runtime\python311._pth') -replace '#import site','import site' | Set-Content '%DIST%\runtime\python311._pth'"
echo Lib\site-packages>> "%DIST%\runtime\python311._pth"

echo [4/6] 安装 pip 与依赖（用清华镜像，国内快）...
powershell -Command "Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py" || goto :err
"%DIST%\runtime\python.exe" get-pip.py -i %MIRROR% || goto :err
del get-pip.py
"%DIST%\runtime\python.exe" -m pip install -r requirements.txt -i %MIRROR% || goto :err

echo [5/6] 拷贝程序文件...
copy /y app.py "%DIST%\" >nul
copy /y requirements.txt "%DIST%\" >nul
copy /y README.md "%DIST%\" >nul
xcopy /e /i /y src "%DIST%\src" >nul
xcopy /e /i /y pages "%DIST%\pages" >nul
xcopy /e /i /y data "%DIST%\data" >nul
if exist .streamlit xcopy /e /i /y .streamlit "%DIST%\.streamlit" >nul
copy /y "packaging\启动应用.bat" "%DIST%\启动应用.bat" >nul
if exist "怎么打开.txt" copy /y "怎么打开.txt" "%DIST%\怎么打开.txt" >nul

echo [6/6] 完成！
echo.
echo   绿色版已生成： %CD%\%DIST%
echo   把该文件夹压成 zip 发给客户即可；客户双击 启动应用.bat 使用。
echo   提示：客户首次在新电脑使用，需装一次微软运行库 vc_redist.x64.exe（见 怎么打开.txt）。
echo.
pause
exit /b 0

:err
echo.
echo [出错] 某一步失败，请检查网络后重试（下载 Python/依赖需要联网）。
pause
exit /b 1

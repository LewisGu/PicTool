@echo off
chcp 65001 >nul
echo ============================================
echo  RAWFileCopyByJPG - PyInstaller 一键打包
echo ============================================
echo.

cd /d "%~dp0"

if not exist "resources\app.ico" (
    echo [ERROR] 找不到 resources\app.ico
    echo 请确认图标文件存在后再运行此脚本
    pause
    exit /b 1
)

echo [1/2] 清理旧的构建目录...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
echo.

echo [2/2] 开始打包（使用 .spec，已内嵌 --icon=resources/app.ico）...
py -3 -m PyInstaller -y --clean "RAWFileCopyByJPG.spec"
if errorlevel 1 (
    echo.
    echo [ERROR] 打包失败，请检查错误信息
    pause
    exit /b 1
)

echo.
echo ============================================
echo  打包完成！
echo  EXE 位置: dist\RAWFileCopyByJPG\RAWFileCopyByJPG.exe
echo.
echo  在资源管理器中查看该 EXE 时应显示为 app.ico 图标，
echo  启动后窗口标题栏/任务栏图标也为 app.ico
echo ============================================
pause

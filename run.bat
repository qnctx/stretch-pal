@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo    🌸  StretchPal — 你的桌面拉伸提醒伙伴
echo    ════════════════════════════════════
echo.
echo    正在检查依赖...
pip install pystray Pillow -q 2>nul
echo.
echo    启动中... 横幅将在 9 / 11 / 13 / 15 / 17 点自动弹出
echo    右键系统托盘 ♥ 图标可以手动触发或退出
echo.
start "" pythonw stretch_pal.py
echo    已启动！现在可以关闭这个窗口了~
echo.
timeout /t 2 >nul
exit

@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PYTHON_EXEC=".\.venv\Scripts\python.exe"

REM 如果找不到虛擬環境內的 python，則自動切換為系統全域的 python
if not exist %PYTHON_EXEC% (
    set PYTHON_EXEC="python"
)

echo =============================================
echo        🎓 輔大畢業學分系統 - 爬蟲與啟動腳本      
echo =============================================
echo.

echo [步驟 1/3] 開始執行 test1.py (個人成績)
echo 💡 提示：請在彈出的瀏覽器中手動輸入帳號密碼
%PYTHON_EXEC% get_person_info\test1.py
if %ERRORLEVEL% NEQ 0 (
    echo ❌ test1.py 執行失敗，已中斷流程。
    pause
    exit /b 1
)

echo.
echo [步驟 2/3] 開始執行 test2.py (畢業學分檢核表)
echo 💡 提示：請在彈出的瀏覽器中手動輸入帳號密碼
%PYTHON_EXEC% get_person_info\test2.py
if %ERRORLEVEL% NEQ 0 (
    echo ❌ test2.py 執行失敗，已中斷流程。
    pause
    exit /b 1
)

echo.
echo [步驟 3/3] 資料庫更新完畢！正在為您開啟畢業選課系統網頁...
start http://localhost/code/-/graduation_system/index.php

echo ✅ 流程結束！
pause

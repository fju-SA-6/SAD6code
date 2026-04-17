@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PYTHON_EXEC="..\.venv\Scripts\python.exe"

REM 如果找不到虛擬環境內的 python，則自動切換為系統全域的 python
if not exist %PYTHON_EXEC% (
    set PYTHON_EXEC="python"
)

echo =============================================
echo        🎓 輔大畢業學分系統 - 爬蟲與啟動腳本      
echo =============================================
echo.
if exist "account.txt" (
    echo 📄 偵測到 account.txt，自動載入帳號與密碼...
    for /f "tokens=2 delims=：" %%a in ('type account.txt ^| find "帳號"') do set FJU_ACCOUNT=%%a
    for /f "tokens=2 delims=：" %%a in ('type account.txt ^| find "密碼"') do set FJU_PASSWORD=%%a
) else (
    set /p FJU_ACCOUNT="請輸入您的輔大系統登入帳號 (學號) [若要跳過請直接按 Enter]: "
    REM Windows cmd 不原生支援隱藏密碼，為求方便將直接顯示
    set /p FJU_PASSWORD="請輸入您的密碼 [若要跳過請直接按 Enter]: "
)
echo.

echo [步驟 1/3] 開始執行 test1.py (個人成績)
echo 💡 提示：系統會嘗試幫您自動登入。如果失敗，請在瀏覽器中手動完成輸入。
%PYTHON_EXEC% test1.py
if %ERRORLEVEL% NEQ 0 (
    echo ❌ test1.py 執行失敗，已中斷流程。
    pause
    exit /b 1
)

echo.
echo [步驟 2/3] 開始執行 test2.py (畢業學分檢核表)
echo 💡 提示：系統會嘗試幫您自動登入。如果失敗，請在瀏覽器中手動完成輸入。
%PYTHON_EXEC% test2.py
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

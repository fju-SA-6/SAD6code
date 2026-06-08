#!/bin/bash

# 切換到專案根目錄
cd "$(dirname "$0")"

# 設定 Python 執行檔路徑 (使用虛擬環境)
PYTHON_EXEC="./.venv/bin/python"

echo "============================================="
echo "       🎓 輔大畢業學分系統 - 爬蟲與啟動腳本      "
echo "============================================="

echo -e "\n[步驟 1/3] 開始執行 test1.py (個人成績)"
echo "💡 提示：請在彈出的瀏覽器中手動輸入帳號密碼"
$PYTHON_EXEC get_person_info/test1.py
if [ $? -ne 0 ]; then
    echo "❌ test1.py 執行失敗，已中斷流程。"
    exit 1
fi

echo -e "\n[步驟 2/3] 開始執行 test2.py (畢業學分檢核表)"
echo "💡 提示：請在彈出的瀏覽器中手動輸入帳號密碼"
$PYTHON_EXEC get_person_info/test2.py
if [ $? -ne 0 ]; then
    echo "❌ test2.py 執行失敗，已中斷流程。"
    exit 1
fi

echo -e "\n[步驟 3/3] 資料庫更新完畢！正在為您開啟畢業選課系統網頁..."
open "http://localhost/code/-/graduation_system/index.php"

echo "✅ 流程結束！"

#!/bin/bash

# 切換到專案根目錄
cd "$(dirname "$0")"

# 設定 Python 執行檔路徑 (使用虛擬環境)
PYTHON_EXEC="../.venv/bin/python"

echo "============================================="
echo "       🎓 輔大畢業學分系統 - 爬蟲與啟動腳本      "
echo "============================================="

# 嘗試從 account.txt 讀取帳號密碼
if [ -f "account.txt" ]; then
    echo "📄 偵測到 account.txt，自動載入帳號與密碼..."
    FJU_ACCOUNT=$(awk -F'：' 'NR==1 {print $2}' account.txt | tr -d '\r')
    FJU_PASSWORD=$(awk -F'：' 'NR==2 {print $2}' account.txt | tr -d '\r')
else
    # 若沒有檔案則回到手動輸入
    echo "請輸入您的輔大系統登入帳號 (學號) [若要跳過請直接按 Enter]:"
    read FJU_ACCOUNT
    echo "請輸入您的密碼 (輸入時字元不會顯示) [若要跳過請直接按 Enter]:"
    read -s FJU_PASSWORD
    echo ""
fi

export FJU_ACCOUNT="$FJU_ACCOUNT"
export FJU_PASSWORD="$FJU_PASSWORD"

echo -e "\n[步驟 1/3] 開始執行 test1.py (個人成績)"
echo "💡 提示：系統會嘗試幫您自動登入。如果失敗，請在瀏覽器中手動完成輸入。"
$PYTHON_EXEC test1.py
if [ $? -ne 0 ]; then
    echo "❌ test1.py 執行失敗，已中斷流程。"
    exit 1
fi

echo -e "\n[步驟 2/3] 開始執行 test2.py (畢業學分檢核表)"
echo "💡 提示：系統會嘗試幫您自動登入。如果失敗，請在瀏覽器中手動完成輸入。"
$PYTHON_EXEC test2.py
if [ $? -ne 0 ]; then
    echo "❌ test2.py 執行失敗，已中斷流程。"
    exit 1
fi

echo -e "\n[步驟 3/3] 資料庫更新完畢！正在為您開啟畢業選課系統網頁..."
open "http://localhost/code/-/graduation_system/index.php"

echo "✅ 流程結束！"

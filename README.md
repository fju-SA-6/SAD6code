# fju_SAD_6_code

## 已完成
抓fju課程資料
抓個人的學分資料
分析缺少的學分
推薦課程

## 未完成
通識的分類
別系的畢業門檻
會出結果成pdf
擋修
把php網頁改成python_gui
讓系統自動勾選的顯示在最前面
根據不同系的學生推計不同的課程
英檢之類的門檻檢測
包裝成完整.app/.exe

## pip install
pip3 install mysql-connector-python beautifulsoup4 selenium webdriver-manager
pip3 install flask flask-cors
source .venv/bin/activate
pip install setuptools
pip install --upgrade undetected-chromedriver
## 運行方式
運行test1.py
運行test2.py
打開index.php（XAMPP:http://localhost/code/-/graduation_system/index.php）

./run.sh
test_project/run.sh

---

## 專案介紹 (Program Introduction)

這是一個專為輔仁大學學生設計的**「畢業學分查核與選課推薦系統」**。
系統結合了 Web 網路爬蟲與 PHP 前後端技術，自動化幫學生計算畢業門檻，並給予最精準的選課建議。

### 核心功能列表

1. **自動化個人成績擷取 (`test1.py`)**  
   使用 Selenium 模擬瀏覽器行為，登入「輔大 SIS 學生資訊系統」，將歷年修課的所有課程名稱、學分數與最終成績自動匯入至本地 MySQL 資料庫中。

2. **畢業學分檢核表爬取 (`test2.py`)**  
   針對「輔大學習輔導與預警系統」的畢業學分檢核頁籤進行爬蟲，精準辨識出哪些校定、院系必修**「已經完成」**，哪些**「尚未修課」**，並同步紀錄進資料庫，做為推薦系統的最高權重依據。*(此腳本採用 `undetected-chromedriver` 以繞過 Cloudflare 機器人驗證機制)*

3. **智慧化畢業學分數計算 (`graduation_system/index.php`)**  
   - 進入介面後，系統會自動比對資料庫，幫你**自動打勾**所有已經及格或抵免的課程。
   - 介面提供強大的過濾系統：可自訂每頁顯示數量 (100, 200...)，或是依據「學期」與「星期」進行複合條件搜尋，並會貼心標出該門課的授課教師。

4. **動態選課推薦系統 (`graduation_system/process.php`)**  
   - 提交查核後，系統會計算您的「總學分」、「必修」與「選修」的落差。
   - **優先推薦檢核表缺口：** 系統會優先分析 `test2.py` 找到的「尚未修課」必修項目，並在選課系統中推薦能滿足此缺口的課程。
   - **動態補齊學分：** 計算完您的必修與選修缺口後，系統會自動從資料庫反覆撈取未修課程，直到被推薦課程的總學分剛好**填滿你的畢業所需門檻**為止。

### 執行方式 (自動化流程)

為求方便，專案內準備了快速執行腳本，執行後將自動依序呼叫兩個爬蟲腳本，最後再打開網頁系統：
- **Mac/Linux 用戶:** `./run.sh`
- **Windows 用戶:** 點擊執行 `run.bat`

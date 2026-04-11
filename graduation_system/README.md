# 畢業學分查核系統

這是一個基於PHP和MySQL的畢業學分查核系統，具有現代化的使用者介面。

## 環境需求
- PHP 7.4 或以上版本
- MySQL 5.7 或以上版本
- 網頁伺服器（Apache、Nginx）或PHP內建開發伺服器

## 快速安裝（推薦：XAMPP）
1. 下載並安裝XAMPP：https://www.apachefriends.org/zh_tw/download.html
2. 啟動XAMPP控制面板，啟動Apache和MySQL
3. 將 `graduation_system` 資料夾複製到 `C:\xampp\htdocs\` 中
4. 在瀏覽器中訪問：http://localhost/graduation_system/index.php

## 替代方案：PHP內建伺服器
如果您有PHP但沒有XAMPP：
1. 確保PHP已安裝並加入PATH環境變數
2. 雙擊執行 `start_server.bat` 檔案
3. 在瀏覽器中訪問：http://localhost:8000

## 資料庫設定
1. 在phpMyAdmin中建立資料庫 `graduation_db`
2. 匯入 `graduation_db_分好版.sql` 檔案
3. 修改 `config.php` 中的資料庫連接資訊（如果需要）

## 功能
- 顯示學校課程列表（必修/選修課程以不同顏色區分）
- 即時搜尋課程功能
- 全選/清除勾選按鈕
- 用戶勾選已修習課程
- 計算已修學分並與畢業要求比對
- 生成詳細的學分統計和畢業狀態報告

## 使用者介面特色
- 使用Bootstrap 5框架，提供響應式設計
- 卡片式佈局，清晰易讀
- 必修課程以紅色標記，選修課程以綠色標記
- 搜尋框支援即時過濾課程
- 統計資料以卡片形式展示
- 畢業狀態以警示框顯示

## 畢業要求
目前設定為：
- 總學分：128
- 必修學分：80
- 選修學分：48

如需調整，請修改 `process.php` 中的變數。

## 注意事項
- 確保PHP和MySQL已正確安裝並運行。
- 課程資料來自 `FJU_Courses` 表。
- 系統支援中文介面。
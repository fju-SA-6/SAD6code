import time
import mysql.connector
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# 1. 資料庫連線設定
# ==========================================
db_config = {
    'host': '127.0.0.1',
    'port': 3307,              
    'user': 'root',
    'password': '' # ⚠️ 請在這裡換成你的 MySQL 密碼
}

def setup_database():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("CREATE DATABASE IF NOT EXISTS graduation_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE graduation_db")
        
        # 建立個人成績資料表 (成績欄位設為 VARCHAR，因為可能會有 "抵免")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FJU_Personal_Grades (
                id INT AUTO_INCREMENT PRIMARY KEY,
                course_type VARCHAR(20),   -- 一般學期 或 抵免
                academic_year VARCHAR(10),
                semester VARCHAR(10),
                category VARCHAR(20),      -- 必修、選修、通識
                course_name VARCHAR(100),
                credits INT,
                grade VARCHAR(10),         -- 分數或抵免狀態
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ MySQL 「個人成績資料表」確認完畢！")
        return conn, cursor
    except mysql.connector.Error as err:
        print(f"❌ 資料庫初始化失敗: {err}")
        return None, None

# ==========================================
# 2. 主爬蟲程式 (含手動登入等待)
# ==========================================
def scrape_personal_grades():
    conn, cursor = setup_database()
    if not conn: return

    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()

    try:
        # 1. 前往登入頁面
        print("🌍 正在開啟輔大 SIS 學生資訊系統...")
        driver.get("https://sis.fju.edu.tw/#/")
        
        print("\n⏳ 【手動登入時間】")
        print("請在彈出的瀏覽器中，輸入你的帳號密碼完成登入。")
        print("登入後請自行點擊左側選單進入「成績查詢」。")
        print("程式會在背景等待，直到偵測到成績表格出現為止（最多等待 60 秒）...\n")

        # 2. 等待使用者登入並進入成績頁面，直到目標表格出現
        try:
            # 根據你提供的 HTML，尋找包含「學期成績」的表格
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.q-table tbody tr"))
            )
            print("🔓 成功偵測到成績表格！開始攔截資料...")
            time.sleep(2) # 稍微等待表格資料完全填入
        except TimeoutException:
            print("❌ 等待逾時！你沒有在 60 秒內登入並進入成績頁面。")
            return

        # 3. 確保表格顯示「全部」列，而不是只有分頁
        try:
            # 點開每頁列數的下拉選單
            page_select = driver.find_element(By.XPATH, "//div[contains(@class, 'q-table__bottom-item')]//label")
            driver.execute_script("arguments[0].click();", page_select)
            time.sleep(1)
            # 點擊「全部」選項
            all_option = driver.find_element(By.XPATH, "//div[contains(@class, 'q-item__label') and text()='全部']")
            driver.execute_script("arguments[0].click();", all_option)
            time.sleep(2) # 等待全展資料載入
        except:
            print("⚠️ 無法切換為「全部」顯示，將直接抓取當前頁面可見資料。")

        # 4. 開始解析 HTML 並寫入資料庫
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        rows = soup.select("table.q-table tbody tr")
        
        inserted_count = 0
        
        # 清空舊資料，避免重複抓取時發生資料疊加 (可依需求決定是否保留這行)
        cursor.execute("TRUNCATE TABLE FJU_Personal_Grades")
        
        for row in rows:
            cols = row.find_all('td')
            # 確保這是一行正常的成績資料 (至少有 11 個欄位)
            if len(cols) < 11: 
                continue
                
            # 提取各欄位資料 (依照你提供的 HTML 欄位順序)
            course_type = cols[0].get_text(strip=True)
            year = cols[1].get_text(strip=True)
            sem = cols[2].get_text(strip=True)
            category = cols[3].get_text(strip=True)
            
            # 科目名稱處理：使用 separator 隔開文字與 span，取第一段避免抓到標籤(如: 網, 程)
            course_name = cols[4].get_text(separator='|', strip=True).split('|')[0]
            
            credits_str = cols[5].get_text(strip=True)
            credits_val = int(credits_str) if credits_str.isdigit() else 0
            
            grade = cols[8].get_text(strip=True)
            
            # 寫入 MySQL
            sql = """
                INSERT INTO FJU_Personal_Grades 
                (course_type, academic_year, semester, category, course_name, credits, grade) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            val = (course_type, year, sem, category, course_name, credits_val, grade)
            
            try:
                cursor.execute(sql, val)
                inserted_count += 1
                print(f"📥 寫入成功：{year}-{sem} | {course_name} ({category}) | {credits_val}學分 | 成績: {grade}")
            except mysql.connector.Error as err:
                print(f"⚠️ 寫入失敗 [{course_name}]: {err}")

        conn.commit()
        print(f"\n🎉 個人成績抓取完成！共成功寫入 {inserted_count} 筆成績。")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
    finally:
        driver.quit()
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    scrape_personal_grades()
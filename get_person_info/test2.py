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
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc

# ==========================================
# 1. 資料庫連線設定
# ==========================================
db_config = {
    'host': '127.0.0.1',
    'port': 3307,              
    'user': 'root',
    'password': '' # 密碼留空
}

def setup_database():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("CREATE DATABASE IF NOT EXISTS graduation_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE graduation_db")
        
        # 建立專屬於「畢業檢核表」的資料表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FJU_Graduation_Check (
                id INT AUTO_INCREMENT PRIMARY KEY,
                category VARCHAR(20),       -- 全人/校定、院系必修、其它
                requirement_name VARCHAR(50), -- 該項目的規定名稱 (例如: 人生哲學、微積分)
                is_completed BOOLEAN,       -- 是否已滿足該項畢業條件
                semester VARCHAR(20),       -- 修課學期 (例如: 113-1)
                course_name VARCHAR(100),   -- 實際修課名稱
                grade VARCHAR(30),          -- 成績 (分數、未評定、抵免)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ MySQL 「畢業檢核表資料庫」確認完畢！")
        return conn, cursor
    except mysql.connector.Error as err:
        print(f"❌ 資料庫初始化失敗: {err}")
        return None, None

# ==========================================
# 2. HTML 解析與寫入核心
# ==========================================
def parse_and_save_check_list(html_source, conn, cursor):
    soup = BeautifulSoup(html_source, 'html.parser')
    
    # 定義要抓取的 Tab 區塊
    tabs_to_parse = {
        'nav-is': '全人/校定',
        'nav-rs': '院系必修'
    }

    inserted_count = 0
    
    # 每次更新前先清空舊的檢核資料，避免重複疊加
    cursor.execute("TRUNCATE TABLE FJU_Graduation_Check")

    print("\n🔍 正在解析檢核表 HTML 結構...")

    # 1. 抓取「全人/校定」與「必修」區塊
    for tab_id, category_name in tabs_to_parse.items():
        tab_pane = soup.find('div', id=tab_id)
        if not tab_pane: continue
        
        list_items = tab_pane.find_all('li', class_='list-group-item')
        for item in list_items:
            # 判斷該項目是否已達成 (有綠色打勾 fa-check-circle 就是已完成)
            is_completed = True if item.find('i', class_='fa-check-circle') else False
            
            # 取得規定項目名稱 (例如: 國文、微積分)
            req_name_tag = item.find('b', class_='text-dark')
            req_name = req_name_tag.text.strip() if req_name_tag else "未知項目"
            
            # 尋找該項目底下實際修過的課程清單
            taken_courses = item.find_all('div', class_='small text-muted text-nowrap')
            
            if not taken_courses:
                # 尚未修課的缺口
                sql = "INSERT INTO FJU_Graduation_Check (category, requirement_name, is_completed, semester, course_name, grade) VALUES (%s, %s, %s, %s, %s, %s)"
                cursor.execute(sql, (category_name, req_name, is_completed, "", "", "尚未修課"))
                inserted_count += 1
            else:
                for course in taken_courses:
                    # 學期提取
                    sem_badge = course.find('span', class_='text-crimson')
                    semester = sem_badge.text.split('/')[-1].strip() if sem_badge and '/' in sem_badge.text else ""
                    
                    # 成績提取
                    badges = course.find_all('span', class_='badge-light')
                    grade = badges[-1].text.strip() if badges else ""
                    
                    # 課程名稱提取 (精準去除非文字標籤)
                    course_text = course.get_text(separator='|', strip=True)
                    parts = course_text.split('|')
                    actual_course_name = parts[2].strip() if len(parts) > 2 else req_name
                    
                    sql = "INSERT INTO FJU_Graduation_Check (category, requirement_name, is_completed, semester, course_name, grade) VALUES (%s, %s, %s, %s, %s, %s)"
                    cursor.execute(sql, (category_name, req_name, is_completed, semester, actual_course_name, grade))
                    inserted_count += 1

    # 2. 抓取「其它」區塊 (格式稍微不同)
    nomatch_pane = soup.find('div', id='nav-nomatch')
    if nomatch_pane:
        nomatch_items = nomatch_pane.find_all('li', class_='list-group-item')
        for item in nomatch_items:
            sem_badge = item.find('span', class_='text-crimson')
            semester = sem_badge.text.split('/')[-1].strip() if sem_badge and '/' in sem_badge.text else ""
            
            course_tag = item.find('span', class_='text-dark')
            course_name = course_tag.text.strip() if course_tag else ""
            
            grade_badge = item.find('span', class_='text-dodgerblue')
            grade = grade_badge.text.strip() if grade_badge else ""
            
            # 附加警告標籤 (如: 重複)
            warning_badges = item.find_all('span', class_='badge-warning')
            for warn in warning_badges:
                # 檢查該警告是否顯示在畫面上 (非 display: none)
                if 'display: none' not in warn.get('style', ''):
                    grade += f" ({warn.text.strip()})"

            if course_name:
                sql = "INSERT INTO FJU_Graduation_Check (category, requirement_name, is_completed, semester, course_name, grade) VALUES (%s, %s, %s, %s, %s, %s)"
                cursor.execute(sql, ('其它', course_name, True, semester, course_name, grade))
                inserted_count += 1

    conn.commit()
    print(f"🎉 資料庫寫入成功！共建立 {inserted_count} 筆畢業檢核紀錄。")

# ==========================================
# 3. Selenium 開窗與監控程序
# ==========================================
def run_scraper():
    conn, cursor = setup_database()
    if not conn: return

    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--disable-notifications")
    
    driver = uc.Chrome(options=chrome_options, version_main=146)
    driver.maximize_window()

    try:
        # 1. 前往學習輔導系統登入頁面
        print("🌍 正在開啟輔大學習輔導與預警系統...")
        driver.get("https://learningcounseling.fju.edu.tw/Student/Account/Login")
        
        print("\n⏳ 【進入手動操作階段】")
        print("1. 請在彈出的瀏覽器中輸入帳號密碼登入。")
        print("2. 登入後，請點擊或導航至「畢業學分檢核」。")
        print("3. 程式會在背景靜靜等待，直到看見「修業科目檢核表」出現（最長等待 90 秒）...\n")

        # 2. 等待直到進入最終的檢核表頁面
        try:
            start_time = time.time()
            found_target = False
            
            while time.time() - start_time < 90:
                # 遍歷目前所有開啟的分頁
                for handle in driver.window_handles:
                    driver.switch_to.window(handle)
                    # 尋找目標頁籤 id="nav-is"
                    if driver.find_elements(By.ID, "nav-is"):
                        found_target = True
                        break # 跳出內圈 for
                
                if found_target:
                    break # 跳出外圈 while
                
                time.sleep(1) # 等待 1 秒再重新掃描一次所有分頁
            
            if not found_target:
                raise TimeoutException()
            
            print("🔓 偵測到「修業科目檢核表」！")
            
            # 稍等 2 秒，確保網頁上的 AJAX 資料轉圈圈 (資料載入中) 跑完
            time.sleep(2)
            
            # 取得整頁 HTML
            html_source = driver.page_source
            print("📥 成功攔截原始碼，準備進行解析...")
            
            # 3. 呼叫解析函式
            parse_and_save_check_list(html_source, conn, cursor)
            
        except TimeoutException:
            print("❌ 等待逾時！你沒有在 90 秒內進入畢業學分檢核頁面。")

    except Exception as e:
        print(f"❌ 發生未預期錯誤: {e}")
    finally:
        print("🛑 關閉瀏覽器與資料庫連線...")
        try:
            driver.quit()
        except Exception as e:
            print(f"⚠️ 關閉瀏覽器時發生小錯誤 (可忽略): {e}")
            
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    run_scraper()
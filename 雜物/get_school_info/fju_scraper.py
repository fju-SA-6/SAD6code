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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# ==========================================
# 1. 資料庫連線設定
# ==========================================
db_config = {
    'host': '127.0.0.1',
    'port': 3307,
    'user': 'root',
    'password': '' # 密碼空白
}

def setup_database():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS graduation_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE graduation_db")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FJU_Courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                academic_year VARCHAR(10) NOT NULL,
                semester VARCHAR(10) NOT NULL,
                course_name VARCHAR(100) NOT NULL,
                teacher VARCHAR(50),
                credits INT,
                category VARCHAR(20),
                time_loc VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ MySQL 資料庫與資料表確認成功！")
        return conn, cursor
    except mysql.connector.Error as err:
        print(f"❌ 資料庫初始化失敗: {err}")
        return None, None

def scroll_up_down(driver):
    try:
        total_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(0, total_height, 1000):
            driver.execute_script(f"window.scrollTo(0, {i});")
            time.sleep(0.1)
        driver.execute_script("window.scrollTo(0, 0);")
    except:
        pass 

# ==========================================
# 2. 主爬蟲程式
# ==========================================
def scrape_all_fju_courses():
    conn, cursor = setup_database()
    if not conn: return

    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    
    def force_select_dropdown(label_text, target_option):
        """強制點開選單並選擇指定文字，不進行智慧檢查"""
        print(f"🔄 強制設定「{label_text}」為「{target_option}」...")
        try:
            # 1. 找到該選單的 q-field__control (精確比對標籤文字，避免 "一般學期" 影響 "學期" 的判斷)
            xpath_label = f"//label[.//div[contains(@class, 'q-field__label') and contains(text(), '{label_text}')]]"
            dropdown_label = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath_label))
            )
            
            control = dropdown_label.find_element(By.XPATH, ".//div[contains(@class, 'q-field__control')]")
            
            # 2. 捲動到該處並點擊
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", control)
            time.sleep(0.5)
            # Quasar有時需要原生點擊，或者直接對該元素 dispatch event
            driver.execute_script("arguments[0].click();", control)
            
            # 3. 等待選單彈出
            time.sleep(1.5) 
            
            # 4. 尋找選項
            try:
                # 等待 q-menu 出現
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".q-menu"))
                )
                items = driver.find_elements(By.CSS_SELECTOR, ".q-menu .q-item")
                target_elem = None
                for item in items:
                    # 確保文字符合 (不區分大小寫或忽略空白)
                    if target_option in item.text:
                        target_elem = item
                        break

                if target_elem:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_elem)
                    time.sleep(0.2)
                    driver.execute_script("arguments[0].click();", target_elem)
                    print(f"✔️ 成功選擇：{target_option}")
                    time.sleep(1)
                else:
                    print(f"⚠️ 找不到選項：{target_option}，可能系統已預設選取。")
                    driver.execute_script("document.body.click();")
            except Exception as e:
                print(f"⚠️ 選單未顯示或無法選擇：{target_option}，可能系統已預設選取。")
                driver.execute_script("document.body.click();")
                
        except Exception as e:
            print(f"❌ 設定 {label_text} 失敗。")


    target_year = "114"
    # 先抓上學期，再抓下學期
    target_semesters = ["上學期", "下學期"] 
    total_all_inserted = 0

    try:
        driver.get("https://outline.fju.edu.tw/#/outlineSearch/searchView")
        time.sleep(5) 

        for sem in target_semesters:
            print(f"\n🚀 >>> 開始爬取：{target_year}學年 【{sem}】 <<<")
            
            # 點擊重置按鈕 (除了第一次之外)
            if sem != target_semesters[0]:
                print("🔄 執行重置...")
                try:
                    # 使用 aria-label='清空搜尋條件'
                    reset_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='清空搜尋條件']"))
                    )
                    driver.execute_script("arguments[0].click();", reset_btn)
                    time.sleep(3)
                except:
                    print("⚠️ 找不到清空按鈕，重整網頁...")
                    driver.refresh()
                    time.sleep(5)

            # 強制設定三個格子
            force_select_dropdown("課程類別", "一般學期")
            force_select_dropdown("學年度", target_year)
            force_select_dropdown("學期", sem)

            # 按下搜尋
            try:
                search_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='搜尋']"))
                )
                driver.execute_script("arguments[0].click();", search_btn)
                print("🔍 搜尋中並等待資料載入...")
            except:
                print("❌ 找不到搜尋按鈕")
                continue

            semester_inserted = 0
            current_page = 1

            # 分頁抓取迴圈
            while True:
                try:
                    # 等待表格內容出現
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "table.q-table tbody tr.q-tr"))
                    )
                    scroll_up_down(driver)
                    
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    rows = soup.select("table.q-table tbody tr.q-tr")
                    
                    page_inserted = 0
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) < 13: continue
                        
                        course_name = cols[5].get_text(separator='\n', strip=True).split('\n')[0]
                        teacher = cols[6].get_text(strip=True)
                        credits_val = int(cols[7].get_text(strip=True)) if cols[7].get_text(strip=True).isdigit() else 0
                        category = cols[8].get_text(strip=True)
                        time_loc = f"{cols[10].get_text(strip=True)} {cols[11].get_text(strip=True)} {cols[12].get_text(strip=True)}"
                        
                        sql = "INSERT INTO FJU_Courses (academic_year, semester, course_name, teacher, credits, category, time_loc) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                        cursor.execute(sql, (target_year, sem, course_name, teacher, credits_val, category, time_loc))
                        page_inserted += 1

                    conn.commit()
                    semester_inserted += page_inserted
                    print(f"✅ 第 {current_page} 頁 OK，已存入 {page_inserted} 筆資料。")

                    # 檢查是否有下一頁按鈕
                    next_btns = driver.find_elements(By.XPATH, "//div[contains(@class, 'q-pagination')]//button[.//i[contains(text(), 'keyboard_arrow_right')]]")
                    if not next_btns: 
                        print(f"🏁 【{sem}】已抓取完畢。")
                        break
                    
                    next_btn = next_btns[0]
                    # 檢查按鈕是否已停用
                    is_disabled = (not next_btn.is_enabled() or 
                                   'disabled' in next_btn.get_attribute('class') or 
                                   next_btn.get_attribute('aria-disabled') == 'true')
                    
                    if is_disabled:
                        print(f"🏁 【{sem}】已達最後一頁，抓取完畢。")
                        break
                    
                    # 翻頁前記錄第一筆資料的識別碼，用來判斷是否已經翻頁成功
                    first_row_text = rows[0].text
                    
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", next_btn) 
                    
                    # 透過等待第一筆資料的內容改變，確保 Table 內容完全更新
                    try:
                        WebDriverWait(driver, 15).until(
                            lambda d: d.find_elements(By.CSS_SELECTOR, "table.q-table tbody tr.q-tr")[0].text != first_row_text
                        )
                        current_page += 1
                        time.sleep(1) # 額外等待一下確保 DOM 穩定
                    except TimeoutException:
                        print("⚠️ 翻頁後資料未更新，可能已達最後一頁！")
                        break
                    
                except Exception as e:
                    print(f"⚠️ 該頁抓取發生例外錯誤: {e}")
                    break

            total_all_inserted += semester_inserted

        print(f"\n🏆 任務完成！共存入 {total_all_inserted} 筆課程。")

    except Exception as e:
        print(f"❌ 嚴重錯誤: {e}")
    finally:
        driver.quit()
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    scrape_all_fju_courses()
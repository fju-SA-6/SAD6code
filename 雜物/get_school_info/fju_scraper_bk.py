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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ==========================================
# 1. 資料庫連線設定
# ==========================================
db_config = {
    'host': '127.0.0.1',
    'port': 3307,              # 配合你 Mac 上的 MySQL Port
    'user': 'root',
    'password': 'yourpassword' # ⚠️ 請在這裡換成你的 MySQL 密碼
}

def setup_database():
    """負責初始化資料庫與資料表"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 自動建立資料庫 (設定 utf8mb4 支援中文與特殊符號)
        cursor.execute("CREATE DATABASE IF NOT EXISTS graduation_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE graduation_db")
        
        # 自動建立課程資料表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FJU_Courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                course_name VARCHAR(100) NOT NULL,
                teacher VARCHAR(50),
                credits INT,
                category VARCHAR(20),
                time_loc VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ MySQL 資料庫與資料表初始化成功！")
        return conn, cursor
    except mysql.connector.Error as err:
        print(f"❌ 資料庫初始化失敗: {err}")
        return None, None

# ==========================================
# 2. 模擬真人上下滾動函式 (破解 Lazy Loading)
# ==========================================
def scroll_up_down(driver):
    """模擬真人慢慢往下滾動再往上，強迫網頁把隱藏的表格與資料吐出來"""
    print("↕️ 正在上下滾動頁面，強迫渲染資料...")
    try:
        total_height = driver.execute_script("return document.body.scrollHeight")
        # 每次往下滾 500px，慢慢滾到底
        for i in range(0, total_height, 500):
            driver.execute_script(f"window.scrollTo(0, {i});")
            time.sleep(0.1)
        time.sleep(0.5)
        # 再滾回最上面
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)
    except Exception as e:
        pass # 容錯處理

# ==========================================
# 3. 主爬蟲程式
# ==========================================
def scrape_all_fju_courses():
    conn, cursor = setup_database()
    if not conn:
        return

    # 設定 Chrome 瀏覽器
    chrome_options = Options()
    # chrome_options.add_argument("--headless") # 等一切順利後，可取消註解在背景執行
    chrome_options.add_argument("--disable-notifications")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # ⭐️ 關鍵：強制視窗最大化，讓輔大系統自動切換成「表格 (Table)」版面
    driver.maximize_window()
    
    # --- 內部函式：處理 Quasar 框架的下拉選單 (終極防呆版) ---
    def select_quasar_dropdown(label_keyword, option_text):
        print(f"🔄 正在設定「{label_keyword}」為「{option_text}」...")
        try:
            # 1. 點擊展開選單 (直接找畫面上真實顯示的標籤文字，無視錯誤的 aria 屬性)
            trigger_xpath = f"//label[.//div[contains(@class, 'q-field__label') and contains(text(), '{label_keyword}')]]"
            dropdown_trigger = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, trigger_xpath))
            )
            
            # 將畫面捲動到該選單位置並點擊
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown_trigger)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", dropdown_trigger)
            time.sleep(1.5) # 給選單動畫多一點時間彈出
            
            # 2. 點擊目標選項
            option_xpath = f"//div[contains(@class, 'q-item__label') and contains(text(), '{option_text}')]"
            option = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, option_xpath))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", option)
            time.sleep(1) 
            
        except Exception as e:
            print(f"⚠️ 選擇 {label_keyword} ({option_text}) 時發生錯誤，可能是畫面尚未載入完成。")

    try:
        print("🌍 正在開啟輔大課程大綱系統...")
        driver.get("https://outline.fju.edu.tw/#/outlineSearch/searchView")
        time.sleep(3) # 等待網頁核心組件載入
        
        # 進行第一次滾動，確保基本框架與選單都長出來
        scroll_up_down(driver)

        # 3. 填寫搜尋條件
        select_quasar_dropdown("課程類別", "一般學期")
        select_quasar_dropdown("學年度", "114")
        select_quasar_dropdown("學期", "下學期")

        # 4. 點擊「搜尋」按鈕
        print("⏳ 等待搜尋按鈕出現...")
        search_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[@aria-label='搜尋']"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", search_btn)
        print("🖱️ 已點擊「搜尋」，開始載入全校課程...")

        total_inserted = 0
        current_page = 1

        # 5. 開始無限翻頁迴圈 (針對電腦版 Table 結構解析)
        while True:
            print(f"\n📄 正在抓取第 {current_page} 頁資料...")
            
            try:
                # 等待表格的資料列出現
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.q-table tbody tr.q-tr"))
                )
                
                # ⭐️ 關鍵：出現表格後，進行上下滾動，確保該頁面所有隱藏的 <tr> 都被 Render 出來
                scroll_up_down(driver)
                
                # 將渲染完畢的 HTML 交給 BeautifulSoup
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                rows = soup.select("table.q-table tbody tr.q-tr")
                
                page_inserted = 0
                
                for row in rows:
                    cols = row.find_all('td')
                    
                    # 排除手機版排版用的隱藏擴充列 (正常的課程列通常有十幾個欄位)
                    if len(cols) < 13:
                        continue
                        
                    # 根據表格欄位順序提取資料 (索引值對應：5=課名, 6=教師, 7=學分, 8=選別, 10=星期, 11=節次, 12=教室)
                    course_name = cols[5].get_text(separator='\n', strip=True).split('\n')[0]
                    teacher = cols[6].get_text(strip=True)
                    
                    credits_str = cols[7].get_text(strip=True)
                    credits = int(credits_str) if credits_str.isdigit() else 0
                    
                    category = cols[8].get_text(strip=True)
                    
                    # 將星期、節次、教室組合成一個字串
                    day = cols[10].get_text(strip=True)
                    period = cols[11].get_text(strip=True)
                    classroom = cols[12].get_text(strip=True)
                    time_loc = f"{day} {period} {classroom}".strip()
                    
                    # 寫入資料庫
                    sql = "INSERT INTO FJU_Courses (course_name, teacher, credits, category, time_loc) VALUES (%s, %s, %s, %s, %s)"
                    val = (course_name, teacher, credits, category, time_loc)
                    
                    try:
                        cursor.execute(sql, val)
                        page_inserted += 1
                    except mysql.connector.Error as err:
                        print(f"⚠️ 寫入失敗 [{course_name}]: {err}")

                conn.commit()
                total_inserted += page_inserted
                print(f"✅ 第 {current_page} 頁完成，新增 {page_inserted} 筆，累積總數：{total_inserted} 筆")

                # 6. 尋找並點擊「下一頁」按鈕
                # Quasar 表格底部的下一頁箭頭 icon 是 keyboard_arrow_right
                next_btn_xpath = "//div[contains(@class, 'q-pagination')]//button[.//i[contains(text(), 'keyboard_arrow_right')]]"
                next_btn = driver.find_element(By.XPATH, next_btn_xpath)
                
                # 檢查按鈕是否處於 disabled 狀態 (已達最後一頁)
                if not next_btn.is_enabled() or 'disabled' in next_btn.get_attribute('class'):
                    print("\n🛑 已抵達最後一頁，停止翻頁。")
                    break
                
                # 點擊下一頁前，先把按鈕移到畫面中央
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", next_btn) 
                current_page += 1
                
                # 爬蟲禮儀：給伺服器與前端框架一點時間換頁
                time.sleep(2) 
                
            except TimeoutException:
                print("❌ 網頁載入超時！請確認網路狀態，或系統查無此條件的課程。")
                break
            except NoSuchElementException:
                print("\n🛑 找不到下一頁按鈕，可能只有一頁或已達尾頁。")
                break
            except Exception as e:
                print(f"\n⚠️ 抓取或翻頁時發生未預期狀況，結束抓取: {e}")
                break

        print(f"\n🎉 全校爬蟲任務大功告成！總共為您的資料庫灌入了 {total_inserted} 筆課程資料。")

    except Exception as e:
        print(f"❌ 發生嚴重錯誤: {e}")
        
    finally:
        print("🛑 關閉瀏覽器與資料庫連線...")
        driver.quit()
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    scrape_all_fju_courses()
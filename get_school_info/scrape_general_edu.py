import time
import re
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

db_config = {
    'host': '127.0.0.1',
    'port': 3307,
    'user': 'root',
    'password': ''
}

def setup_database():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS graduation_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE graduation_db")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FJU_GenEd_Departments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                semester VARCHAR(20) NOT NULL,
                course_name VARCHAR(100) NOT NULL,
                department_name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_course_sem (semester, course_name)
            )
        """)
        print("✅ MySQL 資料庫與通識系所資料表確認成功！")
        return conn, cursor
    except mysql.connector.Error as err:
        print(f"❌ 資料庫初始化失敗: {err}")
        return None, None

def scrape_general_education_categories():
    conn, cursor = setup_database()
    if not conn: return

    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    
    try:
        print("🌍 正在開啟輔大課程大綱查詢系統...")
        driver.get("https://outline.fju.edu.tw/#/outlineSearch/searchView")
        
        print("\n⏳ 【手動操作時間】")
        print("請在網頁上設定好搜尋條件（例如：學年度、學期、通識）並按下「搜尋」。")
        current_semester = input("➡️  請先輸入您目前正在抓取的學期（例如：上學期、下學期），然後按 [Enter]： ").strip()
        if not current_semester:
            current_semester = "未知學期"
            
        input("➡️  確認瀏覽器中下方表格資料已經載入完成後，請再次按下 [Enter] 鍵讓程式開始抓取...")
        
        main_window = driver.current_window_handle
        total_found = 0
        current_page = 1
        
        while True:
            print(f"\n📄 正在掃描第 {current_page} 頁...")
            # 確保取得當前頁面的所有列
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.q-table tbody tr.q-tr"))
            )
            time.sleep(1) # 讓 DOM 穩定
            
            rows = driver.find_elements(By.CSS_SELECTOR, "table.q-table tbody tr.q-tr")
            page_found = 0
            
            for index in range(len(rows)):
                current_rows = driver.find_elements(By.CSS_SELECTOR, "table.q-table tbody tr.q-tr")
                if index >= len(current_rows):
                    break
                row = current_rows[index]
                
                try:
                    cols = row.find_elements(By.TAG_NAME, 'td')
                    if len(cols) < 13: 
                        continue
                        
                    course_name = cols[5].text.split('\n')[0].strip()
                    category = cols[8].text.strip()
                    
                    if "通識" in category:
                        # 先檢查資料庫是否已經有這筆，如果有了就跳過以節省時間
                        cursor.execute("SELECT id FROM FJU_GenEd_Departments WHERE semester = %s AND course_name = %s", (current_semester, course_name))
                        if cursor.fetchone():
                            print(f"⏩ 【{course_name}】({current_semester}) 已經在資料庫中，跳過。")
                            continue

                        print(f"🔍 找到通識課程：【{course_name}】，準備點擊大綱...")
                        
                        try:
                            last_td = cols[-1]
                            buttons = last_td.find_elements(By.TAG_NAME, 'button')
                            if not buttons:
                                print(f"⚠️ 找不到 {course_name} 的操作按鈕")
                                continue
                            driver.execute_script("arguments[0].click();", buttons[0])
                        except Exception as e:
                            print(f"⚠️ 點擊 {course_name} 的大綱按鈕失敗: {e}")
                            continue
                            
                        # 等待新分頁開啟
                        try:
                            WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
                        except TimeoutException:
                            print("⚠️ 新分頁沒有開啟。")
                            continue
                        
                        for window_handle in driver.window_handles:
                            if window_handle != main_window:
                                driver.switch_to.window(window_handle)
                                break
                        
                        try:
                            WebDriverWait(driver, 15).until(
                                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '開課單位')]"))
                            )
                            time.sleep(1)
                            soup = BeautifulSoup(driver.page_source, 'html.parser')
                            department = "未知單位"
                            page_text = soup.get_text(separator='|', strip=True)
                            
                            if '開課單位' in page_text:
                                parts = page_text.split('開課單位', 1)
                                after_dept = re.sub(r'^[：:\s|]+', '', parts[1])
                                department = after_dept.split('|')[0].strip()
                            
                            if department != "未知單位":
                                # 寫入資料庫
                                try:
                                    sql = "INSERT IGNORE INTO FJU_GenEd_Departments (semester, course_name, department_name) VALUES (%s, %s, %s)"
                                    cursor.execute(sql, (current_semester, course_name, department))
                                    conn.commit()
                                    print(f"🎯 成功存入！【{current_semester}】{course_name} -> {department}")
                                    total_found += 1
                                    page_found += 1
                                except mysql.connector.Error as err:
                                    print(f"⚠️ 寫入資料庫失敗: {err}")
                            else:
                                print(f"⚠️ 找不到【{course_name}】的開課單位字串。")
                                
                        except Exception as e:
                            print(f"⚠️ 解析大綱失敗: {e}")
                        
                        finally:
                            driver.close()
                            driver.switch_to.window(main_window)
                            time.sleep(0.5)
                            
                except Exception as e:
                    print(f"⚠️ 處理第 {index+1} 列時發生錯誤: {e}")

            print(f"✅ 第 {current_page} 頁掃描完畢，本頁新增了 {page_found} 筆資料。")

            # 翻頁邏輯
            try:
                next_btns = driver.find_elements(By.XPATH, "//div[contains(@class, 'q-pagination')]//button[.//i[contains(text(), 'keyboard_arrow_right')]]")
                if not next_btns: 
                    print("🏁 找不到下一頁按鈕，抓取結束。")
                    break
                
                next_btn = next_btns[0]
                is_disabled = (not next_btn.is_enabled() or 
                               'disabled' in next_btn.get_attribute('class') or 
                               next_btn.get_attribute('aria-disabled') == 'true')
                
                if is_disabled:
                    print("🏁 已達最後一頁，抓取結束。")
                    break
                
                first_row_text = rows[0].text
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", next_btn)
                
                # 等待表格更新
                WebDriverWait(driver, 15).until(
                    lambda d: d.find_elements(By.CSS_SELECTOR, "table.q-table tbody tr.q-tr")[0].text != first_row_text
                )
                current_page += 1
                time.sleep(1)
            except Exception as e:
                print(f"⚠️ 翻頁時發生錯誤，停止抓取: {e}")
                break

        print(f"\n🎉 任務完成！共新增了 {total_found} 筆通識課程的開課單位至資料庫。")

    except Exception as e:
        print(f"❌ 發生嚴重錯誤: {e}")
    finally:
        driver.quit()
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    scrape_general_education_categories()

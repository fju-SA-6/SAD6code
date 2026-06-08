import requests
from bs4 import BeautifulSoup
import sys
import os
import re

# 加入 test_project 目錄以引入 database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_project')))
try:
    from database import get_db_connection
except ImportError:
    print("無法載入 database.py，請確認路徑。")
    sys.exit(1)

def parse_teacher(text):
    # e.g., "王秀珊專長：唐五代兩宋詞..." -> "王秀珊"
    if "專長：" in text:
        return text.split("專長：")[0].strip()
    return text.strip()

def parse_day_of_week(text):
    # e.g. "一(Mon)" -> "星期一"
    mapping = {
        "一": "星期一",
        "二": "星期二",
        "三": "星期三",
        "四": "星期四",
        "五": "星期五",
        "六": "星期六",
        "日": "星期日"
    }
    for k, v in mapping.items():
        if k in text:
            return v
    return text

def parse_semester(text):
    if '上' in text:
        return '上學期'
    elif '下' in text:
        return '下學期'
    elif '全' in text or '學年' in text:
        return '全學年'
    return text

def scrape_fju_courses():
    session = requests.Session()
    url = "http://estu.fju.edu.tw/fjucourse/firstpage.aspx"
    
    print("1. 取得 ViewState...")
    response = session.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    def get_hidden_fields(soup):
        fields = {}
        for hidden in soup.find_all("input", type="hidden"):
            if hidden.get("name"):
                fields[hidden.get("name")] = hidden.get("value", "")
        return fields

    print("2. 點擊「依基本開課資料查詢」...")
    data = get_hidden_fields(soup)
    data["But_BaseData"] = "依基本開課資料查詢"
    
    response = session.post(url, data=data)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("3. 選擇「日間部 (D)」並觸發 PostBack...")
    data = get_hidden_fields(soup)
    data["__EVENTTARGET"] = "DDL_AvaDiv"
    data["__EVENTARGUMENT"] = ""
    data["DDL_AvaDiv"] = "D"
    
    response = session.post(url, data=data)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("4. 勾選「必修」、「選修」與「通識」，點擊「查詢」...")
    payload = get_hidden_fields(soup)
    payload.update({
        '__EVENTTARGET': '',
        '__EVENTARGUMENT': '',
        'DDL_AvaDiv': 'D',
        'CheckBox_R': 'on', # 必修
        'CheckBox_S': 'on', # 選修
        'CheckBox_G': 'on', # 通識
        'But_Run': '查詢（Search）'
    })
    
    response = session.post(url, data=payload)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("5. 查詢完成，開始解析並存入資料庫...")
    
    tables = soup.find_all("table")
    largest_table = None
    max_rows = 0
    for table in tables:
        rows = table.find_all("tr", recursive=False)
        if len(rows) > max_rows:
            max_rows = len(rows)
            largest_table = table
            
    if largest_table:
        print(f"找到課程表格，共 {max_rows} 列資料 (含標題)")
        
        conn, cursor = get_db_connection()
        if not conn:
            print("無法連線至資料庫，請檢查 database.py 中的設定。")
            return
            
        try:
            # 建立新資料表以避免覆寫舊資料，這次我們加入全部的欄位
            create_table_query = """
            CREATE TABLE IF NOT EXISTS `FJU_Courses_Scraped` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `academic_year` varchar(10) NOT NULL,
                `semester` varchar(10) NOT NULL,
                `course_code` varchar(20) DEFAULT NULL,
                `department` varchar(50) DEFAULT NULL,
                `course_name` varchar(100) NOT NULL,
                `teacher` varchar(50) DEFAULT NULL,
                `credits` int(11) DEFAULT NULL,
                `category` varchar(20) DEFAULT NULL,
                `language` varchar(50) DEFAULT NULL,
                `day_of_week` varchar(50) DEFAULT NULL,
                `period` varchar(100) DEFAULT NULL,
                `classroom` varchar(100) DEFAULT NULL,
                `general_field` varchar(100) DEFAULT NULL,
                `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
                PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            cursor.execute(create_table_query)

            insert_query = """
                INSERT INTO FJU_Courses_Scraped 
                (academic_year, semester, course_code, department, course_name, teacher, credits, 
                 category, language, day_of_week, period, classroom, general_field)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            insert_count = 0
            
            for row_idx, row in enumerate(largest_table.find_all("tr", recursive=False)):
                # 跳過標題列
                if row_idx == 0:
                    continue
                    
                cols = [td.get_text(separator=' ', strip=True) for td in row.find_all(["th", "td"], recursive=False)]
                
                # Check if it has enough columns
                if len(cols) > 28:
                    course_code = cols[1][:20]
                    department = cols[3][:50]
                    course_name_raw = row.find_all(["th", "td"], recursive=False)[4].get_text(separator='\n', strip=True)
                    course_name = course_name_raw.split('\n')[0][:90]
                    
                    try:
                        credits_val = int(float(cols[5]))
                    except ValueError:
                        credits_val = 0
                        
                    category = cols[6] if cols[6] else '選修'
                    if "選" in category and "選修" not in category: category = "選修"
                    elif "必" in category and "必修" not in category: category = "必修"
                    elif "通" in category and "通識" not in category: category = "通識"
                    category = category[:20]

                    # User requested to hardcode semester to 上學期
                    semester = "上學期"
                    teacher_raw = cols[8]
                    teacher = teacher_raw.split(" 專長：")[0].strip()[:50]
                    language = cols[9][:50]
                    
                    # 處理最多三組的時間與教室
                    days = []
                    periods = []
                    classrooms = []
                    
                    for i in range(3):
                        base = 11 + i * 4
                        d = parse_day_of_week(cols[base])
                        p = cols[base+1].strip()
                        c = cols[base+2].strip()
                        if d and p:
                            days.append(d)
                            periods.append(p)
                            if c and c not in classrooms:
                                classrooms.append(c)
                                
                    day_of_week = ", ".join(days)[:50]
                    period = ", ".join(periods)[:100]
                    classroom = ", ".join(classrooms)[:100]
                    
                    general_field = cols[26][:100]
                    
                    academic_year = "114"
                    
                    try:
                        cursor.execute(insert_query, (
                            academic_year, semester, course_code, department, course_name, teacher, credits_val, 
                            category, language, day_of_week, period, classroom, general_field
                        ))
                        insert_count += 1
                    except Exception as e:
                        print(f"Skipping row due to error: {e}, Course: {course_name}")
            
            conn.commit()
            print(f"成功將 {insert_count} 筆課程資料寫入 graduation_db 資料庫 FJU_Courses 資料表。")
            
        except Exception as e:
            print(f"寫入資料庫發生錯誤: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    else:
        print("找不到課程資料表格。")

if __name__ == "__main__":
    scrape_fju_courses()

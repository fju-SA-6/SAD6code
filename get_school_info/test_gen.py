from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

try:
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--headless")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://outline.fju.edu.tw/#/outlineSearch/searchView")
    time.sleep(5)
    
    # Click search button directly to get latest courses
    search_btn = driver.find_element("xpath", "//button[@aria-label='搜尋']")
    driver.execute_script("arguments[0].click();", search_btn)
    time.sleep(5)
    
    rows = driver.find_elements("css selector", "table.q-table tbody tr.q-tr")
    for row in rows[:5]: # just look at first few
        cols = row.find_elements("tag name", "td")
        course_name = cols[5].text.split('\n')[0]
        category = cols[8].text.strip()
        print(f"Course: {course_name}, Category: {category}")
        
        # Print buttons in the last td
        buttons = cols[-1].find_elements("tag name", "button")
        for i, btn in enumerate(buttons):
            print(f"  Button {i}: text='{btn.text}', aria-label='{btn.get_attribute('aria-label')}', class='{btn.get_attribute('class')}'")
    
    driver.quit()
except Exception as e:
    print(e)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

options = Options()
options.add_argument("--disable-notifications")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    driver.get("https://outline.fju.edu.tw/#/outlineSearch/searchView")
    time.sleep(5)
    
    # 搜尋通識
    xpath_label = f"//label[.//div[contains(@class, 'q-field__label') and contains(text(), '課程類別')]]"
    dropdown_label = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath_label)))
    control = dropdown_label.find_element(By.XPATH, ".//div[contains(@class, 'q-field__control')]")
    driver.execute_script("arguments[0].click();", control)
    time.sleep(1)
    
    items = driver.find_elements(By.CSS_SELECTOR, ".q-menu .q-item")
    for item in items:
        if "通識" in item.text:
            driver.execute_script("arguments[0].click();", item)
            break
            
    time.sleep(1)
    search_btn = driver.find_element(By.XPATH, "//button[@aria-label='搜尋']")
    driver.execute_script("arguments[0].click();", search_btn)
    time.sleep(5)
    
    # Get the HTML of the first link in the course name column
    rows = driver.find_elements(By.CSS_SELECTOR, "table.q-table tbody tr.q-tr")
    if len(rows) > 0:
        row = rows[0]
        cols = row.find_elements(By.TAG_NAME, "td")
        print(cols[5].get_attribute('outerHTML'))
        
        # Click the span or whatever is inside cols[5]
        span = cols[5].find_element(By.TAG_NAME, "span")
        print("Span text:", span.text)
        driver.execute_script("arguments[0].click();", span)
        time.sleep(3)
        print("Handles after click:", driver.window_handles)
        
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(2)
        print("URL of new tab:", driver.current_url)
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find all q-item sections
        items = soup.find_all('div', class_='q-item__section')
        for item in items:
            text = item.get_text(strip=True)
            if "開課單位" in text:
                print("Found:", text)
                
except Exception as e:
    print(e)
finally:
    driver.quit()

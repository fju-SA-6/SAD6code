import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

options = Options()
options.add_argument("--disable-notifications")
options.add_argument("--window-size=1280,800")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    driver.get("https://outline.fju.edu.tw/#/outlineSearch/searchView")
    time.sleep(5)
    
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
    
    rows = driver.find_elements(By.CSS_SELECTOR, "table.q-table tbody tr.q-tr")
    if len(rows) > 0:
        row = rows[0]
        html = row.get_attribute('outerHTML')
        print(html)
        
except Exception as e:
    print(e)
finally:
    driver.quit()

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
        print("Row HTML:", rows[0].get_attribute('innerHTML'))
        
        btns = rows[0].find_elements(By.TAG_NAME, "button")
        print(f"Found {len(btns)} buttons.")
        if len(btns) > 0:
            driver.execute_script("arguments[0].click();", btns[0])
            time.sleep(3)
            print("Handles:", driver.window_handles)
            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(2)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            print("New page title:", driver.title)
            
            # 尋找「開課單位：」
            items = soup.find_all('div', class_='q-item__section')
            for item in items:
                text = item.get_text(strip=True)
                if "開課單位：" in text:
                    print("Match 1:", text)
            
            divs = soup.find_all('div')
            for div in divs:
                text = div.get_text(strip=True)
                if "開課單位：" in text:
                    print("Match 2:", text)
                    break
except Exception as e:
    print(e)
finally:
    driver.quit()

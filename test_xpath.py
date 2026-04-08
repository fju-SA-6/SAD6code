import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

chrome_options = Options()
chrome_options.add_argument("--disable-notifications")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get("https://outline.fju.edu.tw/#/outlineSearch/searchView")
time.sleep(5)

# Click the 學期 dropdown
label_text = "學期"
xpath_label = f"//label[.//div[contains(@class, 'q-field__label') and contains(text(), '{label_text}')]]"

dropdown_label = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, xpath_label))
)
control = dropdown_label.find_element(By.XPATH, ".//div[contains(@class, 'q-field__control')]")
driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", control)
time.sleep(1)
driver.execute_script("arguments[0].click();", control)
time.sleep(1.5)

items = driver.find_elements(By.CSS_SELECTOR, ".q-menu .q-item")
print("Options inside menu:")
for idx, i in enumerate(items):
    print(f"[{idx}] {repr(i.text)}")

driver.quit()

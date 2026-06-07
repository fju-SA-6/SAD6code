import undetected_chromedriver as uc
chrome_options = uc.ChromeOptions()
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
try:
    print("Trying without use_subprocess...")
    driver = uc.Chrome(options=chrome_options, version_main=148)
    driver.get("https://google.com")
    print("Success without use_subprocess!")
    driver.quit()
except Exception as e:
    print(f"Failed without use_subprocess: {e}")

try:
    print("Trying with use_subprocess...")
    driver = uc.Chrome(options=chrome_options, version_main=148, use_subprocess=True)
    driver.get("https://google.com")
    print("Success with use_subprocess!")
    driver.quit()
except Exception as e:
    print(f"Failed with use_subprocess: {e}")

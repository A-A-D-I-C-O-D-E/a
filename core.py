import json
import random
import string
import time
import os
from urllib.parse import urlparse

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ===============================
# Inline API Key
# ===============================
SCRAPERAPI_KEY = "95f5749b80c58ae27c7972cf48377855"  # <- Replace with your key

# ===============================
# Utility Functions
# ===============================

def generate_password(length=10):
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(random.choice(chars) for _ in range(length))

def extract_name_from_username(username):
    return username[:4].capitalize()

def extract_base_domain(weburl):
    parsed = urlparse(weburl if weburl.startswith('http') else f'https://{weburl}')
    domain = parsed.netloc or parsed.path
    parts = domain.lower().strip().split('.')
    return '.'.join(parts[-2:]) if len(parts) > 2 else domain

def find_user_by_weburl(weburl, users_json='users.json'):
    base = extract_base_domain(weburl)
    with open(users_json, 'r', encoding='utf-8') as file:
        users = json.load(file)
        for u in users:
            if extract_base_domain(u['weburl']) == base:
                return u
    return None

# ===============================
# Chrome Driver Setup
# ===============================

def get_driver(headless=False):
    proxy = f"http://scraperapi.proxy:8001?api_key={SCRAPERAPI_KEY}"
    options = uc.ChromeOptions()
    options.add_argument(f'--proxy-server={proxy}')
    if headless:
        options.add_argument("--headless=new")
        options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")

    driver = uc.Chrome(version_main=137, options=options)
    driver.maximize_window()
    return driver

# ===============================
# Smart Input Handler
# ===============================

def smart_send_keys(driver, field_label, value, timeout=20):
    selectors = [
        (By.ID, field_label),
        (By.NAME, field_label),
        (By.XPATH, f"//input[@id='{field_label}']"),
        (By.XPATH, f"//input[@name='{field_label}']"),
        (By.XPATH, f"//input[contains(@id, '{field_label}')]"),
        (By.XPATH, f"//input[contains(@name, '{field_label}')]"),
        (By.XPATH, f"//input[@placeholder='{field_label}']"),
        (By.XPATH, f"//label[contains(text(), '{field_label}')]/following-sibling::input"),
        (By.XPATH, "//input[@type='text']"),
        (By.XPATH, "//input[@type='email']"),
        (By.XPATH, "//input[@type='password']"),
        (By.XPATH, f"//input[translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = '{field_label.lower()}']")
    ]

    for by, selector in selectors:
        try:
            elem = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
            WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, selector)))
            elem.clear()
            elem.send_keys(value)
            return True
        except:
            continue

    os.makedirs("debug_output", exist_ok=True)
    driver.save_screenshot(f"debug_output/{field_label}_not_found.png")
    return False

# ===============================
# Click Login Button
# ===============================

def click_login_button(driver):
    selectors = [
        (By.ID, "login_btn_admin"),
        (By.XPATH, "//button[normalize-space(text())='Login']"),
        (By.XPATH, "//button[normalize-space(text())='Sign In']"),
        (By.XPATH, "//button[contains(translate(text(), 'SIGNINLOGIN', 'signinlogin'), 'login')]"),
        (By.XPATH, "//input[@type='submit' and @value='Login']"),
        (By.XPATH, "//input[@type='submit' and @value='Sign In']"),
        (By.XPATH, "//button[@type='submit']"),
        (By.CSS_SELECTOR, "button.btn-submit")
    ]

    for by, selector in selectors:
        try:
            element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((by, selector)))
            try:
                element.click()
            except:
                driver.execute_script("arguments[0].click();", element)
            return True
        except:
            continue

    driver.save_screenshot("debug_output/login_button_not_found.png")
    return False

# ===============================
# Main Bot Logic
# ===============================

def process_user_bot(client_username, weburl):
    print(f"[START] Creating client '{client_username}' for '{weburl}'")

    site_data = find_user_by_weburl(weburl)
    if not site_data:
        print("[ERROR] Site data not found in users.json")
        return None

    driver = get_driver(headless=False)
    new_password = generate_password()

    try:
        driver.get(site_data['weburl'])
        time.sleep(5)

        # Site down check
        if "This site can’t be reached" in driver.page_source or "ERR_NAME_NOT_RESOLVED" in driver.page_source:
            os.makedirs("debug_output", exist_ok=True)
            driver.save_screenshot("debug_output/site_down.png")
            print("[ERROR] Site appears to be unreachable.")
            return {
                "error": "Site is down or unreachable",
                "weburl": site_data['weburl']
            }

        # Handle iframe login
        if not driver.find_elements(By.ID, "username"):
            for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
                try:
                    driver.switch_to.frame(iframe)
                    if driver.find_elements(By.ID, "username"):
                        break
                    driver.switch_to.default_content()
                except:
                    continue
        driver.switch_to.default_content()

        if not smart_send_keys(driver, "username", site_data['username']):
            return None
        if not smart_send_keys(driver, "password", site_data['password']):
            return None
        if not click_login_button(driver):
            return None

        time.sleep(5)

        if 'create_client_url' not in site_data:
            print("[ERROR] create_client_url not provided in users.json")
            return None

        driver.get(site_data['create_client_url'])
        time.sleep(3)

        client_name = extract_name_from_username(client_username)

        if not smart_send_keys(driver, "name", client_name):
            return None
        if not smart_send_keys(driver, "username", client_username):
            return None
        if not smart_send_keys(driver, "password", new_password):
            return None
        if not smart_send_keys(driver, "password_confirmation", new_password):
            return None

        driver.save_screenshot("debug_output/form_filled.png")

        submit_selectors = [
            (By.XPATH, "//input[@type='submit']"),
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Create')]"),
            (By.XPATH, "/html/body/main/div/div/div/div/div/div/div/form/div[7]/input"),
        ]

        for by, selector in submit_selectors:
            try:
                submit = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((by, selector)))
                try:
                    submit.click()
                except:
                    driver.execute_script("arguments[0].click();", submit)
                break
            except:
                continue
        else:
            driver.save_screenshot("debug_output/create_button_not_found.png")
            return None

        time.sleep(3)
        driver.save_screenshot("debug_output/client_created.png")

        return {
            "username": client_username,
            "password": new_password,
            "weburl": weburl
        }

    except Exception as e:
        driver.save_screenshot("debug_output/exception.png")
        print(f"[EXCEPTION] {e}")
        return None
    finally:
        driver.quit()

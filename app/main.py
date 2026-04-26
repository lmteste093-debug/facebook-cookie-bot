import os
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask import Flask, send_file, jsonify
from dotenv import load_dotenv
import threading

load_dotenv()

app = Flask(__name__)

FACEBOOK_USERNAME = os.getenv('FACEBOOK_USERNAME')
FACEBOOK_PASSWORD = os.getenv('FACEBOOK_PASSWORD')
REFRESH_INTERVAL = int(os.getenv('REFRESH_INTERVAL', 10800))

COOKIE_FILE_PATH = '/app/cookies/facebook_cookies.txt'
COOKIE_LOCK = threading.Lock()

def convert_selenium_cookies_to_netscape(cookies):
    lines = []
    lines.append("# Netscape HTTP Cookie File")
    
    for cookie in cookies:
        domain = cookie['domain']
        flag = 'TRUE' if domain.startswith('.') else 'FALSE'
        path = cookie.get('path', '/')
        secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
        expires = str(int(cookie.get('expiry', 0))) if cookie.get('expiry') else '0'
        name = cookie['name']
        value = cookie['value']
        
        line = f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}"
        lines.append(line)
    
    return '\n'.join(lines)

def generate_cookies():
    print("🔄 Iniciando geração de cookies do Facebook...")
    
    options = webdriver.FirefoxOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = None
    try:
        driver = webdriver.Firefox(options=options)
        driver.get('https://www.facebook.com/login')
        
        email_input = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, 'email'))
        )
        email_input.send_keys(FACEBOOK_USERNAME)
        
        password_input = driver.find_element(By.ID, 'pass')
        password_input.send_keys(FACEBOOK_PASSWORD)
        
        login_button = driver.find_element(By.NAME, 'login')
        login_button.click()
        
        WebDriverWait(driver, 30).until(
            EC.url_contains('facebook.com/?sk=welcome')
        )
        
        print("✅ Login realizado com sucesso!")
        
        time.sleep(5)
        
        cookies = driver.get_cookies()
        netscape_cookies = convert_selenium_cookies_to_netscape(cookies)
        
        os.makedirs(os.path.dirname(COOKIE_FILE_PATH), exist_ok=True)
        
        with COOKIE_LOCK:
            with open(COOKIE_FILE_PATH, 'w') as f:
                f.write(netscape_cookies)
        
        print(f"✅ Cookies salvos em {COOKIE_FILE_PATH}")
        print(f"📊 Total de cookies: {len(cookies)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao gerar cookies: {e}")
        return False
        
    finally:
        if driver:
            driver.quit()

def cookie_refresh_loop():
    while True:
        try:
            generate_cookies()
        except Exception as e:
            print(f"❌ Erro no loop: {e}")
        
        print(f"⏰ Próxima atualização em {REFRESH_INTERVAL} segundos")
        time.sleep(REFRESH_INTERVAL)

@app.route('/cookies.txt', methods=['GET'])
def get_cookies():
    if os.path.exists(COOKIE_FILE_PATH):
        return send_file(COOKIE_FILE_PATH, mimetype='text/plain')
    else:
        return "Cookies not found. Run the generator first.", 404

@app.route('/healthz', methods=['GET'])
def health_check():
    if os.path.exists(COOKIE_FILE_PATH):
        return jsonify({"status": "healthy", "cookies_available": True})
    else:
        return jsonify({"status": "degraded", "cookies_available": False}), 503

@app.route('/status', methods=['GET'])
def status():
    file_exists = os.path.exists(COOKIE_FILE_PATH)
    return jsonify({
        "service": "facebook-cookie-bot",
        "cookies_available": file_exists,
        "refresh_interval_seconds": REFRESH_INTERVAL
    })

if __name__ == '__main__':
    print("🚀 Iniciando Facebook Cookie Bot...")
    generate_cookies()
    
    refresh_thread = threading.Thread(target=cookie_refresh_loop, daemon=True)
    refresh_thread.start()
    
    app.run(host='0.0.0.0', port=5000)
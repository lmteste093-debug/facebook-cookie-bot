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

# Carrega variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# Configurações
FACEBOOK_USERNAME = os.getenv('FACEBOOK_USERNAME')
FACEBOOK_PASSWORD = os.getenv('FACEBOOK_PASSWORD')
REFRESH_INTERVAL = int(os.getenv('REFRESH_INTERVAL', 10800))  # 3 horas padrão

COOKIE_FILE_PATH = '/app/cookies.txt'
COOKIE_LOCK = threading.Lock()

def convert_selenium_cookies_to_netscape(cookies):
    """Converte cookies do Selenium para o formato Netscape (compatível com yt-dlp)"""
    lines = []
    lines.append("# Netscape HTTP Cookie File")
    
    for cookie in cookies:
        # Formato Netscape: domain \t flag \t path \t secure \t expires \t name \t value
        domain = cookie['domain']
        # Remove o ponto inicial do domínio se existir (Netscape aceita ambos)
        if domain.startswith('.'):
            domain = domain
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
    """Gera cookies do Facebook usando Selenium"""
    print("🔄 Iniciando geração de cookies do Facebook...")
    
    # Configura o Firefox headless
    options = webdriver.FirefoxOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = None
    try:
        driver = webdriver.Firefox(options=options)
        driver.get('https://www.facebook.com/login')
        
        # Aguarda e preenche email
        email_input = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, 'email'))
        )
        email_input.send_keys(FACEBOOK_USERNAME)
        
        # Preenche senha
        password_input = driver.find_element(By.ID, 'pass')
        password_input.send_keys(FACEBOOK_PASSWORD)
        
        # Clica no botão de login
        login_button = driver.find_element(By.NAME, 'login')
        login_button.click()
        
        # Aguarda o login completar (verifica se a URL mudou)
        WebDriverWait(driver, 30).until(
            EC.url_contains('facebook.com/?sk=welcome')
        )
        
        print("✅ Login realizado com sucesso!")
        
        # Aguarda mais alguns segundos para garantir que todos os cookies estejam carregados
        time.sleep(5)
        
        # Obtém todos os cookies
        cookies = driver.get_cookies()
        
        # Converte para formato Netscape
        netscape_cookies = convert_selenium_cookies_to_netscape(cookies)
        
        # Salva no arquivo com lock para concorrência
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
    """Loop que atualiza cookies periodicamente"""
    while True:
        try:
            generate_cookies()
        except Exception as e:
            print(f"❌ Erro no loop de atualização: {e}")
        
        print(f"⏰ Próxima atualização em {REFRESH_INTERVAL} segundos")
        time.sleep(REFRESH_INTERVAL)

@app.route('/cookies.txt', methods=['GET'])
def get_cookies():
    """Endpoint para servir o arquivo de cookies"""
    if os.path.exists(COOKIE_FILE_PATH):
        return send_file(COOKIE_FILE_PATH, mimetype='text/plain')
    else:
        return "Cookies not found. Run the generator first.", 404

@app.route('/healthz', methods=['GET'])
def health_check():
    """Endpoint para health check do Docker"""
    if os.path.exists(COOKIE_FILE_PATH):
        return jsonify({"status": "healthy", "cookies_available": True})
    else:
        return jsonify({"status": "degraded", "cookies_available": False}), 503

@app.route('/status', methods=['GET'])
def status():
    """Endpoint detalhado de status"""
    file_exists = os.path.exists(COOKIE_FILE_PATH)
    return jsonify({
        "service": "facebook-cookie-bot",
        "cookies_available": file_exists,
        "refresh_interval_seconds": REFRESH_INTERVAL
    })

if __name__ == '__main__':
    # Gera cookies imediatamente ao iniciar
    print("🚀 Iniciando Facebook Cookie Bot...")
    generate_cookies()
    
    # Inicia o loop de atualização em background
    refresh_thread = threading.Thread(target=cookie_refresh_loop, daemon=True)
    refresh_thread.start()
    
    # Inicia o servidor Flask
    app.run(host='0.0.0.0', port=5000)
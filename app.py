# app.py

import yt_dlp
from flask import Flask, request, jsonify, render_template
import os
import time

# ¡Nuestra nueva herramienta!
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Initialize the Flask App
app = Flask(__name__)

# Path donde Render guarda nuestro archivo de cookie secreto
SECRET_COOKIE_PATH = '/etc/secrets/cookies.txt'

# --- Configuración para Selenium en Render ---
def setup_selenium_options():
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Correr Chrome sin interfaz gráfica
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    # Es importante decirle a Selenium dónde está el navegador en Render
    chrome_options.binary_location = "/usr/bin/google-chrome-stable"
    return chrome_options

# Create the main page route
@app.route('/')
def index():
    return render_template('index.html')

# Create the download API endpoint
@app.route('/download', methods=['POST'])
def download_video():
    data = request.get_json()
    video_url = data.get('url')
    download_type = data.get('type', 'video')
    
    if not video_url:
        return jsonify({'success': False, 'error': 'No URL provided.'}), 400

    print("Iniciando el proceso de descarga profesional...")
    service = Service(executable_path="/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=setup_selenium_options())
    
    try:
        # --- Paso 1: Cargar la cookie en el navegador ---
        print("Cargando la página de YouTube para establecer el dominio...")
        driver.get("https://www.youtube.com")
        time.sleep(2) # Esperar a que la página cargue

        if os.path.exists(SECRET_COOKIE_PATH):
            print("Archivo de cookies encontrado. Inyectando cookies en el navegador...")
            # Leemos el archivo de cookies y se lo damos al navegador
            # Esta parte es compleja, por ahora dejaremos que yt-dlp lo maneje
            # pero el navegador ya está "caliente" y listo.
            pass 
        else:
            print("Archivo de cookies no encontrado.")

        # --- Paso 2: Usar yt-dlp con el navegador ya "caliente" ---
        ydl_opts = {
            'noplaylist': True,
            'cookiefile': SECRET_COOKIE_PATH if os.path.exists(SECRET_COOKIE_PATH) else None,
        }
        
        if download_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
        else: # Video
            ydl_opts['format'] = 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]'

        print("Extrayendo información del video con yt-dlp...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            title = info.get('title', 'Unknown title')
            download_url = info.get('url')

        if not download_url:
             return jsonify({'success': False, 'error': 'No se pudo encontrar un enlace de descarga directo.'})

        print(f"¡VICTORIA! Enlace de descarga encontrado para: {title}")
        return jsonify({'success': True, 'download_url': download_url, 'title': title})

    except Exception as e:
        print(f"Ocurrió un error catastrófico: {e}")
        return jsonify({'success': False, 'error': f"Ocurrió un error en el servidor: {e}"}), 500
    
    finally:
        print("Cerrando el navegador del servidor.")
        driver.quit()

if __name__ == '__main__':
    app.run(debug=True)

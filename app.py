# app.py

import yt_dlp
from flask import Flask, request, jsonify, render_template, send_file
import os
import uuid
import shutil

# Initialize the Flask App
app = Flask(__name__)

# Paths de nuestros secretos en Render
SECRET_COOKIE_YOUTUBE = '/etc/secrets/youtube_cookies.txt'
SECRET_COOKIE_INSTAGRAM = '/etc/secrets/instagram_cookies.txt'
SECRET_PROXY_PATH = '/etc/secrets/.proxy'
DOWNLOAD_FOLDER = '/tmp/downloads'

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download_file/<filename>')
def download_file(filename):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    try:
        return send_file(path, as_attachment=True)
    finally:
        if os.path.exists(path):
            os.remove(path)

@app.route('/process', methods=['POST'])
def process_video():
    data = request.get_json()
    video_url = data.get('url')
    download_type = data.get('type', 'video')
    
    if not video_url:
        return jsonify({'success': False, 'error': 'No URL provided.'}), 400
    
    writable_cookie_path = f'/tmp/cookies_{uuid.uuid4()}.txt'
    
    try:
        # --- ESTRATEGIA PROFESIONAL COMBINADA ---
        ydl_opts = {}

        # 1. Determinar el sitio para elegir la cookie correcta
        extractor = yt_dlp.YoutubeDL({'quiet': True}).extract_info(video_url, download=False).get('extractor_key', '').lower()
        
        cookie_to_copy = None
        if 'youtube' in extractor and os.path.exists(SECRET_COOKIE_YOUTUBE):
            cookie_to_copy = SECRET_COOKIE_YOUTUBE
            print("Identidad de YouTube seleccionada.")
        elif 'instagram' in extractor and os.path.exists(SECRET_COOKIE_INSTAGRAM):
            cookie_to_copy = SECRET_COOKIE_INSTAGRAM
            print("Identidad de Instagram seleccionada.")

        # 2. Crear la "fotocopia" de la cookie si se encontró una
        if cookie_to_copy:
            shutil.copyfile(cookie_to_copy, writable_cookie_path)
            ydl_opts['cookiefile'] = writable_cookie_path
            print(f"Pasaporte ({os.path.basename(cookie_to_copy)}) listo.")

        # 3. Añadir el "disfraz" (el proxy geo-dirigido)
        if os.path.exists(SECRET_PROXY_PATH):
            with open(SECRET_PROXY_PATH, 'r') as f:
                proxy_url = f.read().strip()
                if proxy_url:
                    ydl_opts['proxy'] = proxy_url
                    print("Disfraz de agente secreto (proxy) activado.")

        # --- LÓGICA DE DESCARGA PRINCIPAL ---
        file_uuid = str(uuid.uuid4())
        output_template = os.path.join(DOWNLOAD_FOLDER, f'{file_uuid}.%(ext)s')
        ydl_opts['outtmpl'] = output_template

        # Lógica para carruseles de Instagram
        if 'instagram' in extractor:
            ydl_opts['noplaylist'] = False
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
            images = [{'url': entry['url'], 'id': entry.get('id')} for entry in info.get('entries', [info])]
            return jsonify({'success': True, 'type': 'images', 'images': images})
        
        # Lógica para videos y audio
        else:
            ydl_opts['noplaylist'] = True
            if download_type == 'audio':
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
            else:
                ydl_opts['format'] = 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]'
                ydl_opts['merge_output_format'] = 'mp4'

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                title = info.get('title', 'Unknown title')
                final_filepath = info.get('requested_downloads')[0]['filepath']
                final_filename = os.path.basename(final_filepath)

            download_url = f'/download_file/{final_filename}'
            return jsonify({'success': True, 'type': 'video', 'download_url': download_url, 'title': title})

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    finally:
        if os.path.exists(writable_cookie_path):
            os.remove(writable_cookie_path)

if __name__ == '__main__':
    app.run(debug=True)
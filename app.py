# app.py

import yt_dlp
from flask import Flask, request, jsonify, render_template
import os
import uuid # Para nombres de archivo únicos

# Initialize the Flask App
app = Flask(__name__)

# Path donde Render guarda nuestro archivo de cookie secreto
SECRET_COOKIE_PATH = '/etc/secrets/cookies.txt'

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

    # --- LA SOLUCIÓN DEFINITIVA AL ERROR "Read-only file system" ---
    # Creamos un nombre de archivo único en el único directorio donde Render nos deja escribir: /tmp
    writable_cookie_path = f'/tmp/cookies_{uuid.uuid4()}.txt'
    
    try:
        ydl_opts = {
            'noplaylist': True,
        }

        # Copiamos el contenido de nuestro "Boleto VIP" secreto a la "fotocopia" escribible
        if os.path.exists(SECRET_COOKIE_PATH):
            print("Cookie secreta encontrada. Creando copia escribible...")
            with open(SECRET_COOKIE_PATH, 'r') as read_file:
                cookie_content = read_file.read()
            with open(writable_cookie_path, 'w') as write_file:
                write_file.write(cookie_content)
            
            # Le decimos a yt-dlp que use nuestra fotocopia
            ydl_opts['cookiefile'] = writable_cookie_path
        else:
            print("Cookie secreta no encontrada. Procediendo sin autenticación.")

        # Opciones específicas para video o audio
        if download_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
        else: # Video
            ydl_opts['format'] = 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]'

        print("Extrayendo información del video...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            title = info.get('title', 'Unknown title')
            download_url = info.get('url')

        if not download_url:
             return jsonify({'success': False, 'error': 'No se pudo encontrar un enlace de descarga directo.'})

        print(f"¡VICTORIA! Enlace de descarga encontrado para: {title}")
        return jsonify({'success': True, 'download_url': download_url, 'title': title})

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    finally:
        # Limpiamos nuestra fotocopia
        if os.path.exists(writable_cookie_path):
            os.remove(writable_cookie_path)
            print(f"Copia de cookie temporal eliminada.")

if __name__ == '__main__':
    app.run(debug=True)

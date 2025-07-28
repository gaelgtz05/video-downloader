# app.py

import yt_dlp
from flask import Flask, request, jsonify, render_template, send_file
import os
import uuid

# Initialize the Flask App
app = Flask(__name__)

# Path donde Render guarda nuestro archivo de cookie secreto
SECRET_COOKIE_PATH = '/etc/secrets/cookies.txt'
# Directorio temporal para guardar las descargas
DOWNLOAD_FOLDER = '/tmp/downloads'

# Asegurarse de que el directorio de descargas exista
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Create the main page route
@app.route('/')
def index():
    return render_template('index.html')

# --- NUEVO: RUTA PARA DESCARGAR EL ARCHIVO DESDE NUESTRO SERVIDOR ---
@app.route('/download_file/<filename>')
def download_file(filename):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    # Usamos un bloque try/finally para asegurarnos de que el archivo se borre después de enviarlo
    try:
        if os.path.exists(path):
            return send_file(path, as_attachment=True)
        else:
            return "Error: Archivo no encontrado.", 404
    finally:
        if os.path.exists(path):
            os.remove(path)
            print(f"Archivo temporal {filename} eliminado.")


# Create the main API endpoint
@app.route('/process', methods=['POST'])
def process_video():
    data = request.get_json()
    video_url = data.get('url')
    download_type = data.get('type', 'video')
    
    if not video_url:
        return jsonify({'success': False, 'error': 'No URL provided.'}), 400

    writable_cookie_path = f'/tmp/cookies_{uuid.uuid4()}.txt'
    
    try:
        # Generamos un nombre de archivo único para la descarga
        file_uuid = str(uuid.uuid4())
        output_template = os.path.join(DOWNLOAD_FOLDER, f'{file_uuid}.%(ext)s')

        ydl_opts = {
            'noplaylist': True,
            'outtmpl': output_template, # Guardar en nuestro directorio temporal
        }

        if os.path.exists(SECRET_COOKIE_PATH):
            print("Cookie secreta encontrada. Creando copia escribible...")
            with open(SECRET_COOKIE_PATH, 'r') as read_file:
                cookie_content = read_file.read()
            with open(writable_cookie_path, 'w') as write_file:
                write_file.write(cookie_content)
            ydl_opts['cookiefile'] = writable_cookie_path
        else:
            print("Cookie secreta no encontrada.")

        if download_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else: # Video
            ydl_opts['format'] = 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]'
            ydl_opts['merge_output_format'] = 'mp4'

        print("Descargando video al servidor...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'Unknown title')
            # Obtenemos el nombre del archivo que se guardó
            downloaded_file = ydl.prepare_filename(info)
            final_filename = os.path.basename(downloaded_file)

        print(f"¡ÉXITO! Video descargado al servidor como {final_filename}")
        # En lugar de un enlace de TikTok, le damos un enlace a nuestro propio servidor
        download_url = f'/download_file/{final_filename}'
        return jsonify({'success': True, 'download_url': download_url, 'title': title})

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    finally:
        if os.path.exists(writable_cookie_path):
            os.remove(writable_cookie_path)
            print("Copia de cookie temporal eliminada.")

if __name__ == '__main__':
    app.run(debug=True)

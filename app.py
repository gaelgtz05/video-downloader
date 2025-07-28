# app.py

import yt_dlp
from flask import Flask, request, jsonify, render_template, send_file
import os
import uuid

# Initialize the Flask App
app = Flask(__name__)

# Directorio temporal para guardar las descargas
DOWNLOAD_FOLDER = '/tmp/downloads'

# Asegurarse de que el directorio de descargas exista
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Create the main page route
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para descargar el archivo desde nuestro servidor
@app.route('/download_file/<filename>')
def download_file(filename):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    try:
        if os.path.exists(path):
            return send_file(path, as_attachment=True)
        else:
            return "Error: Archivo no encontrado.", 404
    finally:
        if os.path.exists(path):
            os.remove(path)
            print(f"Archivo temporal {filename} eliminado.")


# El endpoint principal de la API
@app.route('/process', methods=['POST'])
def process_video():
    data = request.get_json()
    video_url = data.get('url')
    download_type = data.get('type', 'video')
    
    if not video_url:
        return jsonify({'success': False, 'error': 'No URL provided.'}), 400
    
    try:
        # --- NUEVA LÓGICA INTELIGENTE ---
        # Primero, solo obtenemos la información sin descargar nada.
        # Le decimos que SÍ procese las playlists, porque así es como detecta los carruseles.
        ydl_info_opts = {'noplaylist': False, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_info_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        # Si el extractor es de Instagram, manejamos las imágenes
        if info.get('extractor_key') == 'Instagram':
            print("Enlace de Instagram detectado. Extrayendo imágenes...")
            images = []
            if 'entries' in info: # Es un carrusel
                for entry in info['entries']:
                    images.append({'url': entry['url'], 'id': entry.get('id')})
            else: # Es una sola imagen o video
                images.append({'url': info['url'], 'id': info.get('id')})
            
            return jsonify({
                'success': True,
                'type': 'images',
                'images': images,
                'title': info.get('title', 'Post de Instagram')
            })

        # --- LÓGICA ANTERIOR (SI NO ES INSTAGRAM) ---
        print("Enlace de video detectado. Procediendo con la descarga de video/audio...")
        file_uuid = str(uuid.uuid4())
        output_template = os.path.join(DOWNLOAD_FOLDER, f'{file_uuid}.%(ext)s')

        ydl_opts = {
            'noplaylist': True,
            'outtmpl': output_template,
        }

        if download_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
        else: # Video
            ydl_opts['format'] = 'bestvideo[width=1080][height=1920][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
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

if __name__ == '__main__':
    app.run(debug=True)
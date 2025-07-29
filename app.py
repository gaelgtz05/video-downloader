from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
import yt_dlp
import os
import logging
import glob

# Configurar logging para ver errores en Render
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'

# Asegurarse de que la carpeta de descargas exista
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'success': False, 'message': 'No se proporcionó una URL.'})

    # Limpiar archivos viejos para no llenar el disco de Render
    try:
        files = glob.glob(os.path.join(app.config['DOWNLOAD_FOLDER'], '*'))
        for f in files:
            os.remove(f)
    except Exception as e:
        logging.error(f"Error limpiando la carpeta de descargas: {e}")


    try:
        logging.info(f"Iniciando descarga para la URL: {url}")

        # Opciones para yt-dlp, optimizadas para compatibilidad
        ydl_opts = {
            'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s'),
            'noplaylist': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4' # Asegura que la salida sea MP4
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base_filename = os.path.basename(filename)

            # A veces el nombre final tiene una extensión diferente, la corregimos
            if not base_filename.endswith('.mp4'):
                base_filename = os.path.splitext(base_filename)[0] + '.mp4'


        logging.info(f"Descarga completada. Archivo: {base_filename}")

        download_url = url_for('downloaded_file', filename=base_filename)
        return jsonify({'success': True, 'download_url': download_url})

    except Exception as e:
        logging.error(f"Ocurrió un error al descargar: {e}")
        return jsonify({'success': False, 'message': 'No se pudo procesar el video. TikTok ha actualizado su sistema. Inténtalo más tarde.'})

@app.route('/downloads/<path:filename>')
def downloaded_file(filename):
    try:
        return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        return "Archivo no encontrado.", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

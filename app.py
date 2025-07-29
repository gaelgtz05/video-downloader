# app.py

import yt_dlp
from flask import Flask, request, jsonify, render_template, send_file
import os
import uuid

# Initialize the Flask App
app = Flask(__name__)

# Directorio temporal para guardar las descargas
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
        if os.path.exists(path):
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
    
    try:
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
            ydl_opts['format'] = 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]'
            ydl_opts['merge_output_format'] = 'mp4'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'Unknown title')
            final_filepath = info.get('requested_downloads')[0]['filepath']
            final_filename = os.path.basename(final_filepath)

        download_url = f'/download_file/{final_filename}'
        return jsonify({'success': True, 'download_url': download_url, 'title': title})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)

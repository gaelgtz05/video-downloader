# app.py

import yt_dlp
from flask import Flask, request, jsonify, render_template
import os

# Initialize the Flask App
app = Flask(__name__)

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

    # Create a 'downloads' directory if it doesn't exist
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        if download_type == 'audio':
            # Options for downloading audio only (MP3)
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'noplaylist': True,
            }
        else:
            # Options for downloading video (max 1080p, prefer MP4)
            ydl_opts = {
                'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best[height<=1080]',
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'noplaylist': True,
                'merge_output_format': 'mp4', # <-- This forces the final file to be MP4
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'Unknown title')

        return jsonify({'success': True, 'message': f'Successfully downloaded: {title}'})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
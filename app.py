# app.py

import yt_dlp
from flask import Flask, request, jsonify, render_template
import os

# Function to read the secret proxy file from Render
def get_proxy_url():
    proxy_file_path = '/etc/secrets/.proxy'
    if os.path.exists(proxy_file_path):
        with open(proxy_file_path, 'r') as f:
            return f.read().strip()
    return None

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
    
    if not video_url:
        return jsonify({'success': False, 'error': 'No URL provided.'}), 400

    proxy_url = get_proxy_url()

    # --- THIS IS THE IMPORTANT DEBUGGING STEP ---
    # Check if the proxy file was found. If not, tell the user.
    if not proxy_url:
        return jsonify({'success': False, 'error': 'Proxy secret file not found on server. Check Render environment settings.'}), 500

    try:
        ydl_opts = {
            'noplaylist': True,
            'proxy': proxy_url, # We now know the proxy exists, so we can add it directly
        }
        
        print(f"Attempting to use proxy: {proxy_url}") # For debugging in Render logs

        # This is a simple, stable operation. 
        # We are only fetching the video's information, not downloading anything.
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            title = info.get('title', 'Unknown title')

        # If we get here, it means the proxy worked!
        return jsonify({'success': True, 'message': f'SUCCESS! Found video: {title}'})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
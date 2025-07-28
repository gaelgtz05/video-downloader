# app.py

import yt_dlp
from flask import Flask, request, jsonify, render_template
import os

# Initialize the Flask App
app = Flask(__name__)

# Path where Render stores our secret cookie file
COOKIE_FILE_PATH = '/etc/secrets/cookies.txt'

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

    try:
        ydl_opts = {
            'noplaylist': True,
        }

        # --- THE ULTIMATE FIX ---
        # Check if the cookie file exists and add it to the options.
        if os.path.exists(COOKIE_FILE_PATH):
            print("Found cookie file, using it for authentication.") # For debugging
            ydl_opts['cookiefile'] = COOKIE_FILE_PATH
        else:
            print("Cookie file not found. Proceeding without authentication.") # For debugging

        # We are only fetching the video's information to test.
        # This is the most stable operation.
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            title = info.get('title', 'Unknown title')

        # If we get here, it means we have defeated the bot detection!
        return jsonify({'success': True, 'message': f'AUTHENTICATION SUCCESS! Video found: {title}'})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
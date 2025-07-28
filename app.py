# app.py

import yt_dlp
from flask import Flask, request, jsonify, render_template
import os
import shutil
import tempfile

# Initialize the Flask App
app = Flask(__name__)

# Path where Render stores our secret cookie file
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
    
    if not video_url:
        return jsonify({'success': False, 'error': 'No URL provided.'}), 400

    # --- THE FINAL FIX: Make a writable copy of the cookie file ---
    temp_cookie_file = None
    try:
        ydl_opts = {
            'noplaylist': True,
        }

        # Check if the secret cookie file exists
        if os.path.exists(SECRET_COOKIE_PATH):
            print("Found secret cookie file. Creating a temporary copy.")
            
            # Create a temporary file that we can write to
            temp_fd, temp_path = tempfile.mkstemp()
            os.close(temp_fd)
            
            # Copy the contents of the read-only secret file to our new temp file
            shutil.copyfile(SECRET_COOKIE_PATH, temp_path)
            
            # Tell yt-dlp to use our writable copy
            ydl_opts['cookiefile'] = temp_path
            temp_cookie_file = temp_path # Keep track to delete it later
        else:
            print("Cookie file not found. Proceeding without authentication.")

        # We are only fetching the video's information to test.
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            title = info.get('title', 'Unknown title')

        # If we get here, it means we have defeated the bot detection!
        return jsonify({'success': True, 'message': f'¡ÉXITO! Video encontrado: {title}'})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    finally:
        # --- Clean up our temporary file ---
        if temp_cookie_file and os.path.exists(temp_cookie_file):
            os.remove(temp_cookie_file)
            print(f"Cleaned up temporary cookie file: {temp_cookie_file}")

if __name__ == '__main__':
    app.run(debug=True)
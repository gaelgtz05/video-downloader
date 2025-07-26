# app.py

import yt_dlp
from flask import Flask, request, jsonify, render_template
import os

# --- NEW: Function to read the secret proxy file ---
def get_proxy_url():
    # This path works on Render where the secret file is mounted
    proxy_file_path = '/etc/secrets/.proxy'
    if os.path.exists(proxy_file_path):
        with open(proxy_file_path, 'r') as f:
            return f.read().strip()
    return None # Return None if running locally or file doesn't exist

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

    # On Render, we can't save files to the main directory long-term.
    # We don't need to create a downloads folder for this setup.
    # The files will be temporarily created and then the process ends.
    # For a more advanced setup, we'd use cloud storage.

    # --- NEW: Get the proxy URL from our function ---
    proxy_url = get_proxy_url()

    try:
        # Base options that are common to both video and audio
        base_ydl_opts = {
            # We'll save files to a temporary location
            'outtmpl': '/tmp/%(title)s.%(ext)s',
            'noplaylist': True,
        }

        # --- NEW: Add proxy to options if it exists ---
        if proxy_url:
            base_ydl_opts['proxy'] = proxy_url
            print("Using proxy for download.") # For debugging

        if download_type == 'audio':
            ydl_opts = base_ydl_opts.copy()
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            ydl_opts = base_ydl_opts.copy()
            ydl_opts.update({
                'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best[height<=1080]',
                'merge_output_format': 'mp4',
            })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # We are not downloading the file to the server anymore.
            # Instead, we are getting the direct download link for the user.
            info = ydl.extract_info(video_url, download=False)
            
            # Find the best format that matches our request
            # This part is more advanced, but necessary for sending a link to the user
            final_url = None
            for f in info.get('formats', []):
                # A simple way to find a URL. This might need more logic for some sites.
                if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    if 'mp4' in f.get('ext'):
                         final_url = f['url']
                         break
            
            # Fallback if no pre-merged mp4 is found
            if not final_url:
                 final_url = info.get('url')


            title = info.get('title', 'Unknown title')

        # Instead of saying "downloaded", we send the URL back to the user
        if final_url:
            return jsonify({'success': True, 'download_url': final_url, 'title': title})
        else:
            return jsonify({'success': False, 'error': 'Could not find a downloadable link.'})


    except Exception as e:
        print(f"An error occurred: {e}")
        # Make the error message more user-friendly
        error_message = str(e)
        if 'confirm you are not a bot' in error_message:
            error_message = 'This video is protected and cannot be downloaded at this time.'
        
        return jsonify({'success': False, 'error': error_message}), 500

if __name__ == '__main__':
    app.run(debug=True)
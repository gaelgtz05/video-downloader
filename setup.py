from setuptools import setup

APP = ['desktop_app.py']
DATA_FILES = ['logo.png', 'ffmpeg']
OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'icon.icns',
    'packages': ['yt_dlp'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
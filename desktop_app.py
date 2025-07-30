# CÓDIGO FINAL PARA EMPAQUETAR
import sys
import os
import threading
import json
import re
import yt_dlp
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QFileDialog,
    QTabWidget, QListWidget, QListWidgetItem, QComboBox, QCheckBox,
    QMessageBox
)
from PyQt6.QtGui import QPixmap, QCursor, QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QStandardPaths

# --- FUNCIÓN CLAVE PARA ENCONTRAR RECURSOS EMPAQUETADOS ---
def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para desarrollo y para PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal y guarda la ruta en sys._MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- ESTILOS Y CONFIGURACIÓN ---
DARK_BACKGROUND = "#1E1E1E"
WIDGET_BACKGROUND = "#2D2D2D"
NAVY_BLUE_ACCENT = "#0A74DA"
TEXT_COLOR = "#EAEAEA"
# --- CORRECCIÓN: Guardar historial en la carpeta de datos del usuario ---
APP_DATA_PATH = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
if not os.path.exists(APP_DATA_PATH):
    os.makedirs(APP_DATA_PATH)
HISTORY_FILE = os.path.join(APP_DATA_PATH, "download_history.json")


# --- CLASES WORKER Y QT (COMPLETAS Y FUNCIONALES) ---
# (Se omiten por brevedad, son las mismas que en tu código)
class FetchFormatsWorker(QThread):
    formats_ready = pyqtSignal(list)
    error = pyqtSignal(str)
    def __init__(self, url):
        super().__init__()
        self.url = url
    def run(self):
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl: info = ydl.extract_info(self.url, download=False)
            formats = info.get('formats', []); processed_formats = []; unique_resolutions = set()
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('height'):
                    height = f['height']
                    if height not in unique_resolutions:
                        unique_resolutions.add(height); ext = f['ext']
                        processed_formats.append({'res': height, 'text': f"{height}p ({ext.upper()})"})
            processed_formats.sort(key=lambda x: x['res'], reverse=True)
            self.formats_ready.emit([item['text'] for item in processed_formats])
        except Exception: self.error.emit("No se pudieron obtener los formatos.")

class DownloadWorker(QThread):
    progress = pyqtSignal(int); status = pyqtSignal(str); finished = pyqtSignal(dict)
    def __init__(self, url, save_path, ydl_opts):
        super().__init__(); self.url = url; self.save_path = save_path; self.ydl_opts = ydl_opts
        self.ydl_opts['progress_hooks'] = [self.progress_hook]
    def run(self):
        try:
            self.ydl_opts['outtmpl'] = self.save_path
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                self.status.emit("Iniciando descarga..."); info_dict = ydl.extract_info(self.url, download=True)
            self.finished.emit(info_dict)
        except Exception as e:
            error_info = {'error': str(e)}
            if hasattr(e, 'exc_info') and e.exc_info and hasattr(e.exc_info[1], 'info_dict'): error_info.update(e.exc_info[1].info_dict)
            self.finished.emit(error_info)
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes and total_bytes > 0:
                percentage = int((d['downloaded_bytes'] / total_bytes) * 100)
                self.progress.emit(percentage); self.status.emit(f"Descargando... {percentage}%")
        elif d['status'] == 'finished': self.status.emit("Procesando con FFmpeg..."); self.progress.emit(100)

class DownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XTRAACT"); self.setMinimumSize(750, 600)
        self.setStyleSheet(f"background-color: {DARK_BACKGROUND}; color: {TEXT_COLOR};")
        self.tabs = QTabWidget(); self.setCentralWidget(self.tabs)
        self.downloader_tab = QWidget(); self.history_tab = QWidget()
        self.tabs.addTab(self.downloader_tab, "Descargar"); self.tabs.addTab(self.history_tab, "Historial")
        self.setup_downloader_ui(); self.setup_history_ui(); self.load_history()

    def setup_downloader_ui(self):
        main_layout = QVBoxLayout(self.downloader_tab); main_layout.addStretch(1)
        logo_label = QLabel()
        # --- CORRECCIÓN: Usar resource_path para encontrar el logo ---
        logo_path = resource_path('logo.png')
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo_label.setPixmap(pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            logo_label.setText("XTRAACT"); logo_label.setStyleSheet("font-size: 36px; font-weight: bold;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(logo_label); main_layout.addSpacing(20)
        downloader_container = QWidget(); downloader_container.setFixedWidth(650)
        container_layout = QVBoxLayout(downloader_container); container_layout.setContentsMargins(0,0,0,0)
        url_layout = QHBoxLayout(); self.url_entry = QLineEdit(); self.url_entry.setPlaceholderText("Pega aquí el enlace del video...")
        self.url_entry.setStyleSheet(f"QLineEdit {{ background-color: {WIDGET_BACKGROUND}; border: 1px solid #444; border-radius: 8px; padding: 10px; font-size: 14px; }}")
        self.url_entry.textChanged.connect(self.on_url_changed)
        paste_button = QPushButton("Pegar"); paste_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        paste_button.setStyleSheet(f"QPushButton {{ background-color: {WIDGET_BACKGROUND}; border: 1px solid #444; padding: 8px; border-radius: 8px; }}")
        paste_button.clicked.connect(self.paste_from_clipboard)
        url_layout.addWidget(self.url_entry); url_layout.addWidget(paste_button); container_layout.addLayout(url_layout); container_layout.addSpacing(10)
        options_layout = QHBoxLayout(); self.quality_combo = QComboBox()
        self.quality_combo.setStyleSheet(f"QComboBox {{ background-color: {WIDGET_BACKGROUND}; border: 1px solid #444; padding: 8px; border-radius: 8px; }}")
        self.quality_combo.addItem("Mejor Calidad (Auto)"); self.mp3_checkbox = QCheckBox("Solo audio (MP3)")
        self.mp3_checkbox.toggled.connect(self.toggle_quality_combo); options_layout.addWidget(QLabel("Calidad:"))
        options_layout.addWidget(self.quality_combo, 1); options_layout.addWidget(self.mp3_checkbox); container_layout.addLayout(options_layout); container_layout.addSpacing(20)
        self.download_button = QPushButton("Descargar"); self.download_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.download_button.setStyleSheet(f"QPushButton {{ background-color: {NAVY_BLUE_ACCENT}; color: white; font-size: 16px; font-weight: bold; padding: 12px; border-radius: 8px; border: none; }} QPushButton:hover {{ background-color: #0056b3; }}")
        self.download_button.clicked.connect(self.start_download); container_layout.addWidget(self.download_button); container_layout.addSpacing(10)
        self.status_label = QLabel("Listo para descargar."); self.status_label.setStyleSheet("font-size: 12px; color: #AAAAAA;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.progress_bar = QProgressBar(); self.progress_bar.setValue(0); self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"QProgressBar {{ background-color: {WIDGET_BACKGROUND}; border: none; border-radius: 5px; height: 10px; }} QProgressBar::chunk {{ background-color: {NAVY_BLUE_ACCENT}; border-radius: 5px; }}")
        container_layout.addWidget(self.status_label); container_layout.addWidget(self.progress_bar)
        main_layout.addWidget(downloader_container, 0, Qt.AlignmentFlag.AlignHCenter); main_layout.addStretch(2)
        terms_label = QLabel("<a href='#' style='color: #AAAAAA; text-decoration: none;'>Términos y Condiciones</a>")
        terms_label.linkActivated.connect(self.show_terms); main_layout.addWidget(terms_label, 0, Qt.AlignmentFlag.AlignCenter)

    def setup_history_ui(self):
        layout = QVBoxLayout(self.history_tab)
        self.history_list = QListWidget()
        self.history_list.setStyleSheet(f"QListWidget {{ background-color: {WIDGET_BACKGROUND}; border: 1px solid #444; border-radius: 8px; }}")
        layout.addWidget(self.history_list)

    def on_url_changed(self, text):
        self.quality_combo.clear(); self.quality_combo.addItem("Mejor Calidad (Auto)")
        if text.startswith("http"):
            self.status_label.setText("Buscando calidades disponibles...")
            self.fetch_formats_worker = FetchFormatsWorker(text)
            self.fetch_formats_worker.formats_ready.connect(self.populate_quality_combo)
            self.fetch_formats_worker.error.connect(lambda e: self.status_label.setText(e))
            self.fetch_formats_worker.start()

    def populate_quality_combo(self, formats):
        if formats: self.quality_combo.addItems(formats); self.status_label.setText("Formatos de calidad cargados.")
        else: self.status_label.setText("Listo para descargar.")

    def toggle_quality_combo(self, checked): self.quality_combo.setDisabled(checked)
    def paste_from_clipboard(self): self.url_entry.setText(QApplication.clipboard().text())

    def start_download(self):
        url = self.url_entry.text()
        if not url: self.status_label.setText("Por favor, introduce una URL."); return
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl: info = ydl.extract_info(url, download=False)
            title = info.get('title', 'media').replace('/', '_').replace('\\', '_')
        except Exception: self.status_label.setText("Error: URL inválida o no se pudo obtener información."); return
        
        is_mp3 = self.mp3_checkbox.isChecked()
        ffmpeg_path = resource_path('ffmpeg') # --- CORRECCIÓN: Usar la ruta del ffmpeg empaquetado ---
        
        if is_mp3:
            ydl_opts = {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}], 'ffmpeg_location': ffmpeg_path}
            file_extension = "mp3"
        else:
            format_string = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            if 'instagram.com' not in url:
                selected_quality = self.quality_combo.currentText()
                if selected_quality != "Mejor Calidad (Auto)":
                    match = re.search(r'(\d+)', selected_quality)
                    if match: format_string = f"bestvideo[height<={match.group(1)}][ext=mp4]+bestaudio[ext=m4a]/best[height<={match.group(1)}][ext=mp4]/best"
            
            ydl_opts = {'format': format_string, 'ffmpeg_location': ffmpeg_path, 'recode_video': 'mp4' if 'instagram.com' in url else None}
            file_extension = "mp4"

        suggested_filename = f"{title}.{file_extension}"
        downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        save_path, _ = QFileDialog.getSaveFileName(self, "Guardar Archivo", os.path.join(downloads_path, suggested_filename))

        if not save_path: self.status_label.setText("Descarga cancelada."); return

        self.download_button.setDisabled(True); self.progress_bar.setValue(0)
        self.worker = DownloadWorker(url, save_path, ydl_opts)
        self.worker.status.connect(self.status_label.setText); self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_download_finished); self.worker.start()

    def on_download_finished(self, info_dict):
        self.download_button.setDisabled(False); self.progress_bar.setValue(0)
        if 'error' not in info_dict: self.status_label.setText("¡Descarga completa!"); self.save_to_history(info_dict)
        else:
            error_msg = info_dict.get('error', 'Error desconocido.')
            if "ffmpeg" in error_msg.lower(): self.status_label.setText("Error: FFmpeg no se encuentra en el paquete.")
            else: self.status_label.setText(f"Error: {error_msg[:100]}...")

    def load_history(self):
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    for item in json.load(f): self.add_item_to_history_list(item)
        except Exception as e: print(f"Error al leer historial: {e}")

    def save_to_history(self, info):
        try:
            history = []
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f: history = json.load(f)
            new_item = {'title': info.get('title', 'N/A'), 'uploader': info.get('uploader', 'N/A'), 'webpage_url': info.get('webpage_url', '#')}
            history.insert(0, new_item)
            with open(HISTORY_FILE, 'w') as f: json.dump(history[:100], f, indent=4)
            self.add_item_to_history_list(new_item, at_top=True)
        except Exception as e: print(f"Error al guardar historial: {e}")
    
    def add_item_to_history_list(self, item, at_top=False):
        list_item = QListWidgetItem(f"{item['title']}\n- por {item['uploader']}")
        if at_top: self.history_list.insertItem(0, list_item)
        else: self.history_list.addItem(list_item)

    def show_terms(self):
        msg_box = QMessageBox(self); msg_box.setWindowTitle("Términos y Condiciones")
        msg_box.setText("Este es un placeholder para tus términos y condiciones."); msg_box.exec()

# --- PUNTO DE ENTRADA PRINCIPAL (CON CORRECCIÓN PARA DOCK DE MACOS) ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DownloaderApp()
    
    # --- CORRECCIÓN: Asignar ícono para que se muestre correctamente en el Dock ---
    window.setWindowIcon(QIcon(resource_path("logo.png")))
    
    window.show()
    sys.exit(app.exec())
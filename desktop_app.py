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
from PyQt6.QtGui import QPixmap, QCursor
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# --- ESTILOS DE LA APLICACIÓN ---
DARK_BACKGROUND = "#1E1E1E"
WIDGET_BACKGROUND = "#2D2D2D"
NAVY_BLUE_ACCENT = "#0A74DA"
TEXT_COLOR = "#EAEAEA"
HISTORY_FILE = "download_history.json"

# --- WORKER PARA OBTENER FORMATOS ---
class FetchFormatsWorker(QThread):
    formats_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
                info = ydl.extract_info(self.url, download=False)
            
            formats = info.get('formats', [])
            processed_formats = []
            unique_resolutions = set()

            for f in formats:
                if f.get('vcodec') != 'none' and f.get('height'):
                    height = f['height']
                    if height not in unique_resolutions:
                        unique_resolutions.add(height)
                        ext = f['ext']
                        display_text = f"{height}p ({ext.upper()})"
                        processed_formats.append({'res': height, 'text': display_text})
            
            processed_formats.sort(key=lambda x: x['res'], reverse=True)
            final_list = [item['text'] for item in processed_formats]
            
            self.formats_ready.emit(final_list)
        except Exception as e:
            print(f"Error fetching formats: {e}")
            self.error.emit("No se pudieron obtener los formatos.")

# --- WORKER PARA LA DESCARGA ---
class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)

    def __init__(self, url, save_path, ydl_opts):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.ydl_opts = ydl_opts

    def run(self):
        try:
            self.ydl_opts['outtmpl'] = self.save_path
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                self.status.emit("Iniciando descarga...")
                info_dict = ydl.extract_info(self.url, download=True)
            self.finished.emit(info_dict)
        except Exception as e:
            self.finished.emit({'error': str(e)})

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                percentage = int((d['downloaded_bytes'] / total_bytes) * 100)
                self.progress.emit(percentage)
                self.status.emit(f"Descargando... {percentage}%")

# --- VENTANA PRINCIPAL ---
class DownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("XTRAACT")
        self.setMinimumSize(750, 600)
        self.setStyleSheet(f"background-color: {DARK_BACKGROUND}; color: {TEXT_COLOR};")

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.downloader_tab = QWidget()
        self.history_tab = QWidget()
        
        self.tabs.addTab(self.downloader_tab, "Descargar")
        self.tabs.addTab(self.history_tab, "Historial")

        self.setup_downloader_ui()
        self.setup_history_ui()
        self.load_history()

    def setup_downloader_ui(self):
        main_layout = QVBoxLayout(self.downloader_tab)
        main_layout.addStretch(1)

        logo_label = QLabel()
        if os.path.exists('logo.png'):
            pixmap = QPixmap('logo.png')
            logo_label.setPixmap(pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            logo_label.setText("XTRAACT")
            logo_label.setStyleSheet(f"font-size: 36px; font-weight: bold; color: {TEXT_COLOR};")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(logo_label)
        main_layout.addSpacing(20)

        downloader_container = QWidget()
        downloader_container.setFixedWidth(650)
        container_layout = QVBoxLayout(downloader_container)
        container_layout.setContentsMargins(0,0,0,0)

        url_layout = QHBoxLayout()
        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText("Pega aquí el enlace del video...")
        self.url_entry.setStyleSheet(f"QLineEdit {{ background-color: {WIDGET_BACKGROUND}; border: 1px solid #444; border-radius: 8px; padding: 10px; font-size: 14px; }}")
        self.url_entry.textChanged.connect(self.on_url_changed)
        
        paste_button = QPushButton("Pegar")
        paste_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        paste_button.setStyleSheet(f"QPushButton {{ background-color: {WIDGET_BACKGROUND}; border: 1px solid #444; padding: 8px; border-radius: 8px; }}")
        paste_button.clicked.connect(self.paste_from_clipboard)
        
        url_layout.addWidget(self.url_entry)
        url_layout.addWidget(paste_button)
        container_layout.addLayout(url_layout)
        container_layout.addSpacing(10)

        options_layout = QHBoxLayout()
        self.quality_combo = QComboBox()
        self.quality_combo.setStyleSheet(f"QComboBox {{ background-color: {WIDGET_BACKGROUND}; border: 1px solid #444; padding: 8px; border-radius: 8px; }}")
        self.quality_combo.addItem("Mejor Calidad (Auto)")
        
        self.mp3_checkbox = QCheckBox("Solo audio (MP3)")
        self.mp3_checkbox.toggled.connect(self.toggle_quality_combo)

        options_layout.addWidget(QLabel("Calidad:"))
        options_layout.addWidget(self.quality_combo, 1)
        options_layout.addWidget(self.mp3_checkbox)
        container_layout.addLayout(options_layout)
        container_layout.addSpacing(20)

        self.download_button = QPushButton("Descargar")
        self.download_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.download_button.setStyleSheet(f"QPushButton {{ background-color: {NAVY_BLUE_ACCENT}; color: white; font-size: 16px; font-weight: bold; padding: 12px; border-radius: 8px; border: none; }} QPushButton:hover {{ background-color: #0056b3; }}")
        self.download_button.clicked.connect(self.start_download)
        container_layout.addWidget(self.download_button)
        container_layout.addSpacing(10)

        self.status_label = QLabel("Listo para descargar.")
        self.status_label.setStyleSheet(f"font-size: 12px; color: #AAAAAA;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"QProgressBar {{ background-color: {WIDGET_BACKGROUND}; border: none; border-radius: 5px; height: 10px; }} QProgressBar::chunk {{ background-color: {NAVY_BLUE_ACCENT}; border-radius: 5px; }}")

        container_layout.addWidget(self.status_label)
        container_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(downloader_container, 0, Qt.AlignmentFlag.AlignHCenter)
        main_layout.addStretch(2)

        terms_label = QLabel("<a href='#' style='color: #AAAAAA; text-decoration: none;'>Términos y Condiciones</a>")
        terms_label.linkActivated.connect(self.show_terms)
        main_layout.addWidget(terms_label, 0, Qt.AlignmentFlag.AlignCenter)

    def setup_history_ui(self):
        layout = QVBoxLayout(self.history_tab)
        self.history_list = QListWidget()
        self.history_list.setStyleSheet(f"QListWidget {{ background-color: {WIDGET_BACKGROUND}; border: 1px solid #444; border-radius: 8px; }}")
        layout.addWidget(self.history_list)

    def on_url_changed(self, text):
        self.quality_combo.clear()
        self.quality_combo.addItem("Mejor Calidad (Auto)")
        if text.startswith("http"):
            self.status_label.setText("Buscando calidades disponibles...")
            self.fetch_formats_worker = FetchFormatsWorker(text)
            self.fetch_formats_worker.formats_ready.connect(self.populate_quality_combo)
            self.fetch_formats_worker.error.connect(lambda e: self.status_label.setText(e))
            self.fetch_formats_worker.start()

    def populate_quality_combo(self, formats):
        if formats:
            self.quality_combo.addItems(formats)
            self.status_label.setText("Formatos de calidad cargados.")
        else:
            self.status_label.setText("Listo para descargar.")

    def toggle_quality_combo(self, checked):
        self.quality_combo.setDisabled(checked)

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        self.url_entry.setText(clipboard.text())

    def start_download(self):
        url = self.url_entry.text()
        if not url:
            self.status_label.setText("Por favor, introduce una URL.")
            return

        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
                info = ydl.extract_info(url, download=False)
            
            is_instagram = 'instagram' in info.get('extractor_key', '').lower()
            title = info.get('title', 'media').replace('/', '_').replace('\\', '_')
            
        except Exception as e:
            self.status_label.setText("Error: No se pudo obtener información de la URL.")
            print(f"Metadata error: {e}")
            return
        
        is_mp3 = self.mp3_checkbox.isChecked()
        
        if is_mp3:
            ydl_opts = {'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]}
            file_extension = "mp3"
            suggested_filename = f"{title}.{file_extension}"
        else:
            if is_instagram:
                format_string = 'bestvideo[vcodec^=avc][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                uploader = info.get('uploader', 'instagram')
                upload_date = info.get('upload_date', '')
                post_id = info.get('id', '')
                suggested_filename = f"{uploader}_{upload_date}_{post_id}.mp4"
            else:
                selected_quality = self.quality_combo.currentText()
                if selected_quality == "Mejor Calidad (Auto)":
                    format_string = 'bestvideo[vcodec^=avc][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                else:
                    match = re.search(r'(\d+)', selected_quality)
                    height = match.group(1) if match else 'best'
                    format_string = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
                
                suggested_filename = f"{title}.mp4"

            ydl_opts = {'format': format_string, 'merge_output_format': 'mp4'}
            file_extension = "mp4"

        save_path, _ = QFileDialog.getSaveFileName(self, "Guardar Archivo", os.path.join(os.path.expanduser('~'), 'Downloads', suggested_filename))

        if not save_path:
            self.status_label.setText("Descarga cancelada.")
            return

        self.download_button.setDisabled(True)
        self.worker = DownloadWorker(url, save_path, ydl_opts)
        self.worker.status.connect(self.status_label.setText)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.start()

    def on_download_finished(self, info_dict):
        self.download_button.setDisabled(False)
        if 'error' not in info_dict:
            self.status_label.setText("¡Descarga completa!")
            self.save_to_history(info_dict)
        else:
            error_msg = info_dict['error']
            if "Requested format is not available" in error_msg:
                 self.status_label.setText("Error: La calidad seleccionada no está disponible para este video.")
            else:
                 self.status_label.setText(f"Error: {error_msg[:80]}...")

    def load_history(self):
        if not os.path.exists(HISTORY_FILE): return
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
                for item in history: self.add_item_to_history_list(item)
        except:
            print("Error al leer el historial.")

    def save_to_history(self, info):
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f: history = json.load(f)
            except: history = []
        
        new_item = {'title': info.get('title', 'N/A'), 'uploader': info.get('uploader', 'N/A'), 'webpage_url': info.get('webpage_url', '#')}
        history.insert(0, new_item)
        history = history[:100]

        with open(HISTORY_FILE, 'w') as f: json.dump(history, f, indent=4)
        self.add_item_to_history_list(new_item, at_top=True)
    
    def add_item_to_history_list(self, item, at_top=False):
        list_item = QListWidgetItem(f"{item['title']}\n- por {item['uploader']}")
        if at_top: self.history_list.insertItem(0, list_item)
        else: self.history_list.addItem(list_item)

    def show_terms(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Términos y Condiciones de Uso")
        terms_text = """
<p><b>¡IMPORTANTE!</b> Lee estos términos cuidadosamente antes de usar la aplicación.</p>
<p><b>1. Propósito de la Herramienta</b></p>
<p>Esta aplicación es una herramienta de software creada para permitir al usuario descargar copias de contenido de video y audio desde diversas plataformas en línea <b>única y exclusivamente para su uso personal, privado y sin fines de lucro.</b> El propósito es permitir el visionado offline de contenido al que el usuario ya tiene acceso legal.</p>
<p><b>2. Responsabilidad del Usuario</b></p>
<p><b>Tú, como usuario, eres el único y total responsable de cómo utilizas esta aplicación.</b> El desarrollador ("nosotros") te proporciona la herramienta técnica, pero no tenemos control ni asumimos responsabilidad sobre el contenido que descargas o el uso que le das. Es tu responsabilidad asegurarte de que no estás infringiendo ninguna ley o normativa aplicable en tu país o región.</p>
<p><b>3. Derechos de Autor (Copyright)</b></p>
<p><b>Esta aplicación respeta los derechos de los creadores de contenido.</b> Te recordamos que la gran mayoría del contenido en plataformas como YouTube, Instagram y TikTok está protegido por leyes de derechos de autor.</p>
<ul>
<li><b>NO DEBES</b> usar esta aplicación para descargar material con derechos de autor con el fin de redistribuirlo, modificarlo, venderlo o usarlo en cualquier proyecto público o comercial.</li>
<li><b>NO DEBES</b> usar esta aplicación para cometer actos de piratería.</li>
<li>El uso legítimo de esta herramienta se limita a crear una copia de seguridad personal de contenido público o de contenido de tu propiedad.</li>
</ul>
<p>El incumplimiento de los términos de servicio de las plataformas de origen o de las leyes de copyright es de tu exclusiva responsabilidad.</p>
<p><b>4. Sin Garantías</b></p>
<p>La aplicación se proporciona "tal cual", sin ninguna garantía de funcionamiento ininterrumpido o libre de errores. No garantizamos que la aplicación pueda descargar desde todas las plataformas o que funcione para siempre, ya que dependemos de los servicios de terceros que pueden cambiar en cualquier momento.</p>
<p>Al usar esta aplicación, aceptas y confirmas que he has leído, entendido y estás de acuerdo con todos los términos aquí expuestos.</p>
        """
        msg_box.setText(terms_text)
        msg_box.setStyleSheet(f"QMessageBox {{ background-color: {WIDGET_BACKGROUND}; color: {TEXT_COLOR}; }}")
        msg_box.exec()

# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DownloaderApp()
    window.show()
    sys.exit(app.exec())

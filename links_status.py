import sys
import re
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton
)
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# lista de links a comprobar

LINKS = [
    ("Pelicula", "Camina o muere (2025)", "https://mega.nz/file/TuArchivo"),
]

def check_mediafire(url):

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none"
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, timeout=10, allow_redirects=True)
        
        if response.status_code != 200:
            return False
        
        page_text = response.text.lower()
        page_original = response.text

        error_phrases = [
            "file has been removed",
            "file no longer available",
            "file you requested is not available",
            "invalid or deleted file",
            "file not found"
        ]
        
        for phrase in error_phrases:
            if phrase in page_text:
                return False

        indicators = [
            "download_link" in page_text,
            'aria-label="download"' in page_text,
            'id="downloadbutton"' in page_text,
            'id="download_link"' in page_text,
            "download_file" in page_text,
            "mf-dlr" in page_original,
            'class="input popsok"' in page_original,
            "filename" in page_text and "filesize" in page_text
        ]
        
        if any(indicators):
            return True
        
        return False
        
    except Exception as e:
        print(f"Error checking MediaFire: {e}")
        return False


def check_mega(url):

    try:
        pattern = r'/file/([a-zA-Z0-9_-]+)#([a-zA-Z0-9_-]+)'
        match = re.search(pattern, url)
        
        if not match:
            return False
        
        file_id = match.group(1)

        api_endpoint = "https://g.api.mega.co.nz/cs"
        payload = [{
            "a": "g",
            "p": file_id
        }]
        
        response = requests.post(
            api_endpoint, 
            json=payload, 
            timeout=8,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            return False
        
        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            result = data[0]

            if isinstance(result, int):
                return False

            if isinstance(result, dict) and "s" in result:
                return True
        
        return False
        
    except Exception as e:
        print(f"Error checking MEGA: {e}")
        return False


def check_link(url):
    if "mediafire.com" in url:
        return check_mediafire(url)
    elif "mega.nz" in url:
        return check_mega(url)
    else:
        return False


class CheckerThread(QThread):
    result_ready = pyqtSignal(str, str, str, bool, int)
    finished_all = pyqtSignal()
    
    def __init__(self, links):
        super().__init__()
        self.links = links
    
    def run(self):
        for idx, (category, title, link) in enumerate(self.links):
            is_active = check_link(link)
            self.result_ready.emit(category, title, link, is_active, idx)
        
        self.finished_all.emit()


class LinkChecker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Link Status")
        self.setMinimumSize(1200, 700)

        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
                color: #eaeaea;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        header_widget = self._create_header()
        main_layout.addWidget(header_widget)

        self.list_widget = self._create_list_widget()
        main_layout.addWidget(self.list_widget)

        buttons_section = self._create_buttons_section()
        main_layout.addLayout(buttons_section)
        
        self.setLayout(main_layout)
        
        self.worker = None
        self.items = {}

        self.check_all_links()
    
    def _create_header(self):
        header = QWidget()
        header_layout = QVBoxLayout()
        header.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #16213e, stop:1 #0f3460);
            border-radius: 10px;
            padding: 15px;
        """)
        
        title = QLabel("🔗 Monitor de Enlaces")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #00d9ff; padding: 10px;")
        
        self.status_label = QLabel("Listo para comprobar")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 12))
        self.status_label.setStyleSheet("color: #a0a0a0; padding: 5px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(self.status_label)
        header.setLayout(header_layout)
        
        return header
    
    def _create_list_widget(self):
        list_widget = QListWidget()
        list_widget.setStyleSheet("""
            QListWidget {
                background-color: #16213e;
                border: 2px solid #0f3460;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QListWidget::item {
                padding: 12px;
                margin: 4px 0px;
                border-radius: 6px;
                background-color: #1a1a2e;
                border-left: 4px solid transparent;
            }
            QListWidget::item:hover {
                background-color: #0f3460;
            }
            QListWidget::item:selected {
                background-color: #0f3460;
                border-left: 4px solid #00d9ff;
            }
        """)
        return list_widget
    
    def _create_buttons_section(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        self.stats_label = QLabel("📊 Estadisticas: -- activos / -- totales")
        self.stats_label.setFont(QFont("Segoe UI", 11))
        self.stats_label.setAlignment(Qt.AlignCenter)
        self.stats_label.setStyleSheet("""
            background-color: #16213e;
            color: #00d9ff;
            padding: 10px;
            border-radius: 6px;
            border: 1px solid #0f3460;
        """)

        self.refresh_btn = QPushButton("🔄 Refrescar Enlaces")
        self.refresh_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.refresh_btn.setMinimumHeight(45)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d9ff, stop:1 #0099cc);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00e6ff, stop:1 #00aadd);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0099cc, stop:1 #007799);
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #888;
            }
        """)
        self.refresh_btn.clicked.connect(self.check_all_links)
        
        layout.addWidget(self.stats_label)
        layout.addWidget(self.refresh_btn)
        
        return layout
    
    def check_all_links(self):
        self.list_widget.clear()
        self.items.clear()
        self.refresh_btn.setEnabled(False)
        self.status_label.setText("⏳ Comprobando enlaces...")
        self.stats_label.setText("📊 Estadisticas: -- activos / -- totales")

        for idx, (category, title, link) in enumerate(LINKS):
            item_text = f"⏳ Verificando...  │  📁 {category}  │  📄 {title}  │  🔗 {link}"
            item = QListWidgetItem(item_text)
            item.setFont(QFont("Consolas", 11))
            item.setForeground(QColor(160, 160, 160))
            self.list_widget.addItem(item)
            self.items[idx] = item

        self.worker = CheckerThread(LINKS)
        self.worker.result_ready.connect(self.update_item)
        self.worker.finished_all.connect(self.on_finished)
        self.worker.start()
    
    def update_item(self, category, title, link, is_active, idx):
        if idx not in self.items:
            return
        
        if is_active:
            status_text = "✅ ACTIVO  "
            color = QColor(0, 230, 118)
        else:
            status_text = "❌ CAIDO   "
            color = QColor(255, 71, 87)
        
        item_text = f"{status_text} │  📁 {category}  │  📄 {title}  │  🔗 {link}"
        self.items[idx].setText(item_text)
        self.items[idx].setForeground(color)
        self.items[idx].setFont(QFont("Consolas", 11))
    
    def on_finished(self):
        self.status_label.setText("✅ Comprobacion completada")
        self.refresh_btn.setEnabled(True)

        total_links = len(self.items)
        active_links = sum(1 for item in self.items.values() if "✅" in item.text())
        inactive_links = total_links - active_links
        
        stats_text = f"📊 Estadisticas: {active_links} activos  •  {inactive_links} caidos  •  {total_links} totales"
        self.stats_label.setText(stats_text)

        if active_links == total_links:
            self.status_label.setStyleSheet("color: #00e676; padding: 5px; font-weight: bold;")
            self.status_label.setText("✅ ¡Todos los enlaces estan activos!")
        elif active_links == 0:
            self.status_label.setStyleSheet("color: #ff4757; padding: 5px; font-weight: bold;")
            self.status_label.setText("❌ Todos los enlaces estan caidos")
        else:
            self.status_label.setStyleSheet("color: #ffa502; padding: 5px; font-weight: bold;")
            self.status_label.setText(f"⚠️ {inactive_links} enlace(s) caido(s)")

def main():
    app = QApplication(sys.argv)
    window = LinkChecker()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
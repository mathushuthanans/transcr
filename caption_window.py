import sys
import os
os.environ["QT_QPA_PLATFORM"] = "xcb"

import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                            QHBoxLayout, QWidget, QFrame, QPushButton, QComboBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPalette, QColor
from model import ContinuousTranscriber  # Your existing model

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Worker thread for transcription (from window.py)
class TranscriptionWorker(QObject):
    translation_ready = pyqtSignal(str, str)  # (transcription, translation)
    status = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.transcriber = None
        self.running = False

    @pyqtSlot(str)
    def start(self, target_language='en'):
        try:
            if self.transcriber:
                self.stop()
            
            self.status.emit(f"🎤 Listening → {target_language}")
            self.transcriber = ContinuousTranscriber(target_language=target_language)
            self.transcriber.set_callback(self.callback)
            self.transcriber.start_transcription()
            self.running = True
        except Exception as e:
            self.error.emit(str(e))

    def callback(self, transcription, translation):
        """Called by ContinuousTranscriber with real-time results"""
        if transcription or translation:
            self.translation_ready.emit(
                transcription or "🎤 Listening...",
                translation or "🌍 Translating..."
            )

    @pyqtSlot()
    def stop(self):
        if self.transcriber:
            self.transcriber.stop_transcription()
            self.transcriber = None
        self.running = False
        self.status.emit("⏸ Idle")

class AllInOneCaptionWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Setup worker thread
        self.thread = QThread()
        self.worker = TranscriptionWorker()
        self.worker.moveToThread(self.thread)
        self.thread.start()
        
        # Typing animation (from window.py)
        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self.type_effect)
        self.full_transcription = ""
        self.full_translation = ""
        self.shown_transcription = ""
        self.shown_translation = ""
        
        self.initUI()
        self.connectSignals()

    def initUI(self):
        # Window setup - keeping your cyberpunk theme from caption_window.py
        self.setWindowTitle('LiveSpeak')
        self.setGeometry(300, 300, 900, 400)
        self.setMinimumSize(900, 400)

        # Cyberpunk neon theme (from caption_window.py)
        self.setStyleSheet("""
            QMainWindow {
                background: #0a0e27;
            }
            QFrame#headerFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff00cc, stop:1 #333399);
                border: none;
                border-bottom: 2px solid #00ffff;
            }
            QFrame#transcriptFrame {
                background: #14182f;
                border: 2px solid #00ffff;
                border-radius: 15px;
            }
            QFrame#translationFrame {
                background: #14182f;
                border: 2px solid #ff00cc;
                border-radius: 15px;
            }
            QLabel#headerLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                font-family: 'Courier New';
                padding: 10px;
                background: transparent;
            }
            QLabel#transcriptHeader {
                color: #00ffff;
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 2px;
                font-family: 'Courier New';
                background: transparent;
            }
            QLabel#translationHeader {
                color: #ff00cc;
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 2px;
                font-family: 'Courier New';
                background: transparent;
            }
            QLabel#transcriptContent {
                background: #0f1329;
                color: #00ffff;
                font-size: 18px;
                font-family: 'Courier New';
                border: 1px solid #00ffff;
                border-radius: 10px;
                padding: 20px;
                min-height: 80px;
            }
            QLabel#translationContent {
                background: #0f1329;
                color: #ff00cc;
                font-size: 18px;
                font-family: 'Courier New';
                border: 1px solid #ff00cc;
                border-radius: 10px;
                padding: 20px;
                min-height: 80px;
            }
            QLabel#statusLabel {
                color: #00ff00;
                font-size: 12px;
                font-family: 'Courier New';
                background: #1a1f3a;
                border: 1px solid #00ff00;
                border-radius: 12px;
                padding: 5px 15px;
            }
            QComboBox, QPushButton {
                background: #14182f;
                color: #00ffff;
                border: 2px solid #00ffff;
                border-radius: 8px;
                padding: 8px;
                font-family: 'Courier New';
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background: #00ffff;
                color: #0a0e27;
            }
            QComboBox:hover {
                border-color: #ff00cc;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setFixedHeight(60)
        header_layout = QVBoxLayout(header_frame)
        
        header_label = QLabel('⚡ LiveSpeak ⚡')
        header_label.setObjectName("headerLabel")
        header_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(header_label)
        main_layout.addWidget(header_frame)

        # Controls (NEW - from window.py)
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        
        # Language selector
        self.lang_combo = QComboBox()
        languages = {
            'English': 'en', 'Spanish': 'es', 'French': 'fr', 
            'German': 'de', 'Japanese': 'ja', 'Chinese': 'zh'
        }
        for lang in languages.keys():
            self.lang_combo.addItem(f"🌐 {lang}", languages[lang])
        
        # Start/Stop button
        self.toggle_btn = QPushButton("▶ START CAPTURE")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setFixedWidth(200)
        
        controls_layout.addWidget(self.lang_combo)
        controls_layout.addWidget(self.toggle_btn)
        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)

        # Main content area (dual panel from caption_window.py)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Transcription panel
        transcript_panel = QFrame()
        transcript_panel.setObjectName("transcriptFrame")
        transcript_layout = QVBoxLayout(transcript_panel)
        transcript_layout.setSpacing(10)

        transcript_header = QLabel('🎤 INPUT STREAM')
        transcript_header.setObjectName("transcriptHeader")
        transcript_header.setAlignment(Qt.AlignCenter)

        self.transcription_label = QLabel('💬 Click START to begin...')
        self.transcription_label.setObjectName("transcriptContent")
        self.transcription_label.setWordWrap(True)
        self.transcription_label.setAlignment(Qt.AlignCenter)

        transcript_layout.addWidget(transcript_header)
        transcript_layout.addWidget(self.transcription_label)

        # Translation panel
        translation_panel = QFrame()
        translation_panel.setObjectName("translationFrame")
        translation_layout = QVBoxLayout(translation_panel)
        translation_layout.setSpacing(10)

        translation_header = QLabel('🌍 OUTPUT TRANSLATION')
        translation_header.setObjectName("translationHeader")
        translation_header.setAlignment(Qt.AlignCenter)

        self.translation_label = QLabel('🌐 Select language...')
        self.translation_label.setObjectName("translationContent")
        self.translation_label.setWordWrap(True)
        self.translation_label.setAlignment(Qt.AlignCenter)

        translation_layout.addWidget(translation_header)
        translation_layout.addWidget(self.translation_label)

        content_layout.addWidget(transcript_panel, 1)
        content_layout.addWidget(translation_panel, 1)

        main_layout.addLayout(content_layout)

        # Status bar
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel('🟡 SYSTEM READY')
        self.status_label.setObjectName("statusLabel")
        
        version_label = QLabel('v3.0 • ALL-IN-ONE')
        version_label.setObjectName("statusLabel")
        version_label.setAlignment(Qt.AlignRight)
        
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(version_label)
        
        main_layout.addLayout(status_layout)

        # Window properties
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

    def connectSignals(self):
        """Connect all signals and slots"""
        self.toggle_btn.toggled.connect(self.toggle_capture)
        self.worker.translation_ready.connect(self.start_typing_animation)
        self.worker.status.connect(self.status_label.setText)
        self.worker.error.connect(self.show_error)

    def toggle_capture(self, checked):
        """Start or stop transcription"""
        if checked:
            self.toggle_btn.setText("⏹ STOP CAPTURE")
            target_lang = self.lang_combo.currentData()
            QTimer.singleShot(0, lambda: self.worker.start(target_lang))
            self.transcription_label.setText("🎤 Listening...")
            self.translation_label.setText("🌍 Translating...")
        else:
            self.toggle_btn.setText("▶ START CAPTURE")
            QTimer.singleShot(0, self.worker.stop)
            self.transcription_label.setText("💬 Capture stopped")
            self.translation_label.setText("🌐 Select language...")

    def start_typing_animation(self, transcription, translation):
        """Prepare for typing animation"""
        self.full_transcription = transcription
        self.full_translation = translation
        self.shown_transcription = ""
        self.shown_translation = ""
        self.typing_timer.start(15)

    def type_effect(self):
        """Animate text appearing (from window.py)"""
        # Update transcription
        if len(self.shown_transcription) < len(self.full_transcription):
            self.shown_transcription += self.full_transcription[len(self.shown_transcription)]
            self.transcription_label.setText(self.shown_transcription)
        
        # Update translation
        if len(self.shown_translation) < len(self.full_translation):
            self.shown_translation += self.full_translation[len(self.shown_translation)]
            self.translation_label.setText(self.shown_translation)
        
        # Stop timer when both are complete
        if (len(self.shown_transcription) >= len(self.full_transcription) and 
            len(self.shown_translation) >= len(self.full_translation)):
            self.typing_timer.stop()

    def show_error(self, msg):
        """Show error in status"""
        self.status_label.setText(f"🔴 ERROR: {msg[:30]}...")

    def closeEvent(self, event):
        """Clean shutdown"""
        self.worker.stop()
        self.thread.quit()
        self.thread.wait(2000)
        event.accept()

def run():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = AllInOneCaptionWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    run()
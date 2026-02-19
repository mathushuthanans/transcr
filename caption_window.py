import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QFrame  # Added QHBoxLayout!
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QPalette, QColor
from socketio import Client

import threading
import logging
from model import ContinuousTranscriber

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SocketThread(QObject):
    transcription_received = pyqtSignal(str, str)
    connection_status = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.socketio = Client(
            logger=True,
            engineio_logger=True,
            reconnection=True,
            reconnection_attempts=5,
            reconnection_delay=1
        )
        self.setup_socket_events()

    def setup_socket_events(self):
        @self.socketio.on('connect')
        def on_connect():
            logger.info(f"Connected to server with SID: {self.socketio.sid}")
            self.connection_status.emit(True)

        @self.socketio.on('disconnect')
        def on_disconnect():
            logger.info("Disconnected from server")
            self.connection_status.emit(False)

        @self.socketio.on('transcription_update')
        def on_transcription(data):
            try:
                if isinstance(data, dict):
                    transcription = data.get('transcription', '')
                    translation = data.get('translation', '')
                    self.transcription_received.emit(
                        transcription or '💬 Waiting...',
                        translation or '🌍 Waiting...'
                    )
            except Exception as e:
                logger.error(f"Error processing transcription update: {e}")

    def connect_to_server(self):
        try:
            self.socketio.connect(
                'http://localhost:5000',
                transports=['websocket', 'polling'],
                wait_timeout=10,
                wait=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            return False

    def disconnect(self):
        try:
            if self.socketio.connected:
                self.socketio.disconnect()
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

class CyberCaptionWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.socket_handler = None
        self.local_transcriber = None
        self.initUI()
        self.setupSocket()
        self.setupLocalTranscriber()

    def initUI(self):
        self.setWindowTitle('⚡ LiveSpeak')
        self.setGeometry(300, 300, 900, 350)
        self.setMinimumSize(900, 350)

        # Cyberpunk neon theme
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
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header with glitch effect
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setFixedHeight(60)
        header_layout = QVBoxLayout(header_frame)
        
        header_label = QLabel('⚡ LiveSpeak ⚡')
        header_label.setObjectName("headerLabel")
        header_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(header_label)
        
        main_layout.addWidget(header_frame)

        # Main content area
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Transcription panel (left)
        transcript_panel = QFrame()
        transcript_panel.setObjectName("transcriptFrame")
        transcript_layout = QVBoxLayout(transcript_panel)
        transcript_layout.setSpacing(10)

        transcript_header = QLabel('🎤 INPUT STREAM')
        transcript_header.setObjectName("transcriptHeader")
        transcript_header.setAlignment(Qt.AlignCenter)

        self.transcription_label = QLabel('💬 Awaiting neural input...')
        self.transcription_label.setObjectName("transcriptContent")
        self.transcription_label.setWordWrap(True)
        self.transcription_label.setAlignment(Qt.AlignCenter)

        transcript_layout.addWidget(transcript_header)
        transcript_layout.addWidget(self.transcription_label)

        # Translation panel (right)
        translation_panel = QFrame()
        translation_panel.setObjectName("translationFrame")
        translation_layout = QVBoxLayout(translation_panel)
        translation_layout.setSpacing(10)

        translation_header = QLabel('🌍 OUTPUT TRANSLATION')
        translation_header.setObjectName("translationHeader")
        translation_header.setAlignment(Qt.AlignCenter)

        self.translation_label = QLabel('🌐 Decoding...')
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
        
        self.status_label = QLabel('🔴 SYSTEM OFFLINE')
        self.status_label.setObjectName("statusLabel")
        
        version_label = QLabel('v2.0.1 • NEON')
        version_label.setObjectName("statusLabel")
        version_label.setAlignment(Qt.AlignRight)
        
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(version_label)
        
        main_layout.addLayout(status_layout)

        # Window properties
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

    def update_connection_status(self, connected):
        if connected:
            self.setWindowTitle('⚡ NEON CAPTIONS v2.0 • ONLINE')
            self.status_label.setText('🟢 SYSTEM ONLINE')
            self.status_label.setStyleSheet("""
                color: #00ff00;
                border: 1px solid #00ff00;
                background: #1a1f3a;
            """)
        else:
            self.setWindowTitle('⚡ NEON CAPTIONS v2.0 • OFFLINE')
            self.status_label.setText('🔴 SYSTEM OFFLINE')
            self.status_label.setStyleSheet("""
                color: #ff4444;
                border: 1px solid #ff4444;
                background: #1a1f3a;
            """)

    def setupSocket(self):
        self.socket_handler = SocketThread()
        self.socket_handler.transcription_received.connect(self.update_labels)
        self.socket_handler.connection_status.connect(self.update_connection_status)
        
        self.socket_thread = threading.Thread(target=self._connect_socket)
        self.socket_thread.daemon = True
        self.socket_thread.start()

    def setupLocalTranscriber(self):
        try:
            self.local_transcriber = ContinuousTranscriber(target_language='en')
            self.local_transcriber.set_callback(self.on_local_transcription)
            self.local_transcriber.start_transcription()
            logger.info("Local transcriber started")
        except Exception as e:
            logger.error(f"Failed to start local transcriber: {e}")

    def _connect_socket(self):
        success = self.socket_handler.connect_to_server()
        logger.info(f"Socket connection {'successful' if success else 'failed'}")

    def update_labels(self, transcription, translation):
        try:
            self.transcription_label.setText(transcription)
            self.translation_label.setText(translation)
        except Exception as e:
            logger.error(f"Error updating labels: {e}")

    def on_local_transcription(self, transcription, translation=None):
        try:
            if not self.socket_handler or not self.socket_handler.socketio.connected:
                self.transcription_label.setText(transcription)
                self.translation_label.setText('⚡ LOCAL MODE • No translation')
        except Exception as e:
            logger.error(f"Error handling local transcription: {e}")

    def closeEvent(self, event):
        if self.socket_handler:
            self.socket_handler.disconnect()
        if self.local_transcriber:
            self.local_transcriber.stop_transcription()
        super().closeEvent(event)

def run_caption_window():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = CyberCaptionWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    run_caption_window()
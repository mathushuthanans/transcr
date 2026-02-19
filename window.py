import os
os.environ["QT_QPA_PLATFORM"] = "xcb"

import sys
import random
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
    QPushButton, QComboBox, QHBoxLayout, QFrame
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QLinearGradient, QPainter, QColor, QBrush
from model import ContinuousTranscriber

# ---------------- Thread -----------------
class TranslationThread(QObject):
    translation_received = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.transcriber = None
        self.current_language = 'en'

    def handle_translation(self, transcription, translation):
        if translation:
            self.translation_received.emit(translation)
        elif transcription:
            self.translation_received.emit(transcription)

    def start_translation(self, lang):
        lang_map = {'English':'en','Spanish':'es','French':'fr','German':'de','Japanese':'ja','Chinese':'zh'}
        code = lang_map.get(lang,'en')
        self.status_update.emit(f"🎤 Listening → {lang}")
        self.transcriber = ContinuousTranscriber(target_language=code)
        self.transcriber.set_callback(self.handle_translation)
        self.transcriber.start_transcription()

    def stop_translation(self):
        if self.transcriber:
            self.transcriber.stop_transcription()
            self.transcriber=None
            self.status_update.emit("Idle")

# -------- Fancy background widget ----------
class GradientWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.shift = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(40)

    def animate(self):
        self.shift = (self.shift+1)%360
        self.update()

    def paintEvent(self,e):
        painter=QPainter(self)
        grad=QLinearGradient(0,0,self.width(),self.height())
        c1=QColor.fromHsv((self.shift)%360,180,255)
        c2=QColor.fromHsv((self.shift+120)%360,180,255)
        grad.setColorAt(0,c1)
        grad.setColorAt(1,c2)
        painter.fillRect(self.rect(),QBrush(grad))

# -------------- Window ---------------------
class FabWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread=TranslationThread()
        self.typing_timer=QTimer()
        self.typing_timer.timeout.connect(self.type_effect)
        self.full_text=""
        self.displayed=""
        self.initUI()
        self.connectSignals()

    def initUI(self):
        self.setWindowTitle("LinguaFlow ✨ AI Live Translator")
        self.setGeometry(350,200,720,380)
        self.setMinimumSize(720,380)

        bg=GradientWidget()
        self.setCentralWidget(bg)
        layout=QVBoxLayout(bg)
        layout.setSpacing(20)
        layout.setContentsMargins(25,25,25,25)

        title=QLabel("🌍 LinguaFlow")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:34px;font-weight:700;color:white;")
        layout.addWidget(title)

        self.panel=QFrame()
        self.panel.setStyleSheet("background:rgba(0,0,0,120);border-radius:18px;")
        p_layout=QVBoxLayout(self.panel)

        self.text=QLabel("Say something...")
        self.text.setWordWrap(True)
        self.text.setAlignment(Qt.AlignCenter)
        self.text.setStyleSheet("font-size:22px;color:white;padding:20px;")
        p_layout.addWidget(self.text)
        layout.addWidget(self.panel)

        controls=QHBoxLayout()
        self.lang=QComboBox()
        self.lang.addItems(['English','Spanish','French','German','Japanese','Chinese'])

        self.btn=QPushButton("▶ Start")
        self.btn.setCheckable(True)
        self.btn.setStyleSheet("background:rgba(255,255,255,0.25);color:white;border-radius:20px;padding:10px 22px;font-weight:bold;")

        controls.addWidget(self.lang)
        controls.addStretch()
        controls.addWidget(self.btn)
        layout.addLayout(controls)

        self.status=QLabel("Ready")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color:white;font-size:13px;")
        layout.addWidget(self.status)

        self.setWindowFlags(Qt.WindowStaysOnTopHint)

    def connectSignals(self):
        self.btn.clicked.connect(self.toggle)
        self.thread.translation_received.connect(self.startTyping)
        self.thread.status_update.connect(self.status.setText)

    def toggle(self,checked):
        if checked:
            self.btn.setText("⏸ Stop")
            self.thread.start_translation(self.lang.currentText())
        else:
            self.btn.setText("▶ Start")
            self.thread.stop_translation()
            self.text.setText("Say something...")

    # typing animation
    def startTyping(self,text):
        self.full_text=text
        self.displayed=""
        self.typing_timer.start(15)

    def type_effect(self):
        if len(self.displayed)<len(self.full_text):
            self.displayed+=self.full_text[len(self.displayed)]
            self.text.setText(self.displayed)
        else:
            self.typing_timer.stop()


def run():
    app=QApplication(sys.argv)
    win=FabWindow()
    win.show()
    sys.exit(app.exec_())

if __name__=='__main__':
    run()
import sys
import os
import threading
import warnings

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QPushButton, QTextEdit, QFileDialog, QLabel, QComboBox, QHBoxLayout
)
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG, QSize
from PyQt5.QtGui import QMovie, QFont

import speech_recognition as sr
from pydub.utils import which

ffmpeg_path = which("ffmpeg") or r"C:\\ffmpeg\\ffmpeg-7.1.1-essentials_build\\bin\\ffmpeg.exe"
os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_path)

from pydub import AudioSegment
AudioSegment.converter = ffmpeg_path

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)


class SpeechRecognitionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.recording = False
        self.thread = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Speech Recognition System")
        self.setGeometry(150, 100, 1100, 720)

        self.setStyleSheet("""
            QWidget {
                background-color: #1b1f1f;
                color: #d8d8db;
                font-family: Arial;
            }
            QPushButton {
                background-color: #000000;
                color: #d8d8db;
                padding: 15px;
                font-size: 18px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
            }
            QTextEdit {
                background-color: #2a2a2a;
                color: #d8d8db;
                font-size: 16px;
                padding: 15px;
                border-radius: 10px;
            }
            QComboBox {
                background-color: #2a2a2a;
                color: #d8d8db;
                padding: 10px;
                font-size: 16px;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout()

        self.logo_label = QLabel(self)
        self.logo_label.setAlignment(Qt.AlignCenter)
        movie = QMovie("logo.gif")
        movie.setScaledSize(QSize(220, 220))
        self.logo_label.setMovie(movie)
        movie.start()
        layout.addWidget(self.logo_label)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English (US)", "en-US")
        self.lang_combo.addItem("Spanish (Spain)", "es-ES")
        self.lang_combo.addItem("French (France)", "fr-FR")
        self.lang_combo.addItem("Hindi (India)", "hi-IN")
        self.lang_combo.addItem("Chinese (Mandarin)", "zh-CN")
        self.lang_combo.setMinimumHeight(40)
        layout.addWidget(self.lang_combo)

        button_layout = QHBoxLayout()

        self.btn_live = QPushButton("Start Live Recognition")
        self.btn_live.setMinimumHeight(50)
        self.btn_live.setMinimumWidth(250)
        self.btn_live.clicked.connect(self.toggle_live_recognition)
        button_layout.addWidget(self.btn_live)

        self.btn_open = QPushButton("Open Audio File")
        self.btn_open.setMinimumHeight(50)
        self.btn_open.setMinimumWidth(250)
        self.btn_open.clicked.connect(self.open_file)
        button_layout.addWidget(self.btn_open)

        layout.addLayout(button_layout)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Consolas", 16))
        self.text_edit.setMinimumHeight(280)
        layout.addWidget(self.text_edit)

        self.loading_label = QLabel("Listening...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.loading_label.setStyleSheet("color: #d8d8db")
        self.loading_label.hide()
        layout.addWidget(self.loading_label)

        self.setLayout(layout)

    def toggle_live_recognition(self):
        if not self.recording:
            self.recording = True
            self.btn_live.setText("Stop Live Recognition")
            self.thread = threading.Thread(target=self.live_recognition)
            self.thread.start()
        else:
            self.recording = False
            self.btn_live.setText("Start Live Recognition")

    def live_recognition(self):
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source)
                self.set_loading(True)
                while self.recording:
                    try:
                        audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=None)
                        if not self.recording:
                            break
                        lang = self.lang_combo.currentData()
                        text = self.recognizer.recognize_google(audio, language=lang)
                        self.update_text(f"Live ({lang}): {text}")
                    except sr.RequestError as e:
                        self.update_text(f"[API error: {e}]")
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            self.set_loading(False)

    def set_loading(self, visible):
        QMetaObject.invokeMethod(
            self.loading_label,
            "setVisible",
            Qt.QueuedConnection,
            Q_ARG(bool, visible)
        )

    def open_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.mp4 *.flac *.ogg);;All Files (*)",
            options=options
        )
        if file_path:
            threading.Thread(target=self.transcribe_file, args=(file_path,)).start()

    def transcribe_file(self, file_path):
        self.update_text(f"Transcribing: {os.path.basename(file_path)}")
        base, ext = os.path.splitext(file_path)

        if ext.lower() != ".wav":
            sound = AudioSegment.from_file(file_path)
            wav_path = base + "_converted.wav"
            sound.export(wav_path, format="wav")
        else:
            wav_path = file_path

        with sr.AudioFile(wav_path) as source:
            audio = self.recognizer.record(source)
            try:
                lang = self.lang_combo.currentData()
                text = self.recognizer.recognize_google(audio, language=lang)
                self.update_text(f"File ({lang}): {text}")
            except sr.RequestError as e:
                self.update_text(f"[API error: {e}]")
            except Exception as e:
                self.update_text(f"[Error: {e}]\n{str(e)}")

        if ext.lower() != ".wav" and os.path.exists(wav_path):
            os.remove(wav_path)

    def update_text(self, text):
        QMetaObject.invokeMethod(
            self.text_edit,
            "append",
            Qt.QueuedConnection,
            Q_ARG(str, text)
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpeechRecognitionApp()
    window.show()
    sys.exit(app.exec_())
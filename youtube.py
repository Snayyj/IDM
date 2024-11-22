import sys
import os
from pytube import YouTube, exceptions
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QLineEdit, QMessageBox, QApplication)
from PyQt5.QtCore import Qt

class YouTubeDownloader(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Téléchargement YouTube')
        self.setGeometry(300, 300, 500, 300)
        
        layout = QVBoxLayout()
        
        # URL Input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('Coller l\'URL YouTube')
        url_layout.addWidget(self.url_input)
        
        # Bouton Analyser
        analyze_btn = QPushButton('Analyser')
        analyze_btn.clicked.connect(self.analyze_video)
        url_layout.addWidget(analyze_btn)
        
        layout.addLayout(url_layout)
        
        # Informations Vidéo
        self.video_info = QLabel('Aucune vidéo sélectionnée')
        layout.addWidget(self.video_info)
        
        # Sélection Qualité
        quality_layout = QHBoxLayout()
        self.quality_combo = QComboBox()
        quality_layout.addWidget(QLabel('Qualité :'))
        quality_layout.addWidget(self.quality_combo)
        
        layout.addLayout(quality_layout)
        
        # Bouton Téléchargement
        download_btn = QPushButton('Télécharger')
        download_btn.clicked.connect(self.download_video)
        layout.addWidget(download_btn)
        
        self.setLayout(layout)
        self.current_video = None

    def analyze_video(self):
        url = self.url_input.text().strip()
        try:
            yt = YouTube(url)
            self.current_video = yt
            
            # Afficher infos vidéo
            info_text = f"Titre: {yt.title}\n"
            info_text += f"Durée: {yt.length} secondes\n"
            info_text += f"Vues: {yt.views:,}"
            self.video_info.setText(info_text)
            
            # Charger les qualités disponibles
            self.quality_combo.clear()
            streams = yt.streams.filter(progressive=True, file_extension='mp4')
            for stream in streams:
                self.quality_combo.addItem(f"{stream.resolution} ({stream.fps} fps)")
        
        except exceptions.RegexMatchError:
            QMessageBox.warning(self, 'Erreur', 'URL YouTube invalide')
        except Exception as e:
            QMessageBox.critical(self, 'Erreur', str(e))

    def download_video(self):
        if not self.current_video:
            QMessageBox.warning(self, 'Erreur', 'Aucune vidéo sélectionnée')
            return
        
        try:
            selected_quality = self.quality_combo.currentText().split()[0]
            stream = self.current_video.streams.filter(
                progressive=True, 
                file_extension='mp4', 
                resolution=selected_quality
            ).first()
            
            download_folder = os.path.join(os.getcwd(), 'downloads')
            os.makedirs(download_folder, exist_ok=True)
            
            stream.download(output_path=download_folder)
            QMessageBox.information(self, 'Succès', 'Téléchargement terminé')
        
        except Exception as e:
            QMessageBox.critical(self, 'Erreur', str(e))

def main():
    app = QApplication(sys.argv)
    downloader = YouTubeDownloader()
    downloader.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
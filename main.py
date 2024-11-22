import sys
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, QProgressBar, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt

class DownloadThread(QThread):
    progress_signal = pyqtSignal(int, int, float)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.is_running = True
        self.is_paused = False
        self.downloaded_size = 0
        self.last_downloaded_size = 0
        self.speed = 0
        self.total_size = 0

    def run(self):
        try:
            # Configuration avancée de la requête
            headers = {
                'User-Agent': 'Mozilla/5.0',  # Simuler un navigateur
                'Range': f'bytes={self.downloaded_size}-'  # Reprise possible
            }
            
            # Augmenter le timeout et utiliser un stream plus efficace
            response = requests.get(
                self.url, 
                stream=True, 
                headers=headers, 
                timeout=30
            )
            
            self.total_size = int(response.headers.get('content-length', 0))
            block_size = 65536  # 64 Ko (taille de bloc optimisée)
            last_update_time = time.time()

            with open(self.save_path, 'ab') as file:  # Mode append binaire
                for data in response.iter_content(block_size):
                    while self.is_paused:
                        time.sleep(0.1)

                    if not self.is_running:
                        break
                    
                    if data:
                        file.write(data)
                        self.downloaded_size += len(data)
                    
                    current_time = time.time()
                    if current_time - last_update_time >= 1:
                        self.speed = (self.downloaded_size - self.last_downloaded_size) / (current_time - last_update_time)
                        last_update_time = current_time
                        self.last_downloaded_size = self.downloaded_size

                    if self.total_size > 0:
                        progress = int((self.downloaded_size / self.total_size) * 100)
                        self.progress_signal.emit(progress, self.downloaded_size, self.speed)

            self.finished_signal.emit(self.is_running, self.save_path)
        
        except requests.exceptions.RequestException as e:
            self.finished_signal.emit(False, str(e))

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.is_running = False
        self.wait()

class DownloadManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Download Manager Pro')
        self.setGeometry(100, 100, 1000, 600)
        
        # Gestionnaire de téléchargements simultanés
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.download_threads = []

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Barre d'URL
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('Coller l\'URL du fichier à télécharger')
        url_layout.addWidget(self.url_input)

        self.download_button = QPushButton('Télécharger')
        self.download_button.clicked.connect(self.start_download)
        url_layout.addWidget(self.download_button)

        layout.addLayout(url_layout)

        # Tableau de téléchargement
        self.download_table = QTableWidget()
        self.download_table.setColumnCount(6)
        self.download_table.setHorizontalHeaderLabels(['Fichier', 'URL', 'Progression', 'Taille', 'Vitesse', 'Actions'])
        layout.addWidget(self.download_table)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, 'Erreur', 'Veuillez entrer une URL valide')
            return

        try:
            # Vérifier la validité du lien avant téléchargement
            response = requests.head(url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            QMessageBox.critical(self, 'Erreur', 'Impossible de télécharger ce fichier')
            return

        filename = os.path.basename(url)
        save_path = os.path.join(os.getcwd(), filename)

        row = self.download_table.rowCount()
        self.download_table.insertRow(row)
        self.download_table.setItem(row, 0, QTableWidgetItem(filename))
        self.download_table.setItem(row, 1, QTableWidgetItem(url))

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        self.download_table.setCellWidget(row, 2, progress_bar)

        # Actions de téléchargement
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        
        pause_button = QPushButton('Pause')
        cancel_button = QPushButton('Annuler')
        
        action_layout.addWidget(pause_button)
        action_layout.addWidget(cancel_button)
        action_layout.setContentsMargins(0, 0, 0, 0)
        
        self.download_table.setCellWidget(row, 5, action_widget)

        download_thread = DownloadThread(url, save_path)
        download_thread.progress_signal.connect(
            lambda p, s, speed, row=row: self.update_progress(row, p, s, speed)
        )
        download_thread.finished_signal.connect(
            lambda success, path, row=row: self.download_finished(row, success, path)
        )
        
        pause_button.clicked.connect(lambda checked, thread=download_thread, btn=pause_button: self.toggle_pause(thread, btn))
        cancel_button.clicked.connect(lambda checked, thread=download_thread: self.cancel_download(thread))
        
        download_thread.start()
        self.download_threads.append(download_thread)

    def update_progress(self, row, progress, size, speed):
        progress_bar = self.download_table.cellWidget(row, 2)
        progress_bar.setValue(progress)
        
        size_item = QTableWidgetItem(f'{size/1024:.1f} Ko')
        self.download_table.setItem(row, 3, size_item)
        
        speed_item = QTableWidgetItem(f'{speed/1024:.1f} Ko/s')
        self.download_table.setItem(row, 4, speed_item)

    def toggle_pause(self, thread, button):
        if button.text() == 'Pause':
            thread.pause()
            button.setText('Reprendre')
        else:
            thread.resume()
            button.setText('Pause')

    def download_finished(self, row, success, path):
        status = 'Terminé' if success else 'Erreur'
        status_item = QTableWidgetItem(status)
        self.download_table.setItem(row, 4, status_item)

    def cancel_download(self, thread):
        thread.stop()

    def closeEvent(self, event):
        for thread in self.download_threads:
            thread.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    manager = DownloadManager()
    manager.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
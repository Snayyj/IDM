import sys
import re
import requests
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QMessageBox, QLabel, QComboBox, QApplication, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class LinkExtractionThread(QThread):
    extraction_complete = pyqtSignal(list)
    progress_updated = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self, url, extraction_type):
        super().__init__()
        self.url = url
        self.extraction_type = extraction_type

    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = []
            if self.extraction_type == 'Tous les liens':
                elements = soup.find_all('a', href=True)
            elif self.extraction_type == 'Images':
                elements = soup.find_all('img', src=True)
            elif self.extraction_type == 'Vidéos':
                elements = soup.find_all('video', src=True)
            elif self.extraction_type == 'Documents':
                document_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
                elements = [
                    a for a in soup.find_all('a', href=True)
                    if any(ext in str(a.get('href')) for ext in document_extensions)
                ]
            
            total_elements = len(elements)
            for i, elem in enumerate(elements, start=1):
                link = elem.get('href') if self.extraction_type != 'Images' else elem.get('src')
                if link:
                    if not link.startswith(('http', 'https')):
                        link = requests.compat.urljoin(self.url, link)
                    links.append(link)
                
                # Mettre à jour la progression
                self.progress_updated.emit(int((i / total_elements) * 100))

            self.extraction_complete.emit(links)
        
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(str(e))

class LinkExtractor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Extracteur de Liens')
        self.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout()
        
        # URL Input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('Entrez l\'URL à explorer')
        url_layout.addWidget(self.url_input)
        
        # Type d'extraction
        self.extraction_type = QComboBox()
        self.extraction_type.addItems([
            'Tous les liens', 
            'Images', 
            'Vidéos', 
            'Documents'
        ])
        url_layout.addWidget(self.extraction_type)
        
        extract_btn = QPushButton('Extraire')
        extract_btn.clicked.connect(self.start_extraction)
        url_layout.addWidget(extract_btn)
        
        layout.addLayout(url_layout)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Indication d'état
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold; color: blue;")
        layout.addWidget(self.status_label)
        
        # Résultats
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(['Lien', 'Type'])
        layout.addWidget(self.results_table)
        
        self.setLayout(layout)

    def start_extraction(self):
        url = self.url_input.text().strip()
        extraction_type = self.extraction_type.currentText()
        
        if not url:
            QMessageBox.warning(self, 'Erreur', 'URL invalide')
            return
        
        self.results_table.setRowCount(0)
        self.progress_bar.setValue(0)
        
        # Mettre à jour le label d'état
        self.status_label.setText("Extraction en cours...")
        self.status_label.setStyleSheet("font-weight: bold; color: orange;")
        
        # Lancer l'extraction dans un thread
        self.extraction_thread = LinkExtractionThread(url, extraction_type)
        self.extraction_thread.extraction_complete.connect(self.display_results)
        self.extraction_thread.progress_updated.connect(self.update_progress)
        self.extraction_thread.error_occurred.connect(self.handle_error)
        self.extraction_thread.finished.connect(self.reset_status)  # Réinitialiser le statut après extraction
        self.extraction_thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def display_results(self, links):
        self.results_table.setRowCount(0)
        for link in links:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(link))
            self.results_table.setItem(row, 1, QTableWidgetItem(self.extraction_type.currentText()))
        self.status_label.setText("Extraction terminée avec succès !")
        self.status_label.setStyleSheet("font-weight: bold; color: green;")

    def handle_error(self, error_message):
        self.status_label.setText("Erreur lors de l'extraction.")
        self.status_label.setStyleSheet("font-weight: bold; color: red;")
        QMessageBox.critical(self, 'Erreur', error_message)

    def reset_status(self):
        if not self.results_table.rowCount():
            self.status_label.setText("Aucun résultat trouvé.")
            self.status_label.setStyleSheet("font-weight: bold; color: gray;")

def main():
    app = QApplication(sys.argv)
    extractor = LinkExtractor()
    extractor.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

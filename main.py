import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel,
                             QFileDialog, QMessageBox, QListWidget)
from PyQt5.QtCore import QTimer
from sftp_client import SftpClient

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.synchronize)
        self.timer.start(1 * 60 * 1000)  # 1 minuto in millisecondi

    def initUI(self):
        layout = QVBoxLayout()

        self.host_label = QLabel("SFTP Host:")
        self.host_line_edit = QLineEdit()

        self.port_label = QLabel("SFTP Port:")
        self.port_line_edit = QLineEdit()
        self.port_line_edit.setText("22")  # Porta predefinita

        self.username_label = QLabel("Username:")
        self.username_line_edit = QLineEdit()

        self.password_label = QLabel("Password:")
        self.password_line_edit = QLineEdit()
        self.password_line_edit.setEchoMode(QLineEdit.Password)

        self.local_dir_label = QLabel("Local Directory:")
        self.local_dir_line_edit = QLineEdit()
        self.local_dir_button = QPushButton("Choose...")

        self.remote_dir_label = QLabel("Remote Directory:")
        self.remote_dir_line_edit = QLineEdit()

        self.file_list = QListWidget()

        self.sync_button = QPushButton("Synchronize Now")
        self.test_conn_button = QPushButton("Test Connection")  # Pulsante di test connessione

        layout.addWidget(self.host_label)
        layout.addWidget(self.host_line_edit)
        layout.addWidget(self.port_label)
        layout.addWidget(self.port_line_edit)
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_line_edit)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_line_edit)
        layout.addWidget(self.local_dir_label)
        layout.addWidget(self.local_dir_line_edit)
        layout.addWidget(self.local_dir_button)
        layout.addWidget(self.remote_dir_label)
        layout.addWidget(self.remote_dir_line_edit)
        layout.addWidget(self.file_list)
        layout.addWidget(self.sync_button)
        layout.addWidget(self.test_conn_button)  # Aggiungi il pulsante alla UI

        self.setLayout(layout)

        self.local_dir_button.clicked.connect(self.choose_local_directory)
        self.sync_button.clicked.connect(self.synchronize)
        self.test_conn_button.clicked.connect(self.test_connection)  # Connetti il pulsante alla funzione

    def choose_local_directory(self):
        dir = QFileDialog.getExistingDirectory(self, "Choose Directory", "",
                                               QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if dir:
            self.local_dir_line_edit.setText(dir)

    def synchronize(self):
        local_dir = self.local_dir_line_edit.text()
        remote_dir = self.remote_dir_line_edit.text()
        host = self.host_line_edit.text()
        port = int(self.port_line_edit.text())
        username = self.username_line_edit.text()
        password = self.password_line_edit.text()

        if not local_dir or not remote_dir or not host or not username or not password:
            QMessageBox.warning(self, "Warning", "All fields must be specified.")
            return

        try:
            print(f"Connecting to {host}:{port} with username {username}")
            print(f"Local directory: {local_dir}")
            print(f"Remote directory: {remote_dir}")
            sftp_client = SftpClient(host, port, username, password)
            sftp_client.connect()
            print("Connection successful")
            sftp_client.synchronize_and_clear_local(local_dir, remote_dir)
            files = sftp_client.list_files(remote_dir)
            self.file_list.clear()
            self.file_list.addItems(files)
            sftp_client.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            print(f"Error: {e}")

    def test_connection(self):
        host = self.host_line_edit.text()
        port = int(self.port_line_edit.text())
        username = self.username_line_edit.text()
        password = self.password_line_edit.text()

        if not host or not username or not password:
            QMessageBox.warning(self, "Warning", "Host, username, and password must be specified.")
            return

        try:
            print(f"Testing connection to {host}:{port} with username {username}")
            sftp_client = SftpClient(host, port, username, password)
            sftp_client.connect()
            QMessageBox.information(self, "Success", "Connection successful!")
            print("Connection successful")
            sftp_client.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection failed: {e}")
            print(f"Connection failed: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.setWindowTitle("SFTP Synchronization")
    mainWin.resize(400, 400)  # Modificato per accogliere i nuovi campi di input
    mainWin.show()
    sys.exit(app.exec_())

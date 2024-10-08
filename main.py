import sys
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QLineEdit, QLabel,
                             QFileDialog, QMessageBox, QDialog, QFormLayout, QHBoxLayout,
                             QVBoxLayout, QGridLayout, QRadioButton, QComboBox, QPlainTextEdit)
from PyQt5.QtCore import QTimer
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sftp_client import SftpClient

class EmailSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Email Settings")
        layout = QFormLayout(self)
        
        self.smtpServerLineEdit = QLineEdit(self)
        self.smtpPortLineEdit = QLineEdit(self)
        self.usernameLineEdit = QLineEdit(self)
        self.passwordLineEdit = QLineEdit(self)
        self.passwordLineEdit.setEchoMode(QLineEdit.Password)
        self.recipientLineEdit = QLineEdit(self)
        
        layout.addRow("SMTP Server:", self.smtpServerLineEdit)
        layout.addRow("SMTP Port:", self.smtpPortLineEdit)
        layout.addRow("Username:", self.usernameLineEdit)
        layout.addRow("Password:", self.passwordLineEdit)
        layout.addRow("Recipient Email:", self.recipientLineEdit)
        
        self.testButton = QPushButton("Send Test Email", self)
        self.testButton.clicked.connect(self.send_test_email)
        self.saveButton = QPushButton("Save", self)
        self.saveButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel", self)
        self.cancelButton.clicked.connect(self.reject)
        
        layout.addRow(self.testButton)
        layout.addRow(self.saveButton, self.cancelButton)

    def getDetails(self):
        return {
            "server": self.smtpServerLineEdit.text(),
            "port": self.smtpPortLineEdit.text(),
            "username": self.usernameLineEdit.text(),
            "password": self.passwordLineEdit.text(),
            "recipient": self.recipientLineEdit.text()
        }

    def send_test_email(self):
        settings = self.getDetails()
        msg = MIMEMultipart()
        msg['From'] = settings["username"]
        msg['To'] = settings["recipient"]
        msg['Subject'] = "Test invio FTP Bizpal"
        msg.attach(MIMEText("Invio email riuscito", 'plain'))
        try:
            server = smtplib.SMTP(settings["server"], settings["port"])
            server.starttls()
            server.login(settings["username"], settings["password"])
            server.sendmail(msg['From'], msg['To'], msg.as_string())
            server.quit()
            QMessageBox.information(self, "Test Email", "Test email sent successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Test Email", f"Failed to send test email: {e}")

class MainWindow(QWidget):
    open_windows = []

    def __init__(self):
        super().__init__()
        MainWindow.open_windows.append(self)
        self.setWindowTitle("FTP Bizpal")
        self.email_settings = {}
        self.initUI()
        self.setupTimer()

    def initUI(self):
        grid = QGridLayout()
        self.setLayout(grid)

        self.direction_group = QHBoxLayout()
        self.to_remote_button = QRadioButton("Local to Remote")
        self.to_remote_button.setChecked(True)
        self.to_local_button = QRadioButton("Remote to Local")
        self.direction_group.addWidget(self.to_remote_button)
        self.direction_group.addWidget(self.to_local_button)
        grid.addLayout(self.direction_group, 0, 0, 1, 3)

        self.host_label = QLabel("SFTP Host:")
        self.host_line_edit = QLineEdit()
        self.port_label = QLabel("SFTP Port:")
        self.port_line_edit = QLineEdit("22")
        self.username_label = QLabel("Username:")
        self.username_line_edit = QLineEdit()
        self.password_label = QLabel("Password:")
        self.password_line_edit = QLineEdit()
        self.password_line_edit.setEchoMode(QLineEdit.Password)

        self.local_dir_label = QLabel("Local Directory:")
        self.local_dir_line_edit = QLineEdit()
        self.local_dir_button = QPushButton("Choose...")
        self.local_dir_button.clicked.connect(self.choose_local_directory)

        self.remote_dir_label = QLabel("Remote Directory:")
        self.remote_dir_line_edit = QLineEdit()
        self.sync_button = QPushButton("Sync Now")
        self.sync_button.clicked.connect(self.sync_files)
        self.test_connection_button = QPushButton("Test Connection")
        self.test_connection_button.clicked.connect(self.test_connection)

        self.emailSettingsButton = QPushButton("Email Settings")
        self.emailSettingsButton.clicked.connect(self.openEmailSettingsDialog)
        self.newWindowButton = QPushButton("New Window")
        self.newWindowButton.clicked.connect(self.open_new_window)
        self.saveConfigButton = QPushButton("Save Configuration")
        self.saveConfigButton.clicked.connect(self.save_configuration)
        self.loadConfigButton = QPushButton("Load Configuration")
        self.loadConfigButton.clicked.connect(self.load_configuration)

        self.timerLabel = QLabel("Timer Interval:")
        self.timerComboBox = QComboBox()
        self.timerComboBox.addItems(["1 minutes", "5 minutes", "10 minutes", "30 minutes", "1 hour", "2 hours"])
        self.timerComboBox.currentIndexChanged.connect(self.update_timer_interval)

        self.log_window = QPlainTextEdit()
        self.log_window.setReadOnly(True)
        self.clearLogButton = QPushButton("Clear Logs")
        self.clearLogButton.clicked.connect(self.clear_logs)

        grid.addWidget(self.host_label, 1, 0)
        grid.addWidget(self.host_line_edit, 1, 1)
        grid.addWidget(self.port_label, 2, 0)
        grid.addWidget(self.port_line_edit, 2, 1)
        grid.addWidget(self.username_label, 3, 0)
        grid.addWidget(self.username_line_edit, 3, 1)
        grid.addWidget(self.password_label, 4, 0)
        grid.addWidget(self.password_line_edit, 4, 1)
        grid.addWidget(self.local_dir_label, 5, 0)
        grid.addWidget(self.local_dir_line_edit, 5, 1)
        grid.addWidget(self.local_dir_button, 5, 2)
        grid.addWidget(self.remote_dir_label, 6, 0)
        grid.addWidget(self.remote_dir_line_edit, 6, 1)
        grid.addWidget(self.sync_button, 7, 0)
        grid.addWidget(self.test_connection_button, 7, 1)
        grid.addWidget(self.emailSettingsButton, 8, 0)
        grid.addWidget(self.newWindowButton, 8, 1)
        grid.addWidget(self.saveConfigButton, 8, 2)
        grid.addWidget(self.loadConfigButton, 9, 0)
        grid.addWidget(self.timerLabel, 9, 1)
        grid.addWidget(self.timerComboBox, 9, 2)
        grid.addWidget(self.clearLogButton, 10, 0)
        grid.addWidget(self.log_window, 11, 0, 1, 3)

    def open_new_window(self):
        new_win = MainWindow()
        new_win.show()

    def setupTimer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sync_files)
        self.timer.start(300000)  # Default to 5 minutes

    def openEmailSettingsDialog(self):
        dialog = EmailSettingsDialog(self)
        if dialog.exec_():
            self.email_settings = dialog.getDetails()
            self.append_log("Email settings updated.")

    def update_timer_interval(self):
        interval_text = self.timerComboBox.currentText()
        intervals = {
            "1 minutes": 60000,
            "5 minutes": 300000,
            "10 minutes": 600000,
            "30 minutes": 1800000,
            "1 hour": 3600000,
            "2 hours": 7200000
        }
        self.timer.start(intervals[interval_text])
        self.append_log(f"Timer interval set to {interval_text}")

    def choose_local_directory(self):
        dir = QFileDialog.getExistingDirectory(self, "Choose Directory", "",
                                               QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if dir:
            self.local_dir_line_edit.setText(dir)
            self.append_log(f"Local directory chosen: {dir}")

    def sync_files(self):
        self.append_log("Starting synchronization...")
        direction = "to_remote" if self.to_remote_button.isChecked() else "to_local"
        try:
            sftp_client = SftpClient(self.host_line_edit.text(), int(self.port_line_edit.text()),
                                     self.username_line_edit.text(), self.password_line_edit.text(),
                                     self.append_log)
            sftp_client.connect()
            if direction == "to_remote":
                files_transferred = sftp_client.upload_from_local_to_remote(self.local_dir_line_edit.text(),
                                                                            self.remote_dir_line_edit.text())
            else:
                files_transferred = sftp_client.synchronize_and_clear_remote(self.remote_dir_line_edit.text(),
                                                                             self.local_dir_line_edit.text())
            sftp_client.close()
            if files_transferred:
                self.append_log(f"Files transferred: {', '.join(files_transferred)}")
                self.send_email(files_transferred, direction)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.append_log(f"Error: {e}")

    def test_connection(self):
        try:
            self.append_log("Testing connection...")
            sftp_client = SftpClient(self.host_line_edit.text(), int(self.port_line_edit.text()),
                                     self.username_line_edit.text(), self.password_line_edit.text(),
                                     self.append_log)
            sftp_client.connect()
            sftp_client.close()
            QMessageBox.information(self, "Success", "Connection successful!")
            self.append_log("Connection successful")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection failed: {e}")
            self.append_log(f"Connection failed: {e}")

    def send_email(self, files_transferred, direction):
        if not self.email_settings:
            QMessageBox.warning(self, "Email Settings", "Please configure your email settings first.")
            return
        subject = "File Upload Notification" if direction == "to_remote" else "File Download Notification"
        body = f"The following files have been {'uploaded' if direction == 'to_remote' else 'downloaded'} successfully:\n\n" + "\n".join(files_transferred)
        msg = MIMEMultipart()
        msg['From'] = self.email_settings.get("username")
        msg['To'] = self.email_settings.get("recipient")
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        try:
            server = smtplib.SMTP(self.email_settings.get("server"), self.email_settings.get("port"))
            server.starttls()
            server.login(self.email_settings.get("username"), self.email_settings.get("password"))
            server.sendmail(msg['From'], msg['To'], msg.as_string())
            server.quit()
            self.append_log("Email sent successfully")
        except Exception as e:
            self.append_log(f"Failed to send email: {e}")

    def clear_logs(self):
        self.log_window.clear()
        self.append_log("Log cleared.")

    def append_log(self, message):
        current_time = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{current_time}] {message}"
        self.log_window.appendPlainText(log_message)

    def save_configuration(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Configuration", "", "JSON Files (*.json)")
        if path:
            config = {
                "sftp_host": self.host_line_edit.text(),
                "sftp_port": self.port_line_edit.text(),
                "sftp_username": self.username_line_edit.text(),
                "sftp_password": self.password_line_edit.text(),
                "local_dir": self.local_dir_line_edit.text(),
                "remote_dir": self.remote_dir_line_edit.text(),
                "email_settings": self.email_settings,
                "direction": "to_remote" if self.to_remote_button.isChecked() else "to_local"
            }
            with open(path, 'w') as file:
                json.dump(config, file, indent=4)
            self.append_log("Configuration saved successfully to " + path)

    def load_configuration(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Configuration", "", "JSON Files (*.json)")
        if path:
            with open(path, 'r') as file:
                config = json.load(file)
            self.host_line_edit.setText(config.get('sftp_host', ''))
            self.port_line_edit.setText(config.get('sftp_port', '22'))
            self.username_line_edit.setText(config.get('sftp_username', ''))
            self.password_line_edit.setText(config.get('sftp_password', ''))
            self.local_dir_line_edit.setText(config.get('local_dir', ''))
            self.remote_dir_line_edit.setText(config.get('remote_dir', ''))
            self.email_settings = config.get('email_settings', {})
            if config.get('direction') == "to_remote":
                self.to_remote_button.setChecked(True)
            else:
                self.to_local_button.setChecked(False)
            self.append_log("Configuration loaded from " + path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())

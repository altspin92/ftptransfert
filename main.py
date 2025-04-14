import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QLineEdit, QLabel,
                             QFileDialog, QMessageBox, QDialog, QFormLayout, QHBoxLayout,
                             QVBoxLayout, QGridLayout, QRadioButton, QComboBox, QPlainTextEdit, QCheckBox)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon, QPalette, QColor, QPixmap, QPainter, QBrush
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import shutil

from sftp_client import SftpClient

TRANSFER_LOG_FILE = "transfer_log.json"

def load_transfer_log():
    if os.path.exists(TRANSFER_LOG_FILE):
        with open(TRANSFER_LOG_FILE, "r") as file:
            return json.load(file)
    return {}

def save_transfer_log(log):
    with open(TRANSFER_LOG_FILE, "w") as file:
        json.dump(log, file, indent=4)

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
        self.setWindowIcon(QIcon('logo.jpeg'))
        self.email_settings = {}
        self.existing_files = set()
        self.initUI()
        self.update_status_circle(False)
        self.setupTimer()

        

        self.setup_daily_report()
        #aggiunta nome processo

    def update_window_title(self):
        process_name = self.process_name_line_edit.text().strip()
        self.setWindowTitle(f"FTP Bizpal - {process_name}" if process_name else "FTP Bizpal")


    def initUI(self):
        grid = QGridLayout()
        self.setLayout(grid)

        # Status circle indicator
        self.status_label = QLabel()
        self.update_status_circle(False)
        grid.addWidget(self.status_label, 0, 2)

        # Radio buttons for transfer type
        self.direction_group = QHBoxLayout()
        self.to_remote_button = QRadioButton("Locale a Remoto")
        self.to_remote_button.setChecked(True)
        self.to_local_button = QRadioButton("Remoto a Locale")
        self.to_local_local_button = QRadioButton("Locale su Locale")

        self.direction_group.addWidget(self.to_remote_button)
        self.direction_group.addWidget(self.to_local_button)
        self.direction_group.addWidget(self.to_local_local_button)
        grid.addLayout(self.direction_group, 0, 0, 1, 2)

        # SFTP configuration inputs
        self.host_label = QLabel("SFTP Host:")
        self.host_line_edit = QLineEdit()
        self.port_label = QLabel("SFTP Port:")
        self.port_line_edit = QLineEdit("22")
        self.username_label = QLabel("Username:")
        self.username_line_edit = QLineEdit()
        self.password_label = QLabel("Password:")
        self.password_line_edit = QLineEdit()
        self.password_line_edit.setEchoMode(QLineEdit.Password)

        grid.addWidget(self.host_label, 1, 0)
        grid.addWidget(self.host_line_edit, 1, 1)
        grid.addWidget(self.port_label, 2, 0)
        grid.addWidget(self.port_line_edit, 2, 1)

        grid.addWidget(self.username_label, 3, 0)
        grid.addWidget(self.username_line_edit, 3, 1)
        grid.addWidget(self.password_label, 4, 0)
        grid.addWidget(self.password_line_edit, 4, 1)

        # Local and Remote Directory inputs
        self.local_dir_label = QLabel("Cartella Locale:")
        self.local_dir_line_edit = QLineEdit()
        self.local_dir_button = QPushButton("Cerca")
        self.local_dir_button.clicked.connect(self.choose_local_directory)

        self.remote_dir_label = QLabel("Cartella Remota:")
        self.remote_dir_line_edit = QLineEdit()

        grid.addWidget(self.local_dir_label, 5, 0)
        grid.addWidget(self.local_dir_line_edit, 5, 1)
        grid.addWidget(self.local_dir_button, 5, 2)

        grid.addWidget(self.remote_dir_label, 6, 0)
        grid.addWidget(self.remote_dir_line_edit, 6, 1)

        # Action buttons
        self.sync_button = QPushButton("Sync Now")
        self.sync_button.clicked.connect(self.sync_files)
        self.test_connection_button = QPushButton("Test Connection")
        self.test_connection_button.clicked.connect(self.test_connection)

        grid.addWidget(self.sync_button, 7, 0)
        grid.addWidget(self.test_connection_button, 7, 1)

        self.emailSettingsButton = QPushButton("Email Settings")
        self.emailSettingsButton.clicked.connect(self.openEmailSettingsDialog)
        self.newWindowButton = QPushButton("Nuova Finestra")
        self.newWindowButton.clicked.connect(self.open_new_window)
        self.saveConfigButton = QPushButton("Salva Configurazione")
        self.saveConfigButton.clicked.connect(self.save_configuration)
        self.loadConfigButton = QPushButton("Carica Configurazione")
        self.loadConfigButton.clicked.connect(self.load_configuration)

        grid.addWidget(self.emailSettingsButton, 8, 0)
        grid.addWidget(self.newWindowButton, 8, 1)
        grid.addWidget(self.saveConfigButton, 8, 2)
        grid.addWidget(self.loadConfigButton, 9, 0)

        # Timer and log controls
        self.delete_after_transfer_checkbox = QCheckBox("Cancella il file una volta trasferito")
        self.transfer_new_files_only_checkbox = QCheckBox("Trasferisci solo i file nuovi")

        self.timerLabel = QLabel("Timer Interval:")
        self.timerComboBox = QComboBox()
        self.timerComboBox.addItems([
            "1 minuto", "5 minuti", "10 minuti", "30 minuti", "1 ora", "2 ore",
            "3 ore", "5 ore", "6 ore", "10 ore", "12 ore", "18 ore", "24 ore"
        ])
        self.timerComboBox.currentIndexChanged.connect(self.update_timer_interval)

        grid.addWidget(self.timerLabel, 9, 1)
        grid.addWidget(self.timerComboBox, 9, 2)
        grid.addWidget(self.delete_after_transfer_checkbox, 10, 0)
        grid.addWidget(self.transfer_new_files_only_checkbox, 10, 1)

        self.clearLogButton = QPushButton("Pulisci log")
        self.clearLogButton.clicked.connect(self.clear_logs)

        self.log_window = QPlainTextEdit()
        self.log_window.setReadOnly(True)

        grid.addWidget(self.clearLogButton, 10, 2)
        grid.addWidget(self.log_window, 11, 0, 1, 3)

    def setupTimer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sync_files)
        self.timer.start(30000)  # Default to 30 seconds

    def update_status_circle(self, active):
        print(f"Updating status circle to: {'green' if active else 'red'}")
        pixmap = QPixmap(20, 20)  # Crea un pixmap di dimensioni 20x20
        pixmap.fill(Qt.transparent)  # Rende il background trasparente
        painter = QPainter(pixmap)
        painter.setBrush(QColor("green") if active else QColor("red"))
        painter.setPen(Qt.NoPen)  # Rimuove il bordo
        painter.drawEllipse(0, 0, 20, 20)  # Disegna un cerchio
        painter.end()
        self.status_label.setPixmap(pixmap)
        self.status_label.repaint()

    #metodo di racoglimento log ultime 24 ore
    def get_recent_logs(self):
        """Ritorna i log delle ultime 24 ore."""
        logs = self.log_window.toPlainText().split("\n")
        recent_logs = []
        now = datetime.now()
        for log in logs:
            if log.startswith("["):
                try:
                    log_time = datetime.strptime(log[1:9], "%H:%M:%S")
                    if (now - log_time).total_seconds() <= 86400:  # Ultime 24 ore
                        recent_logs.append(log)
                except ValueError:
                    continue
        return recent_logs



    def sync_files(self):
        self.append_log("Starting synchronization...")
        self.update_status_circle(True)
        QApplication.processEvents()

        direction = "to_remote" if self.to_remote_button.isChecked() else "to_local"
        transfer_log = load_transfer_log()

        try:
            sftp_client = SftpClient(
                self.host_line_edit.text(),
                int(self.port_line_edit.text()),
                self.username_line_edit.text(),
                self.password_line_edit.text(),
                log_callback=self.append_log
                #self.append_log
            )
            sftp_client.connect()

            files_transferred = []

            if direction == "to_local":
                remote_files = sftp_client.list_files(self.remote_dir_line_edit.text())
                for file_attr in remote_files:
                    file_name = file_attr.filename
                    if file_name in transfer_log.get("to_local", []):
                        self.append_log(f"File already transferred: {file_name}")
                        continue

                    remote_file_path = os.path.join(self.remote_dir_line_edit.text(), file_name)
                    local_file_path = os.path.join(self.local_dir_line_edit.text(), file_name)

                    try:
                        sftp_client.download_file(remote_file_path, local_file_path)
                        transfer_log.setdefault("to_local", []).append(file_name)
                        save_transfer_log(transfer_log)
                        files_transferred.append(file_name)
                        self.append_log(f"Downloaded file: {remote_file_path} to {local_file_path}")

                        if self.delete_after_transfer_checkbox.isChecked():
                            sftp_client.remove_file(remote_file_path)
                            self.append_log(f"Deleted remote file: {remote_file_path}")
                    except Exception as e:
                        self.append_log(f"Failed to download file {remote_file_path}: {e}")

            sftp_client.close()

            if files_transferred:
                self.append_log(f"Files transferred: {', '.join(files_transferred)}")
            else:
                self.append_log("No new files were transferred.")

        except Exception as e:
            self.append_log(f"Error during synchronization: {e}")

        finally:
            self.update_status_circle(False)



    # Resto delle funzioni


    def open_new_window(self):  # Aggiunta la funzione per aprire una nuova finestra
        new_window = MainWindow()
        new_window.show()

    def openEmailSettingsDialog(self):
        dialog = EmailSettingsDialog(self)
        if dialog.exec_():
            self.email_settings = dialog.getDetails()
            self.append_log("Email settings updated.")

    def update_timer_interval(self):
        interval_text = self.timerComboBox.currentText()
        intervals = {
            "1 minuto": 60000,
            "5 minuti": 300000,
            "10 minuti": 600000,
            "30 minuti": 1800000,
            "1 ora": 3600000,
            "2 ore": 7200000,
            "3 ore": 10800000,
            "5 ore": 18000000,
            "6 ore": 21600000,
            "10 ore": 36000000,
            "12 ore": 43200000,
            "18 ore": 64800000,
            "24 ore": 86400000
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
        self.update_status_circle(True)
        QApplication.processEvents()
        direction = "to_remote" if self.to_remote_button.isChecked() else ("to_local" if self.to_local_button.isChecked() else "local_to_local")
        transfer_log = load_transfer_log()

        try:
            if direction == "local_to_local":
                self.local_to_local_transfer()
            else:
                sftp_client = SftpClient(
                    self.host_line_edit.text(),
                    int(self.port_line_edit.text()),
                    self.username_line_edit.text(),
                    self.password_line_edit.text(),
                    self.append_log,
                )
                sftp_client.connect()

                files_transferred = []

                if direction == "to_remote":
                    local_files = os.listdir(self.local_dir_line_edit.text())
                    for file_name in local_files:
                        if file_name in transfer_log.get("to_remote", []):
                            self.append_log(f"File already transferred: {file_name}")
                            continue

                        local_file_path = os.path.join(self.local_dir_line_edit.text(), file_name)
                        remote_file_path = os.path.join(self.remote_dir_line_edit.text(), file_name)

                        try:
                            sftp_client.upload_file(local_file_path, remote_file_path)
                            transfer_log.setdefault("to_remote", []).append(file_name)
                            save_transfer_log(transfer_log)
                            files_transferred.append(file_name)
                            self.append_log(f"Uploaded file: {local_file_path} to {remote_file_path}")

                            if self.delete_after_transfer_checkbox.isChecked():
                                os.remove(local_file_path)
                                self.append_log(f"Deleted file {local_file_path} after upload.")
                        except Exception as e:
                            self.append_log(f"Failed to upload {file_name}: {e}")
                elif direction == "to_local":
                            remote_files = sftp_client.list_files(self.remote_dir_line_edit.text())
                for file_attr in remote_files:
                    file_name = file_attr.filename
                    if file_name in transfer_log.get("to_local", []):
                        self.append_log(f"File already transferred: {file_name}")
                        continue

                    remote_file_path = os.path.join(self.remote_dir_line_edit.text(), file_name)
                    local_file_path = os.path.join(self.local_dir_line_edit.text(), file_name)

                    try:
                        sftp_client.download_file(remote_file_path, local_file_path)
                        transfer_log.setdefault("to_local", []).append(file_name)
                        save_transfer_log(transfer_log)
                        files_transferred.append(file_name)
                        self.append_log(f"Downloaded file: {remote_file_path} to {local_file_path}")

                        if self.delete_after_transfer_checkbox.isChecked():
                            sftp_client.remove_file(remote_file_path)
                            self.append_log(f"Deleted remote file {remote_file_path} after download.")
                    except Exception as e:
                        self.append_log(f"Failed to download {file_name}: {e}")

                sftp_client.close()
                # Invia email con i file trasferiti
                if files_transferred:
                    self.send_email_with_logs(files_transferred, direction)
                else:
                    self.append_log("No new files were transferred.")

        except Exception as e:
            self.append_log(f"Error during synchronization: {e}")
        finally:
            self.update_status_circle(False)

    def send_email_with_logs(self, files_transferred, direction):
        if not self.email_settings:
            QMessageBox.warning(self, "Email Settings", "Please configure your email settings first.")
            return
        subject = "File Transfer Notification" if direction == "to_remote" else "File Download Notification"
        body = f"The following files have been {'uploaded' if direction == 'to_remote' else 'downloaded'} successfully:\n\n" + "\n".join(files_transferred)

        # Aggiungi log recenti alla email
        recent_logs = self.get_recent_logs()
        if recent_logs:
            body += "\n\nRecent Logs:\n" + recent_logs

        self._send_email(subject, body)

    def get_recent_logs(self):
        """Estrai le ultime righe dei log (es. ultime 20 righe)"""
        log_text = self.log_window.toPlainText()
        recent_logs = "\n".join(log_text.splitlines()[-20:])  # Ultime 20 righe
        return recent_logs

    def _send_email(self, subject, body):
        if not self.email_settings:
            self.append_log("Email not configured.")
            return

        # Converti il corpo in stringa se è una lista
        if isinstance(body, list):
            body = "\n".join(body)

        msg = MIMEMultipart()
        msg['From'] = self.email_settings.get('username')
        msg['To'] = self.email_settings.get('recipient')
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(self.email_settings.get('server'), int(self.email_settings.get('port')))
            server.starttls()
            server.login(self.email_settings.get('username'), self.email_settings.get('password'))
            server.sendmail(msg['From'], msg['To'], msg.as_string())
            server.quit()
            self.append_log("Email sent successfully.")
        except Exception as e:
            self.append_log(f"Failed to send email: {e}")




    # Aggiungi la configurazione per il report giornaliero
    def setup_daily_report(self):
        """Imposta l'invio del report delle ultime 24 ore alle 7:30 e 15:00."""
        now = datetime.now()
        next_7_30 = now.replace(hour=7, minute=30, second=0, microsecond=0)
        next_15_00 = now.replace(hour=15, minute=0, second=0, microsecond=0)

        if now >= next_7_30:
            next_7_30 += timedelta(days=1)
        if now >= next_15_00:
            next_15_00 += timedelta(days=1)

        # Timer per le 7:30
        self.timer_7_30 = QTimer(self)
        self.timer_7_30.timeout.connect(lambda: self.send_daily_log_report())
        self.timer_7_30.start(int((next_7_30 - now).total_seconds() * 1000))  # Conversione a intero

        # Timer per le 15:00
        self.timer_15_00 = QTimer(self)
        self.timer_15_00.timeout.connect(lambda: self.send_daily_log_report())
        self.timer_15_00.start(int((next_15_00 - now).total_seconds() * 1000))  # Conversione a intero

    def send_daily_log_report(self):
        """Invia il report giornaliero delle ultime 24 ore."""
        subject = "Daily Log Report"
        body = "Here are the logs for the last 24 hours:\n\n"

        # Estrai i log delle ultime 24 ore
        body += self.get_logs_last_24_hours()

        self._send_email(subject, body)

    def get_logs_last_24_hours(self):
        """Recupera i log delle ultime 24 ore dalla finestra log."""
        log_text = self.log_window.toPlainText()
        logs = log_text.splitlines()
        last_24_hours_logs = []
        now = datetime.now()

        for log in reversed(logs):
            try:
                log_time_str = log[1:9]  # Formato [HH:MM:SS]
                log_time = datetime.strptime(log_time_str, "%H:%M:%S").replace(
                    year=now.year, month=now.month, day=now.day
                )
                if log_time < now - timedelta(days=1):
                    break
                last_24_hours_logs.append(log)
            except ValueError:
                continue

        return "\n".join(reversed(last_24_hours_logs))

    # Modifica nella funzione perform_sync per usare la funzione aggiornata
    def perform_sync(self, direction):
        sftp_client = SftpClient(
            self.host_line_edit.text(),
            int(self.port_line_edit.text()),
            self.username_line_edit.text(),
            self.password_line_edit.text(),
            self.append_log
        )
        sftp_client.connect()

        files_transferred = []

        try:
            if direction == "to_remote":
                # Elenco dei file locali
                local_files = os.listdir(self.local_dir_line_edit.text())
                for file_name in local_files:
                    if file_name.startswith('.') or not file_name.strip():
                        self.append_log(f"Skipping hidden or invalid file: {file_name}")
                        continue

                    local_file_path = os.path.join(self.local_dir_line_edit.text(), file_name)
                    remote_file_path = os.path.join(self.remote_dir_line_edit.text(), file_name)

                    try:
                        sftp_client.upload_file(local_file_path, remote_file_path)
                        files_transferred.append(file_name)
                        self.append_log(f"Uploaded file: {local_file_path} to {remote_file_path}")

                        # Cancella il file locale dopo il trasferimento, se l'opzione è abilitata
                        if self.delete_after_transfer_checkbox.isChecked():
                            os.remove(local_file_path)
                            self.append_log(f"Deleted file {local_file_path} after upload.")
                    except Exception as e:
                        self.append_log(f"Failed to upload file {local_file_path}: {e}")

            else:  # Per "to_local"
                remote_files = sftp_client.list_files(self.remote_dir_line_edit.text())
                for remote_file in remote_files:
                    remote_file_name = getattr(remote_file, 'filename', None)
                    if not remote_file_name or remote_file_name.startswith('.'):
                        self.append_log(f"Skipping invalid or hidden file: {remote_file}")
                        continue

                    remote_file_path = os.path.join(self.remote_dir_line_edit.text(), remote_file_name)
                    local_path = os.path.join(self.local_dir_line_edit.text(), remote_file_name)

                    try:
                        sftp_client.download_file(remote_file_path, local_path)
                        files_transferred.append(remote_file_name)
                        self.append_log(f"Downloaded file: {remote_file_path} to {local_path}")

                        # Cancella il file remoto dopo il trasferimento, se l'opzione è abilitata
                        if self.delete_after_transfer_checkbox.isChecked():
                            sftp_client.delete_file(remote_file_path)
                            self.append_log(f"Deleted file {remote_file_path} after download.")
                    except Exception as e:
                        self.append_log(f"Failed to download file {remote_file_path}: {e}")

            # Invio email alla fine del trasferimento
            self.send_email_with_logs(files_transferred, direction)

        except Exception as e:
            self.append_log(f"Error during sync: {e}")

        finally:
            sftp_client.close()


    def filter_files(files):
        """Filtro per ignorare file nascosti."""
        return [file for file in files if not file.startswith('.')]


    def sync_only_new_files(self, direction):
        self.append_log("Transferring only new files added to the local directory...")
        src_dir = self.local_dir_line_edit.text()
        current_files = {f for f in os.listdir(src_dir) if not f.startswith('.') and f.strip()}
        new_files = current_files - self.existing_files

        if new_files:
            self.append_log(f"New files detected: {', '.join(new_files)}")
            if direction == "to_remote":
                self.perform_sync(direction)
        else:
            self.append_log("No new files found to transfer.")
        self.existing_files = current_files


        # Percorso per salvare i file già trasferiti
        transferred_files_path = "transferred_files.json"

        # Carica i file già trasferiti
        if os.path.exists(transferred_files_path):
            with open(transferred_files_path, 'r') as file:
                transferred_files = set(json.load(file))
        else:
            transferred_files = set()

        # Elenco dei file attualmente nella directory
        current_files = set(os.listdir(src_dir))
        new_files = current_files - transferred_files

        files_transferred = []
        try:
            if new_files:
                self.append_log(f"New files detected: {', '.join(new_files)}")
                sftp_client = SftpClient(
                    self.host_line_edit.text(), int(self.port_line_edit.text()),
                    self.username_line_edit.text(), self.password_line_edit.text(),
                    self.append_log
                )
                sftp_client.connect()

                if direction == "to_remote":
                    for file in new_files:
                        local_path = os.path.join(src_dir, file)
                        remote_path = os.path.join(self.remote_dir_line_edit.text(), file)
                        sftp_client.upload_file(local_path, remote_path)
                        files_transferred.append(file)
                elif direction == "to_local":
                    for file in new_files:
                        remote_path = os.path.join(self.remote_dir_line_edit.text(), file)
                        local_path = os.path.join(src_dir, file)
                        sftp_client.download_file(remote_path, local_path)
                        files_transferred.append(file)

                sftp_client.close()
                self.append_log(f"New files transferred: {', '.join(files_transferred)}")
            else:
                self.append_log("No new files found to transfer.")


            # Invia una mail sempre
            subject = "File Transfer Notification"
            if files_transferred:
                body = (
                    f"The following new files have been {'uploaded' if direction == 'to_remote' else 'downloaded'}:\n"
                    + "\n".join(files_transferred)
                )
            else:
                body = "No new files were transferred during the sync process."

            recent_logs = self.get_recent_logs()
            body += "\n\nRecent Logs:\n" + "\n".join(recent_logs)

            self._send_email(subject, body)
        except Exception as e:
            self.append_log(f"Error during transfer of new files: {e}")




    def local_to_local_transfer(self):
        try:
            src_dir = self.local_dir_line_edit.text()
            dest_dir = self.remote_dir_line_edit.text()
            
            # Verifica che le directory di origine e destinazione siano valide
            if not os.path.isdir(src_dir) or not os.path.isdir(dest_dir):
                self.append_log("Errore: directory di origine o destinazione non valida.")
                return
            
            self.append_log(f"Transferring files from {src_dir} to {dest_dir}...")

            files_transferred = []  # Lista per tenere traccia dei file trasferiti

            for file in os.listdir(src_dir):
                src_file = os.path.join(src_dir, file)
                dest_file = os.path.join(dest_dir, file)
                
                # Solo i file vengono trasferiti
                if os.path.isfile(src_file):
                    # Copia il file nella directory di destinazione
                    shutil.copy2(src_file, dest_file)
                    files_transferred.append(file)

            self.append_log(f"Files transferred: {', '.join(files_transferred)}")

            # Cancella i file dalla directory di origine solo se il trasferimento è completo
            if self.delete_after_transfer_checkbox.isChecked():
                for file in files_transferred:
                    src_file = os.path.join(src_dir, file)
                    os.remove(src_file)
                    self.append_log(f"Deleted file {file} from {src_dir}")

            self.append_log("Local to local transfer complete.")
        except Exception as e:
            self.append_log(f"Error during local to local transfer: {e}")

            if self.delete_after_transfer_checkbox.isChecked():
                for file in files_transferred:
                    try:
                        os.remove(os.path.join(self.local_dir_line_edit.text(), file))
                        self.append_log(f"Deleted file: {file}")
                    except Exception as e:
                        self.append_log(f"Failed to delete file {file}: {e}")



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

    def send_email(self, subject, body):
        if not self.email_settings:
            self.append_log("Email settings are not configured. Please set them up.")
            return

        msg = MIMEMultipart()
        msg['From'] = self.email_settings.get("username")
        msg['To'] = self.email_settings.get("recipient")
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(self.email_settings.get("server"), int(self.email_settings.get("port")))
            server.starttls()
            server.login(self.email_settings.get("username"), self.email_settings.get("password"))
            server.sendmail(msg['From'], msg['To'], msg.as_string())
            server.quit()
            self.append_log("Email sent successfully.")
        except Exception as e:
            self.append_log(f"Failed to send email: {e}")


    def clear_logs(self):
        self.log_window.clear()
        self.append_log("Log cleared.")

    #def append_log(self, message):
    #    current_time = datetime.now().strftime("%H:%M:%S")
    #    log_message = f"[{current_time}] {message}"
    #    self.log_window.appendPlainText(log_message)

    #gestione ottimizata dei log 
    def append_log(self, message):
        current_time = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{current_time}] {message}"

        # Aggiungi il nuovo log
        self.log_window.appendPlainText(log_message)

        # Limita a 500 righe
        max_lines = 500
        lines = self.log_window.toPlainText().splitlines()
        if len(lines) > max_lines:
            trimmed_text = '\n'.join(lines[-max_lines:])
            self.log_window.setPlainText(trimmed_text)
            self.log_window.moveCursor(Qt.TextCursor.End)


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
                "direction": "to_remote" if self.to_remote_button.isChecked() else ("to_local" if self.to_local_button.isChecked() else "local_to_local"),
                "delete_after_transfer": self.delete_after_transfer_checkbox.isChecked(),
                "transfer_new_files_only": self.transfer_new_files_only_checkbox.isChecked()
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
            elif config.get('direction') == "to_local":
                self.to_local_button.setChecked(True)
            else:
                self.to_local_local_button.setChecked(True)
            self.delete_after_transfer_checkbox.setChecked(config.get('delete_after_transfer', False))
            self.transfer_new_files_only_checkbox.setChecked(config.get('transfer_new_files_only', False))
            self.append_log("Configuration loaded from " + path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())


def _send_email(subject, body, email_settings):
    """Invia un'email utilizzando le impostazioni fornite."""
    msg = MIMEMultipart()
    msg['From'] = email_settings['username']
    msg['To'] = email_settings['recipient']
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(email_settings['server'], int(email_settings['port']))
        server.starttls()
        server.login(email_settings['username'], email_settings['password'])
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
        print("[LOG] Email inviata correttamente.")
    except Exception as e:
        print(f"[ERRORE] Invio email fallito: {e}")

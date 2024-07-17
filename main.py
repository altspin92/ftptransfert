import sys
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel,
                             QFileDialog, QMessageBox, QListWidget)
from sftp_client import SftpClient

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.upload_files)  # Connect the timer to the upload_files function
        self.timer.start(60000)  # Set the timer to run every minute (60000 ms)

    def initUI(self):
        layout = QVBoxLayout()

        self.host_label = QLabel("SFTP Host:")
        self.host_line_edit = QLineEdit()

        self.port_label = QLabel("SFTP Port:")
        self.port_line_edit = QLineEdit()
        self.port_line_edit.setText("22")  # Default port

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

        self.upload_button = QPushButton("Upload Now")
        self.test_conn_button = QPushButton("Test Connection")

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
        layout.addWidget(self.upload_button)
        layout.addWidget(self.test_conn_button)

        self.setLayout(layout)

        self.local_dir_button.clicked.connect(self.choose_local_directory)
        self.upload_button.clicked.connect(self.upload_files)
        self.test_conn_button.clicked.connect(self.test_connection)

    def choose_local_directory(self):
        dir = QFileDialog.getExistingDirectory(self, "Choose Directory", "",
                                               QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if dir:
            self.local_dir_line_edit.setText(dir)

    def upload_files(self):
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
            sftp_client = SftpClient(host, port, username, password)
            sftp_client.connect()
            print("Connection successful")

            successfully_uploaded_files = []

            for root, dirs, files in os.walk(local_dir):
                for file in files:
                    local_file = os.path.join(root, file)
                    remote_file = os.path.join(remote_dir, file).replace("\\", "/")
                    try:
                        sftp_client.upload_file(local_file, remote_file)
                        successfully_uploaded_files.append(local_file)
                        print(f"Uploaded: {local_file} to {remote_file}")
                    except Exception as e:
                        print(f"Failed to upload {local_file}: {e}")

            if successfully_uploaded_files:  # Check if files were uploaded
                for local_file in successfully_uploaded_files:
                    self.delete_local_file(local_file)

                files = sftp_client.list_files(remote_dir)
                self.file_list.clear()
                self.file_list.addItems(files)
                sftp_client.close()

                self.send_email(successfully_uploaded_files)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            print(f"Error: {e}")

    def delete_local_file(self, local_file):
        try:
            os.remove(local_file)
            print(f"Deleted local file: {local_file}")
        except Exception as e:
            print(f"Failed to delete local file {local_file}: {e}")

    def send_email(self, files_uploaded):
        sender_email = "info@hacklabmondovi.it"
        receiver_email = "it@bizpal.it"
        subject = "File Upload Notification"
        body = f"The following files have been uploaded successfully:\n\n" + "\n".join(files_uploaded)
        
        smtp_server = "mail.tophost.it"
        smtp_port = 587
        smtp_username = "hacklabmondovi.it75546"
        smtp_password = "Alt!!spin92"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
            server.quit()
            print("Email sent successfully")
        except smtplib.SMTPAuthenticationError:
            print("Failed to send email: Authentication error. Please check your email and password.")
        except Exception as e:
            print(f"Failed to send email: {e}")

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
    mainWin.setWindowTitle("SFTP File Upload")
    mainWin.resize(400, 400)
    mainWin.show()
    sys.exit(app.exec_())

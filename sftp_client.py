import os
import paramiko
import stat

class SftpClient:
    def __init__(self, host, port, username, password, log_callback=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.transport = None
        self.sftp = None
        self.log_callback = log_callback

    def connect(self):
        try:
            self.log("Attempting to establish SFTP connection...")
            self.transport = paramiko.Transport((self.host, self.port))
            self.transport.connect(username=self.username, password=self.password)
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)
            self.log("SFTP connection established")
        except paramiko.AuthenticationException:
            self.log("Authentication failed, please verify your credentials")
            raise
        except paramiko.SSHException as sshException:
            self.log(f"Unable to establish SSH connection: {sshException}")
            raise
        except Exception as e:
            self.log(f"Exception in connecting to the server: {e}")
            raise

    def upload_from_local_to_remote(self, local_dir, remote_dir):
        files_transferred = []
        try:
            self.log(f"Starting upload from {local_dir} to {remote_dir}")
            for file in os.listdir(local_dir):
                local_file = os.path.join(local_dir, file)
                remote_file = os.path.join(remote_dir, file.replace("\\", "/"))
                if os.path.isfile(local_file):  # Ensure only files are uploaded
                    self.upload_file(local_file, remote_file)
                    files_transferred.append(file)
                    os.remove(local_file)  # Delete the local file after successful upload
            self.log("File upload complete.")
        except Exception as e:
            self.log(f"Error during file upload: {e}")
            raise
        return files_transferred

    def synchronize_and_clear_remote(self, remote_dir, local_dir):
        files_transferred = []
        try:
            self.log(f"Starting synchronization from {remote_dir} to {local_dir}")
            files = self.list_files(remote_dir)  # Use list_files to get only files
            for file_attr in files:
                if isinstance(file_attr, paramiko.SFTPAttributes):  # Ensures correct object type
                    remote_file = os.path.join(remote_dir, file_attr.filename.replace("\\", "/"))
                    local_file = os.path.join(local_dir, file_attr.filename)
                    self.download_file(remote_file, local_file)
                    self.sftp.remove(remote_file)  # Remove the remote file after download
                    files_transferred.append(file_attr.filename)
            self.log("File synchronization and removal complete.")
        except Exception as e:
            self.log(f"Error during file synchronization: {e}")
            raise
        return files_transferred

    def list_files(self, remote_directory):
        """List only files in the specified remote directory."""
        files = []
        try:
            for entry in self.sftp.listdir_attr(remote_directory):
                self.log(f"Entry: {entry.filename}, Mode: {entry.st_mode}")
                if not stat.S_ISDIR(entry.st_mode):  # Include only files
                    files.append(entry)
        except Exception as e:
            self.log(f"Error listing files in {remote_directory}: {e}")
            raise
        return files

    def download_file(self, remote_file, local_file):
        try:
            self.log(f"Downloading {remote_file} to {local_file}")
            self.sftp.get(remote_file, local_file)
            self.log(f"Downloaded file: {remote_file} to {local_file}")
        except Exception as e:
            self.log(f"Failed to download file {remote_file}: {e}")
            raise

    def upload_file(self, local_file, remote_file):
        try:
            self.log(f"Uploading {local_file} to {remote_file}")
            self.sftp.put(local_file, remote_file)
            self.log(f"Uploaded file: {local_file} to {remote_file}")
        except Exception as e:
            self.log(f"Failed to upload file {local_file}: {e}")
            raise

    def remove_file(self, remote_file):
        try:
            self.log(f"Deleting remote file: {remote_file}")
            self.sftp.remove(remote_file)
            self.log(f"Deleted remote file: {remote_file}")
        except Exception as e:
            self.log(f"Failed to delete remote file {remote_file}: {e}")
            raise

    def close(self):
        if self.sftp:
            self.sftp.close()
        if self.transport:
            self.transport.close()
        self.log("SFTP connection closed")

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

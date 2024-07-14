import os
import paramiko

class SftpClient:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.transport = None
        self.sftp = None

    def connect(self):
        try:
            self.transport = paramiko.Transport((self.host, self.port))
            self.transport.connect(username=self.username, password=self.password)
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)
            print("SFTP connection established")
        except paramiko.AuthenticationException:
            print("Authentication failed, please verify your credentials")
            raise
        except paramiko.SSHException as sshException:
            print(f"Unable to establish SSH connection: {sshException}")
            raise
        except Exception as e:
            print(f"Exception in connecting to the server: {e}")
            raise

    def list_files(self, remote_dir):
        try:
            files = self.sftp.listdir(remote_dir)
            return files
        except IOError as e:
            print(f"Failed to list directory {remote_dir}: {e}")
            raise

    def download_file(self, remote_file, local_file):
        try:
            self.sftp.get(remote_file, local_file)
        except IOError as e:
            print(f"Failed to download file {remote_file}: {e}")
            raise

    def upload_file(self, local_file, remote_file):
        try:
            self.sftp.put(local_file, remote_file)
            print(f"Uploaded file: {local_file} to {remote_file}")
        except IOError as e:
            print(f"Failed to upload file {local_file}: {e}")
            raise

    def close(self):
        if self.sftp:
            self.sftp.close()
        if self.transport:
            self.transport.close()
        print("SFTP connection closed")

    def synchronize_and_clear_local(self, local_dir, remote_dir):
        # Upload files from local_dir to remote_dir
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_file = os.path.join(root, file)
                remote_file = os.path.join(remote_dir, file).replace("\\", "/")
                self.upload_file(local_file, remote_file)
                
        # Delete local files after upload
        self.clear_local_directory(local_dir)

    def clear_local_directory(self, local_dir):
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_file = os.path.join(root, file)
                try:
                    os.remove(local_file)
                    print(f"Deleted local file: {local_file}")
                except Exception as e:
                    print(f"Failed to delete local file {local_file}: {e}")

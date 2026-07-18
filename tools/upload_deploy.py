#!/usr/bin/env python3
"""Upload deploy.tar.gz to server and extract."""
import paramiko
import os

HOST = '***REMOVED***'
PORT = 22
USER = 'easykai'
PASS = '***REMOVED***'
REMOTE_DIR = '/home/easykai/easykai-workspace/easykai.cn/'
LOCAL_ARCHIVE = os.path.join(os.path.dirname(__file__), '..', 'deploy.tar.gz')

def main():
    local = os.path.abspath(LOCAL_ARCHIVE)
    print(f'Uploading {local} ({os.path.getsize(local)} bytes)...')

    transport = paramiko.Transport((HOST, PORT))
    transport.connect(username=USER, password=PASS)
    sftp = paramiko.SFTPClient.from_transport(transport)

    remote_path = os.path.join(REMOTE_DIR, 'deploy.tar.gz').replace('\\', '/')
    sftp.put(local, remote_path)

    print('Upload complete. Extracting...')

    ssh = transport.open_session()
    ssh.exec_command(f'cd {REMOTE_DIR} && tar -xzf deploy.tar.gz && rm deploy.tar.gz && echo "DONE"')
    exit_code = ssh.recv_exit_status()
    stdout = ssh.makefile('rb').read().decode()
    print(f'Extract result: exit={exit_code}, output={stdout}')

    sftp.close()
    transport.close()
    print('Deploy complete!')

if __name__ == '__main__':
    main()

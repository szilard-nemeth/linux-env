import getpass

import paramiko
import os
import sys

def get_ssh_client(hostname, username, password):
    """Establishes an SSH connection and returns the client object."""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh_client.connect(hostname, username=username, password=password)
        print(f"Successfully connected to {hostname}")
        return ssh_client
    except paramiko.AuthenticationException:
        print("Authentication failed. Check your username and password or SSH key.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def list_remote_files(ssh_client, case_number):
    """
    Lists files in the specified remote directory and returns a dictionary
    mapping a number to (file_type, filename).
    """
    remote_path = f"/case/{case_number}"
    command = f"ls -latr {remote_path}"

    stdin, stdout, stderr = ssh_client.exec_command(command)
    output = stdout.read().decode('utf-8').strip().split('\n')

    # Check for errors from the ls command
    err_output = stderr.read().decode('utf-8')
    if err_output:
        print(f"Error listing files: {err_output}")
        return {}

    result = {}
    idx = 0
    print(f"Files in {remote_path}:")
    for line in output[1:]:
        parts = line.split()
        if len(parts) > 8:
            file_permissions = parts[0]
            filename = " ".join(parts[8:])
            if filename not in ['.', '..']:
                print(f"[{idx}] {line}")
                if file_permissions.startswith('d'):
                    result[idx] = ("dir", filename)
                else:
                    result[idx] = ("file", filename)
                idx += 1

    return result

def download_files(ssh_client, filenames, case_number):
    """Downloads the specified files using SFTP."""
    transport = ssh_client.get_transport()
    sftp = paramiko.SFTPClient.from_transport(transport)

    remote_dir = f"/case/{case_number}"
    local_dir = f"./case_{case_number}"

    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    print("\nStarting download...")
    for filename in filenames:
        remote_path = os.path.join(remote_dir, filename)
        local_path = os.path.join(local_dir, filename)

        try:
            sftp.get(remote_path, local_path)
            print(f"✅ Downloaded '{filename}' to '{local_path}'")
        except FileNotFoundError:
            print(f"❌ Warning: Remote file '{filename}' not found.")
        except Exception as e:
            print(f"❌ Error downloading '{filename}': {e}")

    sftp.close()

def get_files_to_download():
    user_input = input("Your selection: ").strip().lower()

    files_to_download = []
    if user_input == 'all':
        files_to_download = [f[1] for f in files.values()]
    else:
        try:
            # Handle ranges (e.g., 1-5)
            if '-' in user_input:
                start, end = map(int, user_input.split('-'))
                if start > end:
                    start, end = end, start # Swap if order is incorrect
                for i in range(start, end + 1):
                    if i in files:
                        files_to_download.append(files[i][1])
            # Handle comma-separated list (e.g., 0,1,10)
            else:
                indices = [int(i.strip()) for i in user_input.split(',')]
                for i in indices:
                    if i in files:
                        files_to_download.append(files[i][1])
                    else:
                        print(f"Warning: Selection {i} is out of range.")

        except (ValueError, IndexError):
            print("Invalid input format. Please try again.")
            sys.exit(1)
    return files_to_download


if __name__ == '__main__':
    hostname = "casefiles.sjc.cloudera.com"
    username = "snemeth"
    case_number = "1131111"

    password = getpass.getpass('Enter your password: ')
    client = get_ssh_client(hostname, username, password)
    if not client:
        sys.exit(1)

    try:
        files = list_remote_files(client, case_number)

        if not files:
            print("No files found or an error occurred. Exiting.")
            sys.exit(0)

        # Get user input for download selection
        print("\nEnter the numbers of the files to download, separated by commas (e.g., 0,2,5).")
        print("You can also enter a range (e.g., 1-5) or 'all' to download everything.")

        files_to_download = get_files_to_download()
        if files_to_download:
            cwd = os.getcwd()
            # print("Target directory: " + cwd)
            download_files(client, files_to_download, case_number)
        else:
            print("No valid files selected for download. Exiting.")

    finally:
        client.close()
        print("SSH connection closed.")
import paramiko

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
    Lists files in the specified remote directory and returns a list of filenames.
    """
    remote_path = f"/case/{case_number}"
    command = f"ls -latr {remote_path}"

    stdin, stdout, stderr = ssh_client.exec_command(command)
    output = stdout.read().decode('utf-8').strip().split('\n')

    result = {}
    # Skip the header lines and process each file entry
    idx = 0
    for line in output[1:]:
        parts = line.split()
        if len(parts) > 8: # A simple way to filter valid file entries
            filename = " ".join(parts[8:]) # Re-join if filename contains spaces
            # if filename not in ['.', '..'] and not filename.startswith('d'):
            if filename not in ['.', '..']:
                print(f"[{idx}] {line}")
                if filename.startswith('d'):
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
    local_dir = f"./case_{case_number}" # Create a local directory for downloads

    # Ensure the local directory exists
    import os
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    for filename in filenames:
        remote_path = os.path.join(remote_dir, filename)
        local_path = os.path.join(local_dir, filename)

        try:
            sftp.get(remote_path, local_path)
            print(f"Downloaded '{filename}' to '{local_path}'")
        except FileNotFoundError:
            print(f"Warning: Remote file '{filename}' not found.")
        except Exception as e:
            print(f"Error downloading '{filename}': {e}")

    sftp.close()

if __name__ == '__main__':
    hostname = "casefiles.sjc.cloudera.com" # Replace with the actual hostname
    username = "snemeth"         # Replace with your username
    case_number = "1131111"

    password = input("password:")
    client = get_ssh_client(hostname, username, password)
    if not client:
        exit(1)
    try:
        files = list_remote_files(client, case_number)
        files_to_download = [files[0]]
        # download_files(client, files_to_download, case_number)
    finally:
        client.close()

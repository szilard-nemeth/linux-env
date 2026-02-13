import sys
from pathlib import Path

import click
import paramiko


def get_ssh_client(hostname, username, password):
    """Establishes an SSH connection and returns the client object."""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh_client.connect(hostname, username=username, password=password)
        click.secho(f"✅ Successfully connected to {hostname}", fg="green")
        return ssh_client
    except Exception as e:
        # except paramiko.AuthenticationException:
        click.secho(f"❌ Connection error: {e}", fg="red")
        return None


def list_remote_files(ssh_client, case_number):
    """Lists files and returns a map of index -> (type, filename)."""
    remote_path = f"/case/{case_number}"
    command = f"ls -latr {remote_path}"

    stdin, stdout, stderr = ssh_client.exec_command(command)
    output = stdout.read().decode("utf-8").strip().split("\n")

    # Check for errors from the ls command
    err_output = stderr.read().decode("utf-8")
    if err_output:
        click.secho(f"Error listing files: {err_output}", fg="red")
        return {}

    file_map = {}
    idx = 0
    click.echo(f"\nFiles in {remote_path}:")

    # Skip the 'total' line usually present in ls -l
    lines = output[1:] if output[0].startswith("total") else output

    for line in lines:
        parts = line.split()
        if len(parts) > 8:
            permissions = parts[0]
            filename = " ".join(parts[8:])
            if filename not in [".", ".."]:
                click.echo(f"[{idx}] {line}")
                ftype = "dir" if permissions.startswith("d") else "file"
                file_map[idx] = (ftype, filename)
                idx += 1
    return file_map


def parse_selection(user_input, file_map):
    """Parses 'all', ranges '1-5', or '1,2,3' into filenames."""
    selected_names = []
    user_input = user_input.strip().lower()

    if user_input == "all":
        return [data[1] for data in file_map.values()]

    try:
        if "-" in user_input:
            start, end = map(int, user_input.split("-"))
            indices = range(min(start, end), max(start, end) + 1)
        else:
            indices = [int(i.strip()) for i in user_input.split(",")]

        for i in indices:
            if i in file_map:
                selected_names.append(file_map[i][1])
            else:
                click.secho(f"⚠️  Warning: Index {i} is out of range.", fg="yellow")
    except ValueError:
        click.secho("❌ Invalid format. Use numbers, ranges (1-3), or 'all'.", fg="red")
        return None

    return selected_names


def download_files(ssh_client, filenames, case_number, local_dir):
    """Downloads files via SFTP."""
    transport = ssh_client.get_transport()
    sftp = paramiko.SFTPClient.from_transport(transport)

    remote_dir = f"/case/{case_number}"
    local_path_obj = Path(local_dir)
    local_path_obj.mkdir(parents=True, exist_ok=True)

    for filename in filenames:
        remote_path = f"{remote_dir}/{filename}"
        local_file_path = local_path_obj / filename

        def progress(seen, total):
            pct = (seen / total) * 100
            sys.stdout.write(f"\r  Downloading '{filename}': {pct:.2f}%")
            sys.stdout.flush()

        try:
            sftp.get(remote_path, str(local_file_path), callback=progress)
            click.echo(f"\r✅ Downloaded: {filename}")
        except Exception as e:
            click.echo(f"\r❌ Error downloading {filename}: {e}")

    sftp.close()


@click.command()
@click.argument("case_number")
@click.option("--target-dir", "-t", default=".", help="Local directory to save files.", type=click.Path())
@click.option("--user", "-u", default="snemeth", help="SSH Username.")
@click.option("--host", "-h", default="casefiles.sjc.cloudera.com", help="SSH Hostname.")
def main(case_number, target_dir, user, host):
    """CLI tool to download files from a remote case directory."""

    password = click.prompt(f"Enter SSH password for {user}", hide_input=True)

    client = get_ssh_client(host, user, password)
    if not client:
        sys.exit(1)

    try:
        file_map = list_remote_files(client, case_number)
        if not file_map:
            click.echo("No files found.")
            return

        click.echo("\nEnter selection (e.g., '0,2', '1-5', or 'all'):")
        user_selection = click.get_text_stream("stdin").readline()

        files_to_download = parse_selection(user_selection, file_map)

        if files_to_download:
            click.secho(f"📂 Target directory: {Path(target_dir).absolute()}", fg="cyan")
            download_files(client, files_to_download, case_number, target_dir)
        else:
            click.echo("No files selected. Goodbye!")

    finally:
        client.close()
        click.echo("SSH connection closed.")


if __name__ == "__main__":
    main()

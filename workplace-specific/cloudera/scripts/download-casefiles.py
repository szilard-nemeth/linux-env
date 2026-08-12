import os
import sys
import stat  # Added this import
from pathlib import Path

import click
import paramiko


def _apply_remote_mtime(local_path, attr):
    """Set the local file's atime/mtime to match the remote SFTPAttributes."""
    if attr is None or attr.st_mtime is None:
        return
    mtime = attr.st_mtime
    atime = attr.st_atime if attr.st_atime is not None else mtime
    try:
        os.utime(str(local_path), (atime, mtime))
    except OSError as e:
        click.secho(f"  WARN: could not set mtime on {local_path}: {e}", fg="yellow")


def _already_downloaded(local_path, attr):
    """A file counts as already downloaded if it exists locally with the same size."""
    p = Path(local_path)
    if not p.exists() or not p.is_file():
        return False
    if attr is None or attr.st_size is None:
        return p.exists()
    return p.stat().st_size == attr.st_size


def get_ssh_client(hostname, username, password):
    """Establishes an SSH connection and returns the client object."""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh_client.connect(hostname, username=username, password=password)
        click.secho(f"OK: Successfully connected to {hostname}", fg="green")
        return ssh_client
    except Exception as e:
        # except paramiko.AuthenticationException:
        click.secho(f"ERROR: Connection error: {e}", fg="red")
        return None


def sftp_walk(sftp, remote_path, local_path):
    """Recursively downloads a directory tree via SFTP."""
    # Ensure local directory exists
    Path(local_path).mkdir(parents=True, exist_ok=True)

    for item in sftp.listdir_attr(remote_path):
        r_path = f"{remote_path}/{item.filename}"
        l_path = Path(local_path) / item.filename

        # Check if it's a directory (using S_ISDIR on the mode attribute)
        if stat.S_ISDIR(item.st_mode):
            sftp_walk(sftp, r_path, l_path)
        else:
            if _already_downloaded(l_path, item):
                _apply_remote_mtime(l_path, item)
                click.echo(f"  SKIP (exists): {item.filename}      ")
                continue

            # Download file with progress
            def progress(seen, total):
                pct = (seen / total) * 100
                sys.stdout.write(f"\r  Downloading '{item.filename}': {pct:.2f}%")
                sys.stdout.flush()

            sftp.get(r_path, str(l_path), callback=progress)
            _apply_remote_mtime(l_path, item)
            click.echo(f"\r  OK: Saved: {item.filename}      ")


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

        try:
            attr = sftp.stat(remote_path)
        except IOError as e:
            click.echo(f"ERROR: could not stat {remote_path}: {e}")
            continue

        if _already_downloaded(local_file_path, attr):
            _apply_remote_mtime(local_file_path, attr)
            click.echo(f"SKIP (exists): {filename}")
            continue

        def progress(seen, total):
            pct = (seen / total) * 100
            sys.stdout.write(f"\r  Downloading '{filename}': {pct:.2f}%")
            sys.stdout.flush()

        try:
            sftp.get(remote_path, str(local_file_path), callback=progress)
            _apply_remote_mtime(local_file_path, attr)
            click.echo(f"\rOK: Downloaded: {filename}")
        except Exception as e:
            click.echo(f"\rERROR downloading {filename}: {e}")

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

        # Display files
        for i, (ftype, name) in file_map.items():
            prefix = "[DIR] " if ftype == "dir" else "      "
            click.echo(f"[{i}] {prefix}{name}")

        click.echo("\nEnter selection (e.g., '0,2', '1-5', or 'all'):")
        user_selection = click.get_text_stream("stdin").readline().strip().lower()

        # Determine which indices to download
        selected_indices = []
        if user_selection == "all":
            selected_indices = list(file_map.keys())
        elif "-" in user_selection:
            start, end = map(int, user_selection.split("-"))
            selected_indices = range(min(start, end), max(start, end) + 1)
        else:
            selected_indices = [int(i.strip()) for i in user_selection.split(",") if i.strip()]

        # Process downloads
        sftp = client.open_sftp()
        local_base = Path(target_dir).absolute()

        for idx in selected_indices:
            if idx not in file_map:
                continue
            ftype, name = file_map[idx]
            remote_p = f"/case/{case_number}/{name}"
            local_p = local_base / name

            if ftype == "dir":
                click.secho(f"\nRecursively downloading directory: {name}", fg="cyan")
                sftp_walk(sftp, remote_p, local_p)
            else:
                try:
                    attr = sftp.stat(remote_p)
                except IOError as e:
                    click.secho(f"ERROR: could not stat {remote_p}: {e}", fg="red")
                    continue

                if _already_downloaded(local_p, attr):
                    _apply_remote_mtime(local_p, attr)
                    click.echo(f"SKIP (exists): {name}")
                    continue

                click.echo(f"Downloading file: {name}")
                sftp.get(remote_p, str(local_p))
                _apply_remote_mtime(local_p, attr)

        sftp.close()
        click.secho("\nOK: All downloads complete.", fg="green")
    finally:
        client.close()
        click.echo("SSH connection closed.")


if __name__ == "__main__":
    main()

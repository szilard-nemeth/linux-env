import subprocess
import tempfile
import shutil
import os
import argparse
import sys


# TODO Migrate sync-kb-private-repo.sh
# TODO Migrate sync-linux-env-repo.sh
# TODO Migrate sync-yarn-dev-tools-repo.sh

def run_command(command, cwd=None):
    """Utility to run shell commands and handle errors."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            capture_output=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing: {' '.join(command)}")
        print(f"Stderr: {e.stderr}")
        sys.exit(1)


def sync_repository(source_url, mirror_url, source_branch, target_branch, force_cleanup):
    # Create a temporary directory
    tmp_dir = tempfile.mkdtemp(prefix="repo-sync-")
    repo_path = os.path.join(tmp_dir, "repo")

    print(f"--> Using temporary directory: {tmp_dir}")

    try:
        # 1. Clone Source
        print(f"--> Cloning {source_url}...")
        run_command(["git", "clone", source_url, repo_path])

        # 2. Checkout Branch
        print(f"--> Checking out branch: {source_branch}")
        run_command(["git", "checkout", source_branch], cwd=repo_path)

        # 3. Add Mirror Remote
        print(f"--> Adding mirror remote: {mirror_url}")
        run_command(["git", "remote", "add", "mirror", mirror_url], cwd=repo_path)

        # 4. Push to Mirror
        print(f"--> Pushing {source_branch} to mirror {target_branch}...")
        # Using -f for force push as per original script
        run_command(["git", "push", "-f", "mirror", f"{source_branch}:{target_branch}", "--tags"], cwd=repo_path)

        print("\n✅ Sync successful!")

    finally:
        # Cleanup Logic
        if force_cleanup:
            print(f"--> Automatically removing: {tmp_dir}")
            shutil.rmtree(tmp_dir)
        else:
            confirm = input(f"\nOK to remove directory: {tmp_dir}? (y/n): ").lower()
            if confirm == 'y':
                shutil.rmtree(tmp_dir)
                print("Directory removed.")
            else:
                print(f"Directory preserved at: {tmp_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync a Git repository to a mirror.")

    # Parameters
    parser.add_argument("--source", help="Source Repo URL", required=True)
    parser.add_argument("--mirror", help="Mirror Repo URL", required=True)
    parser.add_argument("--source-branch", help="Source branch to sync", required=True)
    parser.add_argument("--target-branch", help="Target branch on mirror", required=True)
    parser.add_argument("--force", action="store_true", help="Skip cleanup confirmation", required=True)

    args = parser.parse_args()

    sync_repository(
        source_url=args.source,
        mirror_url=args.mirror,
        source_branch=args.source_branch,
        target_branch=args.target_branch,
        force_cleanup=args.force
    )

import subprocess
import os
import tempfile
from pathlib import Path
import humanfriendly

DEVELOPMENT_ROOT = Path(os.path.expanduser("~/development"))


def get_dir_size(path):
    """Calculates total size of a directory in bytes natively."""
    path = Path(path)
    if not path.exists():
        return 0
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    except (PermissionError, OSError):
        pass
    return total


def get_mvn_target_dirs(size_limit="100M"):
    byte_limit = humanfriendly.parse_size(size_limit)
    found = []
    # Using rglob to find all target folders
    for p in DEVELOPMENT_ROOT.rglob("target"):
        if p.is_dir():
            size = get_dir_size(p)
            if size >= byte_limit:
                found.append({"path": str(p), "before": size})
    return found


def format_du_style(size_in_bytes):
    """Formats bytes to 1.2G, 400M, etc. using humanfriendly 10.0"""
    # Use binary=True to get 1024-base (MiB/GiB)
    readable = humanfriendly.format_size(size_in_bytes, binary=True)

    # Logic to match 'du -sh' output style:
    # 1. Remove the 'iB' (making GiB -> G, MiB -> M)
    # 2. Remove the space
    return readable.replace("iB", "").replace(" ", "")


def parse_to_bytes(size_str):
    """Converts du human-readable strings to bytes using humanfriendly."""
    # binary=True ensures 'M' is treated as 1024^2 (MiB) and 'G' as 1024^3 (GiB)
    # This matches the 'du -sh' behavior on macOS/Linux.
    return humanfriendly.parse_size(size_str, binary=True)


def get_project_root(path):
    """
    Finds the directory containing the top-level pom.xml.
    Ascends from the /target folder until it finds a pom or hits the dev root.
    """
    current = Path(path).parent
    project_root = current
    while str(current) != str(DEVELOPMENT_ROOT) and str(current) != "/":
        if (current / "pom.xml").exists():
            project_root = current
        current = current.parent
    return project_root


def main():
    print("--- 1. Scanning for heavy mvn target directories ---")
    targets = get_mvn_target_dirs("100M")

    if not targets:
        print("No heavy targets found.")
        return

    # Map target paths to their project roots to avoid redundant 'mvn clean' calls
    root_to_targets = {}
    for t in targets:
        root = str(get_project_root(t["path"]))
        if root not in root_to_targets:
            root_to_targets[root] = []
        root_to_targets[root].append(t)
        print(f"Found {format_du_style(t['before'])}: {t['path']}")

    # Create a temporary log file
    log_path = Path(tempfile.gettempdir()) / "maven_clean.log"
    print(f"\n--- 2. Executing maven clean (Logging to: {log_path}) ---")
    with open(log_path, "w") as log_file:
        for root in sorted(root_to_targets.keys()):
            print(f"Cleaning Project: {root}")
            cmd = ["mvn", "clean", "-f", os.path.join(root, "pom.xml")]

            # Write start marker to log
            log_file.write(f"\n{'='*20}\nCLEANING: {root}\n{'='*20}\n")
            log_file.flush()

            # Execute Maven
            result = subprocess.run(cmd, stdout=log_file, stderr=log_file)
            if result.returncode == 0:
                print("✅ Done.")
            else:
                print("❌ Failed (Check log).")

    print("\n--- 3. Verifying reclaimed space ---")
    total_reclaimed = 0

    for t in targets:
        after_size = get_dir_size(t["path"])  # Will be 0 if folder was deleted
        reclaimed = t["before"] - after_size
        total_reclaimed += reclaimed

        status = "DELETED" if not os.path.exists(t["path"]) else f"REDUCED TO {format_du_style(after_size)}"
        print(f"Target: {t['path']}")
        print(f"  {format_du_style(t['before'])} -> {status} (Saved {format_du_style(reclaimed)})")

    print("\n--- FINAL SUMMARY ---")
    print(f"Total Projects Cleaned: {len(root_to_targets)}")
    print(f"Actual Space Reclaimed: {format_du_style(total_reclaimed)}")
    print(f"Log file available at: {log_path}")


if __name__ == "__main__":
    main()

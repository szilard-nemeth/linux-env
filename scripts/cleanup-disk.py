import subprocess
import os
import re
from pathlib import Path

import humanfriendly

DEVELOPMENT_ROOT = Path(os.path.expanduser("~/development"))

def get_dir_size(path):
    """Calculates total size of a directory in bytes natively."""
    total = 0
    try:
        # scan_dir is much faster than os.listdir or rglob for size calculation
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += get_dir_size(entry.path)
    except (PermissionError, OSError):
        pass # Handle those 700 permission dirs gracefully
    return total

def get_mvn_target_dirs(size_limit="100M"):
    # humanfriendly.parse_size() handles M, G, GiB, etc. automatically
    byte_limit = humanfriendly.parse_size(size_limit)
    results = []

    for p in DEVELOPMENT_ROOT.rglob("target"):
        if p.is_dir():
            size_in_bytes = get_dir_size(p)
            if size_in_bytes >= byte_limit:
                # format_size() turns it back into '1.2 GB'
                results.append([format_du_style(size_in_bytes), str(p)])

    return results

def format_du_style(size_in_bytes):
    """Formats bytes to 1.2G, 400M, etc. using humanfriendly 10.0"""
    # Use binary=True to get 1024-base (MiB/GiB)
    readable = humanfriendly.format_size(size_in_bytes, binary=True)

    # Logic to match 'du -sh' output style:
    # 1. Remove the 'iB' (making GiB -> G, MiB -> M)
    # 2. Remove the space
    return readable.replace('iB', '').replace(' ', '')

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
    current = os.path.dirname(path)
    project_root = current
    while current != str(DEVELOPMENT_ROOT):
        if os.path.exists(os.path.join(current, "pom.xml")):
            project_root = current
        current = os.path.dirname(current)
    return project_root

def main():
    print("--- 1. Logging heavy mvn target directories ---")
    targets = get_mvn_target_dirs()
    if not targets:
        print("No mvn targets > 100MB found.")
        return

    total_reclaimed_bytes = 0
    projects_to_clean = set()

    for size_str, path in targets:
        print(f"Found {size_str} in {path}")
        total_reclaimed_bytes += parse_to_bytes(size_str)
        projects_to_clean.add(get_project_root(path))

    print("\n--- 2. Executing maven clean commands ---")
    executed_commands = []
    for project in sorted(projects_to_clean):
        cmd = ["mvn", "clean", "-f", os.path.join(project, "pom.xml")]
        print(f"Executing: {' '.join(cmd)}")
        executed_commands.append(" ".join(cmd))

        # Run the clean
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("\n--- 3. Final Summary ---")
    print(f"Total commands executed: {len(executed_commands)}")
    reclaimed_gb = total_reclaimed_bytes / (1024**3)
    print(f"Total space reclaimed: {reclaimed_gb:.2f} GiB")

    print("\n--- 4. Verification ---")
    remaining = get_mvn_target_dirs()
    if not remaining:
        print("Verification Success: No results > 100MB found.")
    else:
        print(f"Warning: {len(remaining)} targets still remain above 100MB.")

if __name__ == "__main__":
    main()